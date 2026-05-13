export interface Credential {
  id: number
  credential_name: string
  provider_id: number | null
  provider_name: string | null
  provider_type: string | null
  credential_values: Record<string, string | null>
  credential_info: Record<string, unknown>
  litellm_synced: boolean
  is_active: boolean
  deployment_count: number
  created_at: string | null
  updated_at: string | null
}

export interface CreateCredentialParams {
  credential_name: string
  credential_values: Record<string, string>
  provider_id: number
  credential_info?: Record<string, unknown> | null
}

export interface UpdateCredentialParams {
  credential_values?: Record<string, string>
  provider_id?: number | null
  credential_info?: Record<string, unknown> | null
  is_active?: boolean
}

export interface CredentialListResult {
  items: Credential[]
  total: number
  page: number
  page_size: number
}

export interface ProviderFieldMetadata {
  key: string
  label: string
  placeholder?: string | null
  tooltip?: string | null
  required?: boolean
  field_type?: 'text' | 'password' | 'select' | 'upload' | 'textarea'
  options?: string[] | null
  default_value?: string | null
}

export interface ProviderFieldsInfo {
  provider: string
  provider_display_name: string
  litellm_provider: string
  credential_fields: ProviderFieldMetadata[]
  default_model_placeholder?: string | null
}
