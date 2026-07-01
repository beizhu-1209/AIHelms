export type ResourceType = 'model' | 'mcp' | 'skill' | 'agent'
export type ApplicationStatus = 'pending' | 'approved' | 'rejected'

export interface ResourceApplicationUser {
  id: number
  username: string
  display_name: string
}

export interface ResourceApplicationResourceInfo {
  id: number
  name: string
  model_id?: string
  server_name?: string
}

export interface ResourceApplication {
  id: number
  user_id: number
  resource_type: ResourceType
  resource_id: number
  resource_info: ResourceApplicationResourceInfo | null
  reason: string
  request_config: Record<string, unknown>
  status: ApplicationStatus
  reviewed_by: number | null
  reviewed_at: string | null
  review_notes: string
  approval_config: Record<string, unknown>
  created_at: string | null
  updated_at: string | null
  user: ResourceApplicationUser | null
  reviewer: ResourceApplicationUser | null
}

export interface ResourceApplicationListResult {
  items: ResourceApplication[]
  total: number
  page: number
  page_size: number
}

export interface CreateResourceApplicationParams {
  resource_type: ResourceType
  resource_id: number
  reason?: string
  request_config?: Record<string, unknown>
}

export interface ApproveResourceApplicationParams {
  approval_config?: Record<string, unknown>
  review_notes?: string
}

export interface RejectResourceApplicationParams {
  review_notes?: string
}


export interface BatchApproveResourceApplicationsParams {
  app_ids: number[]
  approval_config?: Record<string, unknown>
  review_notes?: string
}

export interface BatchRejectResourceApplicationsParams {
  app_ids: number[]
  review_notes?: string
}

export interface BatchReviewFailure {
  id: number
  reason: string
}

export interface BatchReviewResult {
  success: number[]
  failed: BatchReviewFailure[]
}
