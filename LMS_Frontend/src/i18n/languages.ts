/** Languages supported by the LMS user interface. Codes are BCP 47 primary tags. */

export const SUPPORTED_LANGUAGES = [
  { code: 'en', englishName: 'English', nativeName: 'English' },
  { code: 'bn', englishName: 'Bengali', nativeName: 'বাংলা' },
  { code: 'hi', englishName: 'Hindi', nativeName: 'हिन्दी' },
  { code: 'gu', englishName: 'Gujarati', nativeName: 'ગુજરાતી' },
] as const

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]['code']

export const DEFAULT_LANGUAGE: LanguageCode = 'en'

export const LANGUAGE_STORAGE_KEY = 'lms.language'

export function isSupportedLanguage(value: unknown): value is LanguageCode {
  return SUPPORTED_LANGUAGES.some((language) => language.code === value)
}

/** Maps a browser locale such as "hi-IN" to a supported language, if any. */
export function matchSupportedLanguage(locale: string | undefined): LanguageCode | undefined {
  if (!locale) return undefined
  const primary = locale.toLowerCase().split('-')[0]
  return isSupportedLanguage(primary) ? primary : undefined
}
