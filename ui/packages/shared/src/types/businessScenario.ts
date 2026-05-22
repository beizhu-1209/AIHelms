export interface BusinessScenario {
  id: number
  code: string
  name: string
  description: string
  icon: string
  sort_order: number
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CreateBusinessScenarioParams {
  code: string
  name: string
  description?: string
  icon?: string
  sort_order?: number
}

export interface UpdateBusinessScenarioParams {
  name?: string
  description?: string
  icon?: string
  sort_order?: number
  is_active?: boolean
}

export interface BusinessScenarioListResult {
  items: BusinessScenario[]
  total: number
  page: number
  page_size: number
}
