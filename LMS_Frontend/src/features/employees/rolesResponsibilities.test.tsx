import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { AUDITOR, FUNCTIONAL_ROLES, RESPONSIBILITIES, roleRecord, SAFETY, writeRoutes } from '../../test/employeeFixtures'
import { ref } from '../../test/orgFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const MANAGE_ROLE = ref('role-1', 'TEST_MELT_ROLE', 'Test Melting Work')

async function openRoles(routes = writeRoutes()) {
  const api = mockSignedIn(HR_ADMIN, routes)
  const user = userEvent.setup()
  renderApp('/employees/emp-1/roles')
  await screen.findByRole('table', { name: 'Functional roles' })
  return { api, user }
}

describe('Functional roles', () => {
  it('distinguishes derived, manual and excluded roles with their source assignment', async () => {
    await openRoles()
    const rows = within(screen.getByRole('table', { name: 'Functional roles' })).getAllByRole('row').slice(1)
    const melting = rows.find((row) => row.textContent?.includes('Test Melting Work'))
    expect(melting).toHaveTextContent('In effect')
    expect(melting).toHaveTextContent('From designation Test Operator in Test Melting (Primary assignment)')
    const safety = rows.find((row) => row.textContent?.includes('Test Safety Duty'))
    expect(safety).toHaveTextContent('Not in effect (excluded)')
    const auditor = rows.find((row) => row.textContent?.includes('Test Internal Audit'))
    expect(auditor).toHaveTextContent('Assigned manually')
    // Never presented as login permissions.
    expect(screen.getByText('Functional roles describe the work an employee does. They never grant LMS permissions.')).toBeInTheDocument()
    // Exclude is offered only on a derived role that is not already excluded.
    expect(within(melting!).getByRole('button', { name: 'Exclude Test Melting Work' })).toBeInTheDocument()
    expect(within(safety!).queryByRole('button', { name: /^Exclude/ })).not.toBeInTheDocument()
    expect(within(auditor!).queryByRole('button', { name: /^Exclude/ })).not.toBeInTheDocument()
  })

  it('assigns a role manually with the documented body', async () => {
    const { api, user } = await openRoles(
      writeRoutes({ 'POST /employees/emp-1/functional-roles': reply(roleRecord('fr-9', MANAGE_ROLE, 'manual', null), 201) }),
    )
    await user.click(screen.getByRole('button', { name: 'Assign role manually' }))
    const dialog = await screen.findByRole('dialog', { name: 'Assign a functional role: Test Person One' })
    await within(dialog).findByRole('option', { name: 'Test Melting Work (TEST_MELT_ROLE)' })
    await user.selectOptions(within(dialog).getByLabelText(/^Functional role/), 'role-1')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-12-31')
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Covers audits')
    await user.click(within(dialog).getByRole('button', { name: 'Assign role manually' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/functional-roles')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/functional-roles')[0].body).toEqual({
      functional_role_id: 'role-1',
      kind: 'manual',
      effective_from: '2026-12-01',
      effective_to: '2027-01-01',
      reason: 'Covers audits',
    })
    expect(await screen.findByText('Test Melting Work was assigned.')).toBeInTheDocument()
  })

  it('excludes a derived role inline as an exclusion record', async () => {
    const melting = FUNCTIONAL_ROLES.roles[1].functional_role
    const { api, user } = await openRoles(
      writeRoutes({ 'POST /employees/emp-1/functional-roles': reply(roleRecord('fr-8', melting, 'exclusion', null), 201) }),
    )
    await user.click(screen.getByRole('button', { name: 'Exclude Test Melting Work' }))
    const dialog = await screen.findByRole('dialog', { name: 'Exclude role: Test Melting Work' })
    expect(dialog).toHaveTextContent('Role to exclude: Test Melting Work (TEST_MELTING)')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Exclude role' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/functional-roles')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/functional-roles')[0].body).toEqual({
      functional_role_id: melting.public_id,
      kind: 'exclusion',
      effective_from: '2026-12-01',
      effective_to: null,
      reason: null,
    })
  })

  it('ends a manual role record with the exclusive end', async () => {
    const { api, user } = await openRoles(
      writeRoutes({
        'POST /employees/emp-1/functional-roles/fr-2/end': reply({ ...roleRecord('fr-2', AUDITOR, 'manual', 'Auditor'), effective_to: '2027-01-01' }),
      }),
    )
    const records = screen.getByRole('table', { name: 'Manual roles and exclusions' })
    await user.click(within(records).getByRole('button', { name: 'End Test Internal Audit' }))
    const dialog = await screen.findByRole('dialog', { name: 'End manual role: Test Internal Audit' })
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-12-31')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm end date' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/functional-roles/fr-2/end')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/functional-roles/fr-2/end')[0].body).toEqual({
      effective_to: '2027-01-01',
      reason: null,
    })
  })

  it('shows an ended record without an End action', async () => {
    const ended = { ...roleRecord('fr-1', SAFETY, 'exclusion', 'Medical restriction'), effective_to: '2026-06-01' }
    await openRoles(
      writeRoutes({ 'GET /employees/emp-1/functional-roles': reply({ ...FUNCTIONAL_ROLES, records: [ended] }) }),
    )
    const records = screen.getByRole('table', { name: 'Manual roles and exclusions' })
    expect(records).toHaveTextContent('last day')
    expect(within(records).queryByRole('button', { name: /^End / })).not.toBeInTheDocument()
  })

  it('translates role_assignment_overlap', async () => {
    const { user } = await openRoles(
      writeRoutes({ 'POST /employees/emp-1/functional-roles': reply(errorBody('role_assignment_overlap'), 409) }),
    )
    await user.click(screen.getByRole('button', { name: 'Exclude Test Melting Work' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Exclude role' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'This functional role is already assigned or excluded for part of this period.',
    )
  })

  it('hides role actions without employees.manage', async () => {
    mockSignedIn(makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW] }), writeRoutes())
    renderApp('/employees/emp-1/roles')
    await screen.findByRole('table', { name: 'Functional roles' })
    expect(screen.queryByRole('button', { name: 'Assign role manually' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Exclude/ })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^End / })).not.toBeInTheDocument()
  })
})

