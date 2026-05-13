export interface ModelInfo {
  id: number
  name: string
  model_id: string
  category: string
  capabilities: string[]
  description: string
  is_active: boolean
  deployment_count: number
  created_at: string | null
  updated_at: string | null
  deployments?: Deployment[]
}

export interface Deployment {
  id: number
  model_id: number
  credential_id: number | null
  credential_name: string | null
  litellm_model_id: string | null
  litellm_params: Record<string, unknown>
  model_info: Record<string, unknown>
  deploy_name: string
  billing_type: string
  cost_per_call: string | null
  monthly_call_quota: number | null
  monthly_call_used: number
  is_active: boolean
  created_at: string | null
}

export interface CreateModelParams {
  name: string
  model_id: string
  category?: string
  capabilities?: string[]
  description?: string
}

export interface UpdateModelParams {
  name?: string
  category?: string
  capabilities?: string[]
  description?: string
  is_active?: boolean
}

export interface CreateDeploymentParams {
  litellm_params: Record<string, unknown>
  credential_id?: number | null
  deploy_name?: string
  billing_type?: string
  cost_per_call?: number | null
  monthly_call_quota?: number | null
  model_info?: Record<string, unknown> | null
}

export interface UpdateDeploymentParams {
  litellm_params?: Record<string, unknown>
  credential_id?: number | null
  deploy_name?: string
  billing_type?: string
  cost_per_call?: number | null
  monthly_call_quota?: number | null
  model_info?: Record<string, unknown> | null
  is_active?: boolean
}

export interface ModelListResult {
  items: ModelInfo[]
  total: number
  page: number
  page_size: number
}

export interface ActiveModel {
  id: number
  name: string
  model_id: string
}

export interface AccessGroup {
  id: number
  group_name: string
  description: string
  model_ids: string[]
  is_active: boolean
  created_at: string | null
}

export interface CreateAccessGroupParams {
  group_name: string
  description?: string
  model_ids?: string[]
}

export interface UpdateAccessGroupParams {
  group_name?: string
  description?: string
  model_ids?: string[]
  is_active?: boolean
}

export interface RouterSettings {
  id?: number
  routing_strategy: string
  fallbacks: unknown[]
  allowed_fails: number
  cooldown_time: number
  num_retries: number
  timeout: number
  config: Record<string, unknown>
  updated_at?: string | null
}

export interface UpdateRouterSettingsParams {
  routing_strategy?: string
  fallbacks?: unknown[]
  allowed_fails?: number
  cooldown_time?: number
  num_retries?: number
  timeout?: number
  config?: Record<string, unknown>
}
