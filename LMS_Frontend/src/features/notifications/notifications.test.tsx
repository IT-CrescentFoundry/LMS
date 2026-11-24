import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { EMPLOYEE, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { CHANNELS, notification, PREFERENCES, schemaPending } from '../../test/trainingFixtures'

afterEach(() => {
  vi.unstubAllGlobals()
})

const routes = {
  'GET /notifications': reply({ items: [notification()], unread_count: 1 }),
  'GET /notifications/preferences': reply(PREFERENCES),
  'GET /notifications/channels': reply(CHANNELS),
}

describe('Notification centre', () => {
  it('lists messages, marks one as read and shows the bell count', async () => {
    const api = mockSignedIn(EMPLOYEE, {
      ...routes,
      'POST /notifications/note-1/read': reply(notification({ read_at: '2026-12-02T05:00:00Z' })),
    })
    const user = userEvent.setup()
    renderApp('/notifications')
    const list = await screen.findByRole('list', { name: 'Your notifications' })
    expect(within(list).getByText('Reminder: Synthetic fire safety basics')).toBeInTheDocument()
    expect(within(list).getByRole('link', { name: 'Open' })).toHaveAttribute('href', '/training/events/event-1')
    expect(await screen.findByRole('link', { name: 'Notifications, 1 unread' })).toHaveAttribute('href', '/notifications')

    await user.click(within(list).getByRole('button', { name: 'Mark as read' }))
    await waitFor(() => expect(api.requestsTo('POST /notifications/note-1/read')[0]?.body).toEqual({ read: true }))
  })

  it('never claims Outlook or Teams are connected and locks mandatory types', async () => {
    mockSignedIn(EMPLOYEE, routes)
    renderApp('/notifications')
    const channels = await screen.findByRole('region', { name: 'Delivery channels' })
    expect(await within(channels).findAllByText('Not connected — requires Microsoft 365 setup by IT')).toHaveLength(2)
    expect(within(channels).getByText('Connected')).toBeInTheDocument()
    const prefs = screen.getByRole('region', { name: 'What you receive' })
    expect(within(prefs).getByRole('checkbox', { name: 'Receive Training cancelled' })).toBeDisabled()
    expect(within(prefs).getByRole('checkbox', { name: 'Receive Reminder' })).toBeEnabled()
  })

  it('shows the migration notice and hides the bell while the update is pending', async () => {
    mockSignedIn(EMPLOYEE, {
      'GET /notifications': reply(schemaPending(), 503),
      'GET /notifications/preferences': reply(schemaPending(), 503),
      'GET /notifications/channels': reply(schemaPending(), 503),
    })
    renderApp('/notifications')
    expect(
      await screen.findByText(
        'This module is installed but its database update (migration 0011) is awaiting administrator approval.',
      ),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /unread/ })).not.toBeInTheDocument()
  })
})
