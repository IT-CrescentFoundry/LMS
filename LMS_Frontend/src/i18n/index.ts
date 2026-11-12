/**
 * i18next initialisation.
 *
 * Language resolution order: saved preference -> browser language -> English.
 * English is also the fallback for any key missing in another language.
 * Resources are bundled for Stage A; they can be lazy-loaded per language
 * once the translation catalogue grows.
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
import bn from './locales/bn/common.json'
import en from './locales/en/common.json'
import gu from './locales/gu/common.json'
import hi from './locales/hi/common.json'

export const resources = {
  en: { common: en },
  bn: { common: bn },
  hi: { common: hi },
  gu: { common: gu },
} as const

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

void i18n.use(initReactI18next).init({
  resources,
  lng: resolveInitialLanguage(),
  fallbackLng: DEFAULT_LANGUAGE,
  supportedLngs: SUPPORTED_LANGUAGES.map((language) => language.code),
  defaultNS: 'common',
  ns: ['common'],
  interpolation: { escapeValue: false }, // React already escapes output
  returnNull: false,
  react: { useSuspense: false },
})

/** Changes the UI language and remembers the choice on this device. */
export async function changeLanguage(language: LanguageCode): Promise<void> {
  await i18n.changeLanguage(language)
  storeLanguage(language)
}

export default i18n
