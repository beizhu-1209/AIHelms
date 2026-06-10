import { request } from './request'
import type { DashboardData } from '../types/dashboard'

export interface DashboardQuery {
  period?: string
  start_date?: string
  end_date?: string
}

export function getDashboard(params: DashboardQuery = {}) {
  return request<DashboardData>('/api/v1/dashboard', { params: { ...params } })
}

export interface RefreshTaskStatus {
  task_id?: string
  taskId?: string
  state?: string
  status?: string
  ready?: boolean
  successful?: boolean
  failed?: boolean
  reason?: string
}

export function refreshDashboard() {
  return request<RefreshTaskStatus>('/api/v1/dashboard/refresh', {
    method: 'POST',
    silent: true,
  })
}

export function getDashboardRefreshStatus(taskId: string) {
  return request<RefreshTaskStatus>(`/api/v1/dashboard/refresh/${taskId}`, { silent: true })
}
