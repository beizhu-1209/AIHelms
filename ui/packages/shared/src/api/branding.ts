import { request } from './request'
import type { BrandingInfo } from '../types/branding'

export function getBranding(): Promise<BrandingInfo> {
  return request<BrandingInfo>('/api/v1/branding')
}

export function updatePlatformName(name: string): Promise<BrandingInfo> {
  const form = new FormData()
  form.append('platform_name', name)
  return request<BrandingInfo>('/api/v1/branding', { method: 'PUT', body: form })
}

export function uploadLogo(file: File): Promise<null> {
  const form = new FormData()
  form.append('file', file)
  return request<null>('/api/v1/branding/logo', { method: 'POST', body: form })
}

export function uploadSquareLogo(file: File): Promise<null> {
  const form = new FormData()
  form.append('file', file)
  return request<null>('/api/v1/branding/square-logo', { method: 'POST', body: form })
}

export function uploadFavicon(file: File): Promise<null> {
  const form = new FormData()
  form.append('file', file)
  return request<null>('/api/v1/branding/favicon', { method: 'POST', body: form })
}
