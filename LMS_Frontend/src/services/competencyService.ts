/**
 * Competency library, proficiency scales, skill matrices and assessments
 * (`/competency`, migration 0011). Grids and assessment histories are narrowed to the
 * caller's scope by the server; changes need competency.manage / competency.assess.
 */

import { apiRequest, buildQuery, type HttpMethod } from '../lib/apiClient'
import {
  expectArray,
  expectBoolean,
  expectDateString,
  expectInteger,
  expectIsoDate,
  expectNullableInteger,
  expectNullableIsoDate,
  expectNullableNumber,
  expectNullableString,
  expectOneOf,
  expectRecord,
  expectString,
} from '../lib/parse'
import {
  COMPETENCY_STATUSES,
  GAP_STATUSES,
  RISKS,
  type Assessment,
  type Body,
  type Competency,
  type CompetencyPage,
  type CompetencyStatus,
  type EmployeeSkills,
  type ItemStats,
  type Level,
  type Matrix,
  type MatrixGrid,
  type Scale,
} from '../types/competency'
import { parseEmployeeRef, parseOffsetPage, parseRef } from './trainingService'

const CP = '/competency'
export const COMPETENCY_PAGE_SIZE = 50

export function parseLevel(data: unknown): Level {
  const r = expectRecord(data, 'level')
  return {
    public_id: expectString(r, 'public_id'),
    rank: expectInteger(r, 'rank'),
    code: expectString(r, 'code'),
    label: expectString(r, 'label'),
    numeric_value: expectNullableNumber(r, 'numeric_value'),
    description: expectNullableString(r, 'description'),
  }
}

function nullableLevel(data: unknown): Level | null {
  return data === null || data === undefined ? null : parseLevel(data)
}

function requiredRef(data: unknown) {
  const value = parseRef(data)
  if (value === null) throw new TypeError('ref: expected an object')
  return value
}

export function parseScale(data: unknown): Scale {
  const r = expectRecord(data, 'scale')
  return {
    public_id: expectString(r, 'public_id'),
    code: expectString(r, 'code'),
    name: expectString(r, 'name'),
    description: expectNullableString(r, 'description'),
    gap_method: expectString(r, 'gap_method'),
    source_note: expectNullableString(r, 'source_note'),
    competent_rank: expectNullableInteger(r, 'competent_rank'),
    plan_gap_steps: expectNullableInteger(r, 'plan_gap_steps'),
    is_active: expectBoolean(r, 'is_active'),
    levels: expectArray(r, 'levels').map(parseLevel),
    version: expectInteger(r, 'version'),
  }
}

export function parseCompetency(data: unknown): Competency {
  const r = expectRecord(data, 'competency')
  return {
    public_id: expectString(r, 'public_id'),
    code: expectString(r, 'code'),
    name: expectString(r, 'name'),
    category: expectNullableString(r, 'category'),
    sub_category: expectNullableString(r, 'sub_category'),
    description: expectNullableString(r, 'description'),
    assessment_criteria: expectNullableString(r, 'assessment_criteria'),
    applicability: expectNullableString(r, 'applicability'),
    scale: parseRef(r.scale),
    owner_org_unit: parseRef(r.owner_org_unit),
    source_ref: expectNullableString(r, 'source_ref'),
    is_active: expectBoolean(r, 'is_active'),
    status: expectOneOf(r, 'status', COMPETENCY_STATUSES),
    approved_at: expectNullableString(r, 'approved_at'),
    band_requirements: (Array.isArray(r.band_requirements) ? r.band_requirements : []).map((item) => {
      const b = expectRecord(item, 'band')
      return {
        band_code: expectString(b, 'band_code'),
        band_label: expectNullableString(b, 'band_label'),
        required_level: nullableLevel(b.required_level),
      }
    }),
    version: expectInteger(r, 'version'),
  }
}

