import { isTranslationLocale, type Translations } from '../../types/organisation'

/**
 * Display name in the UI language: the translation when one exists, otherwise the
 * stored (canonical) name. Names are business data and are never machine-translated.
 */
export function localName(
  entity: { name: string; translations?: Translations },
  language: string | undefined,
): string {
  if (isTranslationLocale(language)) {
    const translated = entity.translations?.[language]
    if (translated) return translated
  }
  return entity.name
}

/** Same for designations, whose display field is `title`. */
export function localTitle(
  entity: { title: string; translations?: Translations },
  language: string | undefined,
): string {
  return localName({ name: entity.title, translations: entity.translations }, language)
}

/** Case- and accent-insensitive "contains" used by client-side search boxes. */
export function textMatches(haystack: readonly (string | null | undefined)[], needle: string): boolean {
  const query = normalise(needle)
  if (query === '') return true
  return haystack.some((value) => value !== null && value !== undefined && normalise(value).includes(query))
}

function normalise(value: string): string {
  return value
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLocaleLowerCase()
    .trim()
}
