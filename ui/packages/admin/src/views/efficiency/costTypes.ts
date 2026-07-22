export interface ScopeOption {
  id: number
  name: string
  depth?: number
}

export interface DeptTreeNode {
  id: number
  name: string
  children?: DeptTreeNode[]
}

export interface CostKpi {
  total_cost: number
  external_cost: number
  cost_diff: number
  daily_avg_cost: number
  cost_change: number | null
}

export interface CostTrendItem {
  date: string
  llm_cost: number
  mcp_cost: number
  llm_external_cost: number
  mcp_external_cost: number
}

export interface CostCompositionItem {
  name: string
  value: number
  internal_cost: number
  external_cost: number
}

export interface CostComposition {
  by_resource_type: CostCompositionItem[]
  by_scope?: CostCompositionItem[]
  by_department?: CostCompositionItem[]
}

export interface PerCapitaItem {
  name?: string
  department?: string
  per_capita_cost: number
}

export interface ScopeDetailRow {
  department: string
  scope_name?: string
  scope_id: number | null
  llm_cost: number
  mcp_cost: number
  total_cost: number
  external_cost: number
  cost_diff: number
  requests: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  per_capita_cost: number
  active_per_capita_cost: number
  cost_change: number | null
}

export interface ScopeUserCostRow {
  user_id: number
  user_name: string
  department: string
  internal_cost: number
  external_cost: number
  cost_diff: number
  requests: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
}

export interface UserTop10Row {
  rank: number
  user_id: number
  user_name: string
  department: string
  internal_cost: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  total_tokens: number
  requests: number
}

export interface UserKeyBudgetRow {
  user_name: string
  key_name: string
  is_main: boolean
  budget: number
  used: number
  execution_rate: number
}

export interface ModelCredentialRow {
  credential_id: number | null
  credential_name: string
  provider_name: string
  provider_type: string
  deployment_id: number | null
  deployment_name: string
  route_model: string
  requests: number
  tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  internal_cost: number
  external_cost: number
  cost_diff: number
  avg_cost: number
}

export interface ModelDetailRow {
  model: string
  model_id: string
  requests: number
  tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  cost: number
  internal_cost: number
  external_cost: number
  cost_diff: number
  ratio: number
  avg_cost: number
  credentials: ModelCredentialRow[]
}

export interface McpToolRow {
  tool_name: string
  namespaced_tool_name: string
  requests: number
  internal_cost: number
  external_cost: number
  cost_diff: number
  avg_cost: number
}

export interface McpDetailRow {
  server: string
  server_id: number | null
  server_code: string
  requests: number
  tool_count: number
  cost: number
  internal_cost: number
  external_cost: number
  cost_diff: number
  ratio: number
  avg_cost: number
  tools: McpToolRow[]
}

export interface DateDetailRow {
  date: string
  llm_cost: number
  mcp_cost: number
  total_cost: number
  external_cost: number
  cost_diff: number
  requests: number
  active_users: number
}

export interface AttributionRow {
  date: string
  resource_type: string
  cost_object: string
  user_name: string
  key_name: string
  scope_name: string
  requests: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  internal_input_cost: number
  internal_output_cost: number
  internal_cache_read_cost: number
  internal_cache_creation_cost: number
  internal_cost: number
  external_input_cost: number
  external_output_cost: number
  external_cache_read_cost: number
  external_cache_creation_cost: number
  external_cost: number
  cost_diff: number
  user_id?: number | null
  ai_key_id?: number | null
  model?: string
  server_id?: number | null
}

export type DetailTab = 'department' | 'model' | 'mcp' | 'date' | 'attribution'
