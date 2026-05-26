import { request } from './request'
import type {
  McpServer,
  McpTool,
  McpCategory,
  McpServerListResult,
  CreateMcpServerParams,
  UpdateMcpServerParams,
  UpdateToolBillingParams,
  CreateMcpCategoryParams,
} from '../types/mcp'

export function getMcpServers(
  page: number = 1,
  pageSize: number = 50,
  category?: string,
  isActive?: boolean,
  isPublished?: boolean,
  status?: string,
): Promise<McpServerListResult> {
  const params: Record<string, string | number | boolean> = { page, page_size: pageSize }
  if (category) params.category = category
  if (isActive !== undefined) params.is_active = isActive
  if (isPublished !== undefined) params.is_published = isPublished
  if (status) params.status = status
  return request<McpServerListResult>('/api/v1/mcp/servers', { params })
}

export function getMcpServerById(id: number): Promise<McpServer> {
  return request<McpServer>(`/api/v1/mcp/servers/${id}`)
}

export function createMcpServer(params: CreateMcpServerParams): Promise<McpServer> {
  return request<McpServer>('/api/v1/mcp/servers', { method: 'POST', body: params })
}

export function updateMcpServer(id: number, params: UpdateMcpServerParams): Promise<McpServer> {
  return request<McpServer>(`/api/v1/mcp/servers/${id}`, { method: 'PUT', body: params })
}

export function deleteMcpServer(id: number): Promise<null> {
  return request<null>(`/api/v1/mcp/servers/${id}`, { method: 'DELETE' })
}

export function getMcpTools(serverId: number): Promise<McpTool[]> {
  return request<McpTool[]>(`/api/v1/mcp/servers/${serverId}/tools`)
}

export function refreshMcpTools(serverId: number): Promise<McpTool[]> {
  return request<McpTool[]>(`/api/v1/mcp/servers/${serverId}/refresh-tools`, { method: 'POST' })
}

export function updateToolBilling(
  toolId: number,
  params: UpdateToolBillingParams,
): Promise<McpTool> {
  return request<McpTool>(`/api/v1/mcp/tools/${toolId}/billing`, { method: 'PUT', body: params })
}

export function healthCheckMcpServer(serverId: number): Promise<McpServer> {
  return request<McpServer>(`/api/v1/mcp/servers/${serverId}/health-check`, { method: 'POST' })
}

export function getMcpCategories(): Promise<McpCategory[]> {
  return request<McpCategory[]>('/api/v1/mcp/categories')
}

export function createMcpCategory(params: CreateMcpCategoryParams): Promise<McpCategory> {
  return request<McpCategory>('/api/v1/mcp/categories', { method: 'POST', body: params })
}

export function deleteMcpCategory(id: number): Promise<null> {
  return request<null>(`/api/v1/mcp/categories/${id}`, { method: 'DELETE' })
}
