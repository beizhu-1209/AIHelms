export interface McpCategory {
  id: number
  name: string
  description: string
  sort_order: number
}

export interface CreateMcpCategoryParams {
  name: string
  description?: string
  sort_order?: number
}

export interface McpServer {
  id: number
  server_id: string
  name: string
  server_name: string
  description: string
  url: string
  transport: string
  auth_type: string
  credentials?: Record<string, unknown>
  instructions: string
  mcp_info: Record<string, unknown>
  extra_headers: string[]
  allowed_tools: string[]
  authorization_url: string | null
  token_url: string | null
  registration_url: string | null
  category: string
  tags: string[]
  icon_url: string
  documentation_url: string
  source_url: string
  billing_type: string
  internal_cost_per_call: number
  external_cost_per_call: number
  is_active: boolean
  is_published: boolean
  visibility_type: string
  requires_approval: boolean
  status: string
  last_health_check: string | null
  health_check_error: string | null
  litellm_synced: boolean
  litellm_sync_error: string | null
  created_by: number | null
  created_at: string | null
  updated_at: string | null
  tools?: McpTool[]
}

export interface McpTool {
  id: number
  server_id: number
  tool_name: string
  namespaced_name: string
  display_name: string
  description: string
  input_schema: Record<string, unknown>
  billing_type: string | null
  internal_cost_per_call: number | null
  external_cost_per_call: number | null
  is_active: boolean
}

export interface McpServerListResult {
  items: McpServer[]
  total: number
  page: number
  page_size: number
}

export interface CreateMcpServerParams {
  name: string
  server_name: string
  url: string
  transport?: string
  auth_type?: string
  credentials?: Record<string, unknown>
  description?: string
  instructions?: string
  mcp_info?: Record<string, unknown>
  extra_headers?: string[]
  allowed_tools?: string[]
  authorization_url?: string
  token_url?: string
  registration_url?: string
  category?: string
  tags?: string[]
  icon_url?: string
  documentation_url?: string
  source_url?: string
  billing_type?: string
  internal_cost_per_call?: number
  external_cost_per_call?: number
  is_published?: boolean
  visibility_type?: string
  requires_approval?: boolean
}

export interface UpdateMcpServerParams {
  name?: string
  server_name?: string
  url?: string
  transport?: string
  auth_type?: string
  credentials?: Record<string, unknown>
  description?: string
  instructions?: string
  mcp_info?: Record<string, unknown>
  extra_headers?: string[]
  allowed_tools?: string[]
  authorization_url?: string
  token_url?: string
  registration_url?: string
  category?: string
  tags?: string[]
  icon_url?: string
  documentation_url?: string
  source_url?: string
  billing_type?: string
  internal_cost_per_call?: number
  external_cost_per_call?: number
  is_active?: boolean
  is_published?: boolean
  visibility_type?: string
  requires_approval?: boolean
}

export interface UpdateToolBillingParams {
  billing_type?: string
  internal_cost_per_call?: number
  external_cost_per_call?: number
}
