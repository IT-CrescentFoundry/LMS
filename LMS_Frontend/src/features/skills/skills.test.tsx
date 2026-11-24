import { focusManager } from '@tanstack/react-query'
import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { errorBody, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { DESIGNATION, page, ROLE } from '../../test/orgFixtures'
import { competency, GRID, MATRIX, SCALE, TRAINING_ADMIN } from '../../test/trainingFixtures'

afterEach(() => {
  vi.unstubAllGlobals()
  focusManager.setFocused(undefined)
})

const MY_SKILLS = 'GET /competency/my-skills'
const NOT_LINKED_TEXT = 'Your account is not linked to an employee record, so no personal skills can be shown.'

/** Leaves My skills for the dashboard, comes back, and simulates the window regaining focus. */
async function revisitMySkills(router: ReturnType<typeof renderApp>['router']) {
  await act(() => router.navigate('/'))
  await act(() => router.navigate('/skills/me'))
  await screen.findByRole('heading', { name: 'My skills', level: 1 })
  act(() => {
    focusManager.setFocused(false)
    focusManager.setFocused(true)
  })
}

/**
 * My-skills requests that were answered, i.e. not cancelled by the client. In
 * development, StrictMode's mount-unmount-mount cancels the first in-flight
 * request (the browser lists it as "canceled", not as a 404).
 */
function answeredMySkills(api: ReturnType<typeof mockSignedIn>) {
  return api.fetchMock.mock.calls.filter(
    ([input, init]) => String(input).endsWith('/competency/my-skills') && init?.signal?.aborted !== true,
  )
}

describe('My skills (browser issue fix 2026-11-24)', () => {
  it.each([false, true])('shows the unchanged not-linked message and asks the server only once (strict: %s)', async (strict) => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      [MY_SKILLS]: reply(errorBody('employee_not_linked', 'Your account is not linked to an employee.'), 404),
    })
    const { router } = renderApp('/skills/me', { strict })
    expect(await screen.findByText(NOT_LINKED_TEXT)).toBeInTheDocument()
    expect(screen.getByText('The skill matrices that apply to you, with the required level and your latest assessed level.')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByText('Your skills could not be loaded.')).not.toBeInTheDocument()

    await revisitMySkills(router)
    expect(await screen.findByText(NOT_LINKED_TEXT)).toBeInTheDocument()
    // The answer is stable for the session (the cache is purged at sign-out), so
    // remounts (page, dashboard widget, StrictMode) and focus do not repeat it.
    expect(answeredMySkills(api)).toHaveLength(1)
    if (!strict) expect(api.requestsTo(MY_SKILLS)).toHaveLength(1)
  })

  it('still shows a linked employee their matrices and refreshes them normally', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      [MY_SKILLS]: reply({ employee: GRID.rows[0]!.employee, matrices: [GRID] }),
    })
    const { router } = renderApp('/skills/me')
    expect(await screen.findByRole('heading', { name: 'Synthetic moulding matrix', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: /Skill matrix Synthetic moulding matrix/ })).toBeInTheDocument()
    expect(screen.queryByText(NOT_LINKED_TEXT)).not.toBeInTheDocument()

    const before = api.requestsTo(MY_SKILLS).length
    await revisitMySkills(router)
    await waitFor(() => expect(api.requestsTo(MY_SKILLS).length).toBeGreaterThan(before))
  })

  it.each([
    ['another 404', 404, 'employee_not_found'],
    ['a server failure', 500, 'internal_error'],
  ])('reports %s as an error and asks again on the next visit', async (_label, status, code) => {
    const api = mockSignedIn(TRAINING_ADMIN, { [MY_SKILLS]: reply(errorBody(code), status) })
    const { router } = renderApp('/skills/me')
    expect(await screen.findByText('Your skills could not be loaded.')).toBeInTheDocument()
    expect(screen.queryByText(NOT_LINKED_TEXT)).not.toBeInTheDocument()

    const before = api.requestsTo(MY_SKILLS).length
    await revisitMySkills(router)
    await waitFor(() => expect(api.requestsTo(MY_SKILLS).length).toBeGreaterThan(before))
  })
})

