#!/usr/bin/env bash
# AIHelms 服务器迁移 - 数据库导出/导入
#
# 平台数据（aihelms schema）与 LiteLLM 数据（public schema）在同一个库，一次导出即可整体迁移。
# 需在部署目录下保留本脚本路径 docker/db/server-migrate.sh，任意目录执行均可。
#
#   旧服务器: bash docker/db/server-migrate.sh export [输出目录]          # 生成 aihelms-db-<时间>.tar
#   新服务器: bash docker/db/server-migrate.sh import <aihelms-db-xxx.tar>
#   新服务器: bash docker/db/server-migrate.sh rollback   # 恢复为导入前的库
#   新服务器: bash docker/db/server-migrate.sh cleanup    # 验证无误后删除导入前的备份库
#
# 前提：.env 已就位（新服务器需先复制旧服务器的 .env），且与旧服务器的 POSTGRES_* 一致。
set -Eeuo pipefail

# 路径参数相对执行时所在目录解析
PATH_ARG=""
[[ -n "${2:-}" ]] && PATH_ARG=$(realpath -m "$2")

cd "$(dirname "$0")/../.."

APP_SERVICES_PATTERN='^(nginx|aihelms|litellm)$'
STEP=0
TOTAL_STEPS=0
ON_ERROR_ACTION=""
WORK_DIR=""
DUMP_NAME=aihelms.dump

info() { printf '\033[36m  %s\033[0m\n' "$*"; }
ok() { printf '\033[32m  ✔ %s\033[0m\n' "$*"; }
warn() { printf '\033[33m  ! %s\033[0m\n' "$*"; }
die() { printf '\033[31m  ✘ %s\033[0m\n' "$*" >&2; exit 1; }
step() { STEP=$((STEP + 1)); printf '\n\033[1m[%d/%d] %s\033[0m\n' "$STEP" "$TOTAL_STEPS" "$*"; }
confirm() { local answer; read -r -p "  $1 [y/N] " answer; [[ "$answer" =~ ^[Yy]$ ]]; }

env_get() {
    local value
    value=$(grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '\r' || true)
    value="${value%\"}"
    value="${value#\"}"
    echo "${value:-$2}"
}

[[ -f docker-compose.yml ]] || die "未找到 docker-compose.yml，请确认脚本位于部署目录的 docker/db/ 下"
[[ -f .env ]] || die "未找到 .env，请先把旧服务器的 .env 复制到 $(pwd)"

DB_USER=$(env_get POSTGRES_USER aihelms)
DB_NAME=$(env_get POSTGRES_DB aihelms)
AIHELMS_VERSION=$(env_get AIHELMS_VERSION latest)

psql_admin() { docker compose exec -T db psql -U "$DB_USER" -d postgres -v ON_ERROR_STOP=1 -q "$@"; }

running_app_services() {
    docker compose ps --services --status running | grep -E "$APP_SERVICES_PATTERN" || true
}

wait_db() {
    local attempt
    # 走 TCP 检测：空卷首次启动时 init.sql 由只监听 socket 的临时实例执行，避免与其抢跑
    for attempt in $(seq 1 60); do
        docker compose exec -T db pg_isready -h 127.0.0.1 -U "$DB_USER" -q </dev/null && return 0
        sleep 2
    done
    die "数据库 120 秒内未就绪，请检查: docker compose logs db"
}

db_exists() {
    [[ "$(psql_admin -At -v db="$1" <<<"SELECT 1 FROM pg_database WHERE datname = :'db'")" == "1" ]]
}

terminate_connections() {
    psql_admin -v db="$1" >/dev/null <<'SQL'
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :'db' AND pid <> pg_backend_pid();
SQL
}

rename_database() {
    terminate_connections "$1"
    psql_admin -v from="$1" -v to="$2" <<<'ALTER DATABASE :"from" RENAME TO :"to";'
}

drop_database() {
    terminate_connections "$1"
    psql_admin -v db="$1" <<<'DROP DATABASE IF EXISTS :"db";'
}

