import { request } from './request'
import type {
  ModelInfo,
  ModelListResult,
  CreateModelParams,
  UpdateModelParams,
  Deployment,
  CreateDeploymentParams,
  UpdateDeploymentParams,
  ActiveModel,
  AccessGroup,
  CreateAccessGroupParams,
  UpdateAccessGroupParams,
  RouterSettings,
  UpdateRouterSettingsParams,
  ModelVisibility,
  UpdateModelPublishParams,
  ResyncAnthropicResult,
} from '../types/model'

export function getModels(page: number = 1, pageSize: number = 50, category?: string): Promise<ModelListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (category) params.category = category
  return request<ModelListResult>('/api/v1/models', { params })
}

export function getModelById(id: number): Promise<ModelInfo> {
  return request<ModelInfo>(`/api/v1/models/${id}`)
}

export function getActiveModels(): Promise<ActiveModel[]> {
  return request<ActiveModel[]>('/api/v1/models/active')
}

export function createModel(params: CreateModelParams): Promise<ModelInfo> {
  return request<ModelInfo>('/api/v1/models', { method: 'POST', body: params })
}

export function updateModel(id: number, params: UpdateModelParams): Promise<ModelInfo> {
  return request<ModelInfo>(`/api/v1/models/${id}`, { method: 'PUT', body: params })
}

export function deleteModel(id: number): Promise<null> {
  return request<null>(`/api/v1/models/${id}`, { method: 'DELETE' })
}

export function createDeployment(modelId: number, params: CreateDeploymentParams): Promise<Deployment> {
  return request<Deployment>(`/api/v1/models/${modelId}/deployments`, { method: 'POST', body: params })
}

export function updateDeployment(modelId: number, deploymentId: number, params: UpdateDeploymentParams): Promise<Deployment> {
  return request<Deployment>(`/api/v1/models/${modelId}/deployments/${deploymentId}`, { method: 'PUT', body: params })
}

export function deleteDeployment(modelId: number, deploymentId: number): Promise<null> {
  return request<null>(`/api/v1/models/${modelId}/deployments/${deploymentId}`, { method: 'DELETE' })
}

// --- Access Groups ---

export function getAccessGroups(): Promise<AccessGroup[]> {
  return request<AccessGroup[]>('/api/v1/models/access-groups/list')
}

export function createAccessGroup(params: CreateAccessGroupParams): Promise<AccessGroup> {
  return request<AccessGroup>('/api/v1/models/access-groups', { method: 'POST', body: params })
}

export function updateAccessGroup(id: number, params: UpdateAccessGroupParams): Promise<AccessGroup> {
  return request<AccessGroup>(`/api/v1/models/access-groups/${id}`, { method: 'PUT', body: params })
}

export function deleteAccessGroup(id: number): Promise<null> {
  return request<null>(`/api/v1/models/access-groups/${id}`, { method: 'DELETE' })
}

// --- Router Settings ---

export function getRouterSettings(): Promise<RouterSettings> {
  return request<RouterSettings>('/api/v1/models/router-settings/current')
}

export function updateRouterSettings(params: UpdateRouterSettingsParams): Promise<RouterSettings> {
  return request<RouterSettings>('/api/v1/models/router-settings/current', { method: 'PUT', body: params })
}

// --- Model Publish / Visibility ---

export function getModelVisibility(modelId: number): Promise<ModelVisibility> {
  return request<ModelVisibility>(`/api/v1/models/${modelId}/visibility`)
}

export function updateModelPublish(modelId: number, params: UpdateModelPublishParams): Promise<ModelVisibility> {
  return request<ModelVisibility>(`/api/v1/models/${modelId}/publish`, { method: 'PUT', body: params })
}

export function resyncAnthropicDeployments(): Promise<ResyncAnthropicResult> {
  return request<ResyncAnthropicResult>('/api/v1/models/resync-anthropic', {
    method: 'POST',
    silent: true,
  })
}
