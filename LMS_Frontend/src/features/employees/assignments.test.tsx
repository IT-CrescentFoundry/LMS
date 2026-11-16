import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { formatDate } from '../../lib/format'
import { ASSIGNMENTS, assignmentWrite, writeRoutes } from '../../test/employeeFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const d = (iso: string) => formatDate(iso, 'en')
const OPEN = ASSIGNMENTS[1] // primary in Test Melting from 2026-07-01, version 1
const ENDED = ASSIGNMENTS[0]

async function openTab(routes = writeRoutes()) {
  const api = mockSignedIn(HR_ADMIN, routes)
  const user = userEvent.setup()
  renderApp('/employees/emp-1/assignments')
  await screen.findByRole('table', { name: 'Assignment timeline' })
  return { api, user }
}

async function openAdd(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Add assignment' }))
  const dialog = await screen.findByRole('dialog', { name: 'Add assignment: Test Person One' })
  await within(dialog).findByRole('option', { name: /Test Melting \(TEST_MELT\)/ })
  return dialog
}

describe('Add assignment', () => {
  it.each(['primary', 'additional', 'acting', 'deputation'])('sends a %s assignment', async (type) => {
    const { api, user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments': reply(assignmentWrite(OPEN), 201) }),
    )
    const dialog = await openAdd(user)
    await user.selectOptions(within(dialog).getByLabelText(/^Assignment type/), type)
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-melt')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add assignment' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/assignments')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/assignments')[0].body).toEqual({
      assignment_type: type,
      org_unit_id: 'unit-melt',
      designation_id: null,
      grade_id: null,
      job_level_id: null,
      location_id: null,
      effective_from: '2026-12-01',
      effective_to: null,
      reason: null,
    })
  })

  it('converts the entered last day into the exclusive end and keeps the start unchanged', async () => {
    const { api, user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments': reply(assignmentWrite(OPEN), 201) }),
    )
    const dialog = await openAdd(user)
    await user.selectOptions(within(dialog).getByLabelText(/^Assignment type/), 'acting')
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-ops')
    await within(dialog).findByRole('option', { name: 'Test Grade One (TEST_G1)' })
    await user.selectOptions(within(dialog).getByLabelText(/^Grade/), 'grade-1')
    await user.selectOptions(within(dialog).getByLabelText(/^Location/), 'loc-1')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2028-02-01')
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2028-02-29')
    await user.click(within(dialog).getByRole('button', { name: 'Add assignment' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/assignments')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/assignments')[0].body).toMatchObject({
      assignment_type: 'acting',
      org_unit_id: 'unit-ops',
      grade_id: 'grade-1',
      location_id: 'loc-1',
      effective_from: '2028-02-01',
      effective_to: '2028-03-01', // leap year: last day 29 Feb -> exclusive 1 Mar
    })
  })

  it('refuses a last day before the start without calling the API', async () => {
    const { api, user } = await openTab()
    const dialog = await openAdd(user)
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-melt')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-10')
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add assignment' }))
    expect(within(dialog).getByText('The last day cannot be before the first day.')).toBeInTheDocument()
    expect(api.requestsTo('POST /employees/emp-1/assignments')).toHaveLength(0)
  })

  it('shows the non-assignable unit type warning returned with the saved assignment', async () => {
    const warning = { code: 'unit_type_not_assignable', message: 'English text never shown' }
    const { user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments': reply(assignmentWrite(OPEN, [warning]), 201) }),
    )
    const dialog = await openAdd(user)
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-ops')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add assignment' }))

    const notice = (await screen.findByText('Assignment in Test Melting added.')).closest('[role="status"]')
    expect(notice).not.toBeNull()
    expect(notice).toHaveTextContent('This unit type is not normally used for employee assignments.')
    expect(notice).not.toHaveTextContent('English text never shown')
  })

  it.each([
    ['primary_overlap', 'The employee already has a primary assignment for part of this period.'],
    ['assignment_overlap', 'The employee is already assigned to this unit for part of this period.'],
    ['outside_employment_period', "The dates fall outside the employee's employment period."],
  ])('translates %s from the server', async (code, text) => {
    const { user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments': reply(errorBody(code), code === 'outside_employment_period' ? 422 : 409) }),
    )
    const dialog = await openAdd(user)
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-melt')
    await user.type(within(dialog).getByLabelText(/^Effective from/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add assignment' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(text)
  })
})

