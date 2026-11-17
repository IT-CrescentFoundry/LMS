import '@testing-library/jest-dom/vitest'

import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

import i18n from '../i18n'
import { setAuthHandlers, setCsrfToken } from '../lib/apiClient'

// Pages are route-level lazy modules. The first test in a file that opens a page pays
// the one-off cost of compiling it, which under a full parallel run can exceed Testing
// Library's default 1 s wait for `findBy*` (seen as an intermittent failure of the first
// account-linking test). Waiting longer only delays genuine failures; it never hides one.
configure({ asyncUtilTimeout: 4000 })

afterEach(async () => {
  cleanup()
  window.localStorage.clear()
  window.sessionStorage.clear()
  setCsrfToken(null)
  setAuthHandlers(null)
  await i18n.changeLanguage('en')
})
