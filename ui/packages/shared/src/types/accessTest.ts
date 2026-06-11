export interface TestAccessParams {
  model: string
  messages: { role: string; content: string }[]
  stream?: boolean
  max_tokens?: number
}

export interface AccessTestErrorDetail {
  category: string
  title: string
  message: string
  technical_detail: string
  status_code?: number
}

export interface TestAccessResult {
  success: boolean
  content: string
  model?: string
  error?: string
  error_detail?: AccessTestErrorDetail
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export interface TestEmbeddingParams {
  model: string
  text?: string
}

export interface TestEmbeddingResult {
  success: boolean
  dimensions?: number
  model?: string
  error?: string
  error_detail?: AccessTestErrorDetail
  usage?: {
    prompt_tokens: number
    total_tokens: number
  }
}

export interface TestRerankParams {
  model: string
  query?: string
  documents?: string[]
}

export interface TestRerankResult {
  success: boolean
  results?: { index: number; relevance_score: number }[]
  model?: string
  error?: string
  error_detail?: AccessTestErrorDetail
}
