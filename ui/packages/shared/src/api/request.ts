import { toast } from '../utils/toast'
import { getLoginUrl } from '../utils/auth-redirect'
import { getCurrentLocale } from '../i18n'
import errorsZh from '../i18n/locales/zh-CN/errors.json'
import errorsEn from '../i18n/locales/en-US/errors.json'

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

type LocalErrorKey = keyof typeof errorsZh

function formatLocalMessage(template: string, params: Record<string, string | number> = {}): string {
  return Object.entries(params).reduce(
    (message, [key, value]) => message.split(`{${key}}`).join(String(value)),
    template
  )
}

function getLocalErrorMessage(key: LocalErrorKey, params?: Record<string, string | number>): string {
  const messages = getCurrentLocale() === 'en-US' ? errorsEn : errorsZh
  return formatLocalMessage(messages[key] || errorsZh[key] || key, params)
}

function getToken(): string | null {
  return localStorage.getItem('aihelms_token')
}

async function parseResponseJSON<T>(response: Response, silent: boolean): Promise<ApiResponse<T>> {
  let text: string
  try {
    text = await response.text()
  } catch {
    const message = getLocalErrorMessage('error.readResponse')
    if (!silent) toast.error(message)
    throw new Error(message)
  }
  try {
    return JSON.parse(text) as ApiResponse<T>
  } catch {
    const message = getLocalErrorMessage('error.nonJsonResponse', { body: text.slice(0, 200) })
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
  headers['Accept-Language'] = getCurrentLocale()
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
    const message = getLocalErrorMessage('error.network')
    if (!silent) toast.error(message)
    throw new Error(message)
  }

  const json = await parseResponseJSON<T>(response, silent)

  if (response.status === 401) {
    if (!silent) {
      localStorage.removeItem('aihelms_token')
      window.location.href = getLoginUrl()
    }
    const message = json.message || getLocalErrorMessage('error.unauthorized')
    throw new Error(message)
  }

  if (!response.ok) {
    const message = json.message || getLocalErrorMessage('error.requestFailed', { status: response.status })
    if (!silent) toast.error(message)
    throw new Error(message)
  }

  if (!silent && method !== 'GET' && json.message && json.message !== 'ok') {
    toast.success(json.message)
  }

  return json.data
}
