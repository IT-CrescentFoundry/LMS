import {
  Award,
  BookOpen,
  ChartColumn,
  ClipboardCheck,
  FileSpreadsheet,
  GraduationCap,
  IdCard,
  LayoutDashboard,
  Network,
  Route,
  ScrollText,
  Sparkles,
  Users,
  type LucideIcon,
} from 'lucide-react'

import { hasPermission, PERMISSIONS, type PermissionCode } from '../features/auth/permissions'
import type { CurrentUser } from '../types/auth'

export type NavLabelKey =
  | 'nav.dashboard'
  | 'nav.myLearning'
  | 'nav.courses'
  | 'nav.assessments'
  | 'nav.competencies'
  | 'nav.career'
  | 'nav.certifications'
  | 'nav.organisation'
  | 'nav.employees'
  | 'nav.reports'
  | 'nav.users'
  | 'nav.auditLog'
  | 'nav.imports'

export interface NavItem {
  id: string
  labelKey: NavLabelKey
  icon: LucideIcon
  /** Route path. Planned items have no route yet. */
  to?: string
  status: 'available' | 'planned'
  group: 'main' | 'administration'
  /** Also highlight the item on nested routes (e.g. /organisation/locations). */
  matchNested?: boolean
  /**
   * Hide the item from users without this permission. This is a convenience
   * only: the page and its API enforce the permission themselves.
   */
  requiredPermission?: PermissionCode
}

/**
 * Main navigation. Planned entries are placeholders for modules in the
 * implementation roadmap and are rendered as non-interactive "coming soon"
 * items. Administration entries appear only for users holding the permission.
 */
export const NAV_ITEMS: readonly NavItem[] = [
  { id: 'dashboard', labelKey: 'nav.dashboard', icon: LayoutDashboard, to: '/', status: 'available', group: 'main' },
  {
    id: 'organisation',
    labelKey: 'nav.organisation',
    icon: Network,
    to: '/organisation',
    status: 'available',
    group: 'main',
    matchNested: true,
    requiredPermission: PERMISSIONS.ORGANISATION_VIEW,
  },
  {
    id: 'employees',
    labelKey: 'nav.employees',
    icon: IdCard,
    to: '/employees',
    status: 'available',
    group: 'main',
    matchNested: true,
    requiredPermission: PERMISSIONS.EMPLOYEES_VIEW,
  },
  {
    id: 'users',
    labelKey: 'nav.users',
    icon: Users,
    to: '/admin/users',
    status: 'available',
    group: 'administration',
    requiredPermission: PERMISSIONS.USER_ACCOUNTS_VIEW,
  },
  {
    id: 'imports',
    labelKey: 'nav.imports',
    icon: FileSpreadsheet,
    to: '/imports',
    status: 'available',
    group: 'administration',
    matchNested: true,
    requiredPermission: PERMISSIONS.IMPORTS_VIEW,
  },
  {
    id: 'audit-log',
    labelKey: 'nav.auditLog',
    icon: ScrollText,
    to: '/admin/audit-log',
    status: 'available',
    group: 'administration',
    requiredPermission: PERMISSIONS.AUDIT_VIEW,
  },
  { id: 'my-learning', labelKey: 'nav.myLearning', icon: GraduationCap, status: 'planned', group: 'main' },
  { id: 'courses', labelKey: 'nav.courses', icon: BookOpen, status: 'planned', group: 'main' },
  { id: 'assessments', labelKey: 'nav.assessments', icon: ClipboardCheck, status: 'planned', group: 'main' },
  { id: 'competencies', labelKey: 'nav.competencies', icon: Sparkles, status: 'planned', group: 'main' },
  { id: 'career', labelKey: 'nav.career', icon: Route, status: 'planned', group: 'main' },
  { id: 'certifications', labelKey: 'nav.certifications', icon: Award, status: 'planned', group: 'main' },
  { id: 'reports', labelKey: 'nav.reports', icon: ChartColumn, status: 'planned', group: 'main' },
]

/** Items the user may see (UI visibility only; see `requiredPermission`). */
export function visibleNavItems(user: CurrentUser | null): NavItem[] {
  return NAV_ITEMS.filter(
    (item) => item.requiredPermission === undefined || hasPermission(user, item.requiredPermission),
  )
}
