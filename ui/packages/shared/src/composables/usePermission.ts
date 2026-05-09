import { computed } from 'vue'
import { useAuth } from './useAuth'

export function usePermission() {
  const { currentUser } = useAuth()

  const permissions = computed(() => currentUser.value?.permissions ?? [])

  function hasPermission(code: string): boolean {
    if (currentUser.value?.is_admin) {
      return true
    }
    return permissions.value.includes(code)
  }

  function hasAnyPermission(codes: string[]): boolean {
    return codes.some((code) => hasPermission(code))
  }

  return {
    permissions,
    hasPermission,
    hasAnyPermission,
  }
}
