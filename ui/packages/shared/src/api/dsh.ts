import { request } from './request'
import type { DshSession } from '../types/dsh'

export function createDshSession(): Promise<DshSession> {
  return request<DshSession>('/api/v1/dsh/session')
}
