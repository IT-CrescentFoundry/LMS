import 'i18next'

import type en from './locales/en/common.json'

// Type-checks translation keys against the English resource:
// t('dashboard.title') compiles, t('dashboard.typo') does not.
declare module 'i18next' {
  interface CustomTypeOptions {
    defaultNS: 'common'
    resources: { common: typeof en }
    returnNull: false
  }
}
