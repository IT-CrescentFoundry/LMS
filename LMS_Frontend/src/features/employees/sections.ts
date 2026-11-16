import type { DataQualityCheck } from '../../types/employee'
import { PERMISSIONS, type PermissionCode } from '../auth/permissions'

/** Sections of the employee area (pill navigation above the directory pages). */
export interface EmployeeSection {
  path: string
  labelKey: 'emp.nav.directory' | 'emp.nav.dataQuality'
  permission: PermissionCode
}

export const EMPLOYEE_SECTIONS: readonly EmployeeSection[] = [
  { path: '/employees', labelKey: 'emp.nav.directory', permission: PERMISSIONS.EMPLOYEES_VIEW },
  { path: '/employees/data-quality', labelKey: 'emp.nav.dataQuality', permission: PERMISSIONS.EMPLOYEES_MANAGE },
]

/**
 * The profile tab where each data-quality issue is reviewed and corrected
 * (by the normal, audited workflows - the report itself never changes data).
 */
export const CHECK_TAB: Record<DataQualityCheck, { tab: string; needsHistory: boolean }> = {
  unknown_status: { tab: '', needsHistory: false },
  no_primary_assignment: { tab: 'assignments', needsHistory: true },
  missing_location: { tab: 'assignments', needsHistory: true },
  missing_designation: { tab: 'assignments', needsHistory: true },
  separated_with_active_account: { tab: 'account', needsHistory: false },
  manager_inactive: { tab: 'reporting', needsHistory: false },
  no_line_manager: { tab: 'reporting', needsHistory: false },
  incomplete_record: { tab: '', needsHistory: false },
}
