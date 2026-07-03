import { request } from './request'
import type {
  AiPolicyAudit,
  AiPolicyAuditListResult,
  AiPolicyAuditQuery,
  AiPolicyRiskCatalogItem,
  AiPolicySettings,
} from '../types/aiPolicies'

export function getAiPolicyAudits(params: AiPolicyAuditQuery = {}): Promise<AiPolicyAuditListResult> {
  return request<AiPolicyAuditListResult>('/api/v1/ai-policies/audits', {
    params: params as Record<string, string | number | boolean | undefined>,
  })
}

export function getAiPolicyAudit(
  auditId: string,
  params: Record<string, string | number | boolean | undefined> = {},
): Promise<AiPolicyAudit> {
  return request<AiPolicyAudit>(`/api/v1/ai-policies/audits/${auditId}`, { params })
}

export function getAiPolicyReportDownloadUrl(auditId: string): string {
  return `/api/v1/ai-policies/audits/${auditId}/download`
}

export function getAiPolicyRiskCatalog(): Promise<AiPolicyRiskCatalogItem[]> {
  return request<AiPolicyRiskCatalogItem[]>('/api/v1/ai-policies/catalog')
}

export function getAiPolicySettings(): Promise<AiPolicySettings> {
  return request<AiPolicySettings>('/api/v1/ai-policies/settings')
}

export function updateAiPolicySettings(params: Pick<AiPolicySettings, 'llm_review_enabled' | 'llm_review_model_id'>): Promise<AiPolicySettings> {
  return request<AiPolicySettings>('/api/v1/ai-policies/settings', { method: 'PUT', body: params })
}
