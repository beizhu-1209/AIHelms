import { request } from './request'
import type { AiKey } from '../types/ai-key'
import type { CurrentUser } from '../types/auth'
import type { EfficiencyKpi, TrendItem } from '../types/efficiency'
import type {
  ApplicationStatus,
  ResourceApplicationResourceInfo,
  ResourceType,
} from '../types/resource-application'

interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export type HubUser = Pick<CurrentUser,
  | 'id'
  | 'username'
  | 'email'
  | 'display_name'
  | 'avatar'
  | 'position'
  | 'is_admin'
  | 'departments'
>

export type HubAiKey = Pick<AiKey,
  | 'id'
  | 'name'
  | 'description'
  | 'key_type'
  | 'models'
  | 'mcps'
  | 'skills'
  | 'agents'
  | 'budget_limit'
  | 'budget_used'
  | 'budget_hard_limit'
  | 'budget_duration'
  | 'budget_scope'
  | 'budget_models_total'
  | 'budget_mcps_total'
  | 'budget_models_per'
  | 'budget_mcps_per'
  | 'model_budgets'
  | 'mcp_budgets'
  | 'rate_limit_mode'
  | 'tpm_limit'
  | 'rpm_limit'
  | 'max_parallel_requests'
  | 'is_active'
  | 'expires_at'
> & { key_value: string | null }

export interface HubKeys {
  personal: {
    main_key: HubAiKey | null
  }
}

export interface HubAgent {
  id: number
  name: string
  icon_url: string
  description: string
  platform: string
  category: string
  chat_url: string
  tags: string[]
  requires_approval: boolean
  status: string
  user_count: number
}

export interface HubSkill {
  id: number
  name: string
  icon_url: string
  description: string
  category: string
  tags: string[]
  author: string
  requires_approval: boolean
  install_count: number
}

export interface HubMcp {
  id: number
  name: string
  icon_url: string
  description: string
  category: string
  tags: string[]
  author: string
  requires_approval: boolean
  status: string
  call_count: number
}

export interface HubApplication {
  id: number
  resource_type: ResourceType
  resource_id: number
  resource_info: ResourceApplicationResourceInfo | null
  status: ApplicationStatus
  created_at: string | null
}

export interface ModelSquareModel {
  id: number
  name: string
  model_id: string
  model_id_anthropic: string | null
  category: string
  capabilities: string[]
  description: string
  logo_provider_type: string
  icon_url: string
  base_url: string
  is_active: boolean
  is_published: boolean
  requires_approval: boolean
  has_anthropic_deployment: boolean
}

export interface AiIdentityV2Result {
  user: HubUser
  keys: HubKeys
  overview: EfficiencyKpi | null
  trend: TrendItem[]
  applications: PageResult<HubApplication>
  mcp: PageResult<HubMcp>
  skills: PageResult<HubSkill>
  models: ModelSquareModel[]
}

export interface AgentCenterV2Result {
  agents: PageResult<HubAgent>
  keys: HubKeys
}

export interface MarketV2Result {
  skills: PageResult<HubSkill>
  mcp: PageResult<HubMcp>
  keys: HubKeys
}

export interface ModelSquareV2Result {
  models: ModelSquareModel[]
  keys: HubKeys
}

export function getAiIdentityV2(): Promise<AiIdentityV2Result> {
  return request<AiIdentityV2Result>('/api/v2/ai-identity', { silent: true })
}

export function getAgentCenterV2(page = 1, pageSize = 100): Promise<AgentCenterV2Result> {
  return request<AgentCenterV2Result>('/api/v2/agent-center', {
    params: { page, page_size: pageSize },
  })
}

export function getMarketV2(page = 1, pageSize = 100): Promise<MarketV2Result> {
  return request<MarketV2Result>('/api/v2/market', {
    params: { page, page_size: pageSize },
  })
}

export function getModelSquareV2(): Promise<ModelSquareV2Result> {
  return request<ModelSquareV2Result>('/api/v2/model-square')
}