describe('Skill matrix', () => {
  it('lists matrices with their size', async () => {
    mockSignedIn(TRAINING_ADMIN, { 'GET /competency/matrices': reply([MATRIX]) })
    renderApp('/skills')
    expect(await screen.findByRole('link', { name: 'Synthetic moulding matrix' })).toHaveAttribute('href', '/skills/matrix-1')
    expect(screen.getByText('Competencies: 2')).toBeInTheDocument()
    expect(screen.getByText('Employees: 2')).toBeInTheDocument()
  })

  it('shows required and assessed levels with text labels, plan flags and staffing risk', async () => {
    mockSignedIn(TRAINING_ADMIN, { 'GET /competency/matrices/matrix-1/grid': reply(GRID) })
    renderApp('/skills/matrix-1')
    const table = await screen.findByRole('table', { name: /Skill matrix Synthetic moulding matrix/ })
    expect(within(table).getByText('Below by 2')).toBeInTheDocument()
    expect(within(table).getByText('Meets')).toBeInTheDocument()
    expect(within(table).getByText('Requirement pending')).toBeInTheDocument()
    expect(within(table).getAllByText('Not assessed').length).toBeGreaterThan(0)
    expect(within(table).getByText('Development plan needed')).toBeInTheDocument()
    expect(within(table).getByText('High risk')).toBeInTheDocument()
    expect(within(table).getByText('Skilled (at or above competent level)')).toBeInTheDocument()
  })

  it('opens the assessment panel with history and records a new assessment', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      'GET /competency/matrices/matrix-1/grid': reply(GRID),
      'GET /competency/employees/emp-a/assessments': reply([]),
      'POST /competency/assessments': reply(
        {
          public_id: 'as-1',
          competency: { public_id: 'comp-1', code: 'SYN-01', name: 'Synthetic core making' },
          level: SCALE.levels[2],
          assessed_on: '2026-11-20',
          method: 'assessor_rating',
          assessor: null,
          assessor_name: null,
          evidence: null,
          recorded_at: '2026-11-20T10:00:00Z',
        },
        201,
      ),
    })
    const user = userEvent.setup()
    renderApp('/skills/matrix-1')
    await user.click(await screen.findByRole('button', { name: 'Synthetic core making for Synthetic Person A' }))
    const dialog = await screen.findByRole('dialog', { name: 'Synthetic core making — Synthetic Person A' })
    expect(await within(dialog).findByText('No assessments recorded.')).toBeInTheDocument()
    await user.selectOptions(within(dialog).getByLabelText('Assessed level'), 'lvl-3')
    await user.click(within(dialog).getByRole('button', { name: 'Record assessment' }))
    await waitFor(() =>
      expect(api.requestsTo('POST /competency/assessments')[0]?.body).toMatchObject({
        employee: 'emp-a',
        competency: 'comp-1',
        level: 'lvl-3',
        matrix: 'matrix-1',
      }),
    )
  })
})

describe('Competency library', () => {
  it('lists competencies and shows details', async () => {
    mockSignedIn(TRAINING_ADMIN, {
      'GET /competency/competencies': reply({ items: [competency()], total: 1, limit: 50, offset: 0 }),
      'GET /competency/categories': reply(['Operation']),
    })
    const user = userEvent.setup()
    renderApp('/competencies')
    const table = await screen.findByRole('table', { name: 'Competency library' })
    expect(within(table).getByText('SYN-01')).toBeInTheDocument()
    await user.click(within(table).getByRole('button', { name: 'Synthetic core making' }))
    const dialog = await screen.findByRole('dialog', { name: 'Synthetic core making (SYN-01)' })
    expect(within(dialog).getByText('Synthetic description')).toBeInTheDocument()
    expect(within(dialog).getByText('No band requirements recorded.')).toBeInTheDocument()
  })

  it('shows proficiency scales with their skilled threshold', async () => {
    mockSignedIn(TRAINING_ADMIN, {
      'GET /competency/competencies': reply({ items: [], total: 0, limit: 50, offset: 0 }),
      'GET /competency/categories': reply([]),
      'GET /competency/scales': reply([SCALE]),
    })
    const user = userEvent.setup()
    renderApp('/competencies')
    await user.click(await screen.findByRole('button', { name: 'Proficiency scales' }))
    expect(await screen.findByRole('table', { name: 'Levels of Synthetic scale (1-5)' })).toBeInTheDocument()
    expect(screen.getByText('(skilled from here)')).toBeInTheDocument()
  })
})

