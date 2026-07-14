import { computed, ref } from 'vue'
import { getLicense } from '../api/license'
import type { LicenseStatus } from '../types/license'

const status = ref<LicenseStatus | null>(null)
const loading = ref(false)

export function useLicense() {
  const isEnterprise = computed(() => status.value?.edition === 'enterprise')

  function hasFeature(feature: string): boolean {
    return status.value?.features.includes(feature) ?? false
  }

  async function refresh(): Promise<void> {
    loading.value = true
    try {
      status.value = await getLicense()
    } catch {
      status.value = null
    } finally {
      loading.value = false
    }
  }

  return { status, loading, isEnterprise, hasFeature, refresh }
}
