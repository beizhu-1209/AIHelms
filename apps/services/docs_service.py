"""用户端接入文档文案。

纯文案模块，不与数据库交互。
所有 markdown 片段统一在此维护，支持运行时变量替换（如 LiteLLM 公开地址）。
"""

from core.config import settings


def _public_url() -> str:
    """对外的 LiteLLM 地址，用户客户端实际连接的目标。"""
    return settings.litellm_public_url.rstrip("/")


def _render(template: str) -> str:
    """渲染模板里的占位符。"""
    return template.replace("{{LITELLM_URL}}", _public_url())


# ---------------------------------------------------------------------------
# 总览：接入指南首页
# ---------------------------------------------------------------------------

OVERVIEW = """\
# 接入指南

欢迎使用 AIHelms。本指南帮你把**我的 AI 身份** Key 配置到本地客户端（Claude Code、Cursor、Continue 等），开始使用平台已开通的模型、MCP 工具和 Skill。

## 三步上手

1. **复制你的主 Key**：在「我的 AI 身份」页面点击复制（形如 `sk-xxxx...`）
2. **配置客户端**：参照下方对应客户端的配置说明，填入 Key 与服务地址
3. **开始使用**：直接调用平台已开通的模型即可，所有用量会自动归集到你名下

## 关键信息

| 字段 | 值 |
|------|---|
| 服务地址（Base URL） | `{{LITELLM_URL}}` |
| 认证方式 | Bearer Token（用你的主 Key） |
| 兼容协议 | OpenAI Chat Completions / Anthropic Messages |

> 平台不暴露上游模型厂商的 Key。你看到的 Key 是平台分配给你的虚拟 Key，所有调用经平台统一路由、计费、审计。

## 常见问题

- **Key 用不了？** 检查 Key 是否在「我的 AI 身份」中显示「已启用」；预算用尽时会被限流。
- **想用新模型？** 在「AI 市场」找到目标模型，点击「使用」或「申请使用」。
- **MCP 工具怎么用？** 申请通过后，按下方 MCP 接入文档配置 mcp.json。
- **Skill 怎么用？** 申请通过后，在 Skill 详情页复制 Agent Prompt 粘贴到客户端即可。
"""


# ---------------------------------------------------------------------------
# 各客户端接入文档
# ---------------------------------------------------------------------------

CLAUDE_CODE = """\
# Claude Code

Claude Code 是 Anthropic 官方的 CLI 编程助手，原生支持自定义 Base URL。

## 配置方式

编辑 `~/.claude/settings.json`（不存在则创建）：

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "{{LITELLM_URL}}",
    "ANTHROPIC_AUTH_TOKEN": "<粘贴你的主 Key>"
  }
}
```

或使用环境变量：

```bash
export ANTHROPIC_BASE_URL="{{LITELLM_URL}}"
export ANTHROPIC_AUTH_TOKEN="sk-xxxxxxxxxxxx"
claude
```

## 验证

```bash
claude
> 你好
```

如果返回正常对话，说明配置成功。所有调用都会出现在「我的用量」中。

## 使用 Skill

在「AI 市场 → Skill」找到目标 Skill，点击「申请使用」或「使用」。开通后在 Skill 详情页点击「**复制 Agent Prompt**」，粘贴到 Claude Code 的对话框即可激活该 Skill 的能力。
"""


CURSOR = """\
# Cursor

Cursor 支持通过 OpenAI 兼容端点接入第三方模型。

## 配置方式

1. 打开 Cursor → `Cmd/Ctrl + ,` 进入 **Settings**
2. 找到 **Models** → 启用 **Override OpenAI Base URL**
3. 填写：
   - **OpenAI Base URL**：`{{LITELLM_URL}}`
   - **OpenAI API Key**：粘贴你的主 Key
4. 在 **Models** 列表里勾选你已开通的模型（如 `claude-sonnet-4`、`gpt-4o`）
5. 点击 **Verify** 验证配置

## 注意事项

- Cursor 的 `Verify` 按钮默认会请求 `gpt-4o-mini`，请确保你已开通该模型，或先把默认模型切换为已开通的型号
- 模型 ID 需要与平台「模型管理」里的 `model_id` 完全一致
- Cursor 本身不支持 MCP / Skill，仅支持 LLM 对话

## 验证

新建一个对话，选已开通的模型发送一条消息，能正常返回即成功。
"""


