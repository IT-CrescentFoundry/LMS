import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import {
  EMPLOYEE,
  LIVE_OK,
  mockSignedIn,
  READY_NO_DATABASE,
  READY_OK,
  renderApp,
  reply,
} from '../../test/renderApp'

/** Health-check integration: real API client and services, stubbed network. */
describe('API connectivity', () => {
  it('shows "Connected" when the API is live and ready', async () => {
    const api = mockSignedIn(EMPLOYEE)
    renderApp()

    const indicator = await screen.findByRole('status', { name: /API connection status: Connected$/ })
    expect(indicator).toHaveAttribute('data-state', 'online')

    const panel = await screen.findByRole('region', { name: 'System status' })
    expect(await within(panel).findByText('0.1.0')).toBeInTheDocument()
    expect(within(panel).getAllByText('Available')).toHaveLength(2)

    const paths = api.requests.map((request) => request.path)
    expect(paths).toContain('/health/live')
    expect(paths).toContain('/health/ready')
  })

  it('shows a degraded state when the database is not configured (readiness 503)', async () => {
    mockSignedIn(EMPLOYEE, {
      'GET /health/live': reply(LIVE_OK),
      'GET /health/ready': reply(READY_NO_DATABASE, 503),
    })
    renderApp()

    const indicator = await screen.findByRole('status', {
      name: /API connection status: Connected · database unavailable/,
    })
    expect(indicator).toHaveAttribute('data-state', 'degraded')

    const panel = screen.getByRole('region', { name: 'System status' })
    expect(await within(panel).findByText('Not configured')).toBeInTheDocument()
  })

  it('shows an offline state with a retry action when the API is unreachable', async () => {
    mockSignedIn(EMPLOYEE, {
      'GET /health/live': new TypeError('Failed to fetch'),
      'GET /health/ready': reply(READY_OK),
    })
    renderApp()

    const indicator = await screen.findByRole('status', {
      name: /API connection status: API unreachable/,
    })
    expect(indicator).toHaveAttribute('data-state', 'offline')
    expect(screen.getByRole('alert')).toHaveTextContent('Cannot reach the LMS API')
    expect(screen.getByRole('button', { name: 'Try again' })).toBeEnabled()
  })
})
