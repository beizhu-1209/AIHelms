export interface AdoptionKpi {
  coverage_rate: number
  new_active: number
  daily_avg_frequency: number
  heavy_user_ratio: number
}

export interface ActiveTrend {
  dates: string[]
  values: number[]
}

export interface DepthDistribution {
  light: number
  medium: number
  heavy: number
}

export interface HeavyTrend {
  dates: string[]
  ratios: number[]
}

export interface DeptCoverageRow {
  id: number
  name: string
  total_members: number
  active_members: number
  coverage_rate: number
  daily_avg_calls: number
  heavy_user_ratio: number
  change: number
}

export interface AgentRow {
  id: number
  rank: number
  name: string
  platform: string
  department: string
  user_count: number
  monthly_calls: number
  trend: number[]
}

export interface ResourceRow {
  id: number
  name: string
  type: string
  user_count: number
  monthly_calls: number
  department: string
}

export interface UnusedUser {
  name: string
  department: string
  position: string
  assigned_key: string
  last_active: string
}

export interface ScopeUserRow {
  id: number
  username: string
  name: string
  position: string
  department: string
  total_calls: number
  llm_calls: number
  mcp_calls: number
  last_active: string
}