describe('Responsibilities', () => {
  async function openTab(routes = writeRoutes()) {
    const api = mockSignedIn(HR_ADMIN, routes)
    const user = userEvent.setup()
    renderApp('/employees/emp-1/responsibilities')
    await screen.findByRole('table', { name: 'Responsibilities' })
    return { api, user }
  }

  it('adds a responsibility with an optional unit and location context', async () => {
    const { api, user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/responsibilities': reply(RESPONSIBILITIES[0], 201) }),
    )
    await user.click(screen.getByRole('button', { name: 'Add responsibility' }))
    const dialog = await screen.findByRole('dialog', { name: 'Add responsibility: Test Person One' })
    expect(dialog).toHaveTextContent('do not grant LMS permissions')
    await within(dialog).findByRole('option', { name: 'Test Fire Warden (TEST_WARDEN)' })
    await user.selectOptions(within(dialog).getByLabelText(/^Responsibility/), 'resp-1')
    await within(dialog).findByRole('option', { name: /Test Melting \(TEST_MELT\)/ })
    await user.selectOptions(within(dialog).getByLabelText(/^For organisation unit/), 'unit-melt')
    await user.selectOptions(within(dialog).getByLabelText(/^For location/), 'loc-1')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add responsibility' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/responsibilities')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/responsibilities')[0].body).toEqual({
      responsibility_id: 'resp-1',
      context_unit_id: 'unit-melt',
      context_location_id: 'loc-1',
      effective_from: '2026-12-01',
      effective_to: null,
      reason: null,
    })
  })

  it('requires a responsibility and a start before sending', async () => {
    const { api, user } = await openTab()
    await user.click(screen.getByRole('button', { name: 'Add responsibility' }))
    const dialog = await screen.findByRole('dialog')
    await user.click(within(dialog).getByRole('button', { name: 'Add responsibility' }))
    expect(within(dialog).getAllByText('This field is required.')).toHaveLength(2)
    expect(api.requestsTo('POST /employees/emp-1/responsibilities')).toHaveLength(0)
  })

  it('translates responsibility_overlap', async () => {
    const { user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/responsibilities': reply(errorBody('responsibility_overlap'), 409) }),
    )
    await user.click(screen.getByRole('button', { name: 'Add responsibility' }))
    const dialog = await screen.findByRole('dialog')
    await within(dialog).findByRole('option', { name: 'Test Fire Warden (TEST_WARDEN)' })
    await user.selectOptions(within(dialog).getByLabelText(/^Responsibility/), 'resp-1')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add responsibility' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'This responsibility is already held in this context for part of this period.',
    )
  })

  it('ends a responsibility with the exclusive end', async () => {
    const { api, user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/responsibilities/resp-1/end': reply({ ...RESPONSIBILITIES[0], effective_to: '2026-12-01' }) }),
    )
    await user.click(screen.getByRole('button', { name: 'End Test Fire Warden' }))
    const dialog = await screen.findByRole('dialog', { name: 'End responsibility: Test Fire Warden' })
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-11-30')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    await user.click(within(dialog).getByRole('button', { name: 'Confirm end date' }))
    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/responsibilities/resp-1/end')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/responsibilities/resp-1/end')[0].body).toEqual({
      effective_to: '2026-12-01',
      reason: null,
    })
  })
})
