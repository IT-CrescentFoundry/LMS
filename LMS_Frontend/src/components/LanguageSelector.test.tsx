import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { resources } from '../i18n'
import { LANGUAGE_STORAGE_KEY } from '../i18n/languages'
import { LIVE_OK, mockHealthApi, READY_OK, renderApp } from '../test/renderApp'

describe('LanguageSelector', () => {
  beforeEach(() => {
    mockHealthApi({ live: LIVE_OK, ready: { body: READY_OK, status: 200 } })
  })

  it('offers all four languages by their native names', () => {
    renderApp()

    const select = screen.getByRole('combobox', { name: 'Language' })
    const options = within(select)
      .getAllByRole('option')
      .map((option) => option.textContent)
    expect(options).toEqual(['English', 'বাংলা', 'हिन्दी', 'ગુજરાતી'])
  })

  it('switches the whole interface between English, Bengali, Hindi and Gujarati', async () => {
    const user = userEvent.setup()
    renderApp()

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      resources.en.common.dashboard.title,
    )

    for (const code of ['bn', 'hi', 'gu', 'en'] as const) {
      const strings = resources[code].common
      await user.selectOptions(screen.getByRole('combobox'), code)

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(strings.dashboard.title)
      expect(screen.getAllByText(strings.nav.dashboard).length).toBeGreaterThan(0)
      expect(screen.getByRole('combobox', { name: strings.language.label })).toHaveValue(code)
      expect(document.documentElement.lang).toBe(code)
      expect(window.localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe(code)
    }
  })
})
