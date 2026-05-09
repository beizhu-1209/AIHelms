# Code Review

对代码变更进行全面审查，检查代码质量、安全性、性能和规范合规性。

## 使用场景

- "Review 这个 PR 的代码"
- "检查我刚写的代码有没有问题"
- "审查 apps/services/user_service.py 的实现"

## 审查维度

### 1. 正确性

- 逻辑是否正确，是否覆盖了边界情况
- 异步代码是否正确使用 await
- 数据库操作是否在事务中（需要原子性时）
- 错误处理是否完整（不吞异常、不漏 case）

### 2. 安全性

- SQL 是否使用参数化查询（$1, $2），禁止字符串拼接
- 用户输入是否经过验证（Pydantic Field validators）
- 敏感数据是否暴露在日志或响应中
- API 端点是否有正确的认证/权限检查
- 是否有硬编码的密钥或 token

### 3. 性能

- 是否有 N+1 查询问题
- 是否在循环中做了不必要的 IO 操作
- 大列表是否有分页
- 是否有不必要的全表扫描（缺少索引）
- 前端是否有不必要的重渲染

### 4. 命名规范

#### Python
| 类型 | 规范 | 示例 |
|------|------|------|
| 文件 | snake_case | `user_service.py` |
| 函数 | snake_case，动词开头 | `get_user_by_id()`, `create_api_key()` |
| 变量 | snake_case | `user_count`, `is_active` |
| 类 | PascalCase | `UserService`, `ApiKeyManager` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `DEFAULT_PAGE_SIZE` |
| 私有 | 前缀下划线 | `_validate_email()`, `_pool` |
| 布尔变量 | is_/has_/can_ 前缀 | `is_active`, `has_permission` |

#### TypeScript / Vue
| 类型 | 规范 | 示例 |
|------|------|------|
| 文件（组件） | PascalCase | `UserCard.vue`, `ModelList.vue` |
| 文件（工具） | camelCase | `useAuth.ts`, `formatDate.ts` |
| 组件名 | PascalCase | `<UserCard />`, `<ModelList />` |
| 函数 | camelCase，动词开头 | `getUserList()`, `handleSubmit()` |
| 变量 | camelCase | `userCount`, `isLoading` |
| 类型/接口 | PascalCase | `interface UserProfile`, `type ApiResponse` |
| 常量 | UPPER_SNAKE_CASE | `MAX_PAGE_SIZE`, `API_BASE_URL` |
| Composable | use 前缀 | `useAuth()`, `usePagination()` |
| 事件处理 | handle 前缀 | `handleClick()`, `handleSubmit()` |
| 布尔变量 | is/has/can/should 前缀 | `isLoading`, `hasError` |
| Props | 名词或形容词 | `user`, `disabled`, `modelList` |
| Emits | 动词或动词短语 | `update`, `delete`, `change-page` |

#### 数据库
| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | snake_case 复数 | `users`, `api_keys`, `usage_logs` |
| 列名 | snake_case | `created_at`, `user_id`, `is_active` |
| 索引 | idx_表名_列名 | `idx_users_email`, `idx_usage_logs_user_id` |
| 外键 | fk_表名_引用表 | `fk_api_keys_users` |
| Schema | snake_case | `aihelms`, `public` |

#### API 路径
| 规范 | 示例 |
|------|------|
| 复数名词 | `/api/v1/users`, `/api/v1/api-keys` |
| kebab-case | `/api/v1/usage-logs` |
| 嵌套资源 | `/api/v1/users/{id}/api-keys` |
| 动作用动词 | `/api/v1/auth/login`, `/api/v1/auth/refresh` |

### 5. 架构合规

- 路由层（api/）只做参数解析和响应序列化，不写业务逻辑
- 服务层（services/）处理业务逻辑，不直接返回 HTTP 响应
- 数据库操作在服务层完成，不在路由层直接查询
- 前端组件不直接调用 fetch，走 shared API 层
- admin 和 web 不互相引用，共享代码走 shared 包

### 6. 代码风格

- 函数长度不超过 50 行（超过应拆分）
- 文件长度不超过 500 行（超过应拆分模块）
- 嵌套不超过 3 层（超过应提前 return 或抽取函数）
- 参数不超过 5 个（超过应用对象封装）
- 不留被注释掉的代码
- 不留 TODO 注释（要么做要么删）
- 不留 console.log / print 调试语句

### 7. 类型安全

#### Python
- 所有公开函数有完整类型注解（参数 + 返回值）
- 不用 `Any`（除非确实无法确定）
- 用 `TypedDict` 代替 `dict[str, Any]`
- 可选字段用 `X | None` 而非 `Optional[X]`

#### TypeScript
- strict 模式，不用 `any`
- Props 用 `defineProps<T>()` 泛型
- Emits 用 `defineEmits<T>()` 泛型
- API 响应有明确类型，不用 `as any`

### 8. 测试

- 新功能是否有对应测试
- 测试是否覆盖正常和异常路径
- 测试命名是否清晰描述场景
- Mock 是否合理（不过度 mock）

## 输出格式

```markdown
## Code Review 结果

### 概要
- 文件: [文件列表]
- 总体评价: [优秀/良好/需要修改/需要重写]
- 问题数: Critical: X, Warning: X, Suggestion: X

### Critical（必须修复）
#### 1. [问题标题]
- **位置**: file.py:line
- **问题**: 具体描述
- **影响**: 可能造成的后果
- **修复**:
```python
# 修复前
...
# 修复后
...
```

### Warning（建议修复）
[同上格式]

### Suggestion（可选优化）
[同上格式]

### 优点
- [做得好的地方]
```

## 审查原则

- 关注影响大的问题，不纠结格式细节（有 lint 工具处理）
- 给出具体的修复建议，不只是指出问题
- 理解上下文再评价，不脱离场景谈"最佳实践"
- 区分"必须修"和"建议改"，不把所有问题都标为 critical
- 肯定做得好的地方，不只挑毛病
