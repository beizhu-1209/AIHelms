import { request } from './request'
import type {
  ResourceApplication,
  ResourceApplicationListResult,
  CreateResourceApplicationParams,
  ApproveResourceApplicationParams,
  RejectResourceApplicationParams,
  BatchApproveResourceApplicationsParams,
  BatchRejectResourceApplicationsParams,
  BatchReviewResult,
} from '../types/resource-application'

export function getResourceApplications(
  page: number = 1,
  pageSize: number = 50,
  userId?: number,
  resourceType?: string,
  status?: string,
  createdAfter?: string,
  createdBefore?: string,
  reviewedAfter?: string,
  reviewedBefore?: string,
): Promise<ResourceApplicationListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (userId) params.user_id = userId
  if (resourceType) params.resource_type = resourceType
  if (status) params.status = status
  if (createdAfter) params.created_after = createdAfter
  if (createdBefore) params.created_before = createdBefore
  if (reviewedAfter) params.reviewed_after = reviewedAfter
  if (reviewedBefore) params.reviewed_before = reviewedBefore
  return request<ResourceApplicationListResult>('/api/v1/resource-applications', { params })
}

export function getResourceApplicationById(id: number): Promise<ResourceApplication> {
  return request<ResourceApplication>(`/api/v1/resource-applications/${id}`)
}

export function createResourceApplication(
  params: CreateResourceApplicationParams,
): Promise<ResourceApplication> {
  return request<ResourceApplication>('/api/v1/resource-applications', {
    method: 'POST',
    body: params,
  })
}

export function approveResourceApplication(
  id: number,
  params: ApproveResourceApplicationParams = {},
): Promise<ResourceApplication> {
  return request<ResourceApplication>(`/api/v1/resource-applications/${id}/approve`, {
    method: 'PUT',
    body: params,
  })
}

export function rejectResourceApplication(
  id: number,
  params: RejectResourceApplicationParams = {},
): Promise<ResourceApplication> {
  return request<ResourceApplication>(`/api/v1/resource-applications/${id}/reject`, {
    method: 'PUT',
    body: params,
  })
}


export function batchApproveResourceApplications(
  params: BatchApproveResourceApplicationsParams,
): Promise<BatchReviewResult> {
  return request<BatchReviewResult>('/api/v1/resource-applications/batch-approve', {
    method: 'PUT',
    body: params,
    silent: true,
  })
}

export function batchRejectResourceApplications(
  params: BatchRejectResourceApplicationsParams,
): Promise<BatchReviewResult> {
  return request<BatchReviewResult>('/api/v1/resource-applications/batch-reject', {
    method: 'PUT',
    body: params,
    silent: true,
  })
}