export function parseMatrix(data: unknown): Matrix {
  const r = expectRecord(data, 'matrix')
  return {
    public_id: expectString(r, 'public_id'),
    code: expectString(r, 'code'),
    name: expectString(r, 'name'),
    description: expectNullableString(r, 'description'),
    org_unit: parseRef(r.org_unit),
    location: parseRef(r.location),
    designation: parseRef(r.designation),
    functional_role: parseRef(r.functional_role),
    scale: parseScale(r.scale),
    risk_medium_margin: expectInteger(r, 'risk_medium_margin'),
    is_active: expectBoolean(r, 'is_active'),
    member_count: expectInteger(r, 'member_count'),
    items: expectArray(r, 'items').map((item) => {
      const i = expectRecord(item, 'item')
      return {
        competency: requiredRef(i.competency),
        category: expectNullableString(i, 'category'),
        group_label: expectNullableString(i, 'group_label'),
        display_order: expectInteger(i, 'display_order'),
        required_level: nullableLevel(i.required_level),
        required_headcount: expectNullableInteger(i, 'required_headcount'),
      }
    }),
    version: expectInteger(r, 'version'),
  }
}

function parseItemStats(data: unknown): ItemStats {
  const r = expectRecord(data, 'stats')
  const counts = expectRecord(r.counts_by_rank, 'counts_by_rank')
  const parsed: Record<string, number> = {}
  for (const [key, value] of Object.entries(counts)) {
    if (typeof value !== 'number') throw new TypeError('counts_by_rank: expected numbers')
    parsed[key] = value
  }
  return {
    competency_id: expectString(r, 'competency_id'),
    counts_by_rank: parsed,
    not_assessed: expectInteger(r, 'not_assessed'),
    skilled: expectNullableInteger(r, 'skilled'),
    required_headcount: expectNullableInteger(r, 'required_headcount'),
    risk: r.risk === null || r.risk === undefined ? null : expectOneOf(r, 'risk', RISKS),
  }
}

export function parseGrid(data: unknown): MatrixGrid {
  const r = expectRecord(data, 'grid')
  const summary = expectRecord(r.summary, 'summary')
  const parsedSummary: Record<string, number> = {}
  for (const [key, value] of Object.entries(summary)) {
    if (typeof value === 'number') parsedSummary[key] = value
  }
  return {
    matrix: parseMatrix(r.matrix),
    scope: expectOneOf(r, 'scope', ['global', 'team', 'own', 'none'] as const),
    rows: expectArray(r, 'rows').map((row) => {
      const w = expectRecord(row, 'row')
      const employee = parseEmployeeRef(w.employee)
      if (employee === null) throw new TypeError('employee: expected an object')
      return {
        employee,
        gaps: expectInteger(w, 'gaps'),
        cells: expectArray(w, 'cells').map((cell) => {
          const c = expectRecord(cell, 'cell')
          const gap = expectRecord(c.gap, 'gap')
          return {
            competency_id: expectString(c, 'competency_id'),
            required_level: nullableLevel(c.required_level),
            assessed_level: nullableLevel(c.assessed_level),
            assessed_on: expectNullableIsoDate(c, 'assessed_on'),
            gap: {
              status: expectOneOf(gap, 'status', GAP_STATUSES),
              gap_steps: expectNullableInteger(gap, 'gap_steps'),
              gap_value: expectNullableNumber(gap, 'gap_value'),
            },
            needs_plan: expectBoolean(c, 'needs_plan'),
          }
        }),
      }
    }),
    summary: parsedSummary,
    item_stats: r.item_stats === null || r.item_stats === undefined ? null : expectArray(r, 'item_stats').map(parseItemStats),
  }
}

export function parseAssessment(data: unknown): Assessment {
  const r = expectRecord(data, 'assessment')
  return {
    public_id: expectString(r, 'public_id'),
    competency: requiredRef(r.competency),
    level: parseLevel(r.level),
    assessed_on: expectIsoDate(r, 'assessed_on'),
    method: expectString(r, 'method'),
    assessor: parseEmployeeRef(r.assessor),
    assessor_name: expectNullableString(r, 'assessor_name'),
    evidence: expectNullableString(r, 'evidence'),
    recorded_at: expectDateString(r, 'recorded_at'),
  }
}

function parseSkills(data: unknown): EmployeeSkills {
  const r = expectRecord(data, 'skills')
  const employee = parseEmployeeRef(r.employee)
  if (employee === null) throw new TypeError('employee: expected an object')
  return { employee, matrices: expectArray(r, 'matrices').map(parseGrid) }
}

function list<T>(parseItem: (data: unknown) => T) {
  return (data: unknown): T[] => {
    if (!Array.isArray(data)) throw new TypeError('expected a list')
    return data.map(parseItem)
  }
}

function send<T>(path: string, method: HttpMethod, body: unknown, parse: (data: unknown) => T): Promise<T> {
  return apiRequest(`${CP}${path}`, { method, body, parse })
}

