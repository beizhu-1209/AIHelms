import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, isSupportedLocale, type AppLocale } from './constants'

function getStoredLocale(): AppLocale | null {
  if (typeof localStorage === 'undefined') return null
  const locale = localStorage.getItem(LOCALE_STORAGE_KEY)
  return isSupportedLocale(locale) ? locale : null
}

function getBrowserLocale(): AppLocale | null {
  if (typeof navigator === 'undefined') return null
  const locale = navigator.language.toLowerCase()
  if (locale.startsWith('zh')) return 'zh-CN'
  if (locale.startsWith('en')) return 'en-US'
  return null
}

export function detectInitialLocale(): AppLocale {
  return getStoredLocale() || getBrowserLocale() || DEFAULT_LOCALE
}
