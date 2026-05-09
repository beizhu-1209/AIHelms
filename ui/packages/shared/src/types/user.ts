export interface User {
  id: number
  username: string
  email: string
  is_active: boolean
  is_admin: boolean
  created_at: string
  roles: { id: number; name: string; display_name: string }[]
  organizations: { id: number; name: string; type: string }[]
}

export interface CreateUserParams {
  username: string
  email: string
  password: string
  is_active?: boolean
}

export interface UpdateUserParams {
  email?: string
  is_active?: boolean
}

export interface UserListResult {
  items: User[]
  total: number
  page: number
  page_size: number
}
