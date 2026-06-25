import { request } from './request'
import type {
  AiKey,
  AiKeyRateLimitMode,
  AiKeyListResult,
  CreateAiKeyParams,
  UpdateAiKeyParams,
  BatchCreateAiKeyParams,
  BatchCreateResult,
  MyKeysResult,
  IdentityListResult,
  IdentityUserItem,
  IdentityDepartmentItem,
  IdentityProjectItem,
  AiKeyModelLimit,
  SetModelLimitItem,
} from '../types/ai-key'

export function getAiKeys(
  page: number = 1,
  pageSize: number = 20,
  ownerType?: string,
  ownerId?: number,
  keyType?: string,
): Promise<AiKeyListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (ownerType) params.owner_type = ownerType
  if (ownerId) params.owner_id = ownerId
  if (keyType) params.key_type = keyType
  return request<AiKeyListResult>('/api/v1/ai-keys', { params })
}

export function getAiKeyById(id: number): Promise<AiKey> {
  return request<AiKey>(`/api/v1/ai-keys/${id}`)
}

export function createAiKey(params: CreateAiKeyParams): Promise<AiKey> {
  return request<AiKey>('/api/v1/ai-keys', {
    method: 'POST',
    body: params,
  })
}

export function batchCreateAiKeys(params: BatchCreateAiKeyParams): Promise<BatchCreateResult[]> {
  return request<BatchCreateResult[]>('/api/v1/ai-keys/batch', {
    method: 'POST',
    body: params,
  })
}

export function updateAiKey(id: number, params: UpdateAiKeyParams): Promise<AiKey> {
  return request<AiKey>(`/api/v1/ai-keys/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function toggleAiKey(id: number): Promise<AiKey> {
  return request<AiKey>(`/api/v1/ai-keys/${id}/toggle`, {
    method: 'PUT',
  })
}

export function deleteAiKey(id: number): Promise<null> {
  return request<null>(`/api/v1/ai-keys/${id}`, { method: 'DELETE' })
}

export function getMyKeys(): Promise<MyKeysResult> {
  return request<MyKeysResult>('/api/v1/ai-keys/my')
}

export function getIdentityList(
  tab: 'user',
  page?: number,
  pageSize?: number,
  keyword?: string,
): Promise<IdentityListResult<IdentityUserItem>>
export function getIdentityList(
  tab: 'department',
  page?: number,
  pageSize?: number,
  keyword?: string,
): Promise<IdentityListResult<IdentityDepartmentItem>>
export function getIdentityList(
  tab: 'project',
  page?: number,
  pageSize?: number,
  keyword?: string,
): Promise<IdentityListResult<IdentityProjectItem>>
export function getIdentityList(
  tab: string,
  page: number = 1,
  pageSize: number = 20,
  keyword?: string,
): Promise<IdentityListResult<unknown>> {
  const params: Record<string, string | number> = { tab, page, page_size: pageSize }
  if (keyword) params.keyword = keyword
  return request<IdentityListResult<unknown>>('/api/v1/ai-keys/identity', { params })
}

export function getModelLimits(keyId: number): Promise<AiKeyModelLimit[]> {
  return request<AiKeyModelLimit[]>(`/api/v1/ai-keys/${keyId}/model-limits`)
}

export function setModelLimits(keyId: number, limits: SetModelLimitItem[]): Promise<AiKeyModelLimit[]> {
  return request<AiKeyModelLimit[]>(`/api/v1/ai-keys/${keyId}/model-limits`, {
    method: 'PUT',
    body: { limits },
  })
}

export function deleteModelLimit(keyId: number, modelId: number): Promise<null> {
  return request<null>(`/api/v1/ai-keys/${keyId}/model-limits/${modelId}`, {
    method: 'DELETE',
  })
}

export interface BatchUpdateResourcesParams {
  key_ids?: number[]
  user_ids?: number[]
  models?: string[]
  mcps?: number[]
  skills?: number[]
  agents?: number[]
  budget_limit?: number | null
  budget_hard_limit?: boolean
  budget_duration?: string | null
  budget_scope?: string
  budget_models_total?: number | null
  budget_mcps_total?: number | null
  budget_models_per?: string
  budget_mcps_per?: string
  model_budgets?: Record<string, number> | null
  mcp_budgets?: Record<string, number> | null
  update_rate_limit?: boolean
  rate_limit_mode?: AiKeyRateLimitMode | null
  tpm_limit?: number | null
  rpm_limit?: number | null
  max_parallel_requests?: number | null
  rate_limits?: SetModelLimitItem[] | null
}

export interface BatchUpdateResult {
  successes: number[]
  failures: { key_id: number; error: string }[]
}

export function batchUpdateResources(params: BatchUpdateResourcesParams): Promise<BatchUpdateResult> {
  return request<BatchUpdateResult>('/api/v1/ai-keys/batch', {
    method: 'PUT',
    body: params,
  })
}
