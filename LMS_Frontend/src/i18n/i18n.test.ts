import { describe, expect, it, vi } from 'vitest'

import i18n, { changeLanguage, loadLanguage } from '.'
import { resources } from './catalogues'
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
    const strings = resources[code].common
    const english = resources.en.common
    expect(strings.dashboard.subtitle).not.toBe(english.dashboard.subtitle)
    expect(strings.nav.dashboard).not.toBe(english.nav.dashboard)
    // Stage B6 sections
    expect(strings.auth.login.title).not.toBe(english.auth.login.title)
    expect(strings.auth.errors.invalidCredentials).not.toBe(english.auth.errors.invalidCredentials)
    expect(strings.auth.password.issues.too_common).not.toBe(english.auth.password.issues.too_common)
    expect(strings.admin.users.title).not.toBe(english.admin.users.title)
    expect(strings.admin.audit.viewingRecorded).not.toBe(english.admin.audit.viewingRecorded)
    expect(strings.audit.events.loginSucceeded).not.toBe(english.audit.events.loginSucceeded)
    expect(strings.roles.hr_admin).not.toBe(english.roles.hr_admin)
    expect(strings.errors.forbiddenTitle).not.toBe(english.errors.forbiddenTitle)
  })

  it.each(SUPPORTED_LANGUAGES.map((language) => language.code))(
    '%s keeps every interpolation placeholder of the English text',
    (code) => {
      const translated = flattenKeys(resources[code].common)
      for (const [key, value] of flattenKeys(resources.en.common)) {
        const placeholders = String(value).match(/\{\{\w+\}\}/g) ?? []
        for (const placeholder of placeholders) {
          expect(String(translated.get(key)), `${code}: ${key}`).toContain(placeholder)
        }
      }
    },
  )
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

describe('on-demand catalogues', () => {
  it('bundles only English; other languages are loaded once, exactly as published', async () => {
    expect(i18n.hasResourceBundle('en', 'common')).toBe(true)
    await Promise.all([loadLanguage('gu'), loadLanguage('gu')])
    expect(i18n.getResourceBundle('gu', 'common')).toEqual(resources.gu.common)
  })

  it('keeps the current language when a catalogue cannot be downloaded', async () => {
    i18n.removeResourceBundle('hi', 'common')
    const spy = vi.spyOn(i18n, 'addResourceBundle').mockImplementationOnce(() => {
      throw new Error('offline')
    })
    await changeLanguage('hi')
    expect(spy).toHaveBeenCalledOnce()
    expect(i18n.resolvedLanguage).toBe('en')
    expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBeNull()
    await changeLanguage('hi') // a later attempt loads it normally
    expect(i18n.t('nav.dashboard')).toBe(resources.hi.common.nav.dashboard)
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
