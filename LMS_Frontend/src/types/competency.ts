/**
 * Competency library, proficiency scale and skill matrix types (migration 0011).
 * Mirrors LMS_Backend/app/schemas/competency.py.
 */

import type { Ref } from './organisation'
import type { EmployeeRef, OffsetPage } from './training'

export const GAP_STATUSES = [
  'requirement_pending',
  'not_assessed',
  'scale_mismatch',
  'below',
  'met',
  'exceeds',
] as const
export type GapStatus = (typeof GAP_STATUSES)[number]

export const ASSESSMENT_METHODS = [
  'assessor_rating',
  'manager_rating',
  'practical_evaluation',
  'imported_matrix',
] as const
export type AssessmentMethod = (typeof ASSESSMENT_METHODS)[number]

export const RISKS = ['high', 'medium', 'low'] as const
export type Risk = (typeof RISKS)[number]

export interface Level {
  public_id: string
  rank: number
  code: string
  label: string
  numeric_value: number | null
  description: string | null
}

export interface Scale {
  public_id: string
  code: string
  name: string
  description: string | null
  gap_method: string
  source_note: string | null
  competent_rank: number | null
  plan_gap_steps: number | null
  is_active: boolean
  levels: Level[]
  version: number
}

export interface BandRequirement {
  band_code: string
  band_label: string | null
  required_level: Level | null
}

export interface Competency {
  public_id: string
  code: string
  name: string
  category: string | null
  sub_category: string | null
  description: string | null
  assessment_criteria: string | null
  applicability: string | null
  scale: Ref | null
  owner_org_unit: Ref | null
  source_ref: string | null
  is_active: boolean
  /** Governance state: new entries are drafts until an authorised, audited approval. */
  status: CompetencyStatus
  approved_at: string | null
  band_requirements: BandRequirement[]
  version: number
}

export const COMPETENCY_STATUSES = ['draft', 'approved'] as const
export type CompetencyStatus = (typeof COMPETENCY_STATUSES)[number]

export interface MatrixItem {
  competency: Ref
  category: string | null
  group_label: string | null
  display_order: number
  required_level: Level | null
  required_headcount: number | null
}

export interface Matrix {
  public_id: string
  code: string
  name: string
  description: string | null
  org_unit: Ref | null
  location: Ref | null
  designation: Ref | null
  functional_role: Ref | null
  scale: Scale
  risk_medium_margin: number
  is_active: boolean
  member_count: number
  items: MatrixItem[]
  version: number
}

export interface Gap {
  status: GapStatus
  gap_steps: number | null
  gap_value: number | null
}

export interface MatrixCell {
  competency_id: string
  required_level: Level | null
  assessed_level: Level | null
  assessed_on: string | null
  gap: Gap
  needs_plan: boolean
}

export interface MatrixRow {
  employee: EmployeeRef
  cells: MatrixCell[]
  gaps: number
}

export interface ItemStats {
  competency_id: string
  counts_by_rank: Record<string, number>
  not_assessed: number
  skilled: number | null
  required_headcount: number | null
  risk: Risk | null
}

export interface MatrixGrid {
  matrix: Matrix
  scope: 'global' | 'team' | 'own' | 'none'
  rows: MatrixRow[]
  summary: Record<string, number>
  item_stats: ItemStats[] | null
}

export interface Assessment {
  public_id: string
  competency: Ref
  level: Level
  assessed_on: string
  method: string
  assessor: EmployeeRef | null
  assessor_name: string | null
  evidence: string | null
  recorded_at: string
}

export interface EmployeeSkills {
  employee: EmployeeRef
  matrices: MatrixGrid[]
}

export type CompetencyPage = OffsetPage<Competency>

export interface LevelInput {
  public_id?: string
  rank: number
  code: string
  label: string
  numeric_value?: number | null
  description?: string | null
}

export interface MatrixItemInput {
  competency: string
  required_level?: string | null
  required_headcount?: number | null
  group_label?: string | null
  display_order?: number
}

export type Body = Record<string, unknown>
