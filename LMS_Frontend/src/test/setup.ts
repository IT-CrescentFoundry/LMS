import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import i18n from '../i18n'
import { setAuthHandlers, setCsrfToken } from '../lib/apiClient'

afterEach(async () => {
  cleanup()
  window.localStorage.clear()
  window.sessionStorage.clear()
  setCsrfToken(null)
  setAuthHandlers(null)
  await i18n.changeLanguage('en')
})
