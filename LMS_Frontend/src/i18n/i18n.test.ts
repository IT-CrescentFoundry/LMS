import { describe, expect, it } from 'vitest'

import i18n, { changeLanguage, resources } from '.'
import {
  LANGUAGE_STORAGE_KEY,
  matchSupportedLanguage,
  SUPPORTED_LANGUAGES,
  type LanguageCode,
} from './languages'

function flattenKeys(value: unknown, prefix = ''): Map<string, unknown> {
  const entries = new Map<string, unknown>()
  if (typeof value === 'object' && value !== null) {
    for (const [key, child] of Object.entries(value)) {
      const path = prefix ? `${prefix}.${key}` : key
      if (typeof child === 'object' && child !== null) {
        for (const [nestedKey, nestedValue] of flattenKeys(child, path)) {
          entries.set(nestedKey, nestedValue)
        }
      } else {
        entries.set(path, child)
      }
    }
  }
  return entries
}

const englishKeys = [...flattenKeys(resources.en.common).keys()].sort()
const otherLanguages = SUPPORTED_LANGUAGES.map((language) => language.code).filter(
  (code) => code !== 'en',
)

describe('translation resources', () => {
  it('provides exactly the four supported languages', () => {
    expect(Object.keys(resources).sort()).toEqual(['bn', 'en', 'gu', 'hi'])
  })

  it.each(otherLanguages)('%s has exactly the same keys as English', (code) => {
    const keys = [...flattenKeys(resources[code].common).keys()].sort()
    expect(keys).toEqual(englishKeys)
  })

  it.each(SUPPORTED_LANGUAGES.map((language) => language.code))(
    '%s has no empty translations',
    (code) => {
      for (const [key, value] of flattenKeys(resources[code].common)) {
        expect(typeof value, key).toBe('string')
        expect((value as string).trim(), key).not.toBe('')
      }
    },
  )

  it.each(['bn', 'hi', 'gu'] as const)('%s is actually translated (not a copy of English)', (code) => {
    expect(resources[code].common.dashboard.subtitle).not.toBe(resources.en.common.dashboard.subtitle)
    expect(resources[code].common.nav.dashboard).not.toBe(resources.en.common.nav.dashboard)
  })
})

describe('language switching', () => {
  it.each<[LanguageCode, string]>([
    ['bn', resources.bn.common.nav.dashboard],
    ['hi', resources.hi.common.nav.dashboard],
    ['gu', resources.gu.common.nav.dashboard],
    ['en', 'Dashboard'],
  ])('switches to %s, updates <html lang> and remembers the choice', async (code, expected) => {
    await changeLanguage(code)

    expect(i18n.resolvedLanguage).toBe(code)
    expect(i18n.t('nav.dashboard')).toBe(expected)
    expect(document.documentElement.lang).toBe(code)
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe(code)
  })
})

describe('matchSupportedLanguage', () => {
  it('maps regional browser locales to supported languages', () => {
    expect(matchSupportedLanguage('hi-IN')).toBe('hi')
    expect(matchSupportedLanguage('bn-BD')).toBe('bn')
    expect(matchSupportedLanguage('gu')).toBe('gu')
    expect(matchSupportedLanguage('en-GB')).toBe('en')
  })

  it('ignores unsupported locales', () => {
    expect(matchSupportedLanguage('fr-FR')).toBeUndefined()
    expect(matchSupportedLanguage(undefined)).toBeUndefined()
  })
})
