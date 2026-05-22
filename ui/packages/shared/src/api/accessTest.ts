import type { TestAccessParams, TestAccessResult, TestEmbeddingParams, TestEmbeddingResult, TestRerankParams, TestRerankResult } from '../types/accessTest'
import type { ApiResponse } from './request'

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
  return fetch('/api/v1/access-test/test', {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...params, stream: true }),
  })
}

export async function testModelAccessSync(params: TestAccessParams): Promise<TestAccessResult> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch('/api/v1/access-test/test', {
    method: 'POST',
    headers,
    body: JSON.stringify({ ...params, stream: false }),
  })
  const json: ApiResponse<TestAccessResult> = await response.json()
  return json.data
}

export async function testEmbedding(params: TestEmbeddingParams): Promise<TestEmbeddingResult> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch('/api/v1/access-test/test-embedding', {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  })
  const json: ApiResponse<TestEmbeddingResult> = await response.json()
  return json.data
}

export async function testRerank(params: TestRerankParams): Promise<TestRerankResult> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch('/api/v1/access-test/test-rerank', {
    method: 'POST',
    headers,
    body: JSON.stringify(params),
  })
  const json: ApiResponse<TestRerankResult> = await response.json()
  return json.data
}