CONTINUE_DEV = """\
# Continue (VSCode / JetBrains)

Continue 是开源的 IDE 编程助手插件，配置文件方式接入。

## 配置方式

编辑 `~/.continue/config.json`：

```json
{
  "models": [
    {
      "title": "AIHelms - Claude Sonnet 4",
      "provider": "openai",
      "model": "claude-sonnet-4",
      "apiBase": "{{LITELLM_URL}}",
      "apiKey": "<粘贴你的主 Key>"
    },
    {
      "title": "AIHelms - GPT-4o",
      "provider": "openai",
      "model": "gpt-4o",
      "apiBase": "{{LITELLM_URL}}",
      "apiKey": "<粘贴你的主 Key>"
    }
  ]
}
```

## 验证

重启 IDE → 打开 Continue 面板 → 在模型下拉里选 `AIHelms - Claude Sonnet 4` → 发送测试消息。
"""


DIFY = """\
# Dify

Dify 自带应用可以接入 OpenAI 兼容的模型供应商。

## 配置方式（管理员）

1. Dify 管理后台 → **设置** → **模型供应商** → 找到 **OpenAI-API-compatible**
2. 点击「添加模型」，填写：
   - **Model Name**：填平台的 `model_id`（如 `claude-sonnet-4`）
   - **API Key**：你的主 Key
   - **API endpoint URL**：`{{LITELLM_URL}}`
3. 保存后，在 Dify 应用编排时即可选择该模型

## 使用场景 Key（管理员定制智能体）

如果你是在 Dify 上开发智能体并希望平台统计该智能体的用量，请联系管理员申请「**场景 Key**」（专为智能体应用使用），把场景 Key 配到 Dify 模型供应商里，平台就能识别这是 AI 自动化产生的调用。
"""


CHERRY_STUDIO = """\
# Cherry Studio / 其他 OpenAI 兼容客户端

适用于 Cherry Studio、NextChat、LobeChat、ChatBox 等支持自定义 API endpoint 的图形化客户端。

## 通用配置

| 字段 | 填写内容 |
|------|---------|
| 服务商 / Provider | 选择 **OpenAI** 或 **自定义 OpenAI 兼容** |
| API 地址 / Base URL | `{{LITELLM_URL}}` |
| API Key | 你的主 Key（形如 `sk-xxxx`） |
| 模型列表 | 手动添加平台已开通的模型 ID |

## 验证

新建对话 → 选择模型 → 发送 `hello` → 能正常回复即成功。
"""


MCP_GUIDE = """\
# MCP 工具接入

MCP（Model Context Protocol）是 Anthropic 提出的工具调用协议。平台把 MCP Server 统一纳管，你申请通过后可在支持 MCP 的客户端（Claude Code、Cline 等）配置使用。

## 工作原理

```
你的客户端 ──MCP 协议──> 平台 LiteLLM 网关 ──> 上游 MCP Server
                              ↑
                          用你的主 Key 鉴权
```

你**不需要**接触上游 MCP Server 的原始配置和凭证，全部由平台统一管理。

## Claude Code 配置示例

在「AI 市场 → MCP」找到目标 MCP Server（如 `github`、`postgres`、`filesystem`），点击「使用」或「申请使用」。开通后，在 Claude Code 的 mcp 配置中加入：

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "{{LITELLM_URL}}/mcp",
      "headers": {
        "Authorization": "Bearer <你的主 Key>",
        "x-mcp-servers": "github"
      }
    }
  }
}
```

`x-mcp-servers` 头里填你要使用的 MCP Server 名称，多个用逗号分隔（如 `github,postgres`）。

## 调试

如果工具调用没生效，先在「我的 AI 身份」页面确认目标 MCP Server 已显示在可用列表中。
"""


