import { toast } from '../utils/toast'

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

interface RequestOptions {
  method?: string
  body?: unknown
  params?: Record<string, string | number | boolean | undefined>
  silent?: boolean
}

function getToken(): string | null {
  return localStorage.getItem('aihelms_token')
}

export async function request<T>(url: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params, silent = false } = options

  let fullUrl = url
  if (params) {
    const searchParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        searchParams.append(key, String(value))
      }
    })
    const queryString = searchParams.toString()
    if (queryString) {
      fullUrl += `?${queryString}`
    }
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const fetchOptions: RequestInit = { method, headers }
  if (body && method !== 'GET') {
    fetchOptions.body = JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(fullUrl, fetchOptions)
  } catch {
    const message = '网络连接失败，请检查网络'
    if (!silent) toast.error(message)
    throw new Error(message)
  }

  if (response.status === 401) {
    localStorage.removeItem('aihelms_token')
    window.location.href = '/admin/login'
    throw new Error('未认证')
  }

  const json: ApiResponse<T> = await response.json()

  if (!response.ok) {
    const message = json.message || `请求失败: ${response.status}`
    if (!silent) toast.error(message)
    throw new Error(message)
  }

  if (!silent && method !== 'GET' && json.message && json.message !== 'ok') {
    toast.success(json.message)
  }

  return json.data
}
