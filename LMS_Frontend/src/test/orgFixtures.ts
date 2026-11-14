/**
 * Synthetic organisation data for frontend tests. The five functions are the
 * business-confirmed baseline (names exactly as approved); every other unit,
 * location and reference record here is invented test data.
 */

import { reply, type MockRoute } from './renderApp'

const STAMP = { created_at: '2026-11-01T10:00:00Z', updated_at: '2026-11-01T10:00:00Z' }

export function ref(public_id: string, code: string, name: string) {
  return { public_id, code, name }
}

export const TYPE_FUNCTION = {
  public_id: 'type-function',
  code: 'FUNCTION',
  name: 'Function',
  description: 'Top-level company function',
  sort_order: 10,
  allows_employee_assignment: true,
  is_active: true,
  parent_rule_mode: 'advisory',
  allow_root: true,
  allowed_parent_types: [],
  translations: { hi: 'कार्य' },
  version: 1,
  ...STAMP,
}
export const TYPE_SUB = {
  ...TYPE_FUNCTION,
  public_id: 'type-sub',
  code: 'SUB_FUNCTION',
  name: 'Sub-function',
  description: 'Sub-function within a function',
  sort_order: 20,
  allow_root: false,
  allowed_parent_types: [ref('type-function', 'FUNCTION', 'Function')],
  translations: {},
}
export const TYPE_DEPT = {
  ...TYPE_FUNCTION,
  public_id: 'type-dept',
  code: 'DEPARTMENT',
  name: 'Department',
  description: 'Department',
  sort_order: 30,
  parent_rule_mode: 'strict',
  allow_root: false,
  allowed_parent_types: [ref('type-sub', 'SUB_FUNCTION', 'Sub-function'), ref('type-function', 'FUNCTION', 'Function')],
  translations: {},
}
export const UNIT_TYPES = [TYPE_FUNCTION, TYPE_SUB, TYPE_DEPT]

const FUNCTION_REF = ref('type-function', 'FUNCTION', 'Function')

/** The five approved functions, exactly as seeded by migration 0005. */
export const BASELINE = [
  ['unit-acc', 'ACC_COM', 'Accounts & Commercial'],
  ['unit-hr', 'HR_ADMIN_IT', 'HR, Admin & IT'],
  ['unit-ops', 'OPERATION', 'Operation'],
  ['unit-pur', 'PURCHASE', 'Purchase'],
  ['unit-sal', 'SALES_BD', 'Sales & BD'],
] as const

export function treeNode(
  public_id: string,
  code: string,
  name: string,
  overrides: Record<string, unknown> = {},
) {
  return {
    public_id,
    code,
    name,
    short_name: null,
    unit_type: FUNCTION_REF,
    location: null,
    parent_id: null as string | null,
    status: 'active',
    translations: {},
    ...overrides,
  }
}

export const BASELINE_NODES = BASELINE.map(([id, code, name]) => treeNode(id, code, name))
/** Synthetic sub-structure under Operation. */
export const SUB_NODE = treeNode('unit-melt', 'TEST_MELT', 'Test Melting', {
  unit_type: ref('type-sub', 'SUB_FUNCTION', 'Sub-function'),
  parent_id: 'unit-ops',
  translations: { hi: 'परीक्षण पिघलन' },
})
export const DEPT_NODE = treeNode('unit-furnace', 'TEST_FURNACE', 'Test Furnace Upkeep', {
  unit_type: ref('type-dept', 'DEPARTMENT', 'Department'),
  parent_id: 'unit-melt',
})
export const CLOSED_NODE = treeNode('unit-old', 'TEST_OLD', 'Test Old Section', {
  unit_type: ref('type-dept', 'DEPARTMENT', 'Department'),
  parent_id: 'unit-ops',
  status: 'closed',
})

export function tree(nodes: unknown[], as_of = '2026-11-14') {
  return { as_of, nodes }
}

