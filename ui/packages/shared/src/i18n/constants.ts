export const DEFAULT_LOCALE = 'zh-CN'
export const SUPPORTED_LOCALES = ['zh-CN', 'en-US'] as const
export const LOCALE_STORAGE_KEY = 'aihelms_locale'

export type AppLocale = (typeof SUPPORTED_LOCALES)[number]

export function isSupportedLocale(locale: string | null | undefined): locale is AppLocale {
  return SUPPORTED_LOCALES.includes(locale as AppLocale)
}
