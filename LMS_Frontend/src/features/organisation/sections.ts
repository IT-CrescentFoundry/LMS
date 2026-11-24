/** Sections of the organisation area (routes below /organisation). */

export type OrgSectionLabelKey =
  | 'org.nav.structure'
  | 'org.nav.chart'
  | 'org.nav.unitTypes'
  | 'org.nav.locations'
  | 'org.nav.jobFamilies'
  | 'org.nav.designations'
  | 'org.nav.grades'
  | 'org.nav.levels'
  | 'org.nav.functionalRoles'
  | 'org.nav.responsibilities'

export interface OrgSection {
  path: string
  labelKey: OrgSectionLabelKey
}

export const ORG_SECTIONS: readonly OrgSection[] = [
  { path: '/organisation', labelKey: 'org.nav.structure' },
  { path: '/organisation/chart', labelKey: 'org.nav.chart' },
  { path: '/organisation/unit-types', labelKey: 'org.nav.unitTypes' },
  { path: '/organisation/locations', labelKey: 'org.nav.locations' },
  { path: '/organisation/job-families', labelKey: 'org.nav.jobFamilies' },
  { path: '/organisation/designations', labelKey: 'org.nav.designations' },
  { path: '/organisation/grades', labelKey: 'org.nav.grades' },
  { path: '/organisation/levels', labelKey: 'org.nav.levels' },
  { path: '/organisation/functional-roles', labelKey: 'org.nav.functionalRoles' },
  { path: '/organisation/responsibilities', labelKey: 'org.nav.responsibilities' },
]

export function sectionForPath(pathname: string): OrgSection {
  const normalised = pathname.replace(/\/+$/, '') || '/'
  return ORG_SECTIONS.find((section) => section.path === normalised) ?? ORG_SECTIONS[0]
}
