# Core Rules

<!-- Auto-loaded, applies to all file operations -->

## Roadmap

- 每次完成工作后，必须更新 `roadmap/` 目录中对应模块的进度
- `roadmap/` 不提交 git，仅本地追踪开发进度

## Investigate First

- Never guess code behavior — read the file before answering
- Always read files the user mentions before operating on them
- When uncertain, state it clearly and propose a verification plan
- Before modifying code: read related files, check imports, confirm call chains
- If unsure whether a function/variable is referenced elsewhere, search before modifying

## Scope Discipline

- Do only what is asked — no more, no less
- Do not refactor code that was not requested to be changed
- Do not add comments or docstrings to unmodified code
- Do not create abstractions for single-use cases
- Do not add "just in case" error handling or validation
- Follow limiting words ("only", "just", "exactly") literally
- Bug fixes do not need surrounding code cleaned up
- Simple features do not need extra configurability

## Verification & Safety

- Before finishing: run tests and lint, state what changed and what was not verified
- Confirm before destructive operations: delete files, force push, hard reset, --no-verify
- Prefer editing existing files over creating new ones
- Do not skip git hooks, do not use --no-verify
- Do not push directly to main branch
- For changes involving auth, permissions, or data deletion: state the impact scope

## Efficiency

- Execute independent tool calls in parallel
- Do not use placeholder or guessed parameter values
- Do not repeat operations that already succeeded
- If the same approach fails twice, change strategy instead of tweaking

## Code Quality

- Write self-documenting code; only add comments when logic is non-obvious
- Comments explain "why", not "what"
- Variable and function names must be meaningful — no temp, data, info
- No TODO comments — either do it now or don't
- No commented-out code — delete it

## Error Handling

- Only validate input at system boundaries (user input, external APIs)
- Trust parameters between internal code — no defensive programming
- Error messages must have context for debugging
- Never swallow exceptions — either handle or re-raise

## Security

- SQL must use parameterized queries — no string concatenation
- User input must be validated and escaped
- No hardcoded secrets, passwords, or tokens in code
- No sensitive info in logs
- API endpoints require auth by default; public endpoints must be explicitly marked
