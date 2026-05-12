# Core Rules

<!-- Auto-loaded, applies to all file operations -->

## Roadmap

- After completing work, always update the corresponding module progress in `dev/roadmap/`
- `dev/roadmap/` is not committed to git, local progress tracking only

## Resource

- Development resources are stored in `dev/resource/` directory
- `dev/resource/` is not committed to git, local reference only

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

## Testing

- Functional tests must use Playwright browser automation, never call APIs directly (curl/fetch etc.)
- Test cases simulate real user workflows, WYSIWYG, minimize steps
- Test URLs must read from `.env` config (WEB_PORT etc.), never hardcode localhost or port numbers
- API auth must use platform tokens (JWT or API Key), never use username/password to call APIs directly in tests
- Test flow: login via page → page operations → verify page results
- Backend unit tests use pytest, integration and E2E tests must use Playwright
- After completing each feature module, add corresponding test cases and record in roadmap
- All Playwright screenshots and artifacts must be saved to `.playwright-mcp/` directory, never in the project root or source directories

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
