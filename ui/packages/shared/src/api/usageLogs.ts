import { request } from './request'
import type {
  AgentLog,
  AgentLogFilters,
  LlmLog,
  LlmLogDetail,
  LlmLogFilters,
  LogListResult,
  McpLog,
  McpLogDetail,
  McpLogFilters,
  SkillLog,
  SkillLogFilters,
} from '../types/usageLogs'

interface CommonQuery {
  page?: number
  page_size?: number
  start_time?: string
  end_time?: string
  user_id?: number
}

export interface LlmLogQuery extends CommonQuery {
  ai_key_id?: number
  model?: string
  provider?: string
  status?: 'success' | 'failure'
}

export interface McpLogQuery extends CommonQuery {
  ai_key_id?: number
  server_id?: number
  tool_name?: string
  status?: string
}

export interface SkillLogQuery extends CommonQuery {
  skill_id?: number
  action?: string
}

export interface AgentLogQuery extends CommonQuery {
  agent_id?: number
  platform?: string
}

export function getLlmLogs(query: LlmLogQuery = {}): Promise<LogListResult<LlmLog>> {
  return request<LogListResult<LlmLog>>('/api/v1/usage-logs/llm', { params: { ...query } })
}

export function getLlmLogById(id: number): Promise<LlmLogDetail> {
  return request<LlmLogDetail>(`/api/v1/usage-logs/llm/${id}`)
}

export function getLlmLogFilters(): Promise<LlmLogFilters> {
  return request<LlmLogFilters>('/api/v1/usage-logs/llm/filters')
}

export function getMcpLogs(query: McpLogQuery = {}): Promise<LogListResult<McpLog>> {
  return request<LogListResult<McpLog>>('/api/v1/usage-logs/mcp', { params: { ...query } })
}

export function getMcpLogById(id: number): Promise<McpLogDetail> {
  return request<McpLogDetail>(`/api/v1/usage-logs/mcp/${id}`)
}

export function getMcpLogFilters(): Promise<McpLogFilters> {
  return request<McpLogFilters>('/api/v1/usage-logs/mcp/filters')
}

export function getSkillLogs(query: SkillLogQuery = {}): Promise<LogListResult<SkillLog>> {
  return request<LogListResult<SkillLog>>('/api/v1/usage-logs/skill', { params: { ...query } })
}

export function getSkillLogFilters(): Promise<SkillLogFilters> {
  return request<SkillLogFilters>('/api/v1/usage-logs/skill/filters')
}

export function getAgentLogs(query: AgentLogQuery = {}): Promise<LogListResult<AgentLog>> {
  return request<LogListResult<AgentLog>>('/api/v1/usage-logs/agent', { params: { ...query } })
}

export function getAgentLogFilters(): Promise<AgentLogFilters> {
  return request<AgentLogFilters>('/api/v1/usage-logs/agent/filters')
}
