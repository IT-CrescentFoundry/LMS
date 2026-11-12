import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  LIVE_OK,
  mockHealthApi,
  READY_NO_DATABASE,
  READY_OK,
  renderApp,
} from '../../test/renderApp'

/** Health-check integration: real API client and services, stubbed network. */
describe('API connectivity', () => {
  it('shows "Connected" when the API is live and ready', async () => {
    const fetchMock = mockHealthApi({ live: LIVE_OK, ready: { body: READY_OK, status: 200 } })
    renderApp()

    const indicator = await screen.findByRole('status', { name: /API connection status: Connected$/ })
    expect(indicator).toHaveAttribute('data-state', 'online')

    const panel = screen.getByRole('region', { name: 'System status' })
    expect(within(panel).getByText('0.1.0')).toBeInTheDocument()
    expect(within(panel).getAllByText('Available')).toHaveLength(2)

    const requestedUrls = fetchMock.mock.calls.map(([input]) => String(input))
    expect(requestedUrls).toContain('/api/v1/health/live')
    expect(requestedUrls).toContain('/api/v1/health/ready')
  })

  it('shows a degraded state when the database is not configured (readiness 503)', async () => {
    mockHealthApi({ live: LIVE_OK, ready: { body: READY_NO_DATABASE, status: 503 } })
    renderApp()

    const indicator = await screen.findByRole('status', {
      name: /API connection status: Connected · database unavailable/,
    })
    expect(indicator).toHaveAttribute('data-state', 'degraded')

    const panel = screen.getByRole('region', { name: 'System status' })
    expect(await within(panel).findByText('Not configured')).toBeInTheDocument()
  })

  it('shows an offline state with a retry action when the API is unreachable', async () => {
    mockHealthApi({ live: new TypeError('Failed to fetch') })
    renderApp()

    const indicator = await screen.findByRole('status', {
      name: /API connection status: API unreachable/,
    })
    expect(indicator).toHaveAttribute('data-state', 'offline')
    expect(screen.getByRole('alert')).toHaveTextContent('Cannot reach the LMS API')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
  })
})