describe('Review fixes (2026-11-23)', () => {
  it('explains each staffing-risk classification with the server figures', async () => {
    mockSignedIn(TRAINING_ADMIN, { 'GET /competency/matrices/matrix-1/grid': reply(GRID) })
    renderApp('/skills/matrix-1')
    const table = await screen.findByRole('table', { name: /Skill matrix Synthetic moulding matrix/ })
    expect(within(table).getByText('1 skilled ≤ 2 required')).toBeInTheDocument()
  })

  it('saves designation and functional-role scope from the matrix form', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      'GET /competency/matrices': reply([]),
      'GET /competency/scales': reply([SCALE]),
      'GET /org/designations': page([DESIGNATION]),
      'GET /org/functional-roles': page([ROLE]),
      'POST /competency/matrices': reply({ ...MATRIX, designation: { public_id: 'des-1', code: 'TEST_OPR', name: 'Test Operator' } }, 201),
    })
    const user = userEvent.setup()
    renderApp('/skills')
    await user.click(await screen.findByRole('button', { name: 'New skill matrix' }))
    const dialog = await screen.findByRole('dialog', { name: 'New skill matrix' })
    await user.type(within(dialog).getByLabelText('Code'), 'MX-NEW')
    await user.type(within(dialog).getByLabelText('Name'), 'Synthetic matrix')
    await user.selectOptions(within(dialog).getByLabelText(/Proficiency scale/), SCALE.public_id)
    await user.selectOptions(await within(dialog).findByLabelText('Designation'), 'des-1')
    await user.selectOptions(await within(dialog).findByLabelText('Functional role'), 'role-1')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(api.requestsTo('POST /competency/matrices')[0]?.body).toMatchObject({
        code: 'MX-NEW',
        designation: 'des-1',
        functional_role: 'role-1',
      }),
    )
  })

  it('shows draft status and approves a competency through the audited status endpoint', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      'GET /competency/competencies': reply({ items: [competency()], total: 1, limit: 50, offset: 0 }),
      'GET /competency/categories': reply([]),
      'POST /competency/competencies/comp-1/status': reply(competency({ status: 'approved', approved_at: '2026-11-23T10:00:00Z', version: 2 })),
    })
    const user = userEvent.setup()
    renderApp('/competencies')
    const table = await screen.findByRole('table', { name: 'Competency library' })
    expect(within(table).getByText('Draft')).toBeInTheDocument()
    await user.click(within(table).getByRole('button', { name: 'Synthetic core making' }))
    const dialog = await screen.findByRole('dialog', { name: 'Synthetic core making (SYN-01)' })
    await user.click(within(dialog).getByRole('button', { name: 'Approve' }))
    const confirm = await screen.findByRole('dialog', { name: 'Approve Synthetic core making' })
    await user.click(within(confirm).getByRole('button', { name: 'Approve' }))
    await waitFor(() =>
      expect(api.requestsTo('POST /competency/competencies/comp-1/status')[0]?.body).toEqual({ version: 1, status: 'approved', reason: null }),
    )
    expect(await screen.findByText('Approved', { selector: 'span' })).toBeInTheDocument()
  })

  it('edits grade-band requirements with levels from the competency scale', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      'GET /competency/competencies': reply({ items: [competency({ scale: { public_id: SCALE.public_id, code: SCALE.code, name: SCALE.name } })], total: 1, limit: 50, offset: 0 }),
      'GET /competency/categories': reply([]),
      'GET /competency/scales': reply([SCALE]),
      'PUT /competency/competencies/comp-1/band-requirements': reply(competency({ version: 2 })),
    })
    const user = userEvent.setup()
    renderApp('/competencies')
    const table = await screen.findByRole('table', { name: 'Competency library' })
    await user.click(within(table).getByRole('button', { name: 'Synthetic core making' }))
    const detail = await screen.findByRole('dialog', { name: 'Synthetic core making (SYN-01)' })
    await user.click(within(detail).getByRole('button', { name: 'Band requirements' }))
    const dialog = await screen.findByRole('dialog', { name: /Required level by grade band/ })
    await user.click(within(dialog).getByRole('button', { name: 'Add band' }))
    await user.type(within(dialog).getByLabelText('Band'), 'L6–L5')
    await user.selectOptions(within(dialog).getByLabelText('Required level'), 'lvl-3')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    await waitFor(() =>
      expect(api.requestsTo('PUT /competency/competencies/comp-1/band-requirements')[0]?.body).toEqual({
        version: 1,
        items: [{ band_code: 'L6–L5', band_label: null, required_level: 'lvl-3' }],
      }),
    )
  })
})
