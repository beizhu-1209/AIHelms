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

export function updateUserDepartments(id: number, departmentIds: number[]): Promise<null> {
  return request<null>(`/api/v1/users/${id}/departments`, {
    method: 'PUT',
    body: { department_ids: departmentIds },
  })
}

export function updateUserProjects(id: number, projectIds: number[]): Promise<null> {
  return request<null>(`/api/v1/users/${id}/projects`, {
    method: 'PUT',
    body: { project_ids: projectIds },
  })
}
