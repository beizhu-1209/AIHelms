import { request } from './request'
import type {
  Agent,
  AgentCategory,
  AgentPlatform,
  AgentListResult,
  CreateAgentParams,
  UpdateAgentParams,
  CreateAgentCategoryParams,
  CreateAgentPlatformParams,
  AgentUsageLogListResult,
} from '../types/agent'

export function getAgents(
  page: number = 1,
  pageSize: number = 50,
  category?: string,
  platform?: string,
  isPublished?: boolean,
): Promise<AgentListResult> {
  const params: Record<string, string | number | boolean> = { page, page_size: pageSize }
  if (category) params.category = category
  if (platform) params.platform = platform
  if (isPublished !== undefined) params.is_published = isPublished
  return request<AgentListResult>('/api/v1/agents', { params })
}

export function getAgentById(id: number): Promise<Agent> {
  return request<Agent>(`/api/v1/agents/${id}`)
}

export function createAgent(params: CreateAgentParams): Promise<Agent> {
  return request<Agent>('/api/v1/agents', { method: 'POST', body: params })
}

export function updateAgent(id: number, params: UpdateAgentParams): Promise<Agent> {
  return request<Agent>(`/api/v1/agents/${id}`, { method: 'PUT', body: params })
}

export function deleteAgent(id: number): Promise<null> {
  return request<null>(`/api/v1/agents/${id}`, { method: 'DELETE' })
}

export function getAgentCategories(): Promise<AgentCategory[]> {
  return request<AgentCategory[]>('/api/v1/agents/categories')
}

export function createAgentCategory(params: CreateAgentCategoryParams): Promise<AgentCategory> {
  return request<AgentCategory>('/api/v1/agents/categories', { method: 'POST', body: params })
}

export function deleteAgentCategory(id: number): Promise<null> {
  return request<null>(`/api/v1/agents/categories/${id}`, { method: 'DELETE' })
}

export function getAgentPlatforms(): Promise<AgentPlatform[]> {
  return request<AgentPlatform[]>('/api/v1/agents/platforms')
}

export function createAgentPlatform(params: CreateAgentPlatformParams): Promise<AgentPlatform> {
  return request<AgentPlatform>('/api/v1/agents/platforms', { method: 'POST', body: params })
}

export function deleteAgentPlatform(id: number): Promise<null> {
  return request<null>(`/api/v1/agents/platforms/${id}`, { method: 'DELETE' })
}

export function recordAgentUsage(
  agentId: number,
  sessionId: string = '',
): Promise<{ call_count: number; user_count: number; is_first: boolean }> {
  return request(`/api/v1/agents/${agentId}/use`, {
    method: 'POST',
    body: { session_id: sessionId },
  })
}

export function getAgentUsageLogs(
  agentId: number,
  page: number = 1,
  pageSize: number = 50,
  userId?: number,
): Promise<AgentUsageLogListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (userId) params.user_id = userId
  return request<AgentUsageLogListResult>(`/api/v1/agents/${agentId}/usage-logs`, { params })
}
