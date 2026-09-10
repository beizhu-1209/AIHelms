# Run Tests

Complete test execution flow including backend and frontend tests, lint checks, and coverage reports.

## Quick Test (daily development)

```bash
# Backend: run all tests
cd apps && python -m pytest -v

# Frontend: run all tests
cd ui && pnpm test
```

## Full Test Flow

### Step 1: Backend Tests

```bash
cd apps

# Run all tests (verbose)
python -m pytest -v

# Run single test file
python -m pytest tests/test_users.py -v

# Run tests matching name
python -m pytest -k "test_create_user" -v

# With coverage report
python -m pytest --cov=. --cov-report=html --cov-report=term-missing

# Only fast tests (skip slow-marked)
python -m pytest -m "not slow" -v

# Stop on first failure
python -m pytest -x -v
```

### Step 2: Backend Lint & Format

```bash
cd apps

# Format check (no file changes)
black --check .

# Format (modify files)
black .

# Lint check
ruff check .

# Lint auto-fix
ruff check . --fix

# Full check
black --check . && ruff check .
```

### Step 3: Frontend Tests

```bash
cd ui

# Run all package tests
pnpm test

# Run single package tests
pnpm --filter web test
pnpm --filter admin test

# Watch mode (during development)
pnpm --filter web test -- --watch

# With coverage
pnpm --filter web test -- --coverage
```

### Step 4: Frontend Lint & Type Check

```bash
cd ui

# ESLint check
pnpm lint

# Type check
pnpm type-check

# Full check
pnpm lint && pnpm type-check
```

## CI Full Check (must pass before commit)

```bash
# Backend
cd apps && black --check . && ruff check . && python -m pytest -v

# Frontend
cd ui && pnpm lint && pnpm type-check && pnpm test
```

## Test Writing Conventions

### Backend Tests (pytest)

```python
# tests/test_users.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user_with_valid_data_returns_201():
    """Create user - valid data should return 201"""
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
    """Create user - duplicate email should return 409"""
    # ...
```

### Frontend Tests (Vitest)

```typescript
// src/__tests__/UserCard.test.ts
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
import UserCard from '../components/UserCard.vue'

describe('UserCard', () => {
  it('should display username', () => {
    const wrapper = mount(UserCard, {
      props: {
        user: { id: '1', username: 'test', email: 'test@example.com' }
      }
    })
    expect(wrapper.text()).toContain('test')
  })

  it('should emit delete event on button click', async () => {
    const wrapper = mount(UserCard, {
      props: { user: { id: '1', username: 'test', email: 'test@example.com' } }
    })
    await wrapper.find('[data-testid="delete-btn"]').trigger('click')
    expect(wrapper.emitted('delete')).toHaveLength(1)
    expect(wrapper.emitted('delete')![0]).toEqual(['1'])
  })
})
```

## Test Naming Conventions

- Backend: `test_<feature>_<scenario>_<expected_result>`
  - `test_create_user_with_valid_data_returns_201`
  - `test_login_with_wrong_password_returns_401`
- Frontend: `describe('ComponentName')` + `it('should behavior')`
  - `it('should display username')`
  - `it('should emit delete event on button click')`

## Coverage Targets

| Module | Minimum Coverage |
|--------|-----------------|
| core/ | 90% |
| services/ | 80% |
| api/ | 75% |
| Frontend components | 70% |
| Frontend utilities | 90% |
