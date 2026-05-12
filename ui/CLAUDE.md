# ui/ — Frontend

## Architecture

npm workspace monorepo with three packages:

- **shared** (`@aihelms/shared`): Shared types, API wrappers, utilities
- **admin**: Admin dashboard
- **web**: User-facing app (model marketplace, etc.)

Rule: admin and web must not import from each other. Shared code goes through `@aihelms/shared`.

## Tooling

```bash
# Install dependencies
npm install

# Dev (HMR hot reload, save to see changes)
npm run dev --workspace=@aihelms/web       # User app → http://localhost:4002
npm run dev --workspace=@aihelms/admin     # Admin → http://localhost:4001/admin/

# Build
npm run build                              # All packages
npm run build --workspace=@aihelms/web     # Web only
npm run build --workspace=@aihelms/admin   # Admin only

# Lint
npm run lint

# Type check
npm run type-check --workspaces --if-present

# Test
npm test
```

## Coding Style

### Component Structure

```vue
<!-- ✅ Good — Composition API + script setup -->
<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAuth } from '@aihelms/shared'

interface Props {
  userId: string
  disabled?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  delete: [userId: string]
}>()

const isLoading = ref(false)
const displayName = computed(() => props.userId.slice(0, 8))

function handleDelete() {
  emit('delete', props.userId)
}
</script>

<template>
  <div class="flex items-center gap-2">
    <span class="text-sm text-gray-700">{{ displayName }}</span>
    <button
      class="btn-danger"
      :disabled="disabled || isLoading"
      @click="handleDelete"
    >
      Delete
    </button>
  </div>
</template>
```

```vue
<!-- ❌ Bad — Options API, no types -->
<script>
export default {
  props: ['userId'],
  data() {
    return { isLoading: false }
  },
  methods: {
    handleDelete() {
      this.$emit('delete', this.userId)
    }
  }
}
</script>
```

### Naming

| Type | Convention | Good | Bad |
|------|-----------|------|-----|
| Component file | PascalCase | `UserCard.vue` | `user-card.vue`, `userCard.vue` |
| Utility file | camelCase | `useAuth.ts`, `formatDate.ts` | `UseAuth.ts`, `format-date.ts` |
| Component name | PascalCase | `<UserCard />` | `<user-card />` |
| Function | camelCase, verb prefix | `getUserList()` | `userList()`, `data()` |
| Variable | camelCase, meaningful | `userCount`, `isLoading` | `temp`, `data`, `x` |
| Type/Interface | PascalCase | `interface UserProfile` | `interface userProfile` |
| Constant | UPPER_SNAKE_CASE | `API_BASE_URL` | `apiBaseUrl` |
| Composable | use prefix | `useAuth()` | `auth()`, `getAuth()` |
| Event handler | handle prefix | `handleSubmit()` | `submit()`, `onSubmit()` |
| Boolean | is/has/can prefix | `isLoading`, `hasError` | `loading`, `error` |
| Props | noun or adjective | `user`, `disabled` | `handleClick` |
| Emits | verb or verb phrase | `update`, `delete` | `onUpdate` |

### API Calls

```typescript
// ✅ Good — centralized in shared
// shared/src/api/user.ts
import { request } from '../utils/request'
import type { User, CreateUserParams } from '../types/user'

export function getUsers(page: number, pageSize: number) {
  return request<{ items: User[]; total: number }>('/api/v1/users', {
    params: { page, page_size: pageSize },
  })
}

export function createUser(params: CreateUserParams) {
  return request<User>('/api/v1/users', {
    method: 'POST',
    body: params,
  })
}

// Usage in component
import { getUsers } from '@aihelms/shared'
const { data } = await getUsers(1, 20)
```

```typescript
// ❌ Bad — direct fetch in component
const res = await fetch('/api/v1/users')
const data = await res.json()
```

### Type Definitions

```typescript
// ✅ Good — explicit types, strict mode
interface User {
  id: string
  email: string
  nickname: string
  isActive: boolean
  createdAt: string
}

interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

// ❌ Bad — any, no types
const user: any = await getUser(id)
const data = res as any
```

### Styling

```vue
<!-- ✅ Good — TailwindCSS utility classes -->
<template>
  <div class="flex items-center gap-4 rounded-lg bg-white p-4 shadow-sm">
    <h2 class="text-lg font-semibold text-gray-900">{{ title }}</h2>
  </div>
</template>

<!-- ❌ Bad — custom CSS / inline styles -->
<template>
  <div class="card" :style="{ padding: '16px' }">
    <h2>{{ title }}</h2>
  </div>
</template>

<style scoped>
.card {
  display: flex;
  background: white;
  border-radius: 8px;
}
</style>
```

### Routing

```typescript
// ✅ Good — lazy loading + auth meta
const routes = [
  {
    path: '/dashboard',
    component: () => import('../views/Dashboard.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false },
  },
]

// ❌ Bad — static import
import Dashboard from '../views/Dashboard.vue'
const routes = [
  { path: '/dashboard', component: Dashboard },
]
```

## Verification

- Use dev server (`./dev/start-web`) to verify frontend changes, Vite HMR auto-reloads on save, no restart needed
- Do not use `npm run build` to verify changes during development

## Constraints

- File ≤500 lines, template ≤100 lines
- No `var`, no `==` (use `===`)
- No `console.log` (remove after debugging)
- No `any`, no `as any`
- No custom CSS, no inline styles
- admin and web must not import from each other
- Components must not call fetch/axios directly — use shared API layer
