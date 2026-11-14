import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { changeLanguage, resources } from '../../i18n'
import { formatDate } from '../../lib/format'
import {
  BASELINE_NODES,
  DESIGNATION,
  FAMILY_CHILD,
  FAMILY_TOP,
  LOCATION,
  MAPPING,
  page,
  ranked,
  RESPONSIBILITY,
  ROLE,
  tree,
  TYPE_DEPT,
  TYPE_SUB,
  UNIT_TYPES,
} from '../../test/orgFixtures'
import {
  errorBody,
  HR_ADMIN,
  makeUser,
  mockSignedIn,
  renderApp,
  reply,
  SUPERVISOR,
} from '../../test/renderApp'
import { ORG_ERROR_CODES } from './orgErrors'

function table(name: string) {
  return screen.findByRole('table', { name })
}

function rows(element: HTMLElement) {
  return within(element).getAllByRole('row').slice(1)
}

describe('Organisation section navigation', () => {
  it('links every configuration page and marks the current one', async () => {
    mockSignedIn(HR_ADMIN, { 'GET /org/unit-types': reply(UNIT_TYPES) })
    renderApp('/organisation/unit-types')
    const sections = await screen.findByRole('navigation', { name: 'Organisation sections' })
    expect(within(sections).getAllByRole('link').map((link) => link.textContent)).toEqual([
      'Structure',
      'Unit types',
      'Locations',
      'Job families',
      'Designations',
      'Grades',
      'Levels',
      'Functional roles',
      'Responsibilities',
    ])
    expect(within(sections).getByRole('link', { name: 'Unit types' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('navigation', { name: 'Breadcrumb' })).toHaveTextContent('Unit types')
  })
})

describe('Unit types', () => {
  it('explains advisory and strict rules and lists each type with its allowed parents', async () => {
    mockSignedIn(HR_ADMIN, { 'GET /org/unit-types': reply(UNIT_TYPES) })
    renderApp('/organisation/unit-types')
    const list = await table('Organisation unit types')
    expect(screen.getByText('A placement outside the rules is allowed but shows a warning.')).toBeInTheDocument()
    expect(screen.getByText('A placement outside the rules is refused.')).toBeInTheDocument()

    const [fn, sub, dept] = rows(list)
    expect(fn).toHaveTextContent('Top level')
    expect(within(fn).getByText('Advisory')).toBeInTheDocument()
    expect(sub).toHaveTextContent('Function')
    expect(within(dept).getByText('Strict')).toBeInTheDocument()
    expect(dept).toHaveTextContent('Sub-function')
  })

  it('creates a unit type and replaces its allowed parents', async () => {
    const created = { ...TYPE_SUB, public_id: 'type-plant', code: 'TEST_PLANT', name: 'Test Plant', allowed_parent_types: [] }
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/unit-types': reply(UNIT_TYPES),
      'POST /org/unit-types': reply(created, 201),
      'PUT /org/unit-types/type-dept/parent-rules': reply(TYPE_DEPT),
    })
    const user = userEvent.setup()
    renderApp('/organisation/unit-types')
    await table('Organisation unit types')

    await user.click(screen.getByRole('button', { name: 'Add unit type' }))
    const dialog = screen.getByRole('dialog', { name: 'Add a unit type' })
    await user.type(within(dialog).getByRole('textbox', { name: 'Code' }), 'test_plant')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Test Plant')
    await user.click(within(dialog).getByRole('radio', { name: /Strict/ }))
    await user.click(within(dialog).getByRole('checkbox', { name: /Employees can be assigned/ }))
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(await screen.findByText('Test Plant was created.')).toBeInTheDocument()
    expect(api.requestsTo('POST /org/unit-types')[0].body).toEqual({
      code: 'test_plant',
      name: 'Test Plant',
      description: null,
      sort_order: 0,
      allows_employee_assignment: false,
      parent_rule_mode: 'strict',
      translations: {},
    })

    await user.click(screen.getByRole('button', { name: 'Allowed parents of Department' }))
    const rules = screen.getByRole('dialog', { name: 'Allowed parents of Department' })
    await user.click(within(rules).getByRole('checkbox', { name: 'Function (FUNCTION)' }))
    await user.click(within(rules).getByRole('checkbox', { name: 'May be a top-level unit' }))
    await user.click(within(rules).getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.requestsTo('PUT /org/unit-types/type-dept/parent-rules')).toHaveLength(1))
    expect(api.requestsTo('PUT /org/unit-types/type-dept/parent-rules')[0].body).toEqual({
      version: 1,
      allow_root: true,
      parent_type_ids: ['type-sub'],
    })
  })

  it('keeps the code fixed when editing and sends only changes', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/unit-types': reply(UNIT_TYPES),
      'PATCH /org/unit-types/type-sub': reply({ ...TYPE_SUB, is_active: false, version: 2 }),
    })
    const user = userEvent.setup()
    renderApp('/organisation/unit-types')
    await table('Organisation unit types')
    await user.click(screen.getByRole('button', { name: 'Edit Sub-function' }))
    const dialog = screen.getByRole('dialog', { name: 'Edit unit type Sub-function' })
    expect(within(dialog).queryByRole('textbox', { name: 'Code' })).not.toBeInTheDocument()
    expect(within(dialog).getByText('The code of a unit type cannot be changed.')).toBeInTheDocument()
    await user.click(within(dialog).getByRole('checkbox', { name: 'Active' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.requestsTo('PATCH /org/unit-types/type-sub')).toHaveLength(1))
    expect(api.requestsTo('PATCH /org/unit-types/type-sub')[0].body).toEqual({ version: 1, is_active: false })
  })
})