SKILL_GUIDE = """\
# Skill 使用

Skill 是面向 Claude Code / Anthropic Agent 的能力增强包，由平台统一发布管理。**Skill 本身不消耗模型成本**，只是把一段经过打磨的提示词 + 工具组合打包给你。

## 使用流程

1. 在「AI 市场 → Skill」浏览可用的 Skill
2. 点击「使用」（无需审批）或「申请使用」（需审批）
3. 开通后，在 Skill 详情页或「我的 AI 身份 → 可用 Skill」点击「**复制 Agent Prompt**」
4. 把复制的提示词粘贴到 Claude Code 的对话框，作为对话的第一条消息发送
5. Claude 会按照 Skill 的提示词约定，调用预设的工具完成任务

## 提示词示例（仅作示意）

```
You are a code review assistant.
When the user provides code, analyze it for:
- Bugs and edge cases
- Performance issues
- Style violations
- Security vulnerabilities
Report findings in markdown format with severity levels.
```

## 注意

- Skill 的提示词在 Claude Code 当前会话内生效，新开会话需要重新粘贴
- 不要修改 Agent Prompt 的核心指令，否则可能影响效果
"""


FAQ = """\
# 常见问题

## Key 相关

**Q：我的 Key 是从哪里来的？**
A：你的入职/项目分配时，管理员会为你创建一个**主 Key**（每人唯一）。在「我的 AI 身份」页面可以查看和复制。

**Q：Key 显示「未启用」怎么办？**
A：联系管理员申请启用，或通过「我的申请」提交 Key 启用申请。

**Q：Key 泄漏了怎么办？**
A：立刻联系管理员重置 Key。旧 Key 会立刻失效，新 Key 会重新生成。

## 模型相关

**Q：模型列表里没有我想用的模型？**
A：在「AI 市场 → 模型」搜索目标模型，点击「申请使用」提交审批。

**Q：调用模型报错 `model_not_found`？**
A：客户端里填的模型 ID 与平台不一致；请用「我的 AI 身份 → 可用模型」里显示的 `model_id`。

**Q：能直连模型厂商（OpenAI / Anthropic）的 API 吗？**
A：不能。所有调用必须经平台统一网关，便于审计和成本归集。

## 计费与预算

**Q：怎么看我用了多少钱？**
A：「我的用量」页面查看本月累计和趋势。

**Q：预算用完了会怎样？**
A：若你的 Key 配置了「硬限制」，超额后调用会被拒绝（HTTP 429）；若是「软限制」，会继续可用但会有页面提醒。

## MCP / Skill

**Q：MCP 和 Skill 有什么区别？**
A：MCP 是**工具调用协议**（如查询数据库、读写文件、调 GitHub API），由客户端协议层调用；Skill 是**提示词增强包**（如代码审查助手、文档翻译），用户复制 prompt 即用，不需要协议支持。

**Q：MCP 工具调用收费吗？**
A：是的，按 Server 或 Tool 级别配置定价；具体见「我的用量」里的 MCP 部分。Skill 不收费。
"""


# ---------------------------------------------------------------------------
# 文档清单
# ---------------------------------------------------------------------------

DOCS: dict[str, dict[str, str]] = {
    "overview": {
        "title": "接入指南",
        "category": "入门",
        "content": OVERVIEW,
    },
    "claude-code": {
        "title": "Claude Code",
        "category": "客户端",
        "content": CLAUDE_CODE,
    },
    "cursor": {
        "title": "Cursor",
        "category": "客户端",
        "content": CURSOR,
    },
    "continue": {
        "title": "Continue (IDE 插件)",
        "category": "客户端",
        "content": CONTINUE_DEV,
    },
    "dify": {
        "title": "Dify",
        "category": "客户端",
        "content": DIFY,
    },
    "cherry-studio": {
        "title": "Cherry Studio 等图形客户端",
        "category": "客户端",
        "content": CHERRY_STUDIO,
    },
    "mcp": {
        "title": "MCP 工具接入",
        "category": "资源",
        "content": MCP_GUIDE,
    },
    "skill": {
        "title": "Skill 使用",
        "category": "资源",
        "content": SKILL_GUIDE,
    },
    "faq": {
        "title": "常见问题",
        "category": "帮助",
        "content": FAQ,
    },
}


def list_docs() -> list[dict[str, str]]:
    """返回文档目录（不含正文）。"""
    return [
        {"slug": slug, "title": meta["title"], "category": meta["category"]}
        for slug, meta in DOCS.items()
    ]


def get_doc(slug: str) -> dict[str, str] | None:
    """按 slug 取单篇文档，正文中的占位符已渲染。"""
    meta = DOCS.get(slug)
    if not meta:
        return None
    return {
        "slug": slug,
        "title": meta["title"],
        "category": meta["category"],
        "content": _render(meta["content"]),
    }
