/**
 * Organisation structure and occupational reference API (Stage C1 endpoints under
 * `/org`). Reads need `organisation.view`; writes need the matching `*.manage`
 * permission, the session cookie and the CSRF token (added by `apiRequest`).
 * Every write is audited by the backend.
 */

import { apiRequest, buildQuery, isRecord } from '../lib/apiClient'
import {
  expectBoolean,
  expectDateString,
  expectInteger,
  expectIsoDate,
  expectNullableDateString,
  expectNullableInteger,
  expectNullableIsoDate,
  expectNullableString,
  expectOneOf,
  expectRecord,
  expectString,
} from '../lib/parse'
import type { Page } from '../types/admin'
import {
  PARENT_RULE_MODES,
  TRANSLATION_LOCALES,
  UNIT_STATUSES,
  type Designation,
  type DesignationRoleMapping,
  type FunctionalRole,
  type JobFamily,
  type ListFilters,
  type Location,
  type LocationFields,
  type OrgTree,
  type OrgUnit,
  type OrgUnitWrite,
  type OrgWarning,
  type RankedItem,
  type RankedKind,
  type Ref,
  type Responsibility,
  type TranslationChanges,
  type Translations,
  type TreeFilters,
  type TreeNode,
  type UnitCorrection,
  type UnitCreate,
  type UnitHistory,
  type UnitType,
  type UnitTypeCreate,
  type UnitTypeUpdate,
} from '../types/organisation'
import { parsePage } from './adminService'

// ------------------------------------------------------------------- parsers

function parseList<T>(parseItem: (data: unknown) => T): (data: unknown) => T[] {
  return (data) => {
    if (!Array.isArray(data)) throw new TypeError('expected a list')
    return data.map(parseItem)
  }
}

export function parseRef(data: unknown): Ref {
  const record = expectRecord(data, 'reference')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
  }
}

function parseNullableRef(data: unknown): Ref | null {
  return data === null || data === undefined ? null : parseRef(data)
}

/** Only the supported locales are kept; anything else in the payload is dropped. */
function parseTranslations(data: unknown): Translations {
  if (data === undefined || data === null) return {}
  if (!isRecord(data)) throw new TypeError('translations: expected an object')
  const result: Translations = {}
  for (const locale of TRANSLATION_LOCALES) {
    const value = data[locale]
    if (typeof value === 'string' && value.trim() !== '') result[locale] = value
  }
  return result
}

function parseTracked(record: Record<string, unknown>) {
  return {
    version: expectInteger(record, 'version'),
    created_at: expectDateString(record, 'created_at'),
    updated_at: expectDateString(record, 'updated_at'),
  }
}

function parseWarnings(data: unknown): OrgWarning[] {
  if (data === undefined || data === null) return []
  if (!Array.isArray(data)) throw new TypeError('warnings: expected a list')
  return data.map((item) => {
    const record = expectRecord(item, 'warning')
    return { code: expectString(record, 'code'), message: expectString(record, 'message') }
  })
}

export function parseUnitType(data: unknown): UnitType {
  const record = expectRecord(data, 'unit type')
  if (!Array.isArray(record.allowed_parent_types)) {
    throw new TypeError('allowed_parent_types: expected a list')
  }
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    description: expectNullableString(record, 'description'),
    sort_order: expectInteger(record, 'sort_order'),
    allows_employee_assignment: expectBoolean(record, 'allows_employee_assignment'),
    is_active: expectBoolean(record, 'is_active'),
    parent_rule_mode: expectOneOf(record, 'parent_rule_mode', PARENT_RULE_MODES),
    allow_root: expectBoolean(record, 'allow_root'),
    allowed_parent_types: record.allowed_parent_types.map(parseRef),
    translations: parseTranslations(record.translations),
    ...parseTracked(record),
  }
}

export function parseOrgUnit(data: unknown): OrgUnit {
  const record = expectRecord(data, 'organisation unit')
  if (!Array.isArray(record.path)) throw new TypeError('path: expected a list')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    short_name: expectNullableString(record, 'short_name'),
    unit_type: parseRef(record.unit_type),
    location: parseNullableRef(record.location),
    as_of: expectIsoDate(record, 'as_of'),
    parent: parseNullableRef(record.parent),
    path: record.path.map(parseRef),
    status: expectOneOf(record, 'status', UNIT_STATUSES),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    external_ref: expectNullableString(record, 'external_ref'),
    translations: parseTranslations(record.translations),
    ...parseTracked(record),
  }
}

