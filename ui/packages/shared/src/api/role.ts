import { request } from './request'
import type { Role, Permission, CreateRoleParams, UpdateRoleParams } from '../types/role'

export function getRoles(): Promise<Role[]> {
  return request<Role[]>('/api/v1/roles')
}

export function createRole(params: CreateRoleParams): Promise<Role> {
  return request<Role>('/api/v1/roles', {
    method: 'POST',
    body: params,
  })
}

export function updateRole(id: number, params: UpdateRoleParams): Promise<Role> {
  return request<Role>(`/api/v1/roles/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function deleteRole(id: number): Promise<null> {
  return request<null>(`/api/v1/roles/${id}`, { method: 'DELETE' })
}

export function updateRolePermissions(id: number, permissionIds: number[]): Promise<Role> {
  return request<Role>(`/api/v1/roles/${id}/permissions`, {
    method: 'PUT',
    body: { permission_ids: permissionIds },
  })
}

export function getPermissions(): Promise<Permission[]> {
  return request<Permission[]>('/api/v1/roles/permissions')
}
