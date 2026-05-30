# 企业集成设计

> 本文档详细描述 AIHelms 对接企业 OA（企业微信）的技术方案。具体实施方案待后续详细设计。

## 目标

通过对接企业微信，实现：
1. **SSO 单点登录** — 企业微信 OAuth 2.0 认证，员工免密登录平台
2. **用户同步** — 企业微信通讯录用户自动同步到平台
3. **部门同步** — 企业微信部门层级结构同步到平台
4. **项目同步** — 企业微信应用可见范围或标签映射为平台项目

## 认证流程

### OAuth 2.0 Authorization Code Flow

```
┌──────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  平台登录页   │     │  企业微信 OAuth   │     │  AIHelms 后端    │
└──────┬───────┘     └────────┬────────┘     └────────┬─────────┘
       │                      │                       │
       │ 1. GET /login        │                       │
       │──────────────────────────────────────────────>│
       │                      │                       │
       │ 2. 302 Redirect      │                       │
       │<─────────────────────────────────────────────│
       │    to 企业微信授权页    │                       │
       │                      │                       │
       │ 3. 用户授权后回调      │                       │
       │──────────────────────────────────────────────>│
       │   GET /auth/callback?code=xxx                │
       │                      │                       │
       │                      │ 4. 验证 code           │
       │                      │<──────────────────────│
       │                      │  换取 access_token     │
       │                      │──────────────────────>│
       │                      │                       │
       │                      │ 5. 获取用户身份         │
       │                      │<──────────────────────│
       │                      │  返回 userId           │
       │                      │──────────────────────>│
       │                      │                       │
       │                      │          6. 查找/创建平台用户
       │                      │          (external_id + provider)
       │                      │                       │
       │ 7. 302 Redirect 到首页  │                       │
       │<─────────────────────────────────────────────│
       │   Set-Cookie: platform_jwt                   │
       │                      │                       │
```

### 平台用户匹配逻辑

```python
# 用户唯一标识
external_id = f"{corp_id}:{user_id}"  # 企业微信 corpId + userId
identity_provider = "wecom"

# 查找或创建
user = await find_user(external_id, identity_provider)
if not user:
    user = await create_user_from_wecom(access_token, user_id)
    # 默认分配 'user' 角色
    await assign_role(user, "user")
```

## 数据同步

### 同步模型

```
企业微信通讯录                     AIHelms 平台 DB
┌─────────────┐                  ┌──────────────────────┐
│ 用户 (User)  │ ──定时拉取──→    │ aihelms.users         │
│             │                  │ + external_id         │
│             │                  │ + identity_provider   │
│             │                  │ + is_admin (平台独有)  │
│             │                  │ + position (平台独有)  │
├─────────────┤                  ├──────────────────────┤
│ 部门 (Dept)  │ ──定时拉取──→    │ aihelms.departments   │
│             │                  │ + external_id         │
│             │                  │ + parent_id (树同步)   │
├─────────────┤                  ├──────────────────────┤
│ 标签 (Tag)   │ ──可选映射──→   │ aihelms.projects      │
│ 或可见范围    │                  │ + external_id         │
└─────────────┘                  └──────────────────────┘
```

### 同步策略

| 方式 | 说明 | 适用场景 |
|------|------|---------|
| 定时全量同步 | Celery beat 每小时拉取通讯录全量数据，对比更新 | 初始导入 + 定期校准 |
| Webhook 事件 | 企业微信回调：成员变更、部门变更事件 | 实时同步（推荐） |
| 手动触发 | 管理后台提供「同步通讯录」按钮 | 应急/调试 |

### 同步字段映射

**用户：**
| 企业微信字段 | 平台字段 |
|-------------|---------|
| userid | external_id |
| name | username |
| email / biz_mail | email |
| mobile | phone |
| position | position |
| avatar | avatar |
| department[] | user_departments |

**部门：**
| 企业微信字段 | 平台字段 |
|-------------|---------|
| id | external_id |
| name | name |
| parentid | parent_id |

## 平台扩展字段

以下字段为平台独有，企业微信无对应概念，不在同步范围内：

- `users.is_admin` — 是否平台管理员（由超级管理员分配）
- `users.is_super_admin` — 是否超级管理员
- `user_roles` — RBAC 角色分配
- `ai_keys` — AI 身份 Key
- `ai_keys.budget_limit` — 预算额度
- `ai_key_model_limits` — 模型速率限制

## 待设计项

以下内容后续详细设计时展开：

- [ ] 企业微信 ISV 应用配置（CorpID、AgentID、Secret、Token、EncodingAESKey）
- [ ] OAuth 2.0 授权 URL 构造（redirect_uri、state 防 CSRF）
- [ ] access_token 缓存策略（企业微信 token 有效期 7200 秒，需要中控缓存）
- [ ] Webhook 回调 URL 配置与消息解密
- [ ] 通讯录同步的增量 diff 算法（新增/更新/删除）
- [ ] 平台现有用户与 OA 用户的数据迁移/关联方案
- [ ] 登录页 UI：显示「企业微信登录」按钮 + 保留用户名密码登录入口
- [ ] 部门同步后 LiteLLM Team 同步更新
- [ ] 同步失败告警与重试机制
- [ ] 多企业（corp）支持（如果公司有多主体）
