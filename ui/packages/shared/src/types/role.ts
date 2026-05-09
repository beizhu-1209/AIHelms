export interface Role {
  id: number
  name: string
  display_name: string
  description: string
  is_system: boolean
  created_at: string
  permissions: Permission[]
}

export interface Permission {
  id: number
  code: string
  name: string
  resource: string
  action: string
  description?: string
}

export interface CreateRoleParams {
  name: string
  display_name: string
  description?: string
}

export interface UpdateRoleParams {
  display_name?: string
  description?: string
}