export function parseUnitWrite(data: unknown): OrgUnitWrite {
  const record = expectRecord(data, 'unit write result')
  return { unit: parseOrgUnit(record.unit), warnings: parseWarnings(record.warnings) }
}

function parseTreeNode(data: unknown): TreeNode {
  const record = expectRecord(data, 'tree node')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    short_name: expectNullableString(record, 'short_name'),
    unit_type: parseRef(record.unit_type),
    location: parseNullableRef(record.location),
    parent_id: expectNullableString(record, 'parent_id'),
    status: expectOneOf(record, 'status', UNIT_STATUSES),
    translations: parseTranslations(record.translations),
  }
}

export function parseTree(data: unknown): OrgTree {
  const record = expectRecord(data, 'organisation tree')
  if (!Array.isArray(record.nodes)) throw new TypeError('nodes: expected a list')
  return { as_of: expectIsoDate(record, 'as_of'), nodes: record.nodes.map(parseTreeNode) }
}

function parseHistory(data: unknown): UnitHistory {
  const record = expectRecord(data, 'unit history')
  if (!Array.isArray(record.placements)) throw new TypeError('placements: expected a list')
  return {
    unit: parseRef(record.unit),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    placements: record.placements.map((item) => {
      const placement = expectRecord(item, 'placement')
      return {
        parent: parseRef(placement.parent),
        effective_from: expectNullableIsoDate(placement, 'effective_from'),
        effective_to: expectNullableIsoDate(placement, 'effective_to'),
        recorded_at: expectDateString(placement, 'recorded_at'),
        ended_at: expectNullableDateString(placement, 'ended_at'),
      }
    }),
  }
}

export function parseLocation(data: unknown): Location {
  const record = expectRecord(data, 'location')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    address_line1: expectNullableString(record, 'address_line1'),
    address_line2: expectNullableString(record, 'address_line2'),
    city: expectNullableString(record, 'city'),
    state: expectNullableString(record, 'state'),
    postal_code: expectNullableString(record, 'postal_code'),
    country_code: expectNullableString(record, 'country_code'),
    time_zone: expectNullableString(record, 'time_zone'),
    is_active: expectBoolean(record, 'is_active'),
    ...parseTracked(record),
  }
}

export function parseJobFamily(data: unknown): JobFamily {
  const record = expectRecord(data, 'job family')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    description: expectNullableString(record, 'description'),
    parent: parseNullableRef(record.parent),
    is_active: expectBoolean(record, 'is_active'),
    ...parseTracked(record),
  }
}

export function parseRanked(data: unknown): RankedItem {
  const record = expectRecord(data, 'grade or level')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    rank: expectNullableInteger(record, 'rank'),
    is_active: expectBoolean(record, 'is_active'),
    ...parseTracked(record),
  }
}

export function parseDesignation(data: unknown): Designation {
  const record = expectRecord(data, 'designation')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    title: expectString(record, 'title'),
    job_family: parseNullableRef(record.job_family),
    is_active: expectBoolean(record, 'is_active'),
    translations: parseTranslations(record.translations),
    ...parseTracked(record),
  }
}

export function parseFunctionalRole(data: unknown): FunctionalRole {
  const record = expectRecord(data, 'functional role')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    description: expectNullableString(record, 'description'),
    job_family: parseNullableRef(record.job_family),
    owner_unit: parseNullableRef(record.owner_unit),
    is_active: expectBoolean(record, 'is_active'),
    translations: parseTranslations(record.translations),
    ...parseTracked(record),
  }
}

export function parseMapping(data: unknown): DesignationRoleMapping {
  const record = expectRecord(data, 'designation mapping')
  return {
    public_id: expectString(record, 'public_id'),
    designation: parseRef(record.designation),
    functional_role: parseRef(record.functional_role),
    scope_unit: parseNullableRef(record.scope_unit),
    include_descendants: expectBoolean(record, 'include_descendants'),
    effective_from: expectNullableIsoDate(record, 'effective_from'),
    effective_to: expectNullableIsoDate(record, 'effective_to'),
    created_at: expectDateString(record, 'created_at'),
    ended_at: expectNullableDateString(record, 'ended_at'),
  }
}

export function parseResponsibility(data: unknown): Responsibility {
  const record = expectRecord(data, 'responsibility')
  return {
    public_id: expectString(record, 'public_id'),
    code: expectString(record, 'code'),
    name: expectString(record, 'name'),
    description: expectNullableString(record, 'description'),
    category: expectNullableString(record, 'category'),
    is_active: expectBoolean(record, 'is_active'),
    translations: parseTranslations(record.translations),
    ...parseTracked(record),
  }
}

// ---------------------------------------------------------------------- API

