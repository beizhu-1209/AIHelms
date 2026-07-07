export type AiPolicyAuditStatus = 'queued' | 'running' | 'completed' | 'failed'
export type AiPolicyAuditDecision = '' | 'passed' | 'attention_required' | 'high_risk' | 'failed'
export type AiPolicyAuditSeverity = '' | 'critical' | 'high' | 'medium' | 'low' | 'info' | 'none' | 'unknown'

export interface AiPolicyFindingLocation {
  file?: string
  start_line?: number | null
  end_line?: number | null
}

export interface AiPolicyFindingEvidence {
  snippet?: string
  matched_text?: string
}

export interface AiPolicyFindingGroupLocation extends AiPolicyFindingLocation {
  snippet?: string
}

export interface AiPolicyFinding {
  source?: 'static' | 'llm' | string
  group_id?: string
  rule_id?: string
  category?: string
  raw_category?: string
  scanner_severity?: AiPolicyAuditSeverity
  effective_severity?: AiPolicyAuditSeverity
  severity?: AiPolicyAuditSeverity
  confidence?: number
  title?: string
  description?: string
  recommendation?: string
  file_role?: string
  path_bucket?: string
  finding_type?: 'true_risk' | 'false_positive' | 'review_note' | 'scanner_diagnostic' | string
  counts_toward_score?: boolean
  denoise_reason?: string
  command_context?: Record<string, unknown>
  llm_review?: Record<string, unknown>
  redline?: boolean
  location?: AiPolicyFindingLocation
  evidence?: AiPolicyFindingEvidence
  hit_count?: number
  locations?: AiPolicyFindingGroupLocation[]
  must_review?: boolean
}

export interface AiPolicyAuditSummary {
  audit_id: string
  audit_type: string
  skill_id: number | null
  skill_name: string
  skill_version: string
  status: AiPolicyAuditStatus
  decision: AiPolicyAuditDecision
  severity: AiPolicyAuditSeverity
  risk_score: number
  findings_count: number
  high_risk_count: number
  must_review_count: number
  llm_review_used: boolean
  llm_review_model?: string
  source_sha256?: string
  error_message?: string
  started_at?: string | null
  finished_at?: string | null
  created_at?: string | null
  updated_at?: string | null
  summary?: Record<string, unknown>
}

export interface AiPolicyAuditFileSummary {
  path: string
  role?: string
  role_label?: string
  status?: string
  severity?: AiPolicyAuditSeverity
  risk_count?: number
  size?: number
}

export interface AiPolicyAudit extends AiPolicyAuditSummary {
  id: number
  findings?: AiPolicyFinding[]
  markdown_report?: string
}

export interface AiPolicyAuditListResult {
  items: AiPolicyAuditSummary[]
  total: number
  page: number
  page_size: number
}

export interface AiPolicyAuditQuery {
  page?: number
  page_size?: number
  audit_type?: 'skill' | 'mcp' | 'agent' | 'prompt' | string
  skill_id?: number
  status?: AiPolicyAuditStatus | string
  decision?: AiPolicyAuditDecision | string
  q?: string
  finished_from?: string
  finished_to?: string
  unfinished?: boolean
}

export interface AiPolicyRiskCatalogItem {
  code: string
  name_en: string
  name_zh: string
  severity: string
  description_zh: string
  check_points: string[]
  sort_order: number
}

export interface AiPolicySettings {
  llm_review_enabled: boolean
  llm_review_model_id: number | null
  updated_by?: number | null
  updated_at?: string | null
}
