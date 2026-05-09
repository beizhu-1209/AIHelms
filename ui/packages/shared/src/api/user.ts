import { request } from './request'
import type { User, CreateUserParams, UpdateUserParams, UserListResult } from '../types/user'

export function getUsers(page: number, pageSize: number, keyword?: string): Promise<UserListResult> {
  return request<UserListResult>('/api/v1/users', {
    params: { page, page_size: pageSize, keyword },
  })
}

export function getUserById(id: number): Promise<User> {
  return request<User>(`/api/v1/users/${id}`)
}

export function createUser(params: CreateUserParams): Promise<User> {
  return request<User>('/api/v1/users', {
    method: 'POST',
    body: params,
  })
}

export function updateUser(id: number, params: UpdateUserParams): Promise<User> {
  return request<User>(`/api/v1/users/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function deleteUser(id: number): Promise<null> {
  return request<null>(`/api/v1/users/${id}`, { method: 'DELETE' })
}

export function resetUserPassword(id: number, newPassword: string): Promise<null> {
  return request<null>(`/api/v1/users/${id}/password`, {
    method: 'PUT',
    body: { new_password: newPassword },
  })
}

export function updateUserRoles(id: number, roleIds: number[]): Promise<null> {
  return request<null>(`/api/v1/users/${id}/roles`, {
    method: 'PUT',
    body: { role_ids: roleIds },
  })
}

export function updateUserOrganizations(id: number, orgIds: number[]): Promise<null> {
  return request<null>(`/api/v1/users/${id}/organizations`, {
    method: 'PUT',
    body: { organization_ids: orgIds },
  })
}
