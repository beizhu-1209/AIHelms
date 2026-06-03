import { toast } from '../utils/toast'
import { getLoginUrl } from '../utils/auth-redirect'

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

async function parseResponseJSON<T>(response: Response, silent: boolean): Promise<ApiResponse<T>> {
  let text: string
  try {
    text = await response.text()
  } catch {
    const message = '读取响应数据失败'
    if (!silent) toast.error(message)
    throw new Error(message)
  }
  try {
    return JSON.parse(text) as ApiResponse<T>
  } catch {
    const message = `服务器返回了非 JSON 数据: ${text.slice(0, 200)}`
    if (!silent) toast.error(message)
    throw new Error(message)
  }
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

  const isFormData = body instanceof FormData
  const headers: Record<string, string> = {}
  if (!isFormData) {
    headers['Content-Type'] = 'application/json'
  }

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const fetchOptions: RequestInit = { method, headers }
  if (body && method !== 'GET') {
    fetchOptions.body = isFormData ? (body as FormData) : JSON.stringify(body)
  }

  let response: Response
  try {
    response = await fetch(fullUrl, fetchOptions)
  } catch {
    const message = '网络连接失败，请检查网络'
    if (!silent) toast.error(message)
    throw new Error(message)
  }

  const json = await parseResponseJSON<T>(response, silent)

  if (response.status === 401) {
    if (!silent) {
      localStorage.removeItem('aihelms_token')
      window.location.href = getLoginUrl()
    }
    const message = json.message || '用户名或密码错误'
    throw new Error(message)
  }

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
