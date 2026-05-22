import { ref } from 'vue'
import { login as apiLogin, getMe } from '../api/auth'
import type { CurrentUser } from '../types/auth'
import { getLoginUrl } from '../utils/auth-redirect'

const TOKEN_KEY = 'aihelms_token'
const currentUser = ref<CurrentUser | null>(null)
const isAuthenticated = ref(!!localStorage.getItem(TOKEN_KEY))

export function useAuth() {
  async function login(username: string, password: string): Promise<void> {
    const data = await apiLogin(username, password)
    localStorage.setItem(TOKEN_KEY, data.access_token)
    isAuthenticated.value = true
    await fetchCurrentUser()
  }

  function logout(): void {
    localStorage.removeItem(TOKEN_KEY)
    isAuthenticated.value = false
    currentUser.value = null
    window.location.href = getLoginUrl()
  }

  async function fetchCurrentUser(): Promise<CurrentUser | null> {
    try {
      const user = await getMe()
      currentUser.value = user
      return user
    } catch {
      logout()
      return null
    }
  }

  function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY)
  }

  return {
    currentUser,
    isAuthenticated,
    login,
    logout,
    fetchCurrentUser,
    getToken,
  }
}
