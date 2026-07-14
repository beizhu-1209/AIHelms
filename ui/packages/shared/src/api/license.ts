import { request } from './request'
import type { LicenseStatus } from '../types/license'

export function getLicense(): Promise<LicenseStatus> {
  return request<LicenseStatus>('/api/v1/license')
}

export function importLicense(file: File): Promise<LicenseStatus> {
  const form = new FormData()
  form.append('file', file)
  return request<LicenseStatus>('/api/v1/license/import', {
    method: 'POST',
    body: form,
  })
}
