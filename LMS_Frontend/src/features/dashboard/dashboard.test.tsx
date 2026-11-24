import { screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { EMPLOYEE, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { calendarItem, notification, schemaPending, SUMMARY, TRAINING_ADMIN } from '../../test/trainingFixtures'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Dashboard', () => {
  it('shows only the widgets the user may see, with recorded facts', async () => {
    mockSignedIn(TRAINING_ADMIN, {
      'GET /training/summary': reply(SUMMARY),
      'GET /training/calendar': reply({ scope: 'own', start: '2026-12-01', end: '2026-12-31', items: [calendarItem()] }),
      'GET /notifications': reply({ items: [notification()], unread_count: 1 }),
      'GET /competency/my-skills': reply({ employee: { public_id: 'e', employee_code: 'SYN-001', name: 'A' }, matrices: [] }),
    })
    renderApp('/')
    expect(await screen.findByRole('region', { name: 'Training register' })).toBeInTheDocument()
    expect(await screen.findByRole('region', { name: 'My upcoming training' })).toBeInTheDocument()
    expect(await screen.findByText('Unread: 1')).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'My skill gaps' })).not.toBeInTheDocument()
  })

  it('shows one migration notice instead of the widgets while the update is pending', async () => {
    mockSignedIn(EMPLOYEE, { 'GET /notifications': reply(schemaPending(), 503) })
    renderApp('/')
    expect(
      await screen.findByText(
        'This module is installed but its database update (migration 0011) is awaiting administrator approval.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Notifications' })).not.toBeInTheDocument()
  })
})
