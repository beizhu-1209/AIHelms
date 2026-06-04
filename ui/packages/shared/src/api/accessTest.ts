import { request } from './request'
import type { TestAccessParams, TestAccessResult, TestEmbeddingParams, TestEmbeddingResult, TestRerankParams, TestRerankResult } from '../types/accessTest'

function getToken(): string | null {
  return localStorage.getItem('aihelms_token')
}

export function testModelAccessStream(params: TestAccessParams): Promise<Response> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  // 流式请求需要原始 fetch 以支持 SSE 流读取
  return fetch('/api/v1/access-test/test', {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  })
}

export function testModelAccessSync(params: TestAccessParams): Promise<TestAccessResult> {
  return request<TestAccessResult>('/api/v1/access-test/test', {
    method: 'POST',
    body: { ...params, stream: false },
  })
}

export function testEmbedding(params: TestEmbeddingParams): Promise<TestEmbeddingResult> {
  return request<TestEmbeddingResult>('/api/v1/access-test/test-embedding', {
    method: 'POST',
    body: params,
  })
}

export function testRerank(params: TestRerankParams): Promise<TestRerankResult> {
  return request<TestRerankResult>('/api/v1/access-test/test-rerank', {
    method: 'POST',
    body: params,
  })
}
