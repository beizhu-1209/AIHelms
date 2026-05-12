export interface User {
  id: number
  username: string
  email: string
  phone: string
  display_name: string
  position: string
  is_active: boolean
  is_admin: boolean
  litellm_user_id: string | null
  created_at: string
  updated_at: string | null
  roles: { id: number; name: string; display_name: string }[]
  departments: { id: number; name: string; is_manager: boolean }[]
  projects: { id: number; name: string }[]
}

export interface CreateUserParams {
  username: string
  email: string
  password: string
  phone?: string
  display_name?: string
  position?: string
  is_active?: boolean
  department_ids?: number[]
  project_ids?: number[]
}

export interface UpdateUserParams {
  email?: string
  phone?: string
  display_name?: string
  position?: string
  is_active?: boolean
}

export interface UserListResult {
  items: User[]
  total: number
  page: number
  page_size: number
}
