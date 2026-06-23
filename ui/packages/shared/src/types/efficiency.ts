export interface EfficiencyKpi {
  total_cost: number
  total_requests: number
  active_users: number
  avg_cost_per_user: number
  cost_change: number | null
  requests_change: number | null
}

export interface TrendItem {
  period: string
  cost_type: string
  cost: number
  requests: number
}

export interface CompositionItem {
  cost_type: string
  cost: number
  requests: number
}

export interface KeyTypeItem {
  key_type: string
  cost: number
  requests: number
}

export interface RankingItem {
  value: string | number
  cost: number
  requests: number
}

export interface AnalysisItem {
  value: string | number
  cost: number
  external_cost: number
  requests: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens?: number
  cache_creation_tokens?: number
}

export interface BudgetOverview {
  used: number
  requests: number
  predicted_total: number
}

export interface EfficiencyReport {
  id: number
  report_type: string
  period_start: string
  period_end: string
  model_used: string | null
  summary: string
  content_md?: string
  filters?: Record<string, unknown>
  created_at: string
  generation_cost?: number
  generation_duration_ms?: number
  suggestions?: EfficiencySuggestion[]
}

export interface EfficiencySuggestion {
  id: number
  title: string
  description: string
  priority: 'high' | 'medium' | 'low' | 'opportunity'
  expected_impact: string
  status: 'pending' | 'accepted' | 'rejected' | 'implemented'
  status_note: string
}

export interface CreateReportParams {
  report_type: 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'custom'
  period_start: string
  period_end: string
  model_used?: string
  filters?: Record<string, unknown>
}

export interface DateRangeQuery {
  start_date?: string
  end_date?: string
}
