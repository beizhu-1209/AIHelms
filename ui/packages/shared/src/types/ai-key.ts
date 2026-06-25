export type BudgetScope = 'unified' | 'per_type' | 'per_resource'
export type BudgetSubScope = 'unified' | 'each'
export type AiKeyRateLimitMode = 'none' | 'total' | 'per_model'

export interface AiKey {
  id: number
  name: string
  description: string
  key_type: 'personal_main' | 'personal_scene' | 'dept_main' | 'dept_scene' | 'project_main' | 'project_scene'
  owner_type: 'user' | 'department' | 'project'
  owner_id: number
  tags: string[]
  litellm_key_id: string | null
  litellm_key_alias: string | null
  models: string[]
  mcps: number[]
  skills: number[]
  agents: number[]
  budget_limit: string | null
  budget_used?: string | number | null
  budget_hard_limit: boolean
  budget_duration: string | null
  budget_scope: BudgetScope
  budget_models_total: string | null
  budget_mcps_total: string | null
  budget_models_per: BudgetSubScope
  budget_mcps_per: BudgetSubScope
  model_budgets: Record<string, number>
  mcp_budgets: Record<string, number>
  rate_limit_mode: AiKeyRateLimitMode
  tpm_limit: number | null
  rpm_limit: number | null
  max_parallel_requests: number | null
  scenario_id: number | null
  is_active: boolean
  created_by: number | null
  created_at: string | null
  updated_at: string | null
  expires_at: string | null
  last_used_at: string | null
  key_value?: string | null
}

export interface CreateAiKeyParams {
  name: string
  key_type: string
  owner_type: string
  owner_id: number
  description?: string
  tags?: string[]
  models?: string[]
  mcps?: number[]
  skills?: number[]
  agents?: number[]
  budget_limit?: number | null
  budget_hard_limit?: boolean
  budget_duration?: string | null
  budget_scope?: BudgetScope
  budget_models_total?: number | null
  budget_mcps_total?: number | null
  budget_models_per?: BudgetSubScope
  budget_mcps_per?: BudgetSubScope
  model_budgets?: Record<string, number> | null
  mcp_budgets?: Record<string, number> | null
  scenario_id?: number | null
  duration?: string | null
  rate_limit_mode?: AiKeyRateLimitMode
  tpm_limit?: number | null
  rpm_limit?: number | null
  max_parallel_requests?: number | null
  rate_limits?: RateLimitItem[] | null
}

export interface UpdateAiKeyParams {
  name?: string
  description?: string
  tags?: string[]
  models?: string[]
  mcps?: number[]
  skills?: number[]
  agents?: number[]
  budget_limit?: number | null
  budget_hard_limit?: boolean
  budget_duration?: string | null
  budget_scope?: BudgetScope
  budget_models_total?: number | null
  budget_mcps_total?: number | null
  budget_models_per?: BudgetSubScope
  budget_mcps_per?: BudgetSubScope
  model_budgets?: Record<string, number> | null
  mcp_budgets?: Record<string, number> | null
  scenario_id?: number | null
  rate_limit_mode?: AiKeyRateLimitMode
  tpm_limit?: number | null
  rpm_limit?: number | null
  max_parallel_requests?: number | null
  rate_limits?: RateLimitItem[] | null
}

export interface BatchCreateAiKeyParams {
  user_ids: number[]
  key_type: 'personal_scene'
  name_template: string
  description?: string
  models?: string[]
  mcps?: number[]
  skills?: number[]
  agents?: number[]
  budget_limit?: number | null
  budget_hard_limit?: boolean
  budget_duration?: string | null
  budget_scope?: BudgetScope
  budget_models_total?: number | null
  budget_mcps_total?: number | null
  budget_models_per?: BudgetSubScope
  budget_mcps_per?: BudgetSubScope
  model_budgets?: Record<string, number> | null
  mcp_budgets?: Record<string, number> | null
  scenario_id?: number | null
  rate_limit_mode?: AiKeyRateLimitMode
  tpm_limit?: number | null
  rpm_limit?: number | null
  max_parallel_requests?: number | null
  rate_limits?: RateLimitItem[] | null
}

export interface BatchCreateResult {
  user_id: number
  success: boolean
  error?: string
  key?: AiKey
}

export interface RateLimitItem {
  model_id: number
  tpm?: number | null
  rpm?: number | null
}

export interface AiKeyListResult {
  items: AiKey[]
  total: number
  page: number
  page_size: number
}

export interface MyKeysResult {
  personal: AiKey[]
  department: AiKey[]
  project: AiKey[]
}

// --- Identity list types ---

export interface IdentityUserItem {
  user: {
    id: number
    username: string
    display_name: string
    department_name: string
  }
  main_key: AiKey | null
  scene_keys: AiKey[]
}

export interface IdentityDepartmentItem {
  department: { id: number; name: string }
  main_key: AiKey | null
  scene_keys: AiKey[]
  keys: AiKey[]
}

export interface IdentityProjectItem {
  project: { id: number; name: string }
  main_key: AiKey | null
  scene_keys: AiKey[]
  keys: AiKey[]
}

export interface IdentityListResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// --- Model limit types ---

export interface AiKeyModelLimit {
  model_id: number
  model_name: string
  model_model_id: string
  tpm: number | null
  rpm: number | null
  max_tokens: number | null
  max_calls: number | null
}

export interface SetModelLimitItem {
  model_id: number
  tpm?: number | null
  rpm?: number | null
}
