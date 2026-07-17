export interface UsageLogUser {
  id: number
  username: string
  display_name: string
  department_name: string
}

export interface UsageLogAiKey {
  id: number
  name: string
  key_token?: string
}

export interface UsageLogUserKeyPair {
  user_id: number
  ai_key_id: number
}

export interface UsageLogMcpServer {
  id: number
  name: string
  server_name: string
}

export interface UsageLogSkill {
  id: number
  name: string
  icon: string
  version: string
}

export interface UsageLogAgent {
  id: number
  name: string
  icon: string
  platform: string
}

export interface LlmLog {
  id: number
  request_id: string
  user: UsageLogUser | null
  ai_key: UsageLogAiKey | null
  model: string
  provider: string | null
  call_type: string | null
  status: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  cache_read_tokens: number
  cache_creation_tokens: number
  internal_input_cost: string
  internal_output_cost: string
  internal_cache_read_cost: string
  internal_cache_creation_cost: string
  external_input_cost: string
  external_output_cost: string
  external_cache_read_cost: string
  external_cache_creation_cost: string
  external_cost: string
  internal_cost: string
  duration_ms: number | null
  ttft_ms: number | null
  started_at: string
  ended_at: string | null
  session_id: string
  error_message: string | null
}

export interface LlmLogDetail extends LlmLog {
  deployment: { id: number; deploy_name: string } | null
  metadata: Record<string, unknown>
  messages: unknown
  response: unknown
}

export interface McpLog {
  id: number
  user: UsageLogUser | null
  ai_key: UsageLogAiKey | null
  server: UsageLogMcpServer | null
  tool_name: string
  namespaced_tool_name: string
  status: string
  duration_ms: number | null
  internal_cost: string
  external_cost: string
  response_summary: string
  error_message: string | null
  called_at: string
}

export interface McpLogDetail extends McpLog {
  request_args: Record<string, unknown>
  response_full: string
}

export interface SkillLog {
  id: number
  user: UsageLogUser | null
  skill: UsageLogSkill | null
  action: string
  created_at: string
}

export interface AgentLog {
  id: number
  user: UsageLogUser | null
  agent: UsageLogAgent | null
  platform: string | null
  session_id: string
  created_at: string
}

export interface LogListResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface LlmLogFilters {
  users: UsageLogUser[]
  ai_keys: UsageLogAiKey[]
  models: { value: string; active: boolean }[]
  providers: string[]
  user_key_pairs: UsageLogUserKeyPair[]
}

export interface McpLogFilters {
  users: UsageLogUser[]
  servers: UsageLogMcpServer[]
  ai_keys: UsageLogAiKey[]
  tool_names: string[]
  user_key_pairs: UsageLogUserKeyPair[]
}

export interface SkillLogFilters {
  users: UsageLogUser[]
  skills: UsageLogSkill[]
  actions: string[]
}

export interface AgentLogFilters {
  users: UsageLogUser[]
  agents: UsageLogAgent[]
  platforms: string[]
}
