import { request } from './request'
import type {
  AnalysisItem,
  BudgetOverview,
  CompositionItem,
  EfficiencyKpi,
  EfficiencyReport,
  KeyTypeItem,
  RankingItem,
  TrendItem,
} from '../types/efficiency'

type Params = Record<string, string | number | boolean | undefined>

export function getEfficiencyOverview<T = EfficiencyKpi>(params?: Params) {
  return request<T>('/api/v1/efficiency/overview', { params })
}

export function getEfficiencyTrend(params?: Params) {
  return request<TrendItem[]>('/api/v1/efficiency/trend', { params })
}

export function getEfficiencyComposition(params?: Params) {
  return request<CompositionItem[]>('/api/v1/efficiency/composition', { params })
}

export function getKeyTypeComparison(params?: Params) {
  return request<KeyTypeItem[]>('/api/v1/efficiency/key-type-comparison', { params })
}

export function getEfficiencyRanking(params?: Params) {
  return request<RankingItem[]>('/api/v1/efficiency/ranking', { params })
}

export function getEfficiencyAnalysis(dimension: string, params?: Params) {
  return request<AnalysisItem[]>(`/api/v1/efficiency/analysis/${dimension}`, { params })
}

export function getBudgetOverview(params?: Params) {
  return request<BudgetOverview>('/api/v1/efficiency/budget/overview', { params })
}

export function getEfficiencyReports(params?: Params) {
  return request<{ items: EfficiencyReport[]; total: number; page: number; page_size: number }>(
    '/api/v1/efficiency/reports', { params }
  )
}

export function getEfficiencyReport(id: number) {
  return request<EfficiencyReport>(`/api/v1/efficiency/reports/${id}`)
}


export interface EfficiencyRefreshTaskResponse {
  update_status?: string
  task_id?: string
  reason?: string
}

export function refreshEfficiencyData(scope: string) {
  return request<EfficiencyRefreshTaskResponse>('/api/v1/efficiency/refresh', {
    method: 'POST',
    params: { scope },
    silent: true,
  })
}

export function getEfficiencyAdoption<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/adoption', { params })
}

export function getEfficiencyAdoptionAgents<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/adoption/agents', { params })
}

export function getEfficiencyAdoptionResources<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/adoption/resources', { params })
}

export function getEfficiencyAdoptionUnusedUsers<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/adoption/unused-users', { params })
}

export function getEfficiencyAdoptionScopeUsers<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/adoption/scope-users', { params })
}

export function getEfficiencyCost<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/cost', { params })
}

export function getEfficiencyCostDetail<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/cost/detail', { params })
}

export function getEfficiencyBudget<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/budget', { params })
}

export function getEfficiencyBudgetAlerts<T>(params?: Params) {
  return request<T>('/api/v1/efficiency/budget/alerts', { params })
}

export function getEfficiencyHealth<T>() {
  return request<T>('/api/v1/efficiency/health')
}

export function createEfficiencyReport(params: {
  report_type: string
  period_start: string
  period_end: string
  filters?: Record<string, unknown>
}) {
  return request<EfficiencyReport>('/api/v1/efficiency/reports', {
    method: 'POST',
    body: params,
  })
}
