import {
  Award,
  BookOpen,
  ChartColumn,
  ClipboardCheck,
  GraduationCap,
  LayoutDashboard,
  Network,
  Route,
  Settings,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'

export type NavLabelKey =
  | 'nav.dashboard'
  | 'nav.myLearning'
  | 'nav.courses'
  | 'nav.assessments'
  | 'nav.competencies'
  | 'nav.career'
  | 'nav.certifications'
  | 'nav.organisation'
  | 'nav.reports'
  | 'nav.administration'

export interface NavItem {
  id: string
  labelKey: NavLabelKey
  icon: LucideIcon
  /** Route path. Planned items have no route yet. */
  to?: string
  status: 'available' | 'planned'
}

/**
 * Main navigation. Only the dashboard exists in Stage A; the remaining entries
 * are placeholders for modules in the implementation roadmap and are rendered
 * as non-interactive "coming soon" items. Role-based visibility arrives with
 * authentication (Stage B).
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { id: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, to: '/', status: 'available' },
  { id: 'my-learning', labelKey: 'nav.myLearning', icon: GraduationCap, status: 'planned' },
  { id: 'courses', labelKey: 'nav.courses', icon: BookOpen, status: 'planned' },
  { id: 'assessments', labelKey: 'nav.assessments', icon: ClipboardCheck, status: 'planned' },
  { id: 'competencies', labelKey: 'nav.competencies', icon: Sparkles, status: 'planned' },
  { id: 'career', labelKey: 'nav.career', icon: Route, status: 'planned' },
  { id: 'certifications', labelKey: 'nav.certifications', icon: Award, status: 'planned' },
  { id: 'organisation', labelKey: 'nav.organisation', icon: Network, status: 'planned' },
  { id: 'reports', labelKey: 'nav.reports', icon: ChartColumn, status: 'planned' },
  { id: 'administration', labelKey: 'nav.administration', icon: Settings, status: 'planned' },
]
