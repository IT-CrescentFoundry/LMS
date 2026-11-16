import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { employee, writeRoutes } from '../../test/employeeFixtures'
import { errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

const VIEWER = makeUser({ permissions: [PERMISSIONS.EMPLOYEES_VIEW, PERMISSIONS.EMPLOYEES_HISTORY_VIEW] })

async function openCreate() {
  const user = userEvent.setup()
  renderApp('/employees')
  await user.click(await screen.findByRole('button', { name: 'Add employee' }))
  return { user, dialog: await screen.findByRole('dialog', { name: 'Add employee' }) }
}

describe('Create employee', () => {
  it('validates required fields and the employee code before sending anything', async () => {
    const api = mockSignedIn(HR_ADMIN, writeRoutes())
    const { user, dialog } = await openCreate()

    // The first field has focus when the dialog opens.
    expect(within(dialog).getByLabelText(/^Employee code/)).toHaveFocus()
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))
    expect(within(dialog).getAllByText('This field is required.')).toHaveLength(2)

    await user.type(within(dialog).getByLabelText(/^Employee code/), 'A B#1')
    await user.type(within(dialog).getByLabelText(/^Full name/), 'Test Person New')
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))
    expect(
      within(dialog).getByText('Use letters, digits and / . _ - only (up to 30), starting with a letter or digit.'),
    ).toBeInTheDocument()
    expect(api.requestsTo('POST /employees')).toHaveLength(0)
  })

  it('sends the documented body, shows the stored code and opens the new profile', async () => {
    const created = employee(undefined, { public_id: 'emp-1', employee_code: '00077', employment_status: null })
    const api = mockSignedIn(HR_ADMIN, writeRoutes({ 'POST /employees': reply(created, 201), 'GET /employees/emp-1': reply(created) }))
    const { user, dialog } = await openCreate()

    await user.type(within(dialog).getByLabelText(/^Employee code/), ' t-0077 ')
    expect(within(dialog).getByText('Will be stored as T-0077.')).toBeInTheDocument()
    await user.clear(within(dialog).getByLabelText(/^Employee code/))
    await user.type(within(dialog).getByLabelText(/^Employee code/), '00077')
    await user.type(within(dialog).getByLabelText(/^Full name/), 'Test Person New')
    await user.type(within(dialog).getByLabelText(/^Work email/), 'new.person@example.test')
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))

    await waitFor(() => expect(api.requestsTo('POST /employees')).toHaveLength(1))
    expect(api.requestsTo('POST /employees')[0].body).toEqual({
      employee_code: '00077',
      full_name: 'Test Person New',
      display_name: null,
      preferred_language: null,
      work_email: 'new.person@example.test',
      employment_status: null,
      date_of_joining: null,
      date_of_separation: null,
      external_ref: null,
    })
    expect(await screen.findByText('Employee 00077 was created.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toBeInTheDocument()
  })

  it('needs a last working day only for someone who had already left', async () => {
    const api = mockSignedIn(HR_ADMIN, writeRoutes())
    const { user, dialog } = await openCreate()
    await user.type(within(dialog).getByLabelText(/^Employee code/), 'T-0100')
    await user.type(within(dialog).getByLabelText(/^Full name/), 'Test Former Person')
    await user.type(within(dialog).getByLabelText(/^Date of joining/), '2026-03-01')
    await user.selectOptions(within(dialog).getByLabelText(/^Employment status/), 'separated')
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))
    expect(within(dialog).getByText('This field is required.')).toBeInTheDocument()

    await user.type(within(dialog).getByLabelText(/^Last working day/), '2026-02-01')
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))
    expect(within(dialog).getByText('The last working day cannot be before the date of joining.')).toBeInTheDocument()
    expect(api.requestsTo('POST /employees')).toHaveLength(0)
  })

  it('translates a taken or invalid code from the server', async () => {
    mockSignedIn(HR_ADMIN, writeRoutes({ 'POST /employees': reply(errorBody('employee_code_taken'), 409) }))
    const { user, dialog } = await openCreate()
    await user.type(within(dialog).getByLabelText(/^Employee code/), 'T-0001')
    await user.type(within(dialog).getByLabelText(/^Full name/), 'Test Person')
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))
    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent('Another employee already uses this employee code.')
    expect(alert).toHaveTextContent('req-test-1')
  })

  it('is not offered without employees.manage', async () => {
    mockSignedIn(VIEWER, writeRoutes())
    renderApp('/employees')
    expect(await screen.findByText('Read only')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add employee' })).not.toBeInTheDocument()
  })
})

describe('Server validation errors', () => {
  async function submitNew(details: unknown[]) {
    const api = mockSignedIn(
      HR_ADMIN,
      writeRoutes({ 'POST /employees': reply(errorBody('validation_error', 'English never shown', details), 422) }),
    )
    const { user, dialog } = await openCreate()
    await user.type(within(dialog).getByLabelText(/^Employee code/), 'T-0200')
    await user.type(within(dialog).getByLabelText(/^Full name/), 'Test Person')
    await user.type(within(dialog).getByLabelText(/^Work email/), 'a@example.test')
    await user.click(within(dialog).getByRole('button', { name: 'Add employee' }))
    await within(dialog).findByRole('alert')
    return { api, dialog }
  }

  it('shows structured problems on their fields and keeps the form-level error', async () => {
    const { dialog } = await submitNew([
      { location: ['body', 'work_email'], message: 'x', type: 'string_too_long' },
      { location: ['body', 'date_of_joining'], message: 'x', type: 'date_from_datetime_parsing' },
    ])
    const email = within(dialog).getByLabelText(/^Work email/)
    expect(email).toHaveAttribute('aria-invalid', 'true')
    expect(within(dialog).getByText('This value is too long.')).toBeInTheDocument()
    expect(within(dialog).getByLabelText(/^Date of joining/)).toHaveAttribute('aria-invalid', 'true')
    expect(within(dialog).getByText('Enter a valid date.')).toBeInTheDocument()
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Some of the values are not valid.')
    expect(dialog).not.toHaveTextContent('English never shown')
  })

  it('keeps unknown or unstructured problems at form level only', async () => {
    const { dialog } = await submitNew([
      { location: ['body'], message: 'x', type: 'model_attributes_type' },
      { location: ['query', 'limit'], message: 'x', type: 'int_parsing' },
    ])
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Some of the values are not valid.')
    expect(within(dialog).queryAllByRole('textbox').filter((el) => el.getAttribute('aria-invalid') === 'true')).toHaveLength(0)
  })
})

