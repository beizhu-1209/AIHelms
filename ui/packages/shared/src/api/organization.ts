import { request } from './request'
import type {
  Organization,
  OrgTreeNode,
  CreateOrganizationParams,
  UpdateOrganizationParams,
  OrgMember,
} from '../types/organization'

export function getOrganizations(type?: string, isActive?: boolean): Promise<Organization[]> {
  return request<Organization[]>('/api/v1/organizations', {
    params: { type, is_active: isActive },
  })
}

export function getOrganizationTree(): Promise<OrgTreeNode[]> {
  return request<OrgTreeNode[]>('/api/v1/organizations/tree')
}

export function createOrganization(params: CreateOrganizationParams): Promise<Organization> {
  return request<Organization>('/api/v1/organizations', {
    method: 'POST',
    body: params,
  })
}

export function updateOrganization(id: number, params: UpdateOrganizationParams): Promise<Organization> {
  return request<Organization>(`/api/v1/organizations/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function updateOrgManagers(id: number, managerUserIds: number[]): Promise<Organization> {
  return request<Organization>(`/api/v1/organizations/${id}/managers`, {
    method: 'PUT',
    body: { manager_user_ids: managerUserIds },
  })
}

export function deleteOrganization(id: number): Promise<null> {
  return request<null>(`/api/v1/organizations/${id}`, { method: 'DELETE' })
}

export function getOrganizationMembers(id: number): Promise<OrgMember[]> {
  return request<OrgMember[]>(`/api/v1/organizations/${id}/members`)
}
