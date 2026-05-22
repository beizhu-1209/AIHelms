import { request } from './request'
import type {
  ApiKey,
  ApiKeyListResult,
  CreateApiKeyParams,
  UpdateApiKeyParams,
} from '../types/apiKey'

export function getApiKeys(
  page: number,
  pageSize: number,
  keyword?: string,
): Promise<ApiKeyListResult> {
  return request<ApiKeyListResult>('/api/v1/api-keys', {
    params: { page, page_size: pageSize, keyword },
  })
}

export function getApiKeyById(id: number): Promise<ApiKey> {
  return request<ApiKey>(`/api/v1/api-keys/${id}`)
}

export function createApiKey(params: CreateApiKeyParams): Promise<ApiKey> {
  return request<ApiKey>('/api/v1/api-keys', {
    method: 'POST',
    body: params,
  })
}

export function updateApiKey(id: number, params: UpdateApiKeyParams): Promise<ApiKey> {
  return request<ApiKey>(`/api/v1/api-keys/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function deleteApiKey(id: number): Promise<null> {
  return request<null>(`/api/v1/api-keys/${id}`, { method: 'DELETE' })
}
