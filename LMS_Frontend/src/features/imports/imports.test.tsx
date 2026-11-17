import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  ERROR_ROW,
  FAILED_VALIDATION,
  importRoutes,
  job,
  JOB_ID,
  NEW_ROW,
  page,
  PENDING_MAPPING,
  PROFILE,
  READY,
} from '../../test/importFixtures'
import { EMPLOYEE, errorBody, HR_ADMIN, makeUser, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { changeLanguage } from '../../i18n'
import { PERMISSIONS } from '../auth/permissions'

afterEach(() => {
  vi.unstubAllGlobals()
})

/** Holds imports.view only: may look, may not act. */
const VIEWER = makeUser({
  public_id: '01900000-0000-7000-8000-000000000009',
  login_id: 'test.importviewer',
  display_name: 'Test Import Viewer',
  roles: ['hr_admin'],
  permissions: [PERMISSIONS.IMPORTS_VIEW],
})
const VIEWER_PROFILE = { ...PROFILE, can_run: false, can_commit: false }

/** The job route answers with the latest state, as the server does after an action. */
function statefulJob(initial: unknown, action: string, after: unknown) {
  let current = initial
  return importRoutes(initial, {
    [`GET /imports/${JOB_ID}`]: () => reply(current),
    [action]: () => {
      current = after
      return reply(after)
    },
  })
}

describe('Import Control Room access', () => {
  it('lists Imports in the navigation only for users with imports.view', async () => {
    mockSignedIn(HR_ADMIN, importRoutes(READY))
    renderApp('/')
    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Imports' })).toHaveAttribute('href', '/imports')
  })

  it('hides Imports and refuses the page without imports.view', async () => {
    mockSignedIn(EMPLOYEE, importRoutes(READY))
    renderApp('/imports')
    expect(await screen.findByRole('heading', { name: 'You do not have access to this page' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Imports' })).not.toBeInTheDocument()
  })
})

describe('Overview and history', () => {
  it('shows what needs attention and the history with links to each job', async () => {
    const api = mockSignedIn(HR_ADMIN, importRoutes(READY))
    const user = userEvent.setup()
    renderApp('/imports')
    expect(await screen.findByRole('heading', { level: 1, name: 'Import Control Room' })).toBeInTheDocument()
    expect(screen.getByText(/Nothing is written to employee records until/)).toBeInTheDocument()
    const history = await screen.findByRole('table', { name: 'Import history' })
    expect(within(history).getByText('synthetic-people.xlsx')).toBeInTheDocument()
    expect(within(history).getByText('Ready for approval')).toBeInTheDocument()
    expect(within(history).getByRole('link', { name: 'Open import synthetic-people.xlsx' })).toHaveAttribute(
      'href',
      `/imports/${JOB_ID}`,
    )
    // One pending reference mapping is counted on its tile.
    const tile = screen.getByRole('link', { name: /waiting for review/ })
    expect(await within(tile).findByText('1')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /^Needs corrections/ }))
    await waitFor(() =>
      expect(api.requestsTo('GET /imports').some((request) => request.query.get('status') === 'validation_failed')).toBe(
        true,
      ),
    )
  })

  it('offers New import only to users who may run an import', async () => {
    mockSignedIn(VIEWER, importRoutes(READY, { 'GET /imports/profiles': reply([VIEWER_PROFILE]) }))
    renderApp('/imports')
    expect(await screen.findByRole('table', { name: 'Import history' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'New import' })).not.toBeInTheDocument()
  })
})

describe('New import', () => {
  it('uploads the workbook as the raw body with the CSRF token and opens the job', async () => {
    const created = job()
    const api = mockSignedIn(HR_ADMIN, importRoutes(created, { 'POST /imports': reply(created, 201) }))
    const user = userEvent.setup()
    const { router } = renderApp('/imports/new')
    expect(await screen.findByRole('heading', { level: 1, name: 'New import' })).toBeInTheDocument()
    expect(await screen.findByText(/excluded automatically and never read/)).toBeInTheDocument()

    const file = new File(['synthetic'], 'synthetic people.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    await user.upload(await screen.findByLabelText('Excel workbook (.xlsx)'), file)
    expect(screen.getByText(/Selected: synthetic people.xlsx/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Upload and inspect' }))

    await waitFor(() => expect(router.state.location.pathname).toBe(`/imports/${JOB_ID}`))
    const [upload] = api.requestsTo('POST /imports')
    expect(upload.query.get('profile')).toBe('employees')
    expect(upload.headers['x-csrf-token']).toBe('csrf-test-token-1')
    expect(upload.headers['x-file-name']).toBe('synthetic%20people.xlsx')
    expect(upload.headers['content-type']).toBe('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    const call = api.fetchMock.mock.calls.find(([, init]) => init?.method === 'POST')
    expect(call?.[1]?.body).toBe(file) // the file itself, never a form or JSON
  })

  it('refuses other file types before uploading', async () => {
    const api = mockSignedIn(HR_ADMIN, importRoutes(job()))
    const user = userEvent.setup({ applyAccept: false })
    renderApp('/imports/new')
    await user.upload(await screen.findByLabelText('Excel workbook (.xlsx)'), new File(['a,b'], 'people.csv'))
    expect(screen.getByRole('alert')).toHaveTextContent('Choose an .xlsx workbook.')
    expect(screen.getByRole('button', { name: 'Upload and inspect' })).toBeDisabled()
    expect(api.requestsTo('POST /imports')).toHaveLength(0)
  })

  it('explains a rejected file by its code', async () => {
    mockSignedIn(
      HR_ADMIN,
      importRoutes(job(), { 'POST /imports': reply(errorBody('file_macro_enabled'), 422) }),
    )
    const user = userEvent.setup()
    renderApp('/imports/new')
    await user.upload(await screen.findByLabelText('Excel workbook (.xlsx)'), new File(['x'], 'macro.xlsx'))
    await user.click(screen.getByRole('button', { name: 'Upload and inspect' }))
    expect(await screen.findByText(/contains macros, which are not accepted/)).toBeInTheDocument()
  })
})

describe('Column mapping and validation', () => {
  it('shows excluded columns as unmappable and saves the mapping', async () => {
    const saved = job({ mapping_confirmed: true, version: 2 })
    const api = mockSignedIn(HR_ADMIN, importRoutes(job(), { [`PUT /imports/${JOB_ID}/mapping`]: reply(saved) }))
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    const table = await screen.findByRole('table', { name: 'Columns of worksheet Employees mapped as Employees' })
    const ctc = within(table).getByText('CTC').closest('tr')!
    expect(within(ctc).getByText('Excluded – sensitive')).toBeInTheDocument()
    expect(within(ctc).queryByRole('combobox')).not.toBeInTheDocument()
    expect(within(table).getByLabelText('LMS field for column A (Emp Code)')).toHaveValue('employee_code')

    await user.selectOptions(within(table).getByLabelText('LMS field for column E (Remarks)'), 'employment_status')
    await user.click(screen.getByRole('button', { name: 'Save mapping' }))
    await waitFor(() => expect(api.requestsTo(`PUT /imports/${JOB_ID}/mapping`)).toHaveLength(1))
    expect(api.requestsTo(`PUT /imports/${JOB_ID}/mapping`)[0].body).toEqual({
      version: 1,
      sections: [
        {
          section: 'employees',
          sheet: 'Employees',
          header_row: 1,
          columns: { '1': 'employee_code', '2': 'full_name', '4': 'date_of_joining', '5': 'employment_status' },
        },
      ],
    })
  })

  it('blocks saving while a required field is not mapped', async () => {
    mockSignedIn(HR_ADMIN, importRoutes(job()))
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    const table = await screen.findByRole('table', { name: /Columns of worksheet Employees/ })
    await user.selectOptions(within(table).getByLabelText('LMS field for column B (Employee Name)'), '')
    expect(screen.getByText('Required fields not mapped: Full name')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save mapping' })).toBeDisabled()
  })

  it('validates a confirmed mapping (dry run) and shows the results', async () => {
    const confirmed = job({ mapping_confirmed: true, version: 2 })
    const api = mockSignedIn(HR_ADMIN, statefulJob(confirmed, `POST /imports/${JOB_ID}/validate`, FAILED_VALIDATION))
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    expect(await screen.findByText(/Validation is a dry run/)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Validate' }))
    await waitFor(() => expect(api.requestsTo(`POST /imports/${JOB_ID}/validate`)).toHaveLength(1))
    expect(api.requestsTo(`POST /imports/${JOB_ID}/validate`)[0].body).toEqual({ version: 2 })
    expect(await screen.findByRole('heading', { name: 'Validation results' })).toBeInTheDocument()
    const row = await screen.findByText('Employees row 3')
    const card = row.closest('li')!
    expect(within(card).getByText(/stored as a number, so leading zeros may have been lost/)).toBeInTheDocument()
    expect(within(card).getByText(/in the file: 42/)).toBeInTheDocument()
  })
})

describe('Row decisions', () => {
  it('confirms a probable duplicate as a different person', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      importRoutes(FAILED_VALIDATION, { [`POST /imports/${JOB_ID}/rows/11/decision`]: reply(FAILED_VALIDATION) }),
    )
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    const card = (await screen.findByText('Employees row 2')).closest('li')!
    expect(within(card).getByText(/same name and joining date as employee code\(s\) T-0007/)).toBeInTheDocument()
    await user.click(within(card).getByRole('button', { name: 'Different person' }))
    const dialog = await screen.findByRole('dialog', { name: 'Confirm a different person' })
    await user.click(within(dialog).getByRole('button', { name: 'Confirm different person' }))
    await waitFor(() => expect(api.requestsTo(`POST /imports/${JOB_ID}/rows/11/decision`)).toHaveLength(1))
    expect(api.requestsTo(`POST /imports/${JOB_ID}/rows/11/decision`)[0].body).toEqual({
      version: 3,
      decision: 'distinct',
      reason: null,
    })
  })

  it('needs a reason to skip a row', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      importRoutes(FAILED_VALIDATION, { [`POST /imports/${JOB_ID}/rows/12/decision`]: reply(FAILED_VALIDATION) }),
    )
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    const card = (await screen.findByText('Employees row 3')).closest('li')!
    await user.click(within(card).getByRole('button', { name: 'Skip this row' }))
    const dialog = await screen.findByRole('dialog', { name: 'Skip this row' })
    await user.click(within(dialog).getByRole('button', { name: 'Skip row' }))
    expect(within(dialog).getByText('Enter the reason for skipping this row.')).toBeInTheDocument()
    expect(api.requestsTo(`POST /imports/${JOB_ID}/rows/12/decision`)).toHaveLength(0)
    await user.type(within(dialog).getByLabelText(/^Reason/), 'Code to be confirmed by HR')
    await user.click(within(dialog).getByRole('button', { name: 'Skip row' }))
    await waitFor(() => expect(api.requestsTo(`POST /imports/${JOB_ID}/rows/12/decision`)).toHaveLength(1))
    expect(api.requestsTo(`POST /imports/${JOB_ID}/rows/12/decision`)[0].body).toEqual({
      version: 3,
      decision: 'skip',
      reason: 'Code to be confirmed by HR',
    })
  })
})

describe('Approval', () => {
  it('commits only after explicit confirmation, with apply_updates as chosen', async () => {
    const done = job({
      ...READY,
      status: 'completed',
      version: 6,
      file_stored: false,
      committed_at: '2026-11-16T09:10:00Z',
      committed_by: READY.validated_by,
      counts: { ...READY.counts, committed: { created: 2, updated: 1, unchanged: 0, skipped: 0 } },
    })
    const api = mockSignedIn(HR_ADMIN, statefulJob(READY, `POST /imports/${JOB_ID}/commit`, done))
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    const panel = await screen.findByRole('region', { name: 'Approve and import' })
    const summary = within(panel).getByRole('table', { name: 'Rows to import by section and outcome' })
    expect(within(summary).getByRole('rowheader', { name: 'Employees' }).closest('tr')).toHaveTextContent('Employees210')
    const commit = within(panel).getByRole('button', { name: 'Approve and import' })
    expect(commit).toBeDisabled()
    await user.click(within(panel).getByLabelText('Also apply the listed corrections to 1 existing record'))
    await user.click(within(panel).getByLabelText(/I have reviewed the preview/))
    await user.click(commit)

    await waitFor(() => expect(api.requestsTo(`POST /imports/${JOB_ID}/commit`)).toHaveLength(1))
    expect(api.requestsTo(`POST /imports/${JOB_ID}/commit`)[0].body).toEqual({
      version: 4,
      apply_updates: true,
      confirm: true,
    })
    expect(await screen.findByRole('heading', { name: 'Import completed' })).toBeInTheDocument()
    expect(screen.getByText('Records created').closest('div')).toHaveTextContent('2')
  })

  it('explains a stale preview and offers to reload', async () => {
    mockSignedIn(
      HR_ADMIN,
      importRoutes(READY, { [`POST /imports/${JOB_ID}/commit`]: reply(errorBody('import_preview_expired'), 409) }),
    )
    const user = userEvent.setup()
    renderApp(`/imports/${JOB_ID}`)
    const panel = await screen.findByRole('region', { name: 'Approve and import' })
    await user.click(within(panel).getByLabelText(/I have reviewed the preview/))
    await user.click(within(panel).getByRole('button', { name: 'Approve and import' }))
    expect(await within(panel).findByText('The preview is too old. Validate again before approving.')).toBeInTheDocument()
  })

  it('lets a view-only user review but not map, decide or approve', async () => {
    mockSignedIn(VIEWER, importRoutes(READY, { 'GET /imports/profiles': reply([VIEWER_PROFILE]) }))
    renderApp(`/imports/${JOB_ID}`)
    const panel = await screen.findByRole('region', { name: 'Approve and import' })
    expect(within(panel).getByText(/approving it needs the import approval permission/)).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: 'Approve and import' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Save mapping' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Cancel import' })).not.toBeInTheDocument()
    await screen.findByText('Employees row 2')
    expect(screen.queryByRole('button', { name: 'Different person' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Skip this row' })).not.toBeInTheDocument()
  })
})

describe('Reference mappings', () => {
  it('approves a pending label to a chosen suggestion (never automatically)', async () => {
    const approved = { ...PENDING_MAPPING, status: 'approved', version: 2, suggestions: [] }
    const api = mockSignedIn(
      HR_ADMIN,
      importRoutes(READY, { [`POST /imports/mappings/${PENDING_MAPPING.public_id}/approve`]: reply(approved) }),
    )
    const user = userEvent.setup()
    renderApp('/imports/mappings')
    expect(await screen.findByText(/Nothing is mapped automatically/)).toBeInTheDocument()
    const card = (await screen.findByText('“Sr. Test Opr”')).closest('li')!
    expect(within(card).getByText('Test Senior Operator (T_SR_OPR)')).toBeInTheDocument()
    expect(api.requestsTo('GET /imports/mappings')[0].query.get('status')).toBe('pending')
    await user.click(within(card).getByRole('button', { name: 'Approve a mapping' }))
    const dialog = await screen.findByRole('dialog', { name: 'Approve a mapping' })
    expect(within(dialog).getByLabelText('Test Senior Operator (T_SR_OPR)')).toBeChecked()
    await user.click(within(dialog).getByRole('button', { name: 'Approve mapping' }))
    await waitFor(() =>
      expect(api.requestsTo(`POST /imports/mappings/${PENDING_MAPPING.public_id}/approve`)).toHaveLength(1),
    )
    expect(api.requestsTo(`POST /imports/mappings/${PENDING_MAPPING.public_id}/approve`)[0].body).toEqual({
      version: 1,
      reason: null,
      target_public_id: PENDING_MAPPING.suggestions[0].public_id,
    })
  })

  it('shows the queue without decision buttons to users who cannot manage mappings', async () => {
    mockSignedIn(VIEWER, importRoutes(READY, { 'GET /imports/mappings': reply(page([PENDING_MAPPING])) }))
    renderApp('/imports/mappings')
    const card = (await screen.findByText('“Sr. Test Opr”')).closest('li')!
    expect(within(card).queryByRole('button')).not.toBeInTheDocument()
  })
})

describe('Translations', () => {
  it.each(['bn', 'hi', 'gu'] as const)('renders the job page in %s without missing keys', async (language) => {
    await changeLanguage(language)
    mockSignedIn(HR_ADMIN, importRoutes(READY))
    renderApp(`/imports/${JOB_ID}`)
    await screen.findByRole('heading', { level: 1, name: 'synthetic-people.xlsx' })
    // Both staged rows are listed (each card carries its sheet!row reference).
    await waitFor(() =>
      expect(document.querySelector(`[data-row="${ERROR_ROW.sheet}!${ERROR_ROW.row_number}"]`)).not.toBeNull(),
    )
    expect(document.body.textContent).not.toMatch(/imp\.[a-z]+\.[a-zA-Z_]+/)
    expect(screen.queryByText('Approve and import')).not.toBeInTheDocument()
    expect(NEW_ROW.values.full_name).toBe('Test Person One')
  })
})