describe('Locations', () => {
  it('lists, filters and creates locations', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/locations': reply([LOCATION, { ...LOCATION, public_id: 'loc-2', code: 'TEST_OFFICE', name: 'Test Office', city: 'Other Town' }]),
      'POST /org/locations': reply({ ...LOCATION, public_id: 'loc-3', code: 'TEST_NEW', name: 'Test New Site' }, 201),
    })
    const user = userEvent.setup()
    renderApp('/organisation/locations')
    const list = await table('Locations')
    expect(rows(list)).toHaveLength(2)
    expect(rows(list)[0]).toHaveTextContent('Test City, Test State, IN')

    await user.type(screen.getByRole('searchbox', { name: 'Search' }), 'other')
    expect(rows(list)).toHaveLength(1)
    expect(rows(list)[0]).toHaveTextContent('Test Office')

    await user.click(screen.getByRole('button', { name: 'Add location' }))
    const dialog = screen.getByRole('dialog', { name: 'Add a location' })
    await user.type(within(dialog).getByRole('textbox', { name: 'Code' }), 'test_new')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Test New Site')
    await user.type(within(dialog).getByRole('textbox', { name: 'Country code (optional)' }), '1N')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(within(dialog).getByText('Enter a two-letter country code.')).toBeInTheDocument()
    await user.clear(within(dialog).getByRole('textbox', { name: 'Country code (optional)' }))
    await user.type(within(dialog).getByRole('textbox', { name: 'Country code (optional)' }), 'in')
    await user.type(within(dialog).getByRole('textbox', { name: 'Time zone (optional)' }), 'Asia/Kolkata')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(await screen.findByText('Test New Site was created.')).toBeInTheDocument()
    expect(api.requestsTo('POST /org/locations')[0].body).toMatchObject({
      code: 'test_new',
      name: 'Test New Site',
      country_code: 'in',
      time_zone: 'Asia/Kolkata',
      city: null,
    })
  })

  it('explains why a location in use cannot be deactivated', async () => {
    mockSignedIn(HR_ADMIN, {
      'GET /org/locations': reply([LOCATION]),
      'PATCH /org/locations/loc-1': reply(errorBody('location_in_use'), 409),
    })
    const user = userEvent.setup()
    renderApp('/organisation/locations')
    await table('Locations')
    await user.click(screen.getByRole('button', { name: 'Edit Test Site One' }))
    const dialog = screen.getByRole('dialog')
    await user.click(within(dialog).getByRole('checkbox', { name: 'Active' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    expect(await within(dialog).findByText('Organisation units that are still open use this location.')).toBeInTheDocument()
  })
})

describe('Job families, grades and levels', () => {
  it('never offers a family or its descendants as its own parent and explains a cycle', async () => {
    mockSignedIn(HR_ADMIN, {
      'GET /org/job-families': reply([FAMILY_TOP, FAMILY_CHILD]),
      'PATCH /org/job-families/fam-top': reply(errorBody('job_family_cycle'), 422),
    })
    const user = userEvent.setup()
    renderApp('/organisation/job-families')
    await table('Job families')
    await user.click(screen.getByRole('button', { name: 'Edit Test Engineering' }))
    const dialog = screen.getByRole('dialog', { name: 'Edit job family Test Engineering' })
    const parent = within(dialog).getByRole('combobox', { name: /Parent family/ })
    expect(within(parent).getAllByRole('option').map((option) => option.textContent)).toEqual(['None'])

    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), ' Group')
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    expect(
      await within(dialog).findByText('A job family cannot sit under itself or one of its own sub-families.'),
    ).toBeInTheDocument()
  })

  it('keeps grades and levels as separate lists with their own endpoints', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/grades': reply([ranked('g1', 'G1', 'Test Grade One', 10), ranked('g0', 'G0', 'Test Unranked', null)]),
      'GET /org/levels': reply([ranked('l1', 'L1', 'Test Level One', 1)]),
      'POST /org/levels': reply(ranked('l2', 'L2', 'Test Level Two', 2), 201),
    })
    const user = userEvent.setup()
    renderApp('/organisation/grades')
    const grades = await table('Grades')
    expect(rows(grades).map((row) => row.textContent)).toEqual([
      expect.stringContaining('Test Grade One'),
      expect.stringContaining('Test Unranked'),
    ])
    expect(screen.getByText('Grades and levels are two separate lists. No relationship between them is assumed.')).toBeInTheDocument()

    await user.click(within(screen.getByRole('navigation', { name: 'Organisation sections' })).getByRole('link', { name: 'Levels' }))
    const levels = await table('Levels')
    expect(rows(levels)).toHaveLength(1)
    await user.click(screen.getByRole('button', { name: 'Add level' }))
    const dialog = screen.getByRole('dialog', { name: 'Add a level' })
    await user.type(within(dialog).getByRole('textbox', { name: 'Code' }), 'L2')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Test Level Two')
    await user.type(within(dialog).getByRole('spinbutton', { name: /Rank/ }), '-1')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    expect(within(dialog).getByText('Enter a whole number of 0 or more.')).toBeInTheDocument()
    await user.clear(within(dialog).getByRole('spinbutton', { name: /Rank/ }))
    await user.type(within(dialog).getByRole('spinbutton', { name: /Rank/ }), '2')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    await screen.findByText('Test Level Two was created.')
    expect(api.requestsTo('POST /org/levels')[0].body).toEqual({ code: 'L2', name: 'Test Level Two', rank: 2 })
    expect(api.requestsTo('POST /org/grades')).toHaveLength(0)
  })
})

