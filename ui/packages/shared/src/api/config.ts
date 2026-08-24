import { request } from './request'
import type { PublicConfig } from '../types/config'

export function getPublicConfig(): Promise<PublicConfig> {
  return request<PublicConfig>('/api/v1/config/public', { silent: true })
}
