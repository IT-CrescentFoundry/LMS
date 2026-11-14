/**
 * Mirrors the Stage C1 schemas in LMS_Backend/app/schemas/organisation.py and
 * occupation.py (see docs/architecture/API_REFERENCE.md sections 7 and 8).
 *
 * Organisation units, designations, functional roles and responsibilities are
 * business reference data. None of them grant LMS permissions; functional roles
 * are not access roles.
 */

/** Languages that may carry a translated display name (the stored name is canonical). */
export const TRANSLATION_LOCALES = ['bn', 'hi', 'gu'] as const
export type TranslationLocale = (typeof TRANSLATION_LOCALES)[number]
export type Translations = Partial<Record<TranslationLocale, string>>
/** In requests: a blank value or null removes the locale. */
export type TranslationChanges = Partial<Record<TranslationLocale, string | null>>

export function isTranslationLocale(value: string | undefined): value is TranslationLocale {
  return (TRANSLATION_LOCALES as readonly (string | undefined)[]).includes(value)
}

/** Compact reference to another record. */
export interface Ref {
  public_id: string
  code: string
  name: string
}

export interface OrgWarning {
  code: string
  message: string
}

export interface Tracked {
  version: number
  created_at: string
  updated_at: string
}

// ----------------------------------------------------------------- structure

export const PARENT_RULE_MODES = ['advisory', 'strict'] as const
export type ParentRuleMode = (typeof PARENT_RULE_MODES)[number]

export interface UnitType extends Tracked {
  public_id: string
  code: string
  name: string
  description: string | null
  sort_order: number
  allows_employee_assignment: boolean
  is_active: boolean
  parent_rule_mode: ParentRuleMode
  /** True when a rule allows this type as a top-level unit. */
  allow_root: boolean
  /** Empty together with allow_root=false means no rules: anything is allowed. */
  allowed_parent_types: Ref[]
  translations: Translations
}

export const UNIT_STATUSES = ['active', 'closed', 'not_started'] as const
export type UnitStatus = (typeof UNIT_STATUSES)[number]

export interface OrgUnit extends Tracked {
  public_id: string
  code: string
  name: string
  short_name: string | null
  unit_type: Ref
  location: Ref | null
  /** Business date for which parent, path and status are shown. */
  as_of: string
  parent: Ref | null
  /** Ancestors from the root down to the parent. */
  path: Ref[]
  status: UnitStatus
  /** Null means the start date was not recorded. */
  effective_from: string | null
  /** Closure date (exclusive); null while open. */
  effective_to: string | null
  external_ref: string | null
  translations: Translations
}

export interface OrgUnitWrite {
  unit: OrgUnit
  warnings: OrgWarning[]
}

export interface TreeNode {
  public_id: string
  code: string
  name: string
  short_name: string | null
  unit_type: Ref
  location: Ref | null
  parent_id: string | null
  status: UnitStatus
  translations: Translations
}

export interface OrgTree {
  as_of: string
  nodes: TreeNode[]
}

export interface Placement {
  parent: Ref
  effective_from: string | null
  effective_to: string | null
  recorded_at: string
  ended_at: string | null
}

export interface UnitHistory {
  unit: Ref
  effective_from: string | null
  effective_to: string | null
  placements: Placement[]
}

export interface Location extends Tracked {
  public_id: string
  code: string
  name: string
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  country_code: string | null
  time_zone: string | null
  is_active: boolean
}

// ------------------------------------------------------------ reference data

export interface JobFamily extends Tracked {
  public_id: string
  code: string
  name: string
  description: string | null
  parent: Ref | null
  is_active: boolean
}

/** A grade or a level. The two lists are independent (Q-45). */
export interface RankedItem extends Tracked {
  public_id: string
  code: string
  name: string
  rank: number | null
  is_active: boolean
}

export type RankedKind = 'grades' | 'levels'

export interface Designation extends Tracked {
  public_id: string
  code: string
  title: string
  job_family: Ref | null
  is_active: boolean
  translations: Translations
}

export interface FunctionalRole extends Tracked {
  public_id: string
  code: string
  name: string
  description: string | null
  job_family: Ref | null
  owner_unit: Ref | null
  is_active: boolean
  translations: Translations
}

export interface DesignationRoleMapping {
  public_id: string
  designation: Ref
  functional_role: Ref
  /** Null: the mapping applies everywhere. */
  scope_unit: Ref | null
  include_descendants: boolean
  effective_from: string | null
  effective_to: string | null
  created_at: string
  ended_at: string | null
}

export interface Responsibility extends Tracked {
  public_id: string
  code: string
  name: string
  description: string | null
  category: string | null
  is_active: boolean
  translations: Translations
}

// ------------------------------------------------------------------ requests

export interface TreeFilters {
  as_of?: string
  include_closed?: boolean
}

export interface UnitCreate {
  code: string
  name: string
  short_name?: string | null
  unit_type_id: string
  location_id?: string | null
  parent_id: string | null
  effective_from?: string | null
  external_ref?: string | null
  translations?: TranslationChanges
}

export interface UnitCorrection {
  version: number
  reason?: string | null
  code?: string
  name?: string
  short_name?: string | null
  unit_type_id?: string
  location_id?: string | null
  effective_from?: string | null
  external_ref?: string | null
  translations?: TranslationChanges
}

export interface UnitTypeCreate {
  code: string
  name: string
  description?: string | null
  sort_order?: number
  allows_employee_assignment?: boolean
  parent_rule_mode?: ParentRuleMode
  translations?: TranslationChanges
}

export interface UnitTypeUpdate {
  version: number
  name?: string
  description?: string | null
  sort_order?: number
  allows_employee_assignment?: boolean
  is_active?: boolean
  parent_rule_mode?: ParentRuleMode
  translations?: TranslationChanges
}

export interface LocationFields {
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  postal_code?: string | null
  country_code?: string | null
  time_zone?: string | null
}

export interface ListFilters {
  q?: string
  include_inactive?: boolean
}