describe('Designations and functional-role mappings', () => {
  it('searches on the server and shows translated titles', async () => {
    const api = mockSignedIn(HR_ADMIN, { 'GET /org/designations': page([DESIGNATION]) })
    await changeLanguage('bn')
    const user = userEvent.setup()
    renderApp('/organisation/designations')
    const list = await table(resources.bn.common.org.designations.title)
    expect(rows(list)[0]).toHaveTextContent('পরীক্ষা অপারেটর')

    await user.type(screen.getByRole('searchbox'), ' operator ')
    await user.click(screen.getByRole('button', { name: resources.bn.common.org.common.searchButton }))
    await waitFor(() => expect(api.requestsTo('GET /org/designations')).toHaveLength(2))
    expect(Object.fromEntries(api.requestsTo('GET /org/designations')[1].query)).toEqual({ q: 'operator', limit: '50' })
  })

  it('lists, adds and ends functional-role mappings', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/designations': page([DESIGNATION]),
      'GET /org/designations/des-1/functional-roles': reply([MAPPING]),
      'GET /org/functional-roles': page([ROLE]),
      'GET /org/tree': reply(tree(BASELINE_NODES)),
      'POST /org/designations/des-1/functional-roles': reply(MAPPING, 201),
      'POST /org/designations/des-1/functional-roles/map-1/end': reply({ ...MAPPING, effective_to: '2026-12-31' }),
    })
    const user = userEvent.setup()
    renderApp('/organisation/designations')
    await table('Designations')
    await user.click(screen.getByRole('button', { name: 'Functional roles of Test Operator' }))

    const dialog = await screen.findByRole('dialog', { name: 'Functional roles of Test Operator' })
    expect(within(dialog).getByText('Functional roles are not LMS access roles: they grant no permissions.')).toBeInTheDocument()
    expect(await within(dialog).findByText('In Operation and the units below it')).toBeInTheDocument()

    await user.click(within(dialog).getByRole('button', { name: 'Add functional role' }))
    expect(within(dialog).getByText('This field is required.')).toBeInTheDocument()
    await user.selectOptions(within(dialog).getByRole('combobox', { name: 'Functional role' }), 'Test Melting Work (TEST_MELT_ROLE)')
    await user.selectOptions(within(dialog).getByRole('combobox', { name: /Applies in/ }), 'Purchase (PURCHASE)')
    await user.click(within(dialog).getByRole('checkbox', { name: 'Also apply in the units below it' }))
    await user.click(within(dialog).getByRole('button', { name: 'Add functional role' }))
    expect(await within(dialog).findByText('Test Melting Work was mapped to this designation.')).toBeInTheDocument()
    expect(api.requestsTo('POST /org/designations/des-1/functional-roles')[0].body).toEqual({
      functional_role_id: 'role-1',
      scope_unit_id: 'unit-pur',
      include_descendants: false,
      effective_from: null,
    })

    await user.click(within(dialog).getByRole('button', { name: 'End mapping to Test Melting Work' }))
    await user.click(within(dialog).getByRole('button', { name: 'End mapping' }))
    expect(within(dialog).getByText('This field is required.')).toBeInTheDocument()
    await user.type(within(dialog).getByLabelText(/^End date/), '2026-12-31')
    await user.click(within(dialog).getByRole('button', { name: 'End mapping' }))
    expect(
      await within(dialog).findByText(`The mapping to Test Melting Work ends on ${formatDate('2026-12-31', 'en')}.`),
    ).toBeInTheDocument()
    expect(api.requestsTo('POST /org/designations/des-1/functional-roles/map-1/end')[0].body).toEqual({
      effective_to: '2026-12-31',
      reason: null,
    })
  })

  it('explains an overlapping mapping', async () => {
    mockSignedIn(HR_ADMIN, {
      'GET /org/designations': page([DESIGNATION]),
      'GET /org/designations/des-1/functional-roles': reply([]),
      'GET /org/functional-roles': page([ROLE]),
      'GET /org/tree': reply(tree(BASELINE_NODES)),
      'POST /org/designations/des-1/functional-roles': reply(errorBody('mapping_overlap'), 409),
    })
    const user = userEvent.setup()
    renderApp('/organisation/designations')
    await table('Designations')
    await user.click(screen.getByRole('button', { name: 'Functional roles of Test Operator' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText('No functional roles are mapped to this designation.')).toBeInTheDocument()
    await user.selectOptions(within(dialog).getByRole('combobox', { name: 'Functional role' }), 'Test Melting Work (TEST_MELT_ROLE)')
    await user.click(within(dialog).getByRole('button', { name: 'Add functional role' }))
    expect(await within(dialog).findByText(/already mapped to this role, in the same scope/)).toBeInTheDocument()
  })

  it('lets a user with designations.manage but not functional_roles.manage only view mappings', async () => {
    mockSignedIn(makeUser({ permissions: ['organisation.view', 'designations.manage'] }), {
      'GET /org/designations': page([DESIGNATION]),
      'GET /org/designations/des-1/functional-roles': reply([MAPPING]),
    })
    const user = userEvent.setup()
    renderApp('/organisation/designations')
    await table('Designations')
    expect(screen.getByRole('button', { name: 'Add designation' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Functional roles of Test Operator' }))
    const dialog = await screen.findByRole('dialog')
    expect(await within(dialog).findByText(/Changing them needs the permission to manage functional roles/)).toBeInTheDocument()
    expect(within(dialog).queryByRole('button', { name: /^End mapping/ })).not.toBeInTheDocument()
  })
})

describe('Functional roles and responsibilities', () => {
  it('creates a functional role with an owner unit and states that it grants no access', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/functional-roles': page([ROLE]),
      'GET /org/job-families': reply([FAMILY_TOP]),
      'GET /org/tree': reply(tree(BASELINE_NODES)),
      'POST /org/functional-roles': reply({ ...ROLE, public_id: 'role-2', name: 'Test Pouring Work' }, 201),
    })
    const user = userEvent.setup()
    renderApp('/organisation/functional-roles')
    const list = await table('Functional roles')
    expect(rows(list)[0]).toHaveTextContent('Operation')
    expect(screen.getByText(/they grant no permissions/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Add functional role' }))
    const dialog = screen.getByRole('dialog', { name: 'Add a functional role' })
    await user.type(within(dialog).getByRole('textbox', { name: 'Code' }), 'TEST_POUR')
    await user.type(within(dialog).getByRole('textbox', { name: 'Name' }), 'Test Pouring Work')
    await user.selectOptions(within(dialog).getByRole('combobox', { name: /Owner unit/ }), 'Operation (OPERATION)')
    await user.click(within(dialog).getByRole('button', { name: 'Create' }))
    await screen.findByText('Test Pouring Work was created.')
    expect(api.requestsTo('POST /org/functional-roles')[0].body).toEqual({
      code: 'TEST_POUR',
      name: 'Test Pouring Work',
      description: null,
      job_family_id: null,
      owner_unit_id: 'unit-ops',
      translations: {},
    })
  })

  it('manages responsibilities and never presents them as permissions', async () => {
    const api = mockSignedIn(HR_ADMIN, {
      'GET /org/responsibilities': page([RESPONSIBILITY]),
      'PATCH /org/responsibilities/resp-1': reply({ ...RESPONSIBILITY, category: null, version: 2 }),
    })
    const user = userEvent.setup()
    renderApp('/organisation/responsibilities')
    const list = await table('Responsibilities')
    expect(rows(list)[0]).toHaveTextContent('Safety')
    expect(screen.getByText(/never grants LMS permissions or practical authorisation/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Edit Test Fire Warden' }))
    const dialog = screen.getByRole('dialog')
    await user.clear(within(dialog).getByRole('textbox', { name: 'Category (optional)' }))
    await user.click(within(dialog).getByRole('button', { name: 'Save changes' }))
    await waitFor(() => expect(api.requestsTo('PATCH /org/responsibilities/resp-1')).toHaveLength(1))
    expect(api.requestsTo('PATCH /org/responsibilities/resp-1')[0].body).toEqual({ category: null, version: 1 })
  })

  it.each([
    ['/organisation/unit-types', 'Add unit type', { 'GET /org/unit-types': reply(UNIT_TYPES) }],
    ['/organisation/locations', 'Add location', { 'GET /org/locations': reply([LOCATION]) }],
    ['/organisation/job-families', 'Add job family', { 'GET /org/job-families': reply([FAMILY_TOP]) }],
    ['/organisation/grades', 'Add grade', { 'GET /org/grades': reply([]) }],
    ['/organisation/designations', 'Add designation', { 'GET /org/designations': page([DESIGNATION]) }],
    ['/organisation/functional-roles', 'Add functional role', { 'GET /org/functional-roles': page([ROLE]) }],
    ['/organisation/responsibilities', 'Add responsibility', { 'GET /org/responsibilities': page([RESPONSIBILITY]) }],
  ])('%s is read-only without its manage permission', async (path, addLabel, routes) => {
    mockSignedIn(SUPERVISOR, routes)
    renderApp(path)
    expect(await screen.findByText('Read only')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: addLabel })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Edit / })).not.toBeInTheDocument()
  })
})

describe('Organisation translations', () => {
  it.each(['bn', 'hi', 'gu'] as const)('%s translates the organisation pages and every API error code', (code) => {
    const strings = resources[code].common.org
    const english = resources.en.common.org
    expect(strings.structure.title).not.toBe(english.structure.title)
    expect(strings.unitTypes.strictHelp).not.toBe(english.unitTypes.strictHelp)
    expect(strings.functionalRoles.notAccessRoles).not.toBe(english.functionalRoles.notAccessRoles)
    expect(strings.responsibilities.notAuthorisation).not.toBe(english.responsibilities.notAuthorisation)
    for (const errorCode of ORG_ERROR_CODES) {
      expect(strings.errors.codes[errorCode], errorCode).toBeTruthy()
      expect(strings.errors.codes[errorCode], errorCode).not.toBe(english.errors.codes[errorCode])
    }
  })
})
