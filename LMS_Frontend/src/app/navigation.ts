import {
  Award,
  Bell,
  BookOpen,
  CalendarDays,
  ChartColumn,
  ClipboardCheck,
  FileSpreadsheet,
  GraduationCap,
  Grid3x3,
  IdCard,
  LayoutDashboard,
  Library,
  Network,
  Route,
  ScrollText,
  Users,
  type LucideIcon,
} from 'lucide-react'

import {
  COMPETENCY_VIEW_PERMISSIONS,
  hasAnyPermission,
  hasPermission,
  PERMISSIONS,
  TRAINING_VIEW_PERMISSIONS,
  type PermissionCode,
} from '../features/auth/permissions'
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
  | 'nav.trainingRecords'
  | 'nav.trainingCalendar'
  | 'nav.skillMatrix'
  | 'nav.competencyLibrary'
  | 'nav.notifications'

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
  /** Show the item when the user holds at least one of these permissions. */
  requiredAnyPermission?: readonly PermissionCode[]
  /** Nested paths that belong to another item (not highlighted here). */
  excludeNested?: readonly string[]
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
    id: 'training',
    labelKey: 'nav.trainingRecords',
    icon: GraduationCap,
    to: '/training',
    status: 'available',
    group: 'main',
    matchNested: true,
    excludeNested: ['/training/calendar'],
    requiredAnyPermission: TRAINING_VIEW_PERMISSIONS,
  },
  {
    id: 'training-calendar',
    labelKey: 'nav.trainingCalendar',
    icon: CalendarDays,
    to: '/training/calendar',
    status: 'available',
    group: 'main',
    requiredAnyPermission: TRAINING_VIEW_PERMISSIONS,
  },
  {
    id: 'skills',
    labelKey: 'nav.skillMatrix',
    icon: Grid3x3,
    to: '/skills',
    status: 'available',
    group: 'main',
    matchNested: true,
    requiredAnyPermission: COMPETENCY_VIEW_PERMISSIONS,
  },
  {
    id: 'competencies',
    labelKey: 'nav.competencyLibrary',
    icon: Library,
    to: '/competencies',
    status: 'available',
    group: 'main',
    matchNested: true,
    requiredAnyPermission: COMPETENCY_VIEW_PERMISSIONS,
  },
  {
    id: 'notifications',
    labelKey: 'nav.notifications',
    icon: Bell,
    to: '/notifications',
    status: 'available',
    group: 'main',
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
  { id: 'career', labelKey: 'nav.career', icon: Route, status: 'planned', group: 'main' },
  { id: 'certifications', labelKey: 'nav.certifications', icon: Award, status: 'planned', group: 'main' },
  { id: 'reports', labelKey: 'nav.reports', icon: ChartColumn, status: 'planned', group: 'main' },
]

/** Items the user may see (UI visibility only; see `requiredPermission`). */
export function visibleNavItems(user: CurrentUser | null): NavItem[] {
  return NAV_ITEMS.filter(
    (item) =>
      (item.requiredPermission === undefined || hasPermission(user, item.requiredPermission)) &&
      (item.requiredAnyPermission === undefined || hasAnyPermission(user, item.requiredAnyPermission)),
  )
}
