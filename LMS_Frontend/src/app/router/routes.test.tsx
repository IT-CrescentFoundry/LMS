/**
 * Router regression tests (browser issue fix 2026-11-24): the first load of a
 * lazy route used to render nothing and log "No `HydrateFallback` element
 * provided to render during initial hydration".
 */

import { act, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { errorBody, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { competency, TRAINING_ADMIN } from '../../test/trainingFixtures'

const HYDRATE_WARNING = 'HydrateFallback'

function hydrateWarnings(spy: { mock: { calls: unknown[][] } }): unknown[][] {
  return spy.mock.calls.filter((args) => args.some((arg) => String(arg).includes(HYDRATE_WARNING)))
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

function signedInAdmin() {
  return mockSignedIn(TRAINING_ADMIN, {
    'GET /competency/my-skills': reply(errorBody('employee_not_linked'), 404),
    'GET /competency/competencies': reply({ items: [competency()], total: 1, limit: 50, offset: 0 }),
    'GET /competency/categories': reply(['Operation']),
  })
}

describe('Initial route loading', () => {
  it.each([
    ['/', { name: 'Welcome to Crescent Foundry LMS', level: 1 }],
    ['/skills/me', { name: 'My skills', level: 1 }],
    ['/competencies', { name: 'Competency library', level: 1 }],
  ])('shows the branded loading screen, then %s, without a hydration warning', async (path, heading) => {
    const warn = vi.spyOn(console, 'warn')
    signedInAdmin()
    renderApp(path, { strict: true })
    // First render: the lazy route's code is not loaded yet - never a blank page.
    expect(screen.getByRole('status')).toHaveTextContent('Loading…')
    expect(await screen.findByRole('heading', heading)).toBeInTheDocument()
    expect(hydrateWarnings(warn)).toEqual([])
  })

  it('navigates between sections after the first load', async () => {
    const warn = vi.spyOn(console, 'warn')
    signedInAdmin()
    const { router } = renderApp('/')
    await screen.findByRole('heading', { name: 'Welcome to Crescent Foundry LMS', level: 1 })
    for (const [path, name] of [
      ['/organisation', 'Organisation structure'],
      ['/employees', 'Employees'],
      ['/training', 'Training records'],
      ['/skills/me', 'My skills'],
      ['/competencies', 'Competency library'],
      ['/', 'Welcome to Crescent Foundry LMS'],
    ] as const) {
      await act(() => router.navigate(path))
      expect(await screen.findByRole('heading', { name, level: 1 })).toBeInTheDocument()
      expect(router.state.location.pathname).toBe(path)
    }
    expect(hydrateWarnings(warn)).toEqual([])
  })
})
