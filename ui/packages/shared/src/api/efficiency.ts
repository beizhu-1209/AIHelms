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

export function getEfficiencyOverview(params?: Params) {
  return request<EfficiencyKpi>('/api/v1/efficiency/overview', { params })
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

export function createEfficiencyReport(body: {
  report_type: string
  period_start: string
  period_end: string
  model_used?: string
}) {
  return request('/api/v1/efficiency/reports', { method: 'POST', body })
}
