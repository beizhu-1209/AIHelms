import { request } from './request'
import type {
  BusinessScenario,
  BusinessScenarioListResult,
  CreateBusinessScenarioParams,
  UpdateBusinessScenarioParams,
} from '../types/businessScenario'

export function getBusinessScenarios(
  page: number = 1,
  pageSize: number = 50,
  keyword?: string,
  includeInactive?: boolean,
): Promise<BusinessScenarioListResult> {
  const params: Record<string, string | number | boolean> = { page, page_size: pageSize }
  if (keyword) params.keyword = keyword
  if (includeInactive) params.include_inactive = includeInactive
  return request<BusinessScenarioListResult>('/api/v1/business-scenarios', { params })
}

export function getAllBusinessScenarios(): Promise<BusinessScenario[]> {
  return request<BusinessScenario[]>('/api/v1/business-scenarios/all')
}

export function createBusinessScenario(
  params: CreateBusinessScenarioParams,
): Promise<BusinessScenario> {
  return request<BusinessScenario>('/api/v1/business-scenarios', {
    method: 'POST',
    body: params,
  })
}

export function updateBusinessScenario(
  id: number,
  params: UpdateBusinessScenarioParams,
): Promise<BusinessScenario> {
  return request<BusinessScenario>(`/api/v1/business-scenarios/${id}`, {
    method: 'PUT',
    body: params,
  })
}

export function deleteBusinessScenario(id: number): Promise<null> {
  return request<null>(`/api/v1/business-scenarios/${id}`, { method: 'DELETE' })
}
