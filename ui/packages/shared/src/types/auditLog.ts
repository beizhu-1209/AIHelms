export interface AuditLog {
  id: number
  user_id: number
  username: string
  identity_type: 'user' | 'api_key'
  method: string
  path: string
  action: string
  status_code: number
  ip: string
  user_agent: string
  duration_ms: number
  request_summary: string
  created_at: string
}

export interface AuditLogQuery {
  page?: number
  page_size?: number
  start_time?: string
  end_time?: string
  user_id?: number
  method?: string
  status?: 'success' | 'failed'
  action?: string
}

export interface AuditLogListResult {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface AuditLogActor {
  user_id: number
  username: string
}

export interface AuditLogFilters {
  actors: AuditLogActor[]
  actions: string[]
}
