import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import {
  EMPLOYEE,
  HR_ADMIN,
  mockSignedIn,
  renderApp,
  reply,
  SUPER_ADMIN,
  SUPERVISOR,
} from '../test/renderApp'

describe('AppLayout', () => {
  it('renders branding, navigation, the user and the dashboard', async () => {
    mockSignedIn(EMPLOYEE)
    renderApp()

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Welcome to Crescent Foundry LMS' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Crescent Foundry')).toBeInTheDocument()
    expect(screen.getByText('Learning Management System')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute(
      'href',
      '#main-content',
    )
    expect(screen.getByRole('button', { name: 'Account menu for Test Employee' })).toBeInTheDocument()

    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
  })

  it('shows planned modules as non-interactive placeholders', async () => {
    mockSignedIn(EMPLOYEE)
    renderApp()

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getAllByRole('link')).toHaveLength(1)

    const plannedGroup = within(nav).getByRole('list', { name: 'Coming soon' })
    const plannedItems = within(plannedGroup).getAllByRole('listitem')
    // Organisation became a real page in Stage C2 (and needs organisation.view).
    expect(plannedItems).toHaveLength(7)
    expect(within(plannedGroup).queryByText('Organisation')).not.toBeInTheDocument()
    for (const item of plannedItems) {
      expect(item).toHaveAttribute('aria-disabled', 'true')
      expect(within(item).queryByRole('link')).not.toBeInTheDocument()
    }
    expect(within(plannedGroup).getByText('Course Catalogue')).toBeInTheDocument()
  })

  it('shows an employee no Administration group', async () => {
    mockSignedIn(EMPLOYEE)
    renderApp()

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).queryByRole('list', { name: 'Administration' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'User accounts' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Audit log' })).not.toBeInTheDocument()
  })

  it.each([
    ['HR Admin', HR_ADMIN],
    ['Super Admin', SUPER_ADMIN],
  ])('shows %s the Administration pages they are permitted to use', async (_label, user) => {
    mockSignedIn(user)
    renderApp()

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    const adminGroup = within(nav).getByRole('list', { name: 'Administration' })
    expect(within(adminGroup).getByRole('link', { name: 'User accounts' })).toHaveAttribute(
      'href',
      '/admin/users',
    )
    expect(within(adminGroup).getByRole('link', { name: 'Audit log' })).toHaveAttribute(
      'href',
      '/admin/audit-log',
    )
  })

  it('shows the Organisation link only with organisation.view and keeps it active on sub-pages', async () => {
    mockSignedIn(SUPERVISOR, { 'GET /org/locations': reply([]) })
    renderApp('/organisation/locations')

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    const link = within(nav).getByRole('link', { name: 'Organisation' })
    expect(link).toHaveAttribute('href', '/organisation')
    expect(link).toHaveAttribute('aria-current', 'page')
  })

  it('hides the Organisation link from users without organisation.view', async () => {
    mockSignedIn(EMPLOYEE)
    renderApp()

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).queryByRole('link', { name: 'Organisation' })).not.toBeInTheDocument()
  })

  it('shows only the items matching each permission (no role-name checks)', async () => {
    mockSignedIn({ ...EMPLOYEE, roles: ['custom_role'], permissions: ['audit.view'] })
    renderApp()

    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    const adminGroup = within(nav).getByRole('list', { name: 'Administration' })
    expect(within(adminGroup).getAllByRole('link')).toHaveLength(1)
    expect(within(adminGroup).getByRole('link', { name: 'Audit log' })).toBeInTheDocument()
  })

  it('opens and closes the mobile navigation drawer', async () => {
    mockSignedIn(EMPLOYEE)
    const user = userEvent.setup()
    renderApp()

    const openButton = await screen.findByRole('button', { name: 'Open navigation menu' })
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

  it('shows a translated not-found page for unknown routes when signed in', async () => {
    mockSignedIn(EMPLOYEE)
    renderApp('/no-such-page')

    expect(await screen.findByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Back to dashboard' })).toHaveAttribute('href', '/')
  })

  it('does not reveal unknown routes to anonymous visitors (sign-in first)', async () => {
    mockSignedIn(EMPLOYEE, { 'GET /auth/session': reply({ authenticated: false }) })
    renderApp('/no-such-page')

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByText('Page not found')).not.toBeInTheDocument()
  })
})
