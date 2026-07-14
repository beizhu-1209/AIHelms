export interface LicenseStatus {
  edition: 'community' | 'enterprise'
  licensed_to: string | null
  expires_at: string | null
  features: string[]
  status: string
}
