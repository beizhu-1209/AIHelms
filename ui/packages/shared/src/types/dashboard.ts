export interface DashboardStatus {
  activeUsers: number
  activeUsersChange: number
  todayRequests: number
  totalRequests: number
  llmRequests: number
  mcpRequests: number
  todayCost: number
  internalCost: number
  externalCost: number
  costDiff: number
  costChangePercent: number
  totalTokens: number
  inputTokens: number
  outputTokens: number
  cacheReadTokens: number
  cacheCreationTokens: number
  pendingCount: number
  pendingApprovals: number
  pendingAlerts: number
}

export interface PendingItem {
  id?: number
  type: 'approval' | 'budget_alert'
  applicant?: string
  resourceType?: string
  resourceTypeLabel?: string
  resourceName?: string
  reason?: string
  description?: string
  createdAt?: string | null
  timeAgo: string
  linkUrl: string
}

export interface TrendPoint {
  label: string
  hour: number
  requests: number
}

export type HourlyTrend = TrendPoint

export interface ResourceSummary {
  name: string
  icon: string
  total: number
  active: number | null
  activeLabel: string
  linkPath: string
}

export interface RecentActivity {
  actor: string
  action: string
  timeAgo: string
}

export interface ServiceStatusItem {
  key: string
  label: string
  healthy: number
  total: number
  state: 'healthy' | 'warning' | 'danger' | 'empty'
  description: string
}

export interface DashboardPeriod {
  startDate: string
  endDate: string
  label: string
}

export interface CostLeaderboardItem {
  rank: number
  user_name: string
  department: string
  internal_cost: number
}

export interface DashboardData {
  period: DashboardPeriod
  lastUpdatedAt: string | null
  lastUpdatedLabel: string
  status: DashboardStatus
  pendingItems: PendingItem[]
  pendingApprovalsList: PendingItem[]
  hourlyTrend: TrendPoint[]
  requestTrend: TrendPoint[]
  resources: ResourceSummary[]
  recentActivities: RecentActivity[]
  serviceStatus: ServiceStatusItem[]
  costLeaderboard: CostLeaderboardItem[]
}
