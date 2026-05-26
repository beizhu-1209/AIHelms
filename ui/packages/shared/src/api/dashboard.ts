import { request } from './request'
import type { DashboardData } from '../types/dashboard'

export function getDashboard() {
  return request<DashboardData>('/api/v1/dashboard')
}
