import { request } from './request'
import type { AuditLogListResult, AuditLogFilters, AuditLogQuery } from '../types/auditLog'

export function getAuditLogs(query: AuditLogQuery = {}): Promise<AuditLogListResult> {
  return request<AuditLogListResult>('/api/v1/audit-logs', {
    params: {
      page: query.page,
      page_size: query.page_size,
      start_time: query.start_time,
      end_time: query.end_time,
      user_id: query.user_id,
      method: query.method,
      status: query.status,
      action: query.action,
    },
  })
}

export function getAuditLogFilters(): Promise<AuditLogFilters> {
  return request<AuditLogFilters>('/api/v1/audit-logs/filters')
}