describe('Change, end and correct', () => {
  it('offers change and end only on the open row, correction on every row', async () => {
    await openTab()
    const [ended, open] = screen.getAllByRole('row').slice(1)
    expect(within(open).getByRole('button', { name: 'Change Test Melting assignment from a date' })).toBeInTheDocument()
    expect(within(open).getByRole('button', { name: 'End Test Melting' })).toBeInTheDocument()
    expect(within(ended).queryByRole('button', { name: /from a date/ })).not.toBeInTheDocument()
    expect(within(ended).getByRole('button', { name: `Correct ${ENDED.org_unit.name} assignment` })).toBeInTheDocument()
  })

  it('changes from a date with only the changed fields; the date is sent unchanged', async () => {
    const { api, user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments/asg-2/change': reply(assignmentWrite(OPEN), 201) }),
    )
    await user.click(screen.getByRole('button', { name: 'Change Test Melting assignment from a date' }))
    const dialog = await screen.findByRole('dialog', { name: 'Change from a date: Test Melting' })
    expect(dialog).toHaveTextContent('history')
    await within(dialog).findByRole('option', { name: /Operation \(OPERATION\)/ })
    await user.type(within(dialog).getByLabelText(/^Effective from \(first day/), '2027-01-01')
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-ops')
    await user.click(within(dialog).getByRole('button', { name: 'Save change' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/assignments/asg-2/change')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/assignments/asg-2/change')[0].body).toEqual({
      version: 1,
      effective_date: '2027-01-01',
      reason: null,
      org_unit_id: 'unit-ops',
    })
  })

  it('offers a reload on a version conflict', async () => {
    const { user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments/asg-2/change': reply(errorBody('version_conflict'), 409) }),
    )
    await user.click(screen.getByRole('button', { name: 'Change Test Melting assignment from a date' }))
    const dialog = await screen.findByRole('dialog')
    await within(dialog).findByRole('option', { name: /Operation \(OPERATION\)/ })
    await user.type(within(dialog).getByLabelText(/^Effective from \(first day/), '2027-01-01')
    await user.selectOptions(within(dialog).getByLabelText(/^Organisation unit/), 'unit-ops')
    await user.click(within(dialog).getByRole('button', { name: 'Save change' }))
    const alert = await within(dialog).findByRole('alert')
    expect(within(alert).getByRole('button', { name: 'Reload the latest data' })).toBeInTheDocument()
  })

  it('ends with the last day + 1 as the exclusive end, after a confirmation', async () => {
    const { api, user } = await openTab(
      writeRoutes({ 'POST /employees/emp-1/assignments/asg-2/end': reply({ ...OPEN, effective_to: '2027-01-01' }) }),
    )
    await user.click(screen.getByRole('button', { name: 'End Test Melting' }))
    const dialog = await screen.findByRole('dialog', { name: 'End assignment: Test Melting' })
    expect(within(dialog).getByLabelText(/^Last day in effect/)).toHaveFocus()
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-12-31')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(dialog).toHaveTextContent(
      `Last day in effect: ${d('2026-12-31')}. It no longer applies from ${d('2027-01-01')}.`,
    )
    expect(api.requestsTo('POST /employees/emp-1/assignments/asg-2/end')).toHaveLength(0)
    await user.click(within(dialog).getByRole('button', { name: 'Confirm end date' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/assignments/asg-2/end')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/assignments/asg-2/end')[0].body).toEqual({
      version: 1,
      effective_to: '2027-01-01',
      reason: null,
    })
  })

  it('requires a reason and a confirmation for a historical correction', async () => {
    const { api, user } = await openTab(
      writeRoutes({ 'PATCH /employees/emp-1/assignments/asg-1': reply(assignmentWrite(ENDED)) }),
    )
    await user.click(screen.getByRole('button', { name: 'Correct Operation assignment' }))
    const dialog = await screen.findByRole('dialog', { name: 'Correction: Operation' })
    expect(dialog).toHaveTextContent('Correction (fixes wrongly recorded data)')
    // The stored exclusive end 2026-07-01 is shown as the last day 2026-06-30.
    expect(within(dialog).getByLabelText(/^Last day in effect/)).toHaveValue('2026-06-30')

    await user.selectOptions(within(dialog).getByLabelText(/^Assignment type/), 'acting')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(within(dialog).getByText('A reason is required for a correction.')).toBeInTheDocument()

    await user.clear(within(dialog).getByLabelText(/^Last day in effect/))
    await user.type(within(dialog).getByLabelText(/^Last day in effect/), '2026-05-31')
    await user.type(within(dialog).getByLabelText(/^Reason for the correction/), 'Wrong type recorded')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(dialog).toHaveTextContent('Correct this assignment record?')
    await user.click(within(dialog).getByRole('button', { name: 'Confirm correction' }))

    await waitFor(() => expect(api.requestsTo('PATCH /employees/emp-1/assignments/asg-1')).toHaveLength(1))
    expect(api.requestsTo('PATCH /employees/emp-1/assignments/asg-1')[0].body).toEqual({
      version: 2,
      reason: 'Wrong type recorded',
      assignment_type: 'acting',
      effective_to: '2026-06-01',
    })
  })

  it('shows no change actions without employees.manage', async () => {
    const viewer = makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.EMPLOYEES_HISTORY_VIEW] })
    mockSignedIn(viewer, writeRoutes())
    renderApp('/employees/emp-1/assignments')
    await screen.findByRole('table', { name: 'Assignment timeline' })
    expect(screen.queryByRole('button', { name: 'Add assignment' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Correct / })).not.toBeInTheDocument()
    expect(screen.queryByRole('columnheader', { name: 'Actions' })).not.toBeInTheDocument()
  })
})
