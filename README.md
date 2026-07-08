<div align="center">

<img src="ui/static/img/logo.png" alt="AIHelms" width="100">


<p><strong>企业 AI 资源纳管平台</strong></p>

<p>承载 AI 数字资产 · 释放 AI 生产力 · 链接未来</p>


[![Release](https://img.shields.io/badge/Release-v0.1.14-brightgreen.svg)](https://github.com/beizhu-1209/AIHelms/releases/tag/0.1.14)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4+-4FC08D.svg)](https://vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6.svg)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-06B6D4.svg)](https://tailwindcss.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D.svg)](https://redis.io/)
[![vLLM](https://img.shields.io/badge/vLLM-FF6F00.svg)](https://docs.vllm.ai/)
[![SGLang](https://img.shields.io/badge/SGLang-8B5CF6.svg)](https://github.com/sgl-project/sglang)

<p align="center">
| <b>简体中文</b> | <a href="./README.en.md"><b>English</b></a> | 
</p>

<p align="center">

 [核心价值](#核心价值) · [功能展示](#主要功能)  · [快速开始](#快速开始)  · [部署文档](#部署)

</div>

---

<!-- Banner 截图：管理后台 Dashboard 全貌 -->
<!-- ![AIHelms](docs/assets/screenshot-banner.png) -->

## 这是什么

AIHelms 是面向企业的 AI 资源纳管平台。帮助企业**管理 AI 资产、控制 AI 成本、衡量 AI 价值**的管理工具。
- **决策层** - 平台全程记录用量、核算成本、生成报表，让看得见 AI 的投入产出比
- **管理员** - 通过后台统一接入模型、分配身份、设定预算
- **员工** - 通过用户端获取 AI 身份，接入任意客户端使用

![架构图](docs/struct.png)


## 核心价值

### 成本可见可控

企业使用 AI 最大的焦虑是"钱花了但不知道花在哪"。AIHelms 建立了完整的成本体系：

- **内外双轨定价** — 外部成本（供应商实际收费）和内部结算价（企业对部门的计费）分开核算。企业可以按成本价透传，也可以加价内部结算
- **多维预算管控** — 按人、按部门、按项目、按模型设预算，支持软限制（预警）和硬限制（超支停用）
- **实时成本归因** — 每一次调用都能追溯到具体的人、部门、项目、模型，精确到 token 级别

### 统一身份统一入口

- 每位员工一个 AI 身份（API Key），一个入口访问所有 AI 资源
- AI员工（进行中）

### 量化 AI 价值

- **覆盖率** — 部门覆盖率、人员激活率、模型使用分布
- **活跃度** — 日均调用量、人均 token 消耗、使用趋势曲线
- **成本效能** — 部门成本排名、模型性价比、预算消耗进度、内外成本差异
- **效能报告** — 周/月自动生成，支持按部门、项目、模型多维下钻

### 安全审计

- 敏感信息识别
- 高风险 prompt 拦截
- 管理员操作追踪

### 资源集中管理

- **模型纳管** — 多供应商统一接入，同模型多部署负载均衡，OpenAI/Anthropic 双格式兼容
- **Skill & MCP** — 企业内部 AI 工具统一注册、审批、分发
- **权限精细化** — 谁能用什么模型、用多少额度、什么时候过期，全部可配置

## 更新日志

最近版本汇总自 [GitHub Releases](https://github.com/beizhu-1209/AIHelms/releases)，完整变更请以发布页为准。

| 版本 | 发布时间 | 一句话更新 |
|------|----------|----------|
| `0.1.14` | 2026-07-07 | AI Policies 增加大模型审查。 |
| `0.1.13` | 2026-07-03 | 新增 AI Policies 安全审查：一键扫描 Skill，自动识别恶意指令、数据外传、权限过大等风险并生成报告。 |
| `0.1.12` | 2026-07-01 | 资源申请支持批量审批；Skill / MCP 新增作者信息，用户端显示使用量。 |
| `0.1.11` | 2026-06-29 | 优化日志修复codex /goal 等长Agent日志错配问题。 |
| `0.1.9` | 2026-06-27 | 新增小米 MiMo 模型接入和模型 Logo 选择；AI 身份限流更完善（总量 + 按模型限速）。 |
| `0.1.8` | 2026-06-23 | 支持 vLLM 的 Anthropic 格式接入。 |
| `0.1.7` | 2026-06-23 | 修复成本计算和日志统计的若干问题，账目更准。 |
| `0.1.6` | 2026-06-16 | 完善模型连通性测试。 |
| `0.1.5` | 2026-06-10 | 升级管理员看板与成本、效能、预算分析体验。 |
| `0.1.4` | 2026-06-04 | 修复若干问题，合入社区贡献。 |

## 主要功能

### 管理后台

面向 IT 管理员和 AI 负责人，覆盖资源管理全流程。

| <img src="docs/dashboard.png" width="400" height="250"> | <img src="docs/model.png" width="400" height="250"> |
|:---:|:---:|
| **Dashboard** — 今日调用、成本、待办一览 | **模型纳管** — 供应商接入、多部署、连通性测试 |
| <img src="docs/id.png" width="400" height="250"> | <img src="docs/datacenter.png" width="400" height="250"> |
| **AI 身份** — Key 签发、预算分配、生命周期 | **AI效能** — 成本分析、覆盖率、效能报告 |

<details>
<summary><b>管理后台功能清单</b></summary>

| 模块 | 能力 |
|------|------|
| 模型纳管 | 供应商管理、凭证管理、模型注册、多部署负载均衡、路由策略、连通性测试 |
| AI 身份 | 部门/项目/人员管理、Key 签发、预算额度、速率限制、模型白名单 |
| AI 市场 | Skill 发布上架、MCP Server 注册发现、资源申请审批 |
| AI 效能 | 成本分析（内/外）、落地覆盖率、预算管控、效能报告 |
| 安全 | 管理员审计日志、操作追踪 |
| 智能体中心 | 智能体创建、配置、生命周期管理 |

</details>

### 用户端 AI Hub

面向全体员工，简洁直观，获取 AI 身份后即可使用。

![用户端](docs/web.png)

- 查看 AI 身份，一键复制 Key 和接入点
- 浏览模型广场，按场景选择模型 ID
- 浏览 AI 市场，申请 Skill / MCP 使用权限
- 查看本月用量和预算消耗

## 快速开始

### 环境要求

- Docker 20.10+ & Docker Compose v2+
- 4 核 8G 内存（最低）

### 部署

```bash
git clone https://github.com/beizhu-1209/AIHelms.git
cd AIHelms
cp .env.example .env
# 编辑 .env 填入密钥
docker compose up -d
```

### 访问

| 地址 | 说明 |
|------|------|
| `http://your-host` | 用户端 |
| `http://your-host/admin` | 管理后台 |
| `http://your-host/api/docs` | API 文档 |

默认管理员：`admin` / 密码见 `.env` 中 `SUPER_ADMIN_PASSWORD`

### 三步上手

```
1. 管理后台 → 供应商管理 → 添加凭证
2. 管理后台 → 模型管理 → 新建模型 → 关联凭证 → 发布
3. 用户端 → 我的 AI 身份 → 复制 Key 和 Endpoint → 配置到客户端
```



## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+, FastAPI, Gunicorn, Celery |
| 前端 | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS |
| 数据库 | PostgreSQL 16+ |
| 缓存 | Redis 7+ |
| 部署 | Docker Compose, Nginx |

<details>
<summary><b>环境变量说明</b></summary>

| 变量 | 说明 |
|------|------|
| `POSTGRES_PASSWORD` | 数据库密码 |
| `SECRET_KEY` | JWT 签名密钥 |
| `SUPER_ADMIN_PASSWORD` | 超级管理员初始密码 |
| `WEB_PORT` | Web 对外端口 |

完整列表见 `.env.example`

</details>

<details>
<summary><b>开发环境</b></summary>

```bash
./dev/setup              # 首次设置
./dev/start-docker-compose  # 启动中间件
./dev/start-api          # 启动后端（热重载）
./dev/start-web          # 启动前端（HMR）
```

详见 [开发与发布流程](docs/INTERNAL.md)

</details>

## RoadMap

### AI 实验室

| 功能 | 一句话总结 |
|------|------------|
| 报告 | 汇总 AI 效能、成本、预算等分析结果，形成面向管理汇报的报告视图。 |
| AI 健康 | 集中查看 MCP 上游、模型部署、Docker 环境和效能数据更新状态。 |
| 敏感信息识别 | 识别 AI 交互内容中的敏感信息，支撑后续告警、审计和处置。 |
| A2A | 规划智能体之间的协作、调用关系和任务联动能力。 |
| 上下文缓存 | 缓存高频上下文和会话材料，减少重复输入并降低调用成本。 |
| 策略管理 | 高风险识别，包括电子围栏、prompt 注入等。 |
| 文件处理 | 对上传文件进行解析、切分、索引和预处理，供后续 AI 能力调用。 |

## Contributing

1. Fork 本仓库
2. 创建分支：`git checkout -b feature/xxx`
3. 提交代码到dev分支：`git commit -m "feat: 功能描述"`
4. 推送并创建 Pull Request

详细开发规范见 [开发与发布流程](docs/INTERNAL.md)

## 交流反馈

- 微信交流群：扫码加入

  <img src="docs/wechat.jpg" alt="微信交流群" width="200">

- 商业合作：[联系邮件](mailto:jiangshiwei@microbaton.com)
- Issue 反馈：[GitHub Issues](https://github.com/beizhu-1209/AIHelms/issues)

## License

本项目采用 [GPL-3.0](LICENSE) 开源协议，底座应用 LiteLLM 社区版（MIT License）。

如果您所在组织的政策不允许使用 GPL-3.0 许可的软件，或您希望规避 GPL-3.0 的开源义务，请发送邮件至 [联系邮件](mailto:jiangshiwei@microbaton.com) 咨询商业授权。
