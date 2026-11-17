/**
 * Every translation catalogue, imported statically.
 *
 * For tests and key-consistency checks only: application code must not import this
 * module, otherwise all four catalogues are bundled into the first download again.
 * The application loads English up front and the others on demand (./index.ts).
 */

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
