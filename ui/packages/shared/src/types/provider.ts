export interface Provider {
  id: number
  name: string
  provider_type: string
  billing_type: string
  monthly_budget: string | null
  monthly_used: string
  is_active: boolean
  description: string
  config: Record<string, unknown> | null
  credential_count: number
  created_at: string | null
  updated_at: string | null
}

export interface CreateProviderParams {
  name: string
  provider_type: string
  billing_type?: string
  monthly_budget?: number | null
  description?: string
  config?: Record<string, unknown> | null
}

export interface UpdateProviderParams {
  name?: string
  provider_type?: string
  billing_type?: string
  monthly_budget?: number | null
  is_active?: boolean
  description?: string
  config?: Record<string, unknown> | null
}

export interface ProviderListResult {
  items: Provider[]
  total: number
  page: number
  page_size: number
}
