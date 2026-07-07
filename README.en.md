<div align="center">

<img src="ui/static/img/logo.png" alt="AIHelms" width="100">


<p><strong>Enterprise AI Resource Management Platform</strong></p>

<p>Built on top of LiteLLM · Model distribution, AI identity, cost control, and governance</p>


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

**English** · [简体中文](README.md)

[What Is It](#what-is-it) · [Why AIHelms](#why-aihelms) · [Built on LiteLLM](#built-on-litellm) · [Quick Start](#quick-start) · [Deployment](#deployment)

</div>

---

## What Is It

AIHelms is an AI resource management platform for enterprises. It helps companies **manage AI assets, control AI spend, and measure the value of AI**.

- **For leadership** — the platform records usage, calculates cost, and generates reports, so the return on your AI investment is visible.
- **For administrators** — onboard models, assign identities, and set budgets from a single admin console.
- **For employees** — get an AI identity from the user portal and use it with any client.

![Architecture](docs/struct.png)


## Why AIHelms

### Cost you can see and control

The biggest worry with enterprise AI is spending money without knowing where it goes. AIHelms builds a full cost model around that:

- **Dual pricing, internal and external** — external cost (what the provider charges) and internal settlement price (what you bill departments) are tracked separately. Pass cost through as-is, or add a markup for internal settlement.
- **Multi-dimensional budgets** — set budgets per person, department, project, or model, with soft limits (alerts) and hard limits (cut off on overspend).
- **Real-time attribution** — every call traces back to a specific person, department, project, and model, down to the token level.

### One identity, one entry point

- One AI identity (API key) per employee, one entry point to every AI resource.
- AI employees (in progress).

### AI value, quantified

- **Coverage** — department coverage, activation rate, model usage distribution.
- **Activity** — daily call volume, tokens per person, usage trends.
- **Cost efficiency** — department cost ranking, model cost-effectiveness, budget burn, internal vs. external cost gaps.
- **Efficiency reports** — generated weekly and monthly, with drill-down by department, project, and model.

### Security and audit

- Sensitive data detection.
- High-risk prompt interception.
- Admin action tracking.

### Centralized resource management

- **Model management** — onboard multiple providers behind one gateway, load-balance across deployments of the same model, support both OpenAI and Anthropic formats.
- **Skill & MCP** — register, approve, and distribute internal AI tools in one place.
- **Fine-grained permissions** — who can use which model, how much quota, and when it expires, all configurable.

## Changelog

Recent versions are summarized from [GitHub Releases](https://github.com/beizhu-1209/AIHelms/releases). See the release page for the full changelog.

| Version | Date | Summary |
|------|----------|----------|
| `0.1.14` | 2026-07-07 | AI Policies adds LLM-based review. |
| `0.1.13` | 2026-07-03 | New AI Policies security review: scan a Skill in one click, flag malicious instructions, data exfiltration, and excessive permissions, and generate a report. |
| `0.1.12` | 2026-07-01 | Resource requests support batch approval; Skill / MCP add author info, with usage shown in the user portal. |
| `0.1.11` | 2026-06-29 | Fixed log mismatches for long agent logs such as codex /goal. |
| `0.1.9` | 2026-06-27 | Added Xiaomi MiMo model onboarding and model logo selection; more complete AI identity rate limiting (total plus per-model). |
| `0.1.8` | 2026-06-23 | Support for LiteLLM Anthropic-format access through vLLM. |
| `0.1.7` | 2026-06-23 | Fixed several cost calculation and log statistics issues for more accurate accounting. |
| `0.1.6` | 2026-06-16 | Improved model connectivity testing. |
| `0.1.5` | 2026-06-10 | Upgraded the admin dashboard and the cost, efficiency, and budget analysis experience. |
| `0.1.4` | 2026-06-04 | Fixed several issues and merged community contributions. |

## Features

### Admin console

For IT administrators and AI owners, covering the full resource management workflow.

| <img src="docs/dashboard.png" width="400" height="250"> | <img src="docs/model.png" width="400" height="250"> |
|:---:|:---:|
| **Dashboard** — today's calls, cost, and to-dos at a glance | **Model management** — provider onboarding, multiple deployments, connectivity testing |
| <img src="docs/id.png" width="400" height="250"> | <img src="docs/datacenter.png" width="400" height="250"> |
| **AI identity** — key issuance, budget allocation, lifecycle | **AI efficiency** — cost analysis, coverage, efficiency reports |

<details>
<summary><b>Admin console feature list</b></summary>

| Module | Capabilities |
|------|------|
| Model management | Provider management, credential management, model registration, multi-deployment load balancing, routing strategy, connectivity testing |
| AI identity | Department / project / people management, key issuance, budget quota, rate limiting, model allow-list |
| AI marketplace | Skill publishing, MCP Server registration and discovery, resource request approval |
| AI efficiency | Cost analysis (internal / external), adoption coverage, budget control, efficiency reports |
| Security | Admin audit log, action tracking |
| Agent center | Agent creation, configuration, lifecycle management |

</details>

### User portal (AI Hub)

For all employees. Simple and direct: get an AI identity and start using it.

![User portal](docs/web.png)

- View your AI identity and copy the key and endpoint in one click.
- Browse the model square and pick a model ID by scenario.
- Browse the AI marketplace and request access to Skills / MCP.
- Check this month's usage and budget burn.

## Quick Start

### Requirements

- Docker 20.10+ & Docker Compose v2+
- 4 cores, 8 GB RAM (minimum)

### Deployment

```bash
git clone https://github.com/beizhu-1209/AIHelms.git
cd AIHelms
cp .env.example .env
# Edit .env and fill in your secrets
docker compose up -d
```

### Access

| URL | Description |
|------|------|
| `http://your-host` | User portal |
| `http://your-host/admin` | Admin console |
| `http://your-host/api/docs` | API docs |

Default admin: `admin` / password is `SUPER_ADMIN_PASSWORD` in `.env`.

### Three steps to get started

```
1. Admin console → Providers → Add credential
2. Admin console → Models → Create model → Link credential → Publish
3. User portal → My AI Identity → Copy key and endpoint → Configure your client
```

## Tech Stack

| Layer | Technology |
|------|------|
| Backend | Python 3.11+, FastAPI, Gunicorn, Celery |
| Frontend | Vue 3.4+, TypeScript, Vite 5+, TailwindCSS |
| Database | PostgreSQL 16+ |
| Cache | Redis 7+ |
| Deployment | Docker Compose, Nginx |

<details>
<summary><b>Environment variables</b></summary>

| Variable | Description |
|------|------|
| `POSTGRES_PASSWORD` | Database password |
| `SECRET_KEY` | JWT signing key |
| `SUPER_ADMIN_PASSWORD` | Super admin initial password |
| `WEB_PORT` | Web external port |

See `.env.example` for the full list.

</details>

<details>
<summary><b>Development</b></summary>

```bash
./dev/setup                 # First-time setup
./dev/start-docker-compose  # Start middleware
./dev/start-api             # Start backend (hot reload)
./dev/start-web             # Start frontend (HMR)
```

See [Development and release workflow](docs/INTERNAL.md).

</details>

## Roadmap

### AI Lab

| Feature | Summary |
|------|------------|
| Reports | Aggregate AI efficiency, cost, and budget analysis into a management-facing report view. |
| AI health | Monitor MCP upstreams, model deployments, the Docker environment, and efficiency data refresh status in one place. |
| Sensitive data detection | Detect sensitive information in AI interactions to support alerts, audit, and handling. |
| A2A | Plan collaboration, call relationships, and task chaining between agents. |
| Context caching | Cache frequent context and session material to reduce repeated input and call cost. |
| Policy management | High-risk detection, including geo-fencing and prompt injection. |
| File processing | Parse, chunk, index, and preprocess uploaded files for downstream AI capabilities. |

## Contributing

1. Fork this repository.
2. Create a branch: `git checkout -b feature/xxx`.
3. Commit to the dev branch: `git commit -m "feat: describe your feature"`.
4. Push and open a Pull Request.

See [Development and release workflow](docs/INTERNAL.md) for detailed conventions.

## Community

- WeChat group: scan to join.

  <img src="docs/wechat.jpg" alt="WeChat group" width="200">

- Business inquiries: [email us](mailto:jiangshiwei@microbaton.com)
- Issues: [GitHub Issues](https://github.com/beizhu-1209/AIHelms/issues)

## License

AIHelms is licensed under [GPL-3.0](LICENSE), and runs on the LiteLLM community edition (MIT License).

If your organization's policies do not allow GPL-3.0 licensed software, or you want to use AIHelms without the obligations of GPL-3.0, email us at [jiangshiwei@microbaton.com](mailto:jiangshiwei@microbaton.com) for a commercial license.