const id = encodeURIComponent

export const competencyService = {
  listScales(signal?: AbortSignal): Promise<Scale[]> {
    return apiRequest(`${CP}/scales`, { parse: list(parseScale), signal })
  },
  createScale(body: Body): Promise<Scale> {
    return send('/scales', 'POST', body, parseScale)
  },
  updateScale(scaleId: string, body: Body): Promise<Scale> {
    return send(`/scales/${id(scaleId)}`, 'PATCH', body, parseScale)
  },

  listCompetencies(
    filters: { q?: string; category?: string; include_inactive?: boolean; status?: CompetencyStatus },
    offset: number,
    signal?: AbortSignal,
    limit = COMPETENCY_PAGE_SIZE,
  ): Promise<CompetencyPage> {
    const query = buildQuery({
      q: filters.q,
      category: filters.category,
      status: filters.status,
      include_inactive: filters.include_inactive ? true : undefined,
      limit,
      offset,
    })
    return apiRequest(`${CP}/competencies${query}`, { parse: parseOffsetPage(parseCompetency), signal })
  },
  categories(signal?: AbortSignal): Promise<string[]> {
    return apiRequest(`${CP}/categories`, {
      parse: (data) => {
        if (!Array.isArray(data) || !data.every((v) => typeof v === 'string')) {
          throw new TypeError('expected a list of strings')
        }
        return [...data]
      },
      signal,
    })
  },
  createCompetency(body: Body): Promise<Competency> {
    return send('/competencies', 'POST', body, parseCompetency)
  },
  updateCompetency(competencyId: string, body: Body): Promise<Competency> {
    return send(`/competencies/${id(competencyId)}`, 'PATCH', body, parseCompetency)
  },
  /** Approve a draft, or return it to draft (reason required). Audited server-side. */
  changeCompetencyStatus(
    competencyId: string,
    body: { version: number; status: CompetencyStatus; reason: string | null },
  ): Promise<Competency> {
    return send(`/competencies/${id(competencyId)}/status`, 'POST', body, parseCompetency)
  },
  /** Replace the grade-band required levels (bands stored verbatim). */
  setBandRequirements(
    competencyId: string,
    body: { version: number; items: { band_code: string; band_label: string | null; required_level: string | null }[] },
  ): Promise<Competency> {
    return send(`/competencies/${id(competencyId)}/band-requirements`, 'PUT', body, parseCompetency)
  },

  listMatrices(
    filters: { q?: string; unit?: string; location?: string; include_inactive?: boolean },
    signal?: AbortSignal,
  ): Promise<Matrix[]> {
    const query = buildQuery({
      q: filters.q,
      unit: filters.unit,
      location: filters.location,
      include_inactive: filters.include_inactive ? true : undefined,
    })
    return apiRequest(`${CP}/matrices${query}`, { parse: list(parseMatrix), signal })
  },
  createMatrix(body: Body): Promise<Matrix> {
    return send('/matrices', 'POST', body, parseMatrix)
  },
  updateMatrix(matrixId: string, body: Body): Promise<Matrix> {
    return send(`/matrices/${id(matrixId)}`, 'PATCH', body, parseMatrix)
  },
  setItems(matrixId: string, body: Body): Promise<Matrix> {
    return send(`/matrices/${id(matrixId)}/items`, 'PUT', body, parseMatrix)
  },
  setMembers(matrixId: string, body: { add: string[]; remove: string[] }): Promise<Matrix> {
    return send(`/matrices/${id(matrixId)}/members`, 'POST', body, parseMatrix)
  },
  grid(matrixId: string, signal?: AbortSignal): Promise<MatrixGrid> {
    return apiRequest(`${CP}/matrices/${id(matrixId)}/grid`, { parse: parseGrid, signal })
  },

  recordAssessment(body: Body): Promise<Assessment> {
    return send('/assessments', 'POST', body, parseAssessment)
  },
  assessments(employeeId: string, competencyId: string | undefined, signal?: AbortSignal): Promise<Assessment[]> {
    return apiRequest(
      `${CP}/employees/${id(employeeId)}/assessments${buildQuery({ competency: competencyId })}`,
      { parse: list(parseAssessment), signal },
    )
  },
  mySkills(signal?: AbortSignal): Promise<EmployeeSkills> {
    return apiRequest(`${CP}/my-skills`, { parse: parseSkills, signal })
  },
}