export function orgUnit(node: ReturnType<typeof treeNode>, overrides: Record<string, unknown> = {}) {
  const parents: Record<string, unknown> = {
    'unit-melt': ref('unit-ops', 'OPERATION', 'Operation'),
    'unit-furnace': ref('unit-melt', 'TEST_MELT', 'Test Melting'),
  }
  const paths: Record<string, unknown[]> = {
    'unit-melt': [ref('unit-ops', 'OPERATION', 'Operation')],
    'unit-furnace': [ref('unit-ops', 'OPERATION', 'Operation'), ref('unit-melt', 'TEST_MELT', 'Test Melting')],
  }
  return {
    public_id: node.public_id,
    code: node.code,
    name: node.name,
    short_name: null,
    unit_type: node.unit_type,
    location: null,
    as_of: '2026-11-14',
    parent: parents[node.public_id] ?? null,
    path: paths[node.public_id] ?? [],
    status: node.status,
    effective_from: null,
    effective_to: null,
    external_ref: null,
    translations: node.translations,
    version: 3,
    ...STAMP,
    ...overrides,
  }
}

export function history(node: ReturnType<typeof treeNode>, placements: unknown[] = []) {
  return {
    unit: ref(node.public_id, node.code, node.name),
    effective_from: null,
    effective_to: null,
    placements,
  }
}

export const LOCATION = {
  public_id: 'loc-1',
  code: 'TEST_SITE',
  name: 'Test Site One',
  address_line1: null,
  address_line2: null,
  city: 'Test City',
  state: 'Test State',
  postal_code: null,
  country_code: 'IN',
  time_zone: 'Asia/Kolkata',
  is_active: true,
  version: 1,
  ...STAMP,
}

export function ranked(public_id: string, code: string, name: string, rank: number | null, is_active = true) {
  return { public_id, code, name, rank, is_active, version: 1, ...STAMP }
}

export const FAMILY_TOP = {
  public_id: 'fam-top',
  code: 'TEST_ENG',
  name: 'Test Engineering',
  description: null,
  parent: null,
  is_active: true,
  version: 1,
  ...STAMP,
}
export const FAMILY_CHILD = {
  ...FAMILY_TOP,
  public_id: 'fam-child',
  code: 'TEST_MECH',
  name: 'Test Mechanical',
  parent: ref('fam-top', 'TEST_ENG', 'Test Engineering'),
}

export const DESIGNATION = {
  public_id: 'des-1',
  code: 'TEST_OPR',
  title: 'Test Operator',
  job_family: ref('fam-top', 'TEST_ENG', 'Test Engineering'),
  is_active: true,
  translations: { bn: 'পরীক্ষা অপারেটর' },
  version: 2,
  ...STAMP,
}

export const ROLE = {
  public_id: 'role-1',
  code: 'TEST_MELT_ROLE',
  name: 'Test Melting Work',
  description: null,
  job_family: null,
  owner_unit: ref('unit-ops', 'OPERATION', 'Operation'),
  is_active: true,
  translations: {},
  version: 1,
  ...STAMP,
}

export const MAPPING = {
  public_id: 'map-1',
  designation: ref('des-1', 'TEST_OPR', 'Test Operator'),
  functional_role: ref('role-1', 'TEST_MELT_ROLE', 'Test Melting Work'),
  scope_unit: ref('unit-ops', 'OPERATION', 'Operation'),
  include_descendants: true,
  effective_from: '2026-01-01',
  effective_to: null,
  created_at: '2026-01-01T09:00:00Z',
  ended_at: null,
}

export const RESPONSIBILITY = {
  public_id: 'resp-1',
  code: 'TEST_WARDEN',
  name: 'Test Fire Warden',
  description: null,
  category: 'Safety',
  is_active: true,
  translations: { gu: 'પરીક્ષણ ફાયર વૉર્ડન' },
  version: 1,
  ...STAMP,
}

export function page(items: unknown[], next_cursor: string | null = null) {
  return reply({ items, next_cursor })
}

/** Routes for the structure page with the baseline plus the synthetic sub-structure. */
export function structureRoutes(extra: Record<string, MockRoute> = {}): Record<string, MockRoute> {
  const nodes = [...BASELINE_NODES, SUB_NODE, DEPT_NODE]
  return {
    'GET /org/unit-types': reply(UNIT_TYPES),
    'GET /org/tree': reply(tree(nodes)),
    'GET /org/locations': reply([LOCATION]),
    ...Object.fromEntries(
      nodes.map((node) => [`GET /org/units/${node.public_id}`, reply(orgUnit(node))]),
    ),
    ...Object.fromEntries(nodes.map((node) => [`GET /org/units/${node.public_id}/history`, reply(history(node))])),
    ...extra,
  }
}