list_backups() {
    psql_admin -At -v pattern="${DB_NAME}_premigrate_%" \
        <<<"SELECT datname FROM pg_database WHERE datname LIKE :'pattern' ORDER BY datname DESC"
}

# 输出 "schema.table|行数"，用于导出/导入两端核对
count_rows() {
    docker compose exec -T db psql -U "$DB_USER" -d "$1" -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT n.nspname || '.' || c.relname || '|' ||
       (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I', n.nspname, c.relname), false, true, '')))[1]::text
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY 1;
SQL
}

# 每张表数据量（不含索引），作为进度权重；行数差异大的表按字节估算更接近真实耗时
table_sizes() {
    docker compose exec -T db psql -U "$DB_USER" -d "$1" -At -v ON_ERROR_STOP=1 <<'SQL'
SELECT n.nspname || '.' || c.relname || '|' || pg_table_size(c.oid)
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind = 'r' AND n.nspname NOT IN ('pg_catalog', 'information_schema') AND n.nspname NOT LIKE 'pg_toast%'
ORDER BY 1;
SQL
}

declare -A TABLE_ROWS=() TABLE_WEIGHT=()
TOTAL_WEIGHT=0
SPINNER=(⠋ ⠙ ⠹ ⠸ ⠼ ⠴ ⠦ ⠧ ⠇ ⠏)

load_weights() {
    local name value
    [[ -f "$1" ]] || return 0
    while IFS='|' read -r name value; do TABLE_ROWS[$name]=$value; TABLE_WEIGHT[$name]=$value; done <"$1"
    if [[ -f "$2" ]]; then
        while IFS='|' read -r name value; do TABLE_WEIGHT[$name]=$value; done <"$2"
    fi
    for name in "${!TABLE_WEIGHT[@]}"; do TOTAL_WEIGHT=$((TOTAL_WEIGHT + TABLE_WEIGHT[$name])); done
}

# 当前 COPY 已处理行数（PG14+ pg_stat_progress_copy），用于大表内部进度
copied_tuples() {
    local value
    value=$(psql_admin -At -v db="$DB_NAME" 2>/dev/null \
        <<<"SELECT coalesce(max(tuples_processed), 0) FROM pg_stat_progress_copy WHERE datname = :'db'" || true)
    [[ "$value" =~ ^[0-9]+$ ]] && echo "$value" || echo 0
}

render_progress() {
    local done_weight=$1 table=$2 copied=$3 label=$4 extra=$5 tick=$6
    local rows=0 weight=0 percent bar rest elapsed=$((SECONDS - PROGRESS_START))
    if [[ -n "$table" ]]; then
        rows=${TABLE_ROWS[$table]:-0}
        weight=${TABLE_WEIGHT[$table]:-0}
    fi
    if ((rows > 0)); then
        ((copied < rows)) || copied=$rows
        done_weight=$((done_weight + weight * copied / rows))
    fi
    percent=$((TOTAL_WEIGHT > 0 ? done_weight * 100 / TOTAL_WEIGHT : 0))
    ((percent <= 100)) || percent=100
    printf -v bar '%*s' $((percent * 25 / 100)) ''
    printf -v rest '%*s' $((25 - percent * 25 / 100)) ''
    printf '\r\033[K  %s [%s%s] %3d%%  %s  %s用时 %02d:%02d' "${SPINNER[tick % 10]}" "${bar// /█}" "${rest// /░}" \
        "$percent" "${label:0:48}" "$extra" $((elapsed / 60)) $((elapsed % 60))
}

# 读取 pg_dump / pg_restore 的 -v 输出；无新输出时每秒刷新一次大表内部进度
show_progress() {
    local total=$1 pattern=$2 size_file=${3:-} done_count=0 done_weight=0 table="" label="准备中" line=""
    local chunk status copied=0 tick=0 extra=""
    PROGRESS_START=$SECONDS
    while true; do
        status=0
        IFS= read -r -t 1 chunk || status=$?
        line+=$chunk
        if ((status == 0)); then
            if [[ "$line" == *"$pattern"* ]]; then
                [[ -z "$table" ]] || done_weight=$((done_weight + ${TABLE_WEIGHT[$table]:-0}))
                table=${line##*"$pattern" }
                table=${table//\"/}
                done_count=$((done_count + 1))
                copied=0
                label="$done_count/$total $table"
            elif ((done_count > 0)) && [[ "$line" == *"creating INDEX"* || "$line" == *"CONSTRAINT"* ]]; then
                done_weight=$TOTAL_WEIGHT
                table=""
                label="数据已导入，正在重建索引"
            elif [[ "$line" == *"error"* ]]; then
                printf '\r\033[K'
                warn "$line"
            fi
            line=""
        elif ((status > 128)); then
            [[ -z "$table" ]] || copied=$(copied_tuples)
        else
            break
        fi
        [[ -z "$size_file" || ! -f "$size_file" ]] || extra="已写入 $(du -h "$size_file" | cut -f1)  "
        tick=$((tick + 1))
        render_progress "$done_weight" "$table" "$copied" "$label" "$extra" "$tick"
    done
    printf '\r\033[K'
}

on_exit() {
    local status=$1
    if [[ $status -ne 0 && -n "$ON_ERROR_ACTION" ]]; then
        printf '\n'
        warn "执行中断（退出码 $status）"
        "$ON_ERROR_ACTION"
    fi
    [[ -z "$WORK_DIR" ]] || rm -rf "$WORK_DIR"
}
trap 'on_exit $?' EXIT

STOPPED_SERVICES=()

hint_restart_services() {
    [[ ${#STOPPED_SERVICES[@]} -gt 0 ]] || return 0
    warn "导出未完成，已停止的服务未恢复。确认要恢复旧服务器业务请执行:"
    warn "  docker compose start ${STOPPED_SERVICES[*]}"
}

cmd_export() {
    local out_dir=${1:-$(pwd)} package dump_file total_tables
    mkdir -p "$out_dir"
    package="$out_dir/aihelms-db-$(date +%Y%m%d-%H%M%S).tar"
    WORK_DIR=$(mktemp -d "$out_dir/.aihelms-export-XXXXXX")
    dump_file="$WORK_DIR/$DUMP_NAME"
    TOTAL_STEPS=6

    step "检查环境"
    docker compose ps --services --status running | grep -qx db || die "db 服务未运行，请先 docker compose up -d db"
    info "数据库: $DB_NAME  用户: $DB_USER  镜像版本: $AIHELMS_VERSION"
    total_tables=$(count_rows "$DB_NAME" | wc -l)
    ok "共 $total_tables 张表"

    step "停止写入（可选）"
    mapfile -t STOPPED_SERVICES < <(running_app_services)
    if [[ ${#STOPPED_SERVICES[@]} -gt 0 ]] && confirm "正式切换请选 y：停止 ${STOPPED_SERVICES[*]}，保证导出期间无新数据写入。演练选 N 不停机"; then
        ON_ERROR_ACTION=hint_restart_services
        docker compose stop "${STOPPED_SERVICES[@]}" </dev/null
        ok "已停止，旧服务器业务暂停中"
    else
        STOPPED_SERVICES=()
        warn "不停机导出：导出期间产生的新调用日志不会包含在内，仅适合演练"
    fi

    step "记录各表行数"
    count_rows "$DB_NAME" >"$dump_file.rows"
    table_sizes "$DB_NAME" >"$dump_file.sizes"
    load_weights "$dump_file.rows" "$dump_file.sizes"
    ok "已记录"

    step "导出数据库"
    docker compose exec -T db pg_dump -U "$DB_USER" -d "$DB_NAME" -Fc -v </dev/null 2>&1 >"$dump_file" \
        | show_progress "$total_tables" "dumping contents of table" "$dump_file"
    ok "导出完成 $(du -h "$dump_file" | cut -f1)"

    step "校验导出文件"
    docker compose exec -T db pg_restore -l <"$dump_file" >/dev/null || die "导出文件损坏: $dump_file"
    cat >"$dump_file.meta" <<META
AIHELMS_VERSION=$AIHELMS_VERSION
POSTGRES_DB=$DB_NAME
EXPORTED_AT=$(date '+%F %T')
SHA256=$(sha256sum "$dump_file" | cut -d' ' -f1)
META
    ok "校验通过"

    # dump 本身已压缩，打包不再 gzip，避免多花时间
    step "打包"
    tar -cf "$package" -C "$WORK_DIR" "$DUMP_NAME" "$DUMP_NAME.rows" "$DUMP_NAME.sizes" "$DUMP_NAME.meta"
    ok "已生成 $package ($(du -h "$package" | cut -f1))"
    ON_ERROR_ACTION=""

    printf '\n\033[32m导出完成。把压缩包拷到新服务器后执行：\033[0m\n'
    printf '  bash docker/db/server-migrate.sh import %s\n' "$(basename "$package")"
    if [[ ${#STOPPED_SERVICES[@]} -gt 0 ]]; then
        warn "旧服务器 ${STOPPED_SERVICES[*]} 仍处于停止状态。切换失败需回退旧服务器时执行:"
        warn "  docker compose start ${STOPPED_SERVICES[*]}"
    fi
}
BACKUP_DB=""

restore_backup() {
    info "停止应用服务并恢复数据库 $BACKUP_DB → $DB_NAME"
    docker compose stop nginx aihelms litellm </dev/null >/dev/null 2>&1 || true
    drop_database "$DB_NAME"
    rename_database "$BACKUP_DB" "$DB_NAME"
    ok "已恢复为导入前的数据库"
}

auto_rollback() {
    [[ -n "$BACKUP_DB" ]] || return 0
    warn "开始自动回滚"
    restore_backup
    warn "导入失败，新服务器数据库已回到导入前状态，应用服务保持停止。排查后可重新执行 import"
}

check_dump_meta() {
    local meta_file=$1.meta expected_sha dump_version
    if [[ ! -f "$meta_file" ]]; then
        warn "未找到 $meta_file，跳过完整性与版本校验"
        return 0
    fi
    info "文件导出时间: $(grep '^EXPORTED_AT=' "$meta_file" | cut -d= -f2-)"
    expected_sha=$(grep '^SHA256=' "$meta_file" | cut -d= -f2)
    info "校验 SHA256（大文件需要一点时间）..."
    [[ "$(sha256sum "$1" | cut -d' ' -f1)" == "$expected_sha" ]] || die "SHA256 不一致，文件在传输中损坏，请重新拷贝"
    ok "文件完整"
    dump_version=$(grep '^AIHELMS_VERSION=' "$meta_file" | cut -d= -f2)
    if [[ "$dump_version" != "$AIHELMS_VERSION" ]]; then
        warn "版本不一致：旧服务器 $dump_version，新服务器 .env 为 $AIHELMS_VERSION"
        confirm "建议先改 .env 的 AIHELMS_VERSION 与旧服务器一致，迁移后再升级。仍要继续？" || die "已取消"
    fi
}

verify_row_counts() {
    local rows_file=$1.rows mismatch
    if [[ ! -f "$rows_file" ]]; then
        warn "未找到 $rows_file，跳过行数核对"
        return 0
    fi
    mismatch=$(diff <(sort "$rows_file") <(count_rows "$DB_NAME" | sort) || true)
    if [[ -z "$mismatch" ]]; then
        ok "$(wc -l <"$rows_file") 张表行数与旧服务器一致"
        return 0
    fi
    warn "以下表行数不一致（< 旧服务器  > 新服务器）："
    printf '%s\n' "$mismatch" | grep -E '^[<>]' | sed 's/^/    /'
    warn "不停机导出时属正常现象（导出期间仍有写入）"
    confirm "是否继续？选 N 将自动回滚" || die "用户取消"
}
cmd_import() {
    local package=${1:-} dump_file total_tables
    [[ -n "$package" ]] || die "用法: $0 import <aihelms-db-xxx.tar>"
    [[ -f "$package" ]] || die "文件不存在: $package"
    TOTAL_STEPS=6

    step "解包并校验"
    WORK_DIR=$(mktemp -d "$(dirname "$package")/.aihelms-import-XXXXXX")
    tar -xf "$package" -C "$WORK_DIR" || die "压缩包损坏: $package"
    dump_file="$WORK_DIR/$DUMP_NAME"
    [[ -f "$dump_file" ]] || die "压缩包中没有 $DUMP_NAME，请确认是 export 生成的文件"
    check_dump_meta "$dump_file"

    step "启动数据库"
    docker compose up -d db </dev/null
    wait_db
    docker compose exec -T db pg_restore -l <"$dump_file" >/tmp/aihelms-restore.list || die "导出文件无法读取: $dump_file"
    total_tables=$(grep -c ' TABLE DATA ' /tmp/aihelms-restore.list || true)
    rm -f /tmp/aihelms-restore.list
    ok "数据库就绪，待导入 $total_tables 张表"

    step "停止应用服务并备份当前库"
    if db_exists "$DB_NAME"; then
        info "当前库 $DB_NAME 现有 $(count_rows "$DB_NAME" | wc -l) 张表，将重命名保留用于回滚"
    fi
    confirm "导入会替换新服务器上的 $DB_NAME 库（旧库改名保留，不删除），继续？" || die "已取消"
    docker compose stop nginx aihelms litellm </dev/null >/dev/null 2>&1 || true
    ON_ERROR_ACTION=auto_rollback
    if db_exists "$DB_NAME"; then
        BACKUP_DB="${DB_NAME}_premigrate_$(date +%Y%m%d%H%M%S)"
        rename_database "$DB_NAME" "$BACKUP_DB"
        ok "当前库已备份为 $BACKUP_DB"
    fi
    psql_admin -v db="$DB_NAME" -v owner="$DB_USER" <<<'CREATE DATABASE :"db" OWNER :"owner";'

    step "导入数据"
    load_weights "$dump_file.rows" "$dump_file.sizes"
    docker compose exec -T db pg_restore -U "$DB_USER" -d "$DB_NAME" --no-owner --exit-on-error -v <"$dump_file" 2>&1 \
        | show_progress "$total_tables" "processing data for table"
    docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" -q -c "ANALYZE;" </dev/null
    ok "导入完成"

    step "核对行数"
    verify_row_counts "$dump_file"
    ON_ERROR_ACTION=""

    step "启动全部服务"
    docker compose up -d </dev/null
    ok "服务已启动（aihelms 启动时会自动执行增量迁移）"

    printf '\n\033[32m导入完成。请验证：\033[0m\n'
    printf '  1. 登录管理后台，查看模型、供应商、AI 身份 Key 数据\n'
    printf '  2. 用一个已有用户 Key 调用新服务器 LiteLLM，确认供应商 Key 能正常解密\n'
    printf '  3. docker compose logs -f aihelms 无报错\n'
    printf '有问题回滚: bash docker/db/server-migrate.sh rollback\n'
    printf '确认无误后释放空间: bash docker/db/server-migrate.sh cleanup\n'
}

cmd_rollback() {
    TOTAL_STEPS=2
    step "查找备份库"
    BACKUP_DB=$(list_backups | head -1)
    [[ -n "$BACKUP_DB" ]] || die "没有找到 ${DB_NAME}_premigrate_* 备份库"
    info "将恢复: $BACKUP_DB"
    warn "导入之后在新服务器产生的数据（新的调用日志、配置修改）会被丢弃"
    confirm "确认回滚？" || die "已取消"

    step "恢复数据库"
    restore_backup
    docker compose up -d </dev/null
    ok "回滚完成，服务已启动"
}

cmd_cleanup() {
    local backups db
    mapfile -t backups < <(list_backups)
    [[ ${#backups[@]} -gt 0 ]] || { ok "没有需要清理的备份库"; return 0; }
    info "导入前备份库: ${backups[*]}"
    warn "删除后将无法再执行 rollback"
    confirm "确认删除？" || die "已取消"
    for db in "${backups[@]}"; do
        drop_database "$db"
        ok "已删除 $db"
    done
}

case "${1:-}" in
    export) cmd_export "$PATH_ARG" ;;
    import) cmd_import "$PATH_ARG" ;;
    rollback) cmd_rollback ;;
    cleanup) cmd_cleanup ;;
    *) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
