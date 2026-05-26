import { request } from './request'
import type {
  KeyScenario,
  KeyScenarioListResult,
  CreateKeyScenarioParams,
  UpdateKeyScenarioParams,
} from '../types/key-scenario'

export function getKeyScenarios(
  page: number = 1,
  pageSize: number = 50,
  keyword?: string,
): Promise<KeyScenarioListResult> {
  const params: Record<string, string | number> = { page, page_size: pageSize }
  if (keyword) params.keyword = keyword
  return request<KeyScenarioListResult>('/api/v1/key-scenarios', { params })
}

export function getAllKeyScenarios(): Promise<KeyScenario[]> {
  return request<KeyScenario[]>('/api/v1/key-scenarios/all')
}

export function createKeyScenario(params: CreateKeyScenarioParams): Promise<KeyScenario> {
  return request<KeyScenario>('/api/v1/key-scenarios', {
    method: 'POST',
    body: params,
  })
}

export function updateKeyScenario(id: number, params: UpdateKeyScenarioParams): Promise<KeyScenario> {
  return request<KeyScenario>(`/api/v1/key-scenarios/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function deleteKeyScenario(id: number): Promise<null> {
  return request<null>(`/api/v1/key-scenarios/${id}`, { method: 'DELETE' })
}
