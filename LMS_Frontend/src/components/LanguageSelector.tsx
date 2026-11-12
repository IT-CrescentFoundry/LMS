import { Languages } from 'lucide-react'
import { useId } from 'react'
import { useTranslation } from 'react-i18next'

import { changeLanguage } from '../i18n'
import { isSupportedLanguage, SUPPORTED_LANGUAGES } from '../i18n/languages'

/** Native <select>: accessible, keyboard-friendly and familiar on phones. */
export function LanguageSelector() {
  const { t, i18n } = useTranslation()
  const id = useId()

  return (
    <div className="flex items-center gap-1.5">
      <label htmlFor={id} className="flex items-center text-white/80">
        <Languages aria-hidden="true" className="hidden size-4 sm:block" />
        <span className="sr-only">{t('language.label')}</span>
      </label>
      <select
        id={id}
        value={i18n.resolvedLanguage}
        onChange={(event) => {
          const next = event.target.value
          if (isSupportedLanguage(next)) void changeLanguage(next)
        }}
        className="rounded-md border border-white/20 bg-brand-800 py-1 pr-7 pl-2 text-sm text-white focus:ring-2 focus:ring-ember-400 focus:outline-none"
      >
        {SUPPORTED_LANGUAGES.map((language) => (
          <option key={language.code} value={language.code} lang={language.code}>
            {language.nativeName}
          </option>
        ))}
      </select>
    </div>
  )
}
