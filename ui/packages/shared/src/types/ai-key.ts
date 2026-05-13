export interface AiKey {
  id: number
  name: string
  description: string
  key_type: 'personal_main' | 'personal_scene' | 'dept_shared' | 'project_shared'
  owner_type: 'user' | 'department' | 'project'
  owner_id: number
  tags: string[]
  litellm_key_id: string | null
  litellm_key_alias: string | null
  models: string[]
  budget_limit: string | null
  budget_type: 'money' | 'count'
  budget_hard_limit: boolean
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
  budget_limit?: number | null
  budget_type?: 'money' | 'count'
  budget_hard_limit?: boolean
  duration?: string | null
}

export interface UpdateAiKeyParams {
  name?: string
  description?: string
  tags?: string[]
  models?: string[]
  budget_limit?: number | null
  budget_type?: 'money' | 'count'
  budget_hard_limit?: boolean
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
  keys: AiKey[]
}

export interface IdentityProjectItem {
  project: { id: number; name: string }
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
  max_tokens?: number | null
  max_calls?: number | null
}
