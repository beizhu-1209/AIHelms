# apps/ — 后端

- 详细编码规范见 `.claude/rules/backend.md`
- 架构：Router → Service → Database（分层，禁止跨层调用）
- 格式化 & Lint：`black . && ruff check .`
- 测试：`python -m pytest -v`
- 配置读取走 `core/config.py`，不直接 `os.getenv()`
- 日志用 `logging.getLogger(__name__)`，不用 `print()`
