import { request } from './request'
import type {
  Credential,
  CredentialListResult,
  CreateCredentialParams,
  UpdateCredentialParams,
  ProviderFieldsInfo,
} from '../types/credential'

export function getCredentials(page: number = 1, pageSize: number = 50, providerId?: number): Promise<CredentialListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (providerId) params.provider_id = providerId
  return request<CredentialListResult>('/api/v1/credentials', { params })
}

export function getCredentialById(id: number): Promise<Credential> {
  return request<Credential>(`/api/v1/credentials/${id}`)
}

export function createCredential(params: CreateCredentialParams): Promise<Credential> {
  return request<Credential>('/api/v1/credentials', { method: 'POST', body: params })
}

export function updateCredential(id: number, params: UpdateCredentialParams): Promise<Credential> {
  return request<Credential>(`/api/v1/credentials/${id}`, { method: 'PUT', body: params })
}

export function deleteCredential(id: number): Promise<null> {
  return request<null>(`/api/v1/credentials/${id}`, { method: 'DELETE' })
}

export async function getProviderFields(): Promise<ProviderFieldsInfo[]> {
  const result = await request<ProviderFieldsInfo[]>('/api/v1/credentials/provider-fields')
  return result
}
