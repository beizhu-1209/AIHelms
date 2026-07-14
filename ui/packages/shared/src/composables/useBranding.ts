import { computed, ref } from 'vue'
import { getBranding } from '../api/branding'
import type { BrandingInfo } from '../types/branding'

const branding = ref<BrandingInfo | null>(null)
const loading = ref(false)
const assetRevision = ref(Date.now())

export function useBranding() {
  const logoUrl = computed(() =>
    branding.value?.has_logo ? `/api/v1/branding/logo?v=${assetRevision.value}` : null,
  )
  const faviconUrl = computed(() =>
    branding.value?.has_favicon ? `/api/v1/branding/favicon?v=${assetRevision.value}` : null,
  )
  const squareLogoUrl = computed(() => {
    if (branding.value?.has_square_logo) {
      return `/api/v1/branding/square-logo?v=${assetRevision.value}`
    }
    return faviconUrl.value
  })

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      branding.value = await getBranding()
      assetRevision.value = Date.now()
    } catch {
      branding.value = null
    } finally {
      loading.value = false
    }
  }

  function applyToDocument(): void {
    document.title = branding.value?.platform_name || 'AIHelms'
    const existing = document.querySelector<HTMLLinkElement>("link[rel='icon']")
    const link = existing ?? document.createElement('link')
    link.rel = 'icon'
    link.href = faviconUrl.value ?? '/favicon.ico'
    if (!existing) document.head.appendChild(link)
  }

  return { branding, loading, logoUrl, squareLogoUrl, faviconUrl, refresh, applyToDocument }
}
