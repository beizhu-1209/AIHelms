export interface Organization {
  id: number
  name: string
  type: 'department' | 'group'
  parent_id: number | null
  description: string
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
  managers: OrgManager[]
}

export interface OrgManager {
  id: number
  username: string
}

export interface OrgTreeNode {
  id: number
  name: string
  type: string
  description: string
  sort_order: number
  is_active: boolean
  managers: OrgManager[]
  children: OrgTreeNode[]
}

export interface CreateOrganizationParams {
  name: string
  type: 'department' | 'group'
  parent_id?: number | null
  description?: string
  sort_order?: number
}

export interface UpdateOrganizationParams {
  name?: string
  description?: string
  sort_order?: number
  is_active?: boolean
}

export interface OrgMember {
  id: number
  username: string
  email: string
  is_active: boolean
  is_manager: boolean
  joined_at: string
}
