export interface ApiKey {
  id: number
  name: string
  description: string
  key_prefix: string
  raw_key: string
  is_active: boolean
  created_by: number
  created_at: string
  updated_at: string
  expires_at: string | null
  last_used_at: string | null
}

export interface ApiKeyListResult {
  items: ApiKey[]
  total: number
  page: number
  page_size: number
}

export interface CreateApiKeyParams {
  name: string
  description?: string
  expires_at?: string | null
}

export interface UpdateApiKeyParams {
  name?: string
  description?: string
  is_active?: boolean
  expires_at?: string | null
}
