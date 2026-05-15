export interface KeyScenario {
  id: number
  name: string
  description: string
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CreateKeyScenarioParams {
  name: string
  description?: string
}

export interface UpdateKeyScenarioParams {
  name?: string
  description?: string
}

export interface KeyScenarioListResult {
  items: KeyScenario[]
  total: number
  page: number
  page_size: number
}
