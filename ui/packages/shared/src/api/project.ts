import { request } from './request'
import type {
  Project,
  CreateProjectParams,
  UpdateProjectParams,
  ProjectMember,
  ProjectListResult,
} from '../types/project'

export function getProjects(page: number = 1, pageSize: number = 20, keyword: string = ''): Promise<ProjectListResult> {
  return request<ProjectListResult>('/api/v1/projects', {
    params: { page, page_size: pageSize, keyword },
  })
}

export function getProjectById(id: number): Promise<Project> {
  return request<Project>(`/api/v1/projects/${id}`)
}

export function createProject(params: CreateProjectParams): Promise<Project> {
  return request<Project>('/api/v1/projects', {
    method: 'POST',
    body: params,
  })
}

export function updateProject(id: number, params: UpdateProjectParams): Promise<Project> {
  return request<Project>(`/api/v1/projects/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function deleteProject(id: number): Promise<null> {
  return request<null>(`/api/v1/projects/${id}`, { method: 'DELETE' })
}

export function getProjectMembers(id: number): Promise<ProjectMember[]> {
  return request<ProjectMember[]>(`/api/v1/projects/${id}/members`)
}

export function addProjectMember(projectId: number, userId: number): Promise<null> {
  return request<null>(`/api/v1/projects/${projectId}/members`, {
    method: 'POST',
    body: { user_id: userId },
  })
}

export function removeProjectMember(projectId: number, userId: number): Promise<null> {
  return request<null>(`/api/v1/projects/${projectId}/members/${userId}`, {
    method: 'DELETE',
  })
}
