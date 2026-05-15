export interface TestAccessParams {
  model: string
  messages: { role: string; content: string }[]
  stream?: boolean
}

export interface TestAccessResult {
  success: boolean
  content: string
  model?: string
  error?: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}
