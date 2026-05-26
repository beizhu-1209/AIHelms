export interface DashboardStatus {
  activeUsers: number
  activeUsersChange: number
  todayRequests: number
  llmRequests: number
  mcpRequests: number
  todayCost: number
  costChangePercent: number
  pendingCount: number
  pendingApprovals: number
  pendingAlerts: number
}

export interface PendingItem {
  type: 'approval' | 'budget_alert'
  description: string
  timeAgo: string
  linkUrl: string
}

export interface HourlyTrend {
  hour: number
  requests: number
}

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

export interface DashboardData {
  status: DashboardStatus
  pendingItems: PendingItem[]
  hourlyTrend: HourlyTrend[]
  resources: ResourceSummary[]
  recentActivities: RecentActivity[]
}
