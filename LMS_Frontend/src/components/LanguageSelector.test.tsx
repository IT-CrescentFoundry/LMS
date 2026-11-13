import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { resources } from '../i18n'
import { LANGUAGE_STORAGE_KEY } from '../i18n/languages'
import { EMPLOYEE, mockApi, mockSignedIn, renderApp } from '../test/renderApp'

describe('LanguageSelector', () => {
  it('offers all four languages by their native names', async () => {
    mockSignedIn(EMPLOYEE)
    renderApp()

    const select = await screen.findByRole('combobox', { name: 'Language' })
    const options = within(select)
      .getAllByRole('option')
      .map((option) => option.textContent)
    expect(options).toEqual(['English', 'বাংলা', 'हिन्दी', 'ગુજરાતી'])
  })

  it('switches the whole interface between English, Bengali, Hindi and Gujarati', async () => {
    mockSignedIn(EMPLOYEE)
    const user = userEvent.setup()
    renderApp()

    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
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

  it('is available on the sign-in page and translates it', async () => {
    mockApi()
    const user = userEvent.setup()
    renderApp('/login')

    expect(await screen.findByRole('heading', { level: 1 })).toHaveTextContent(
      resources.en.common.auth.login.title,
    )

    for (const code of ['bn', 'hi', 'gu'] as const) {
      const strings = resources[code].common
      await user.selectOptions(screen.getByRole('combobox'), code)

      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(strings.auth.login.title)
      expect(screen.getByLabelText(strings.auth.login.loginId)).toBeInTheDocument()
      expect(screen.getByLabelText(strings.auth.login.password)).toBeInTheDocument()
      expect(
        screen.getByRole('button', { name: strings.auth.login.submit }),
      ).toBeInTheDocument()
      expect(document.documentElement.lang).toBe(code)
    }
  })
})
