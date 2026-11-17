/**
 * i18next initialisation.
 *
 * Language resolution order: saved preference -> browser language -> English.
 * English is also the fallback for any key missing in another language.
 *
 * Only the English catalogue is bundled with the application. Bengali, Hindi and
 * Gujarati are separate files loaded on demand: before the first render for the
 * initial language (`i18nReady`, awaited by main.tsx) and before switching
 * (`changeLanguage`). Each catalogue is downloaded at most once.
 */

import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import {
  DEFAULT_LANGUAGE,
  isSupportedLanguage,
  LANGUAGE_STORAGE_KEY,
  matchSupportedLanguage,
  SUPPORTED_LANGUAGES,
  type LanguageCode,
} from './languages'
import en from './locales/en/common.json'

type OnDemandLanguage = Exclude<LanguageCode, 'en'> // English is bundled

const loaders: Record<OnDemandLanguage, () => Promise<{ default: object }>> = {
  bn: () => import('./locales/bn/common.json'),
  hi: () => import('./locales/hi/common.json'),
  gu: () => import('./locales/gu/common.json'),
}
const pending = new Map<LanguageCode, Promise<void>>()

function readStoredLanguage(): LanguageCode | undefined {
  try {
    const stored = window.localStorage.getItem(LANGUAGE_STORAGE_KEY)
    return isSupportedLanguage(stored) ? stored : undefined
  } catch {
    return undefined // storage unavailable (private mode, blocked cookies)
  }
}

function storeLanguage(language: LanguageCode): void {
  try {
    window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language)
  } catch {
    // Preference simply isn't remembered; the UI still works.
  }
}

function detectBrowserLanguage(): LanguageCode | undefined {
  const candidates = navigator.languages?.length ? navigator.languages : [navigator.language]
  for (const locale of candidates) {
    const match = matchSupportedLanguage(locale)
    if (match) return match
  }
  return undefined
}

export function resolveInitialLanguage(): LanguageCode {
  return readStoredLanguage() ?? detectBrowserLanguage() ?? DEFAULT_LANGUAGE
}

i18n.on('languageChanged', (language) => {
  if (isSupportedLanguage(language)) {
    document.documentElement.lang = language
  }
})

const initialLanguage = resolveInitialLanguage()

void i18n.use(initReactI18next).init({
  resources: { [DEFAULT_LANGUAGE]: { common: en } },
  lng: initialLanguage,
  fallbackLng: DEFAULT_LANGUAGE,
  supportedLngs: SUPPORTED_LANGUAGES.map((language) => language.code),
  defaultNS: 'common',
  ns: ['common'],
  interpolation: { escapeValue: false }, // React already escapes output
  returnNull: false,
  react: { useSuspense: false },
})

/** Downloads a language's catalogue once (English is always present). */
export function loadLanguage(language: LanguageCode): Promise<void> {
  const loader = language in loaders ? loaders[language as OnDemandLanguage] : undefined
  if (!loader || i18n.hasResourceBundle(language, 'common')) {
    return Promise.resolve()
  }
  const inFlight = pending.get(language)
  if (inFlight) return inFlight
  const loading = loader()
    .then((module: { default: object }) => {
      i18n.addResourceBundle(language, 'common', module.default, true, true)
    })
    .finally(() => pending.delete(language))
  pending.set(language, loading)
  return loading
}

/**
 * Resolves when the initial language is ready to render. Never rejects: if its
 * catalogue cannot be downloaded the interface falls back to English.
 */
export const i18nReady: Promise<void> = loadLanguage(initialLanguage).then(
  async () => {
    if (initialLanguage !== DEFAULT_LANGUAGE) await i18n.changeLanguage(initialLanguage)
  },
  async () => {
    await i18n.changeLanguage(DEFAULT_LANGUAGE)
  },
)

/**
 * Changes the UI language and remembers the choice on this device. If the
 * catalogue cannot be downloaded (e.g. offline) the current language is kept.
 */
export async function changeLanguage(language: LanguageCode): Promise<void> {
  try {
    await loadLanguage(language)
  } catch {
    return
  }
  await i18n.changeLanguage(language)
  storeLanguage(language)
}

export default i18n