const ORG = '/org'
export const PICKER_PAGE_SIZE = 200
export const LIST_PAGE_SIZE = 50

type Body = Record<string, unknown>

function send<T>(
  path: string,
  method: 'POST' | 'PUT' | 'PATCH',
  body: Body,
  parse: (data: unknown) => T,
): Promise<T> {
  return apiRequest(`${ORG}${path}`, { method, body, parse })
}

function listQuery(filters: ListFilters, limit: number, cursor: string | null): string {
  return buildQuery({
    q: filters.q,
    include_inactive: filters.include_inactive ? true : undefined,
    limit,
    cursor,
  })
}

export const organisationService = {
  // --- unit types ---------------------------------------------------------
  listUnitTypes(signal?: AbortSignal): Promise<UnitType[]> {
    return apiRequest(`${ORG}/unit-types`, { parse: parseList(parseUnitType), signal })
  },
  createUnitType(body: UnitTypeCreate | Body): Promise<UnitType> {
    return send('/unit-types', 'POST', { ...body }, parseUnitType)
  },
  updateUnitType(id: string, body: UnitTypeUpdate | (Body & { version: number })): Promise<UnitType> {
    return send(`/unit-types/${id}`, 'PATCH', { ...body }, parseUnitType)
  },
  setParentRules(
    id: string,
    body: { version: number; allow_root: boolean; parent_type_ids: string[] },
  ): Promise<UnitType> {
    return send(`/unit-types/${id}/parent-rules`, 'PUT', body, parseUnitType)
  },

  // --- units and hierarchy -------------------------------------------------
  getTree(filters: TreeFilters, signal?: AbortSignal): Promise<OrgTree> {
    const query = buildQuery({
      as_of: filters.as_of,
      include_closed: filters.include_closed ? true : undefined,
    })
    return apiRequest(`${ORG}/tree${query}`, { parse: parseTree, signal })
  },
  getUnit(id: string, asOf: string | undefined, signal?: AbortSignal): Promise<OrgUnit> {
    return apiRequest(`${ORG}/units/${id}${buildQuery({ as_of: asOf })}`, {
      parse: parseOrgUnit,
      signal,
    })
  },
  getUnitHistory(id: string, signal?: AbortSignal): Promise<UnitHistory> {
    return apiRequest(`${ORG}/units/${id}/history`, { parse: parseHistory, signal })
  },
  createUnit(body: UnitCreate): Promise<OrgUnitWrite> {
    return send('/units', 'POST', { ...body }, parseUnitWrite)
  },
  correctUnit(id: string, body: UnitCorrection): Promise<OrgUnitWrite> {
    return send(`/units/${id}`, 'PATCH', { ...body }, parseUnitWrite)
  },
  moveUnit(
    id: string,
    body: { version: number; new_parent_id: string | null; effective_date: string },
  ): Promise<OrgUnitWrite> {
    return send(`/units/${id}/move`, 'POST', body, parseUnitWrite)
  },
  closeUnit(
    id: string,
    body: { version: number; effective_date: string; reason?: string | null },
  ): Promise<OrgUnitWrite> {
    return send(`/units/${id}/close`, 'POST', body, parseUnitWrite)
  },
  reopenUnit(id: string, body: { version: number; reason?: string | null }): Promise<OrgUnitWrite> {
    return send(`/units/${id}/reopen`, 'POST', body, parseUnitWrite)
  },

  // --- locations ------------------------------------------------------------
  listLocations(includeInactive: boolean, signal?: AbortSignal): Promise<Location[]> {
    const query = buildQuery({ include_inactive: includeInactive ? true : undefined })
    return apiRequest(`${ORG}/locations${query}`, { parse: parseList(parseLocation), signal })
  },
  createLocation(body: { code: string; name: string } & LocationFields): Promise<Location> {
    return send('/locations', 'POST', { ...body }, parseLocation)
  },
  updateLocation(id: string, body: Body & { version: number }): Promise<Location> {
    return send(`/locations/${id}`, 'PATCH', body, parseLocation)
  },

  // --- job families, grades, levels -----------------------------------------
  listJobFamilies(includeInactive: boolean, signal?: AbortSignal): Promise<JobFamily[]> {
    const query = buildQuery({ include_inactive: includeInactive ? true : undefined })
    return apiRequest(`${ORG}/job-families${query}`, { parse: parseList(parseJobFamily), signal })
  },
  createJobFamily(body: Body): Promise<JobFamily> {
    return send('/job-families', 'POST', body, parseJobFamily)
  },
  updateJobFamily(id: string, body: Body & { version: number }): Promise<JobFamily> {
    return send(`/job-families/${id}`, 'PATCH', body, parseJobFamily)
  },
  listRanked(kind: RankedKind, includeInactive: boolean, signal?: AbortSignal): Promise<RankedItem[]> {
    const query = buildQuery({ include_inactive: includeInactive ? true : undefined })
    return apiRequest(`${ORG}/${kind}${query}`, { parse: parseList(parseRanked), signal })
  },
  createRanked(kind: RankedKind, body: Body): Promise<RankedItem> {
    return send(`/${kind}`, 'POST', body, parseRanked)
  },
  updateRanked(kind: RankedKind, id: string, body: Body & { version: number }): Promise<RankedItem> {
    return send(`/${kind}/${id}`, 'PATCH', body, parseRanked)
  },

  // --- designations and mappings --------------------------------------------
  listDesignations(
    filters: ListFilters,
    cursor: string | null,
    signal?: AbortSignal,
    limit: number = LIST_PAGE_SIZE,
  ): Promise<Page<Designation>> {
    return apiRequest(`${ORG}/designations${listQuery(filters, limit, cursor)}`, {
      parse: parsePage(parseDesignation),
      signal,
    })
  },
  createDesignation(body: Body): Promise<Designation> {
    return send('/designations', 'POST', body, parseDesignation)
  },
  updateDesignation(id: string, body: Body & { version: number }): Promise<Designation> {
    return send(`/designations/${id}`, 'PATCH', body, parseDesignation)
  },
  listMappings(
    designationId: string,
    includeEnded: boolean,
    signal?: AbortSignal,
  ): Promise<DesignationRoleMapping[]> {
    const query = buildQuery({ include_ended: includeEnded ? true : undefined })
    return apiRequest(`${ORG}/designations/${designationId}/functional-roles${query}`, {
      parse: parseList(parseMapping),
      signal,
    })
  },
  createMapping(
    designationId: string,
    body: {
      functional_role_id: string
      scope_unit_id: string | null
      include_descendants: boolean
      effective_from?: string | null
    },
  ): Promise<DesignationRoleMapping> {
    return send(`/designations/${designationId}/functional-roles`, 'POST', body, parseMapping)
  },
  endMapping(
    designationId: string,
    mappingId: string,
    body: { effective_to: string; reason?: string | null },
  ): Promise<DesignationRoleMapping> {
    return send(
      `/designations/${designationId}/functional-roles/${mappingId}/end`,
      'POST',
      body,
      parseMapping,
    )
  },

  // --- functional roles -----------------------------------------------------
  listFunctionalRoles(
    filters: ListFilters,
    cursor: string | null,
    signal?: AbortSignal,
    limit: number = LIST_PAGE_SIZE,
  ): Promise<Page<FunctionalRole>> {
    return apiRequest(`${ORG}/functional-roles${listQuery(filters, limit, cursor)}`, {
      parse: parsePage(parseFunctionalRole),
      signal,
    })
  },
  createFunctionalRole(body: Body): Promise<FunctionalRole> {
    return send('/functional-roles', 'POST', body, parseFunctionalRole)
  },
  updateFunctionalRole(id: string, body: Body & { version: number }): Promise<FunctionalRole> {
    return send(`/functional-roles/${id}`, 'PATCH', body, parseFunctionalRole)
  },

  // --- responsibilities -----------------------------------------------------
  listResponsibilities(
    filters: ListFilters,
    cursor: string | null,
    signal?: AbortSignal,
  ): Promise<Page<Responsibility>> {
    return apiRequest(`${ORG}/responsibilities${listQuery(filters, LIST_PAGE_SIZE, cursor)}`, {
      parse: parsePage(parseResponsibility),
      signal,
    })
  },
  createResponsibility(body: Body): Promise<Responsibility> {
    return send('/responsibilities', 'POST', body, parseResponsibility)
  },
  updateResponsibility(id: string, body: Body & { version: number }): Promise<Responsibility> {
    return send(`/responsibilities/${id}`, 'PATCH', body, parseResponsibility)
  },
}

/** Request helper: only locales whose value changed (blank/null removes a locale). */
export function translationChanges(
  before: Translations,
  after: Record<string, string>,
): TranslationChanges | undefined {
  const changes: TranslationChanges = {}
  for (const locale of TRANSLATION_LOCALES) {
    const next = (after[locale] ?? '').trim()
    const previous = before[locale] ?? ''
    if (next !== previous) changes[locale] = next === '' ? null : next
  }
  return Object.keys(changes).length > 0 ? changes : undefined
}
