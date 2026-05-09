# 运行测试

完整的测试执行流程，包含后端和前端测试、lint 检查、覆盖率报告。

## 快速测试（日常开发）

```bash
# 后端：运行所有测试
cd apps && python -m pytest -v

# 前端：运行所有测试
cd ui && pnpm test
```

## 完整测试流程

### Step 1: 后端测试

```bash
cd apps

# 运行所有测试（详细输出）
python -m pytest -v

# 运行单个测试文件
python -m pytest tests/test_users.py -v

# 运行匹配名称的测试
python -m pytest -k "test_create_user" -v

# 带覆盖率报告
python -m pytest --cov=. --cov-report=html --cov-report=term-missing

# 只运行快速测试（跳过标记为 slow 的）
python -m pytest -m "not slow" -v

# 失败时立即停止
python -m pytest -x -v
```

### Step 2: 后端 Lint & 格式化

```bash
cd apps

# 格式化检查（不修改文件）
black --check .

# 格式化（修改文件）
black .

# Lint 检查
ruff check .

# Lint 自动修复
ruff check . --fix

# 完整检查流程
black --check . && ruff check .
```

### Step 3: 前端测试

```bash
cd ui

# 运行所有包的测试
pnpm test

# 运行单个包的测试
pnpm --filter web test
pnpm --filter admin test

# 监听模式（开发时使用）
pnpm --filter web test -- --watch

# 带覆盖率
pnpm --filter web test -- --coverage
```

### Step 4: 前端 Lint & 类型检查

```bash
cd ui

# ESLint 检查
pnpm lint

# 类型检查
pnpm type-check

# 完整检查流程
pnpm lint && pnpm type-check
```

## CI 完整检查（提交前必须通过）

```bash
# 后端
cd apps && black --check . && ruff check . && python -m pytest -v

# 前端
cd ui && pnpm lint && pnpm type-check && pnpm test
```

## 测试编写规范

### 后端测试（pytest）

```python
# tests/test_users.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user_with_valid_data_returns_201():
    """创建用户 - 有效数据应返回 201"""
    # Arrange
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123"
    }

    # Act
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/users", json=user_data)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == 200
    assert data["data"]["username"] == "testuser"

@pytest.mark.asyncio
async def test_create_user_with_duplicate_email_returns_409():
    """创建用户 - 重复邮箱应返回 409"""
    # ...
```

### 前端测试（Vitest）

```typescript
// src/__tests__/UserCard.test.ts
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import UserCard from '../components/UserCard.vue'

describe('UserCard', () => {
  it('should display username', () => {
    const wrapper = mount(UserCard, {
      props: {
        user: { id: 1, username: 'test', email: 'test@example.com' }
      }
    })
    expect(wrapper.text()).toContain('test')
  })

  it('should emit delete event on button click', async () => {
    const wrapper = mount(UserCard, {
      props: { user: { id: 1, username: 'test', email: 'test@example.com' } }
    })
    await wrapper.find('[data-testid="delete-btn"]').trigger('click')
    expect(wrapper.emitted('delete')).toHaveLength(1)
    expect(wrapper.emitted('delete')![0]).toEqual([1])
  })
})
```

## 测试命名规范

- 后端：`test_<功能>_<场景>_<预期结果>`
  - `test_create_user_with_valid_data_returns_201`
  - `test_login_with_wrong_password_returns_401`
- 前端：`describe('组件名')` + `it('should 行为描述')`
  - `it('should display username')`
  - `it('should emit delete event on button click')`

## 覆盖率目标

| 模块 | 最低覆盖率 |
|------|-----------|
| core/ | 90% |
| services/ | 80% |
| api/ | 75% |
| 前端组件 | 70% |
| 前端工具函数 | 90% |
