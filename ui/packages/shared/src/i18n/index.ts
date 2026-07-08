import { createI18n, type I18nOptions } from 'vue-i18n'
import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, SUPPORTED_LOCALES, isSupportedLocale, type AppLocale } from './constants'

export { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, SUPPORTED_LOCALES, isSupportedLocale }
export type { AppLocale }

type MessageSchema = Record<string, string>
type LocaleMessages = Record<AppLocale, MessageSchema>
type WritableLocale = { value: string }
type ActiveI18n = { global: { locale: string | WritableLocale } }

let activeI18n: ActiveI18n | null = null

export function getCurrentLocale(): AppLocale {
  if (typeof localStorage === 'undefined') return DEFAULT_LOCALE
  const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
  return isSupportedLocale(stored) ? stored : DEFAULT_LOCALE
}

export function createI18nInstance(locale: AppLocale, messages: LocaleMessages) {
  const i18n = createI18n({
    legacy: false,
    locale,
    fallbackLocale: DEFAULT_LOCALE,
    flatJson: true,
    messages,
  } as I18nOptions)

  activeI18n = i18n as unknown as ActiveI18n
  setLocale(locale)
  return i18n
}

export function setLocale(locale: AppLocale): void {
  if (!isSupportedLocale(locale)) return
  if (activeI18n) {
    const globalLocale = activeI18n.global.locale
    if (typeof globalLocale === 'string') {
      activeI18n.global.locale = locale
    } else {
      globalLocale.value = locale
    }
  }
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem(LOCALE_STORAGE_KEY, locale)
  }
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
    window.dispatchEvent(new CustomEvent('aihelms:locale-changed', { detail: locale }))
  }
}

export { detectInitialLocale } from './detect'
