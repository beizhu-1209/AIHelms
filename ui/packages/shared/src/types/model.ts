export interface ModelInfo {
  id: number
  name: string
  model_id: string
  category: string
  capabilities: string[]
  description: string
  is_active: boolean
  is_published: boolean
  visibility_type: string
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
  model_id?: string
  category?: string
  capabilities?: string[]
  description?: string
}

export interface UpdateModelParams {
  name?: string
  model_id?: string
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
  model_id_str?: string
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
  category?: string
  capabilities?: string[]
  description?: string
  is_published?: boolean
  requires_approval?: boolean
  has_anthropic_deployment?: boolean
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

export interface ModelVisibility {
  is_published: boolean
  visibility_type: string
  requires_approval: boolean
  department_ids: number[]
  departments: { id: number; name: string }[]
  user_ids: number[]
  user_count: number
}

export interface UpdateModelPublishParams {
  is_published?: boolean
  visibility_type?: string
  department_ids?: number[]
  requires_approval?: boolean
}

export interface ResyncAnthropicResult {
  deployments_synced: number
  deployment_errors: number
  keys_updated: number
}
