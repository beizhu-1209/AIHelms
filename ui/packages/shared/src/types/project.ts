export interface Project {
  id: number
  name: string
  description: string
  is_active: boolean
  litellm_team_id: string | null
  created_at: string
  updated_at: string
}

export interface CreateProjectParams {
  name: string
  description?: string
}

export interface UpdateProjectParams {
  name?: string
  description?: string
}

export interface ProjectMember {
  id: number
  username: string
  email: string
  phone: string
  display_name: string
  position: string
  is_active: boolean
  joined_at: string
}

export interface ProjectListResult {
  items: Project[]
  total: number
  page: number
  page_size: number
}
