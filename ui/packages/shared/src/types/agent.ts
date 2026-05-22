export interface AgentCategory {
  id: number
  name: string
  description: string
  sort_order: number
}

export interface AgentPlatform {
  id: number
  name: string
  label: string
  description: string
  sort_order: number
}

export interface Agent {
  id: number
  agent_id: string
  name: string
  icon: string
  description: string
  platform: string
  category: string
  department_id: number | null
  project_id: number | null
  cost_attribution: string
  ai_key_id: number | null
  chat_url: string
  external_id: string
  tags: string[]
  is_active: boolean
  is_published: boolean
  requires_approval: boolean
  status: string
  user_count: number
  call_count: number
  created_by: number | null
  created_at: string | null
  updated_at: string | null
}

export interface AgentListResult {
  items: Agent[]
  total: number
  page: number
  page_size: number
}

export interface CreateAgentParams {
  name: string
  icon?: string
  description?: string
  platform: string
  category?: string
  department_id?: number | null
  project_id?: number | null
  cost_attribution?: string
  ai_key_id?: number | null
  chat_url?: string
  tags?: string[]
  is_published?: boolean
  requires_approval?: boolean
  status?: string
}

export interface UpdateAgentParams {
  name?: string
  icon?: string
  description?: string
  platform?: string
  category?: string
  department_id?: number | null
  project_id?: number | null
  cost_attribution?: string
  ai_key_id?: number | null
  chat_url?: string
  tags?: string[]
  is_active?: boolean
  is_published?: boolean
  requires_approval?: boolean
  status?: string
}

export interface CreateAgentCategoryParams {
  name: string
  description?: string
  sort_order?: number
}

export interface CreateAgentPlatformParams {
  name: string
  label?: string
  description?: string
  sort_order?: number
}

export interface AgentUsageLog {
  id: number
  agent_id: number
  user_id: number
  session_id: string
  created_at: string | null
}

export interface AgentUsageLogListResult {
  items: AgentUsageLog[]
  total: number
  page: number
  page_size: number
}
