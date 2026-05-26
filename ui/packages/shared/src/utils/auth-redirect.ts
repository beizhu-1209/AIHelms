/**
 * 根据当前页面所在的子应用，计算登录页 URL。
 * 用于 401 跳转和 logout 跳转。
 *
 * - 当前在 `/admin/*` → `/admin/login`
 * - 其他（包括根路径、未知路径）→ `/login`
 */
export function getLoginUrl(): string {
  if (typeof window === 'undefined') return '/login'
  return window.location.pathname.startsWith('/admin') ? '/admin/login' : '/login'
}
