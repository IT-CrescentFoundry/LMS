import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'

import { LIVE_OK, mockHealthApi, READY_OK, renderApp } from '../test/renderApp'

describe('AppLayout', () => {
  beforeEach(() => {
    mockHealthApi({ live: LIVE_OK, ready: { body: READY_OK, status: 200 } })
  })

  it('renders branding, navigation and the dashboard', () => {
    renderApp()

    expect(screen.getByText('Crescent Foundry')).toBeInTheDocument()
    expect(screen.getByText('Learning Management System')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main-content',
    )

    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(
      'Welcome to Crescent Foundry LMS',
    )
  })

  it('shows planned modules as non-interactive placeholders', () => {
    renderApp()

    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getAllByRole('link')).toHaveLength(1)

    const plannedGroup = within(nav).getByRole('list', { name: 'Coming soon' })
    const plannedItems = within(plannedGroup).getAllByRole('listitem')
    expect(plannedItems).toHaveLength(9)
    for (const item of plannedItems) {
      expect(item).toHaveAttribute('aria-disabled', 'true')
      expect(within(item).queryByRole('link')).not.toBeInTheDocument()
    }
    expect(within(plannedGroup).getByText('Course Catalogue')).toBeInTheDocument()
  })

  it('opens and closes the mobile navigation drawer', async () => {
    const user = userEvent.setup()
    renderApp()

    const openButton = screen.getByRole('button', { name: 'Open navigation menu' })
    expect(openButton).toHaveAttribute('aria-expanded', 'false')

    await user.click(openButton)
    const drawer = screen.getByRole('dialog', { name: 'Main navigation' })
    expect(within(drawer).getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(openButton).toHaveAttribute('aria-expanded', 'true')

    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.click(openButton)
    await user.click(screen.getByRole('button', { name: 'Close navigation menu' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('shows a translated not-found page for unknown routes', () => {
    renderApp('/no-such-page')

    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/')
  })
})