describe('Edit employee details', () => {
  it('sends only the changed fields with the version and reason', async () => {
    const api = mockSignedIn(HR_ADMIN, writeRoutes({ 'PATCH /employees/emp-1': reply(employee()) }))
    const user = userEvent.setup()
    renderApp('/employees/emp-1')
    await user.click(await screen.findByRole('button', { name: 'Edit details' }))
    const dialog = await screen.findByRole('dialog', { name: 'Edit details: Test Person One' })
    // Status is not edited here.
    expect(within(dialog).queryByLabelText(/^Employment status/)).not.toBeInTheDocument()

    await user.click(within(dialog).getByRole('button', { name: 'Save correction' }))
    expect(within(dialog).getByText('Nothing has changed, so there is nothing to save.')).toBeInTheDocument()
    expect(api.requestsTo('PATCH /employees/emp-1')).toHaveLength(0)

    await user.type(within(dialog).getByLabelText(/^Display name/), 'Person One')
    await user.clear(within(dialog).getByLabelText(/^Work email/))
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Spelling fixed')
    await user.click(within(dialog).getByRole('button', { name: 'Save correction' }))

    await waitFor(() => expect(api.requestsTo('PATCH /employees/emp-1')).toHaveLength(1))
    expect(api.requestsTo('PATCH /employees/emp-1')[0].body).toEqual({
      version: 3,
      reason: 'Spelling fixed',
      display_name: 'Person One',
      work_email: null,
    })
    expect(await screen.findByText('The details of 00042 were corrected.')).toBeInTheDocument()
  })

  it('offers a reload after a version conflict and never retries', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      writeRoutes({ 'PATCH /employees/emp-1': reply(errorBody('version_conflict'), 409) }),
    )
    const user = userEvent.setup()
    renderApp('/employees/emp-1')
    await user.click(await screen.findByRole('button', { name: 'Edit details' }))
    const dialog = await screen.findByRole('dialog')
    await user.type(within(dialog).getByLabelText(/^Display name/), 'X')
    await user.click(within(dialog).getByRole('button', { name: 'Save correction' }))
    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent('Someone else changed this record in the meantime.')
    expect(api.requestsTo('PATCH /employees/emp-1')).toHaveLength(1)

    const reads = api.requestsTo('GET /employees/emp-1').length
    await user.click(within(alert).getByRole('button', { name: 'Reload the latest data' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    await waitFor(() => expect(api.requestsTo('GET /employees/emp-1').length).toBeGreaterThan(reads))
    expect(api.requestsTo('PATCH /employees/emp-1')).toHaveLength(1)
  })
})

describe('Employment status', () => {
  it('changes to On leave without offering separation', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      writeRoutes({ 'POST /employees/emp-1/employment-status': reply(employee(undefined, { employment_status: 'on_leave' })) }),
    )
    const user = userEvent.setup()
    renderApp('/employees/emp-1')
    await user.click(await screen.findByRole('button', { name: 'Change status' }))
    const dialog = await screen.findByRole('dialog', { name: 'Change status: Test Person One' })
    const select = within(dialog).getByLabelText(/^New status/)
    expect(select).toHaveFocus() // the dialog opens on its first field
    const options = within(select).getAllByRole('option').map((option) => option.textContent)
    expect(options).toEqual(['On leave']) // already active; never "Separated"
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Long leave')
    await user.click(within(dialog).getByRole('button', { name: 'Save status' }))

    await waitFor(() => expect(api.requestsTo('POST /employees/emp-1/employment-status')).toHaveLength(1))
    expect(api.requestsTo('POST /employees/emp-1/employment-status')[0].body).toEqual({
      version: 3,
      status: 'on_leave',
      separation_date: null,
      end_open_records: false,
      end_direct_reports: false,
      reason: 'Long leave',
    })
    expect(await screen.findByText('The status is now On leave.')).toBeInTheDocument()
  })

  it('lets a not-recorded status become Active or On leave', async () => {
    mockSignedIn(HR_ADMIN, writeRoutes({ 'GET /employees/emp-1': reply(employee(undefined, { employment_status: null })) }))
    const user = userEvent.setup()
    renderApp('/employees/emp-1')
    await user.click(await screen.findByRole('button', { name: 'Change status' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('Current status: Not recorded')
    const options = within(within(dialog).getByLabelText(/^New status/)).getAllByRole('option')
    expect(options.map((option) => option.textContent)).toEqual(['Choose…', 'Active', 'On leave'])
  })

  it('hides every change action from a view-only user', async () => {
    mockSignedIn(VIEWER, writeRoutes())
    renderApp('/employees/emp-1')
    await screen.findByRole('heading', { level: 1, name: 'Test Person One' })
    for (const name of ['Edit details', 'Change status', 'Separate employee']) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
    }
  })
})
