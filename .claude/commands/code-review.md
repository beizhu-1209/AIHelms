# Code Review

Perform a comprehensive review of code changes, checking quality, security, performance, and convention compliance.

## Usage

- "Review this PR"
- "Check the code I just wrote"
- "Review apps/services/user_service.py"

## Review Dimensions

### 1. Correctness

- Is the logic correct? Are edge cases covered?
- Is async code using await correctly?
- Are database operations in transactions when atomicity is needed?
- Is error handling complete (no swallowed exceptions, no missed cases)?

### 2. Security

- SQL uses parameterized queries ($1, $2) — no string concatenation
- User input validated (Pydantic Field validators)
- No sensitive data exposed in logs or responses
- API endpoints have proper auth/permission checks
- No hardcoded secrets or tokens

### 3. Performance

- No N+1 query problems
- No unnecessary IO in loops
- Large lists have pagination
- No full table scans (missing indexes)
- Frontend: no unnecessary re-renders

### 4. Naming Conventions

#### Python
| Type | Convention | Good | Bad |
|------|-----------|------|-----|
| File | snake_case | `user_service.py` | `UserService.py` |
| Function | snake_case, verb prefix | `get_user_by_id()` | `user()`, `userData()` |
| Variable | snake_case | `user_count`, `is_active` | `temp`, `data`, `x` |
| Class | PascalCase | `UserService` | `user_service` |
| Constant | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` | `maxRetryCount` |
| Private | underscore prefix | `_validate_email()` | `validate_internal()` |
| Boolean | is_/has_/can_ prefix | `is_active` | `active`, `flag` |

#### TypeScript / Vue
| Type | Convention | Good | Bad |
|------|-----------|------|-----|
| Component file | PascalCase | `UserCard.vue` | `user-card.vue` |
| Utility file | camelCase | `useAuth.ts` | `UseAuth.ts` |
| Component name | PascalCase | `<UserCard />` | `<user-card />` |
| Function | camelCase, verb prefix | `getUserList()` | `userList()` |
| Variable | camelCase | `userCount`, `isLoading` | `temp`, `data` |
| Type/Interface | PascalCase | `interface UserProfile` | `interface userProfile` |
| Constant | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE` | `maxPageSize` |
| Composable | use prefix | `useAuth()` | `auth()` |
| Event handler | handle prefix | `handleClick()` | `click()` |
| Boolean | is/has/can prefix | `isLoading` | `loading` |
| Props | noun or adjective | `user`, `disabled` | `handleClick` |
| Emits | verb or verb phrase | `update`, `delete` | `onUpdate` |

#### Database
| Type | Convention | Good | Bad |
|------|-----------|------|-----|
| Table | snake_case plural | `users`, `api_keys` | `User`, `apiKey` |
| Column | snake_case | `created_at`, `user_id` | `createdAt` |
| Index | idx_table_column | `idx_users_email` | `index1` |
| Foreign key | fk_table_ref | `fk_api_keys_users` | `fk1` |
| Schema | snake_case | `aihelms` | `AiHelms` |

#### API Paths
| Convention | Good | Bad |
|-----------|------|-----|
| Plural nouns | `/api/v1/users` | `/api/v1/user` |
| kebab-case | `/api/v1/usage-logs` | `/api/v1/usageLogs` |
| Nested resources | `/api/v1/users/{id}/api-keys` | `/api/v1/getUserKeys` |
| Actions use verbs | `/api/v1/auth/login` | `/api/v1/auth/do-login` |

### 5. Architecture Compliance

- Router layer (api/) only parses params and serializes responses — no business logic
- Service layer (services/) handles business logic — no HTTP response objects
- Database operations happen in service layer — not in routers
- Frontend components don't call fetch directly — use shared API layer
- admin and web don't import from each other — shared code in shared package

### 6. Code Style

- Function length ≤50 lines (split if longer)
- File length ≤500 lines (split into modules if longer)
- Nesting ≤3 levels (early return or extract function)
- Parameters ≤5 (use object if more)
- No commented-out code
- No TODO comments (either do it or remove)
- No console.log / print debug statements

### 7. Type Safety

#### Python
- All public functions have complete type annotations (params + return)
- No `Any` (unless truly indeterminate)
- Use `TypedDict` instead of `dict[str, Any]`
- Use `X | None` not `Optional[X]`

#### TypeScript
- strict mode, no `any`
- Props via `defineProps<T>()` generic
- Emits via `defineEmits<T>()` generic
- API responses have explicit types, no `as any`

### 8. Testing

- Does new functionality have corresponding tests?
- Do tests cover both happy and error paths?
- Are test names clearly describing the scenario?
- Are mocks reasonable (not over-mocked)?

## Output Format

```markdown
## Code Review Result

### Summary
- Files: [file list]
- Overall: [Excellent / Good / Needs Changes / Needs Rewrite]
- Issues: Critical: X, Warning: X, Suggestion: X

### Critical (must fix)
#### 1. [Issue title]
- **Location**: file.py:line
- **Problem**: specific description
- **Impact**: potential consequences
- **Fix**:
```python
# Before
...
# After
...
```

### Warning (should fix)
[same format]

### Suggestion (optional improvement)
[same format]

### Positives
- [things done well]
```

## Review Principles

- Focus on high-impact issues, don't nitpick formatting (lint tools handle that)
- Provide concrete fix suggestions, don't just point out problems
- Understand context before judging — don't cite "best practices" out of context
- Distinguish "must fix" from "nice to have" — not everything is critical
- Acknowledge what's done well — don't only find faults
