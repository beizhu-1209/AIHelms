# ui/ — 前端

- 详细编码规范见 `.claude/rules/frontend.md`
- 架构：pnpm workspace monorepo（shared / admin / web）
- 组件风格：Composition API + `<script setup lang="ts">`
- CSS：TailwindCSS 原子类，不写自定义 CSS
- API 调用统一走 `@aihelms/shared`，组件不直接 fetch
- Lint：`pnpm lint && pnpm type-check`
- 测试：`pnpm test`
