import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { changeLanguage } from '../../i18n'
import { formatDate } from '../../lib/format'
import {
  BASELINE,
  BASELINE_NODES,
  CLOSED_NODE,
  history,
  orgUnit,
  ref,
  structureRoutes,
  SUB_NODE,
  tree,
} from '../../test/orgFixtures'
import {
  EMPLOYEE,
  errorBody,
  HR_ADMIN,
  mockSignedIn,
  renderApp,
  reply,
  SUPERVISOR,
} from '../../test/renderApp'

afterEach(() => {
  vi.unstubAllGlobals()
})

/** Dates as the UI formats them in English (locale data differs between runtimes). */
const d = (iso: string) => formatDate(iso, 'en')

async function findTree() {
  return screen.findByRole('tree', { name: 'Organisation units' })
}

function treeItem(name: string) {
  return screen.getByRole('treeitem', { name: new RegExp(`^${name}`) })
}

describe('Organisation structure page', () => {
  it('shows the five baseline functions with their exact names', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    renderApp('/organisation')

    const tree = await findTree()
    const items = within(tree).getAllByRole('treeitem')
    expect(items.map((item) => item.querySelector('.block')?.textContent)).toEqual(BASELINE.map(([, , name]) => name))
    expect(screen.getByRole('heading', { level: 1, name: 'Organisation structure' })).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent('Organisation')
    expect(screen.getByText(`Structure as of ${d('2026-11-14')}`)).toBeInTheDocument()
  })

  it('expands, collapses and moves focus with the keyboard (ARIA tree pattern)', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()

    const operation = treeItem('Operation')
    expect(operation).toHaveAttribute('aria-expanded', 'false')
    expect(operation).toHaveAttribute('aria-level', '1')
    expect(operation).toHaveAttribute('aria-posinset', '3')
    expect(operation).toHaveAttribute('aria-setsize', '5')

    await user.tab() // skip link etc. are outside the tree; focus the tree directly
    treeItem('Accounts & Commercial').focus()
    await user.keyboard('{ArrowDown}{ArrowDown}')
    expect(treeItem('Operation')).toHaveFocus()
    expect(treeItem('Operation')).toHaveAttribute('tabindex', '0')

    await user.keyboard('{ArrowRight}')
    expect(treeItem('Operation')).toHaveAttribute('aria-expanded', 'true')
    const melting = treeItem('Test Melting')
    expect(melting).toHaveAttribute('aria-level', '2')

    await user.keyboard('{ArrowRight}')
    expect(treeItem('Test Melting')).toHaveFocus()
    await user.keyboard('{ArrowLeft}')
    expect(treeItem('Operation')).toHaveFocus()
    await user.keyboard('{ArrowLeft}')
    expect(treeItem('Operation')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('treeitem', { name: /^Test Melting/ })).not.toBeInTheDocument()

    await user.keyboard('{End}')
    expect(treeItem('Sales & BD')).toHaveFocus()
    await user.keyboard('{Home}')
    expect(treeItem('Accounts & Commercial')).toHaveFocus()
  })

  it('searches and filters by type, showing matches with their ancestors', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()

    await user.type(screen.getByRole('searchbox', { name: 'Search units' }), 'furnace')
    const tree = screen.getByRole('tree')
    expect(within(tree).getAllByRole('treeitem').map((item) => item.getAttribute('aria-level'))).toEqual(['1', '2', '3'])
    expect(treeItem('Test Furnace Upkeep')).toBeInTheDocument()
    expect(screen.getByText(/1 matching unit/)).toBeInTheDocument()

    await user.clear(screen.getByRole('searchbox', { name: 'Search units' }))
    await user.selectOptions(screen.getByRole('combobox', { name: 'Unit type' }), 'Sub-function')
    expect(treeItem('Test Melting')).toBeInTheDocument()
    expect(screen.queryByRole('treeitem', { name: /^Purchase/ })).not.toBeInTheDocument()

    await user.type(screen.getByRole('searchbox', { name: 'Search units' }), 'zzz')
    expect(screen.getByText('No units match these filters.')).toBeInTheDocument()
  })

  it('asks the API for closed units and for another date when requested', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'GET /org/tree': (request) =>
          reply(
            request.query.get('include_closed') === 'true'
              ? tree([...BASELINE_NODES, SUB_NODE, CLOSED_NODE], request.query.get('as_of') ?? '2026-11-14')
              : tree(BASELINE_NODES, request.query.get('as_of') ?? '2026-11-14'),
          ),
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    expect(api.requestsTo('GET /org/tree')[0].query.has('include_closed')).toBe(false)

    await user.selectOptions(screen.getByRole('combobox', { name: 'Show' }), 'Closed units only')
    await waitFor(() => expect(screen.getByRole('treeitem', { name: /^Test Old Section/ })).toBeInTheDocument())
    expect(api.requestsTo('GET /org/tree').at(-1)?.query.get('include_closed')).toBe('true')
    expect(within(treeItem('Test Old Section')).getByText('Closed')).toBeInTheDocument()

    await user.type(screen.getByLabelText('View as of'), '2026-03-31')
    await waitFor(() => expect(api.requestsTo('GET /org/tree').at(-1)?.query.get('as_of')).toBe('2026-03-31'))
    expect(await screen.findByText((text) => text.startsWith(`Structure as of ${d('2026-03-31')}`))).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Today' }))
    await waitFor(() => expect(api.requestsTo('GET /org/tree').at(-1)?.query.has('as_of')).toBe(false))
  })

  it('shows details, children and placement history of the selected unit', async () => {
    mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'GET /org/units/unit-melt/history': reply(
          history(SUB_NODE, [
            {
              parent: ref('unit-pur', 'PURCHASE', 'Purchase'),
              effective_from: '2026-01-01',
              effective_to: '2026-06-01',
              recorded_at: '2026-01-01T09:00:00Z',
              ended_at: '2026-05-20T09:00:00Z',
            },
            {
              parent: ref('unit-ops', 'OPERATION', 'Operation'),
              effective_from: '2026-06-01',
              effective_to: null,
              recorded_at: '2026-05-20T09:00:00Z',
              ended_at: null,
            },
          ]),
        ),
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()

    await user.click(treeItem('Operation'))
    expect(await screen.findByRole('heading', { level: 2, name: 'Operation' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '1 unit below' })).toBeInTheDocument()
    expect(screen.getByText('This unit has always been a top-level unit.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Test Melting/ }))
    expect(await screen.findByRole('heading', { level: 2, name: 'Test Melting' })).toBeInTheDocument()
    const historyTable = await screen.findByRole('table', { name: 'Placement history of Test Melting' })
    const rows = within(historyTable).getAllByRole('row').slice(1)
    expect(rows).toHaveLength(2)
    expect(rows[0]).toHaveTextContent('Purchase')
    expect(rows[0]).toHaveTextContent(d('2026-01-01'))
    expect(rows[1]).toHaveTextContent('Current')
  })

  it('creates a unit below the selected one and shows an advisory warning', async () => {
    const created = orgUnit(
      { ...SUB_NODE, public_id: 'unit-new', code: 'TEST_NEW', name: 'Test New Unit', parent_id: 'unit-ops' },
      { unit_type: ref('type-dept', 'DEPARTMENT', 'Department') },
    )
    const api = mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'POST /org/units': reply(
          {
            unit: created,
            warnings: [{ code: 'type_rule_advisory', message: 'English text never shown' }],
          },
          201,
        ),
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(treeItem('Operation'))
    await user.click(await screen.findByRole('button', { name: 'Add unit below' }))

    const dialog = screen.getByRole('dialog', { name: 'Add a unit below Operation' })
    expect(within(dialog).getByRole('textbox', { name: 'Code' })).toHaveFocus()
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(within(dialog).getAllByText('This field is required.')).toHaveLength(3)
    expect(api.requestsTo('POST /org/units')).toHaveLength(0)

    await user.type(within(dialog).getByRole('textbox', { name: 'Code' }), ' test_new ')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Test New Unit')
    await user.selectOptions(within(dialog).getByRole('combobox', { name: 'Unit type' }), 'Department')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name in हिन्दी (optional)' }), 'नई इकाई')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))

    const status = await screen.findByText('Test New Unit was created.')
    expect(status.closest('[role="status"]')).toHaveTextContent('outside the usual parent rules')
    expect(screen.queryByText('English text never shown')).not.toBeInTheDocument()
    const request = api.requestsTo('POST /org/units')[0]
    expect(request.body).toEqual({
      code: 'test_new',
      name: 'Test New Unit',
      short_name: null,
      unit_type_id: 'type-dept',
      location_id: null,
      parent_id: 'unit-ops',
      effective_from: null,
      external_ref: null,
      translations: { hi: 'नई इकाई' },
    })
    expect(request.headers['x-csrf-token']).toBe('csrf-test-token-1')
  })

  it('corrects only the changed fields, with version and reason', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'PATCH /org/units/unit-melt': reply({ unit: orgUnit(SUB_NODE, { name: 'Test Melting Shop', version: 4 }), warnings: [] }),
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(treeItem('Operation'))
    await user.click(await screen.findByRole('button', { name: /Test Melting/ }))
    await user.click(await screen.findByRole('button', { name: 'Correct details' }))

    const dialog = screen.getByRole('dialog', { name: 'Correct details of Test Melting' })
    await user.click(within(dialog).getByRole('button', { name: 'Save correction' }))
    expect(within(dialog).getByText('Nothing has changed, so there is nothing to save.')).toBeInTheDocument()

    const name = within(dialog).getByRole('textbox', { name: 'Name' })
    await user.clear(name)
    await user.type(name, 'Test Melting Shop')
    await user.clear(within(dialog).getByRole('textbox', { name: 'Name in हिन्दी (optional)' }))
    await user.type(within(dialog).getByRole('textbox', { name: 'Reason (optional)' }), 'Spelling')
    await user.click(within(dialog).getByRole('button', { name: 'Save correction' }))

    expect(await screen.findByText('The details of Test Melting Shop were corrected.')).toBeInTheDocument()
    expect(api.requestsTo('PATCH /org/units/unit-melt')[0].body).toEqual({
      name: 'Test Melting Shop',
      translations: { hi: null },
      version: 3,
      reason: 'Spelling',
    })
  })

  it('moves a unit after confirmation and explains a rejected move', async () => {
    let attempt = 0
    const api = mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'POST /org/units/unit-melt/move': () => {
          attempt += 1
          return attempt === 1
            ? reply(errorBody('hierarchy_cycle'), 422)
            : reply({ unit: orgUnit(SUB_NODE, { version: 4 }), warnings: [] })
        },
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(treeItem('Operation'))
    await user.click(await screen.findByRole('button', { name: /Test Melting/ }))
    await user.click(await screen.findByRole('button', { name: 'Move' }))

    const dialog = screen.getByRole('dialog', { name: 'Move Test Melting' })
    const parents = within(dialog).getByRole('listbox', { name: /^New parent unit/ })
    const options = within(parents).getAllByRole('option').map((option) => option.textContent)
    expect(options).toContain('Top level (no parent unit)')
    expect(options).toContain('Purchase (PURCHASE)')
    expect(options.some((label) => label?.startsWith('Test Melting'))).toBe(false) // never under itself
    expect(options.some((label) => label?.startsWith('Test Furnace'))).toBe(false) // nor under its own child

    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(within(dialog).getByText('Choose a new parent unit or the top level.')).toBeInTheDocument()

    await user.type(within(dialog).getByRole('textbox', { name: 'Filter the list of units (optional)' }), 'purch')
    await user.selectOptions(parents, 'Purchase (PURCHASE)')
    await user.type(within(dialog).getByLabelText(/^Effective date/), '2026-12-01')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(within(dialog).getByText(`Move Test Melting under Purchase (PURCHASE) from ${d('2026-12-01')}?`)).toBeInTheDocument()
    expect(api.requestsTo('POST /org/units/unit-melt/move')).toHaveLength(0)
    // On the confirmation step the secondary button returns to the form.
    await user.click(within(dialog).getByRole('button', { name: 'Back' }))
    expect(within(dialog).getByRole('listbox', { name: /^New parent unit/ })).toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))

    await user.click(within(dialog).getByRole('button', { name: 'Confirm move' }))
    expect(await within(dialog).findByText('This change would place the unit inside its own sub-tree.')).toBeInTheDocument()

    await user.click(within(dialog).getByRole('button', { name: 'Confirm move' }))
    expect(await screen.findByText(`Test Melting was moved, effective ${d('2026-12-01')}.`)).toBeInTheDocument()
    expect(api.requestsTo('POST /org/units/unit-melt/move')[1].body).toEqual({
      version: 3,
      new_parent_id: 'unit-pur',
      effective_date: '2026-12-01',
    })
  })

  it('lists the dependants that block a closure', async () => {
    mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'POST /org/units/unit-ops/close': reply(
          errorBody('unit_has_dependants', 'Blocked', [
            { location: ['children', 'TEST_MELT'], message: 'Active child unit', type: 'active_child' },
            { location: ['functional_roles', 'TEST_ROLE'], message: 'x', type: 'owned_functional_role' },
            { location: ['designation_role_mappings', 'id'], message: 'x', type: 'scoped_mapping' },
          ]),
          409,
        ),
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(treeItem('Operation'))
    await user.click(await screen.findByRole('button', { name: 'Close unit' }))

    const dialog = screen.getByRole('dialog', { name: 'Close Operation' })
    await user.type(within(dialog).getByLabelText(/^Closure date/), '2026-12-31')
    await user.click(within(dialog).getByRole('button', { name: 'Continue' }))
    expect(within(dialog).getByText(`Close Operation from ${d('2026-12-31')}?`)).toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Close unit' }))

    const alert = await within(dialog).findByRole('alert')
    expect(alert).toHaveTextContent('The unit still has active records that depend on it.')
    expect(alert).toHaveTextContent('Unit below it: TEST_MELT')
    expect(alert).toHaveTextContent('Functional role it owns: TEST_ROLE')
    expect(alert).toHaveTextContent('Designation-to-role mapping limited to this unit')
  })

  it('reopens a closed unit', async () => {
    const closed = orgUnit(CLOSED_NODE, { effective_to: '2026-10-01', parent: ref('unit-ops', 'OPERATION', 'Operation') })
    const api = mockSignedIn(
      HR_ADMIN,
      structureRoutes({
        'GET /org/tree': reply(tree([...BASELINE_NODES, CLOSED_NODE])),
        'GET /org/units/unit-old': reply(closed),
        'GET /org/units/unit-old/history': reply(history(CLOSED_NODE)),
        'POST /org/units/unit-old/reopen': reply({ unit: { ...closed, effective_to: null, status: 'active' }, warnings: [] }),
      }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(treeItem('Operation'))
    await user.click(await screen.findByRole('button', { name: /Test Old Section/ }))
    expect(screen.queryByRole('button', { name: 'Move' })).not.toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: 'Reopen' }))

    const dialog = screen.getByRole('dialog', { name: 'Reopen Test Old Section' })
    expect(within(dialog).getByText(`Closed from ${d('2026-10-01')}.`)).toBeInTheDocument()
    await user.click(within(dialog).getByRole('button', { name: 'Reopen unit' }))
    expect(await screen.findByText('Test Old Section was reopened.')).toBeInTheDocument()
    expect(api.requestsTo('POST /org/units/unit-old/reopen')[0].body).toEqual({ version: 3, reason: null })
  })

  it('never overwrites after a version conflict: it offers a reload instead', async () => {
    const api = mockSignedIn(
      HR_ADMIN,
      structureRoutes({ 'PATCH /org/units/unit-ops': reply(errorBody('version_conflict'), 409) }),
    )
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(treeItem('Operation'))
    await user.click(await screen.findByRole('button', { name: 'Correct details' }))
    const dialog = screen.getByRole('dialog')
    await user.type(within(dialog).getByRole('textbox', { name: 'Short name (optional)' }), 'OPS')
    await user.click(within(dialog).getByRole('button', { name: 'Save correction' }))

    expect(await within(dialog).findByText(/Someone else changed this record/)).toBeInTheDocument()
    expect(api.requestsTo('PATCH /org/units/unit-ops')).toHaveLength(1)
    const treeReads = api.requestsTo('GET /org/tree').length
    await user.click(within(dialog).getByRole('button', { name: 'Reload the latest data' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await waitFor(() => expect(api.requestsTo('GET /org/tree').length).toBeGreaterThan(treeReads))
    expect(api.requestsTo('PATCH /org/units/unit-ops')).toHaveLength(1)
  })

  it('translates a strict rule violation', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes({ 'POST /org/units': reply(errorBody('type_rule_violation'), 422) }))
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    await user.click(screen.getByRole('button', { name: 'Add top-level unit' }))
    const dialog = screen.getByRole('dialog', { name: 'Add a top-level unit' })
    await user.type(within(dialog).getByRole('textbox', { name: 'Code' }), 'X1')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Test Root')
    await user.selectOptions(within(dialog).getByRole('combobox', { name: 'Unit type' }), 'Department')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(await within(dialog).findByText('This unit type cannot be placed here: its parent rules are strict.')).toBeInTheDocument()
  })

  it('closes dialogs with Escape and returns focus to the opener', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    const opener = screen.getByRole('button', { name: 'Add top-level unit' })
    await user.click(opener)
    expect(screen.getByRole('dialog')).toHaveAttribute('aria-modal', 'true')
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(opener).toHaveFocus()
  })

  it('is read-only for users with organisation.view only', async () => {
    mockSignedIn(SUPERVISOR, structureRoutes())
    const user = userEvent.setup()
    renderApp('/organisation')
    await findTree()
    expect(screen.getByText('Read only')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add top-level unit' })).not.toBeInTheDocument()
    await user.click(treeItem('Operation'))
    await screen.findByRole('heading', { level: 2, name: 'Operation' })
    for (const name of ['Add unit below', 'Correct details', 'Move', 'Close unit']) {
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
    }
  })

  it('shows the forbidden page without calling the API when organisation.view is missing', async () => {
    const api = mockSignedIn(EMPLOYEE)
    renderApp('/organisation')
    expect(await screen.findByRole('heading', { name: 'You do not have access to this page' })).toBeInTheDocument()
    expect(api.requests.some((request) => request.path.startsWith('/org'))).toBe(false)
  })

  it('uses drill-down navigation on narrow screens', async () => {
    vi.stubGlobal('matchMedia', (query: string) => ({
      matches: false,
      media: query,
      addEventListener: () => undefined,
      removeEventListener: () => undefined,
    }))
    mockSignedIn(HR_ADMIN, structureRoutes())
    const user = userEvent.setup()
    renderApp('/organisation')

    await screen.findByRole('list', { name: 'Organisation units' })
    expect(screen.queryByRole('tree')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Show 1 unit below Operation' }))
    const trail = screen.getByRole('navigation', { name: 'Position in the structure' })
    expect(within(trail).getByRole('button', { name: 'Operation' })).toHaveAttribute('aria-current', 'location')
    await user.click(screen.getByRole('button', { name: /^Test Melting/ }))
    expect(await screen.findByRole('heading', { level: 2, name: 'Test Melting' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Back to the list' }))
    await user.click(within(screen.getByRole('navigation', { name: 'Position in the structure' })).getByRole('button', { name: 'All top-level units' }))
    expect(screen.getByRole('button', { name: /^Purchase/ })).toBeInTheDocument()
  })

  it('shows translated names in the UI language, with the recorded name as fallback', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    await changeLanguage('hi')
    const user = userEvent.setup()
    renderApp('/organisation')
    await screen.findByRole('tree', { name: 'संगठनात्मक इकाइयाँ' })
    expect(screen.getByRole('heading', { level: 1, name: 'संगठन की संरचना' })).toBeInTheDocument()
    await user.click(screen.getByRole('treeitem', { name: /^Operation/ }))
    expect(await screen.findByRole('button', { name: /परीक्षण पिघलन/ })).toBeInTheDocument() // translated child
    expect(screen.getByRole('treeitem', { name: /^Purchase/ })).toBeInTheDocument() // no translation: recorded name
  })
})
