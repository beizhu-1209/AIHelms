import { request } from './request'
import type {
  ResourceApplication,
  ResourceApplicationListResult,
  CreateResourceApplicationParams,
  ApproveResourceApplicationParams,
  RejectResourceApplicationParams,
} from '../types/resource-application'

export function getResourceApplications(
  page: number = 1,
  pageSize: number = 50,
  userId?: number,
  resourceType?: string,
  status?: string,
): Promise<ResourceApplicationListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (userId) params.user_id = userId
  if (resourceType) params.resource_type = resourceType
  if (status) params.status = status
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
