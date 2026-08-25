# API 响应消息参考

本文件记录各模块 API 的 message 返回值，供开发时查阅。

## 通用规则

- GET 请求：message 固定 `"ok"`
- POST/PUT/DELETE 请求：message 返回业务语义描述
- 错误响应：message 描述具体原因，禁止暴露系统内部信息

## 状态码

| code | 含义 | 触发场景 |
|------|------|---------|
| 200 | 操作成功 | 正常完成 |
| 400 | 参数错误 | 缺少必填项、格式不对、旧密码错误 |
| 401 | 未认证 | token 缺失或过期 |
| 403 | 权限不足 | 无对应权限 |
| 404 | 资源不存在 | ID 无效或已删除 |
| 409 | 数据冲突 | 重复创建、有关联数据无法删除 |
| 422 | 参数校验失败 | Pydantic 校验不通过 |
| 500 | 服务器内部错误 | 未捕获异常（兜底） |

---

## 认证模块 (auth)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/auth/login | POST | 登录成功 | 账号或密码错误；账户已被禁用 |
| /api/v1/auth/password | PUT | 密码修改成功 | 旧密码错误；用户不存在 |

## 用户模块 (users)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/users | POST | 用户创建成功 | 用户名已存在；邮箱已被注册 |
| /api/v1/users/{id} | PUT | 用户更新成功 | 用户不存在；邮箱已被注册 |
| /api/v1/users/{id} | DELETE | 用户删除成功 | 用户不存在 |
| /api/v1/users/{id}/password | PUT | 密码重置成功 | 用户不存在 |
| /api/v1/users/{id}/roles | PUT | 角色更新成功 | 用户不存在 |
| /api/v1/users/{id}/departments | PUT | 部门更新成功 | 用户不存在 |
| /api/v1/users/{id}/projects | PUT | 项目更新成功 | 用户不存在 |

## 角色模块 (roles)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/roles | POST | 角色创建成功 | 角色名已存在 |
| /api/v1/roles/{id} | PUT | 角色更新成功 | 角色不存在 |
| /api/v1/roles/{id} | DELETE | 角色删除成功 | 角色不存在；该角色下有用户，无法删除 |
| /api/v1/roles/{id}/permissions | PUT | 权限更新成功 | 角色不存在 |

## 部门模块 (departments)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/departments | POST | 部门创建成功 | 父部门不存在 |
| /api/v1/departments/{id} | PUT | 部门更新成功 | 部门不存在 |
| /api/v1/departments/{id} | DELETE | 部门删除成功 | 部门不存在；该部门下有子部门或成员，无法删除 |
| /api/v1/departments/{id}/members | POST | 成员添加成功 | 部门不存在；用户不存在；用户已在该部门 |
| /api/v1/departments/{id}/members/{uid} | DELETE | 成员移除成功 | 部门不存在；用户不在该部门 |
| /api/v1/departments/{id}/managers | PUT | 管理员更新成功 | 部门不存在 |

## 项目模块 (projects)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/projects | POST | 项目创建成功 | — |
| /api/v1/projects/{id} | PUT | 项目更新成功 | 项目不存在 |
| /api/v1/projects/{id} | DELETE | 项目删除成功 | 项目不存在；该项目下有成员，无法删除 |
| /api/v1/projects/{id}/members | POST | 成员添加成功 | 项目不存在；用户不存在；用户已在该项目 |
| /api/v1/projects/{id}/members/{uid} | DELETE | 成员移除成功 | 项目不存在；用户不在该项目 |

## 供应商模块 (providers)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/providers | POST | 供应商创建成功 | — |
| /api/v1/providers/{id} | PUT | 供应商更新成功 | 供应商不存在 |
| /api/v1/providers/{id} | DELETE | 供应商删除成功 | 供应商不存在；该供应商下有凭证，无法删除 |

## 凭证模块 (credentials)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/credentials | POST | 凭证添加成功 | 凭证名已存在 |
| /api/v1/credentials/{id} | PUT | 凭证更新成功 | 凭证不存在 |
| /api/v1/credentials/{id} | DELETE | 凭证删除成功 | 凭证不存在；该凭证被渠道引用，无法删除 |

## 模型模块 (models)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/models | POST | 模型创建成功 | 模型 ID 已存在 |
| /api/v1/models/{id} | PUT | 模型更新成功 | 模型不存在 |
| /api/v1/models/{id} | DELETE | 模型删除成功 | 模型不存在 |
| /api/v1/models/{id}/deployments | POST | 渠道创建成功 | 模型不存在；凭证不存在 |
| /api/v1/models/{id}/deployments/{did} | PUT | 渠道更新成功 | 部署不存在 |
| /api/v1/models/{id}/deployments/{did} | DELETE | 渠道删除成功 | 部署不存在 |
| /api/v1/models/access-groups | POST | 访问组创建成功 | 访问组名已存在 |
| /api/v1/models/access-groups/{id} | PUT | 访问组更新成功 | 访问组不存在 |
| /api/v1/models/access-groups/{id} | DELETE | 访问组删除成功 | 访问组不存在 |
| /api/v1/models/router-settings/current | PUT | 路由设置更新成功 | — |

## AI Key 模块 (ai-keys)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/ai-keys | POST | AI Key 创建成功 | 名称已存在；归属对象不存在 |
| /api/v1/ai-keys/{id} | PUT | AI Key 更新成功 | Key 不存在 |
| /api/v1/ai-keys/{id}/toggle | PUT | 状态切换成功 | Key 不存在 |
| /api/v1/ai-keys/{id} | DELETE | AI Key 删除成功 | Key 不存在 |
| /api/v1/ai-keys/{id}/model-limits | PUT | 模型限制更新成功 | Key 不存在 |
| /api/v1/ai-keys/{id}/model-limits/{mid} | DELETE | 模型限制删除成功 | 限制记录不存在 |
| /api/v1/ai-keys/batch | PUT | 批量更新成功 | — |

## 模型测试 (access-test)

| 接口 | 方法 | 成功 message | 错误 message |
|------|------|-------------|-------------|
| /api/v1/access-test/test | POST | 模型测试完成 | LiteLLM 服务不可用；模型不存在 |

---

## 全局兜底错误

以下错误由全局异常处理器自动返回，无需在各模块手动处理：

| 场景 | code | message |
|------|------|---------|
| 未捕获的 Python 异常 | 500 | 服务器内部错误，请稍后重试 |
| Pydantic 请求校验失败 | 422 | 参数校验失败: {字段}: {原因} |
| 网络连接失败（前端） | — | 网络连接失败，请检查网络 |

## LiteLLM 同步失败处理

LiteLLM 同步失败不影响平台功能：
- 平台数据库写入成功即返回成功
- 同步失败记录日志，标记状态待重试
- 不向用户暴露 LiteLLM 内部错误
