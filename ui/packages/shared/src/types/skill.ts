export interface SkillCategory {
  id: number
  name: string
  description: string
  sort_order: number
}

export interface Skill {
  id: number
  skill_id: string
  name: string
  icon: string
  description: string
  category: string
  version: string
  tags: string[]
  agent_install_prompt: string
  usage_instructions: string
  zip_path: string
  zip_size: number
  zip_filename: string
  has_zip: boolean
  is_active: boolean
  is_published: boolean
  requires_approval: boolean
  install_count: number
  created_by: number | null
  created_at: string | null
  updated_at: string | null
}

export interface SkillListResult {
  items: Skill[]
  total: number
  page: number
  page_size: number
}

export interface CreateSkillCategoryParams {
  name: string
  description?: string
  sort_order?: number
}
