export interface LoginParams {
  username: string
  password: string
}

export interface TokenData {
  access_token: string
  token_type: string
}

export interface CurrentUser {
  id: number
  username: string
  email: string
  is_active: boolean
  is_admin: boolean
  position?: string
  display_name?: string
  avatar?: string
  created_at: string
  permissions: string[]
  roles: { id: number; name: string; display_name: string }[]
  departments?: { id: number; name: string }[]
}

export interface ChangePasswordParams {
  old_password: string
  new_password: string
}
