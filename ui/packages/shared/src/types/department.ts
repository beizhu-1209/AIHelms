export interface Department {
  id: number
  name: string
  parent_id: number | null
  description: string
  sort_order: number
  is_active: boolean
  litellm_team_id: string | null
  created_at: string
  updated_at: string
  managers?: DeptManager[]
}

export interface DeptManager {
  id: number
  username: string
  display_name: string
}

export interface DeptTreeNode {
  id: number
  name: string
  parent_id: number | null
  description: string
  sort_order: number
  is_active: boolean
  litellm_team_id: string | null
  created_at: string
  updated_at: string
  children: DeptTreeNode[]
}

export interface CreateDepartmentParams {
  name: string
  parent_id?: number | null
  description?: string
}

export interface UpdateDepartmentParams {
  name?: string
  description?: string
  sort_order?: number
}

export interface DeptMember {
  id: number
  username: string
  email: string
  phone: string
  display_name: string
  position: string
  is_active: boolean
  is_manager: boolean
  joined_at: string
}
