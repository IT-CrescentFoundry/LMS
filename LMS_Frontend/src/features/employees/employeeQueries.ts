import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { adminService } from '../../services/adminService'
import { EMPLOYEE_PICKER_SIZE, employeeService } from '../../services/employeeService'
import { organisationService, PICKER_PAGE_SIZE } from '../../services/organisationService'
import type { DataQualityCheck, EmployeeFilters } from '../../types/employee'

/**
 * Server state for the employee screens. Every key starts with `employees`, so one
 * invalidation after a successful change refreshes every employee view - including
 * other employees affected by the change (e.g. direct reports after a separation).
 */
export const employeeQueryKeys = {
  all: ['employees'] as const,
  list: (filters: EmployeeFilters) => [...employeeQueryKeys.all, 'list', filters] as const,
  detail: (id: string, asOf: string | undefined) =>
    [...employeeQueryKeys.all, 'detail', id, asOf] as const,
  assignments: (id: string, includeEnded: boolean) =>
    [...employeeQueryKeys.all, 'assignments', id, includeEnded] as const,
  roles: (id: string, asOf: string | undefined, includeEnded: boolean) =>
    [...employeeQueryKeys.all, 'roles', id, asOf, includeEnded] as const,
  responsibilities: (id: string, includeEnded: boolean) =>
    [...employeeQueryKeys.all, 'responsibilities', id, includeEnded] as const,
  reporting: (id: string, asOf: string | undefined) =>
    [...employeeQueryKeys.all, 'reporting', id, asOf] as const,
  account: (id: string) => [...employeeQueryKeys.all, 'account', id] as const,
  history: (id: string) => [...employeeQueryKeys.all, 'history', id] as const,
  dataQuality: (asOf: string | undefined, check: DataQualityCheck | null) =>
    [...employeeQueryKeys.all, 'data-quality', asOf, check] as const,
  reportingTypes: () => [...employeeQueryKeys.all, 'reporting-types'] as const,
  picker: (q: string) => [...employeeQueryKeys.all, 'picker', q] as const,
  separationPreview: (id: string, lastWorkingDay: string) =>
    [...employeeQueryKeys.all, 'separation-preview', id, lastWorkingDay] as const,
}

export function useEmployees(filters: EmployeeFilters) {
  return useInfiniteQuery({
    queryKey: employeeQueryKeys.list(filters),
    queryFn: ({ pageParam, signal }) => employeeService.list(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

export function useEmployee(id: string, asOf: string | undefined) {
  return useQuery({
    queryKey: employeeQueryKeys.detail(id, asOf),
    queryFn: ({ signal }) => employeeService.get(id, asOf, signal),
  })
}

export function useAssignments(id: string, includeEnded: boolean, enabled = true) {
  return useQuery({
    queryKey: employeeQueryKeys.assignments(id, includeEnded),
    queryFn: ({ signal }) => employeeService.listAssignments(id, includeEnded, signal),
    enabled,
  })
}

export function useFunctionalRoles(id: string, asOf: string | undefined, includeEnded: boolean) {
  return useQuery({
    queryKey: employeeQueryKeys.roles(id, asOf, includeEnded),
    queryFn: ({ signal }) => employeeService.getFunctionalRoles(id, asOf, includeEnded, signal),
  })
}

export function useResponsibilities(id: string, includeEnded: boolean) {
  return useQuery({
    queryKey: employeeQueryKeys.responsibilities(id, includeEnded),
    queryFn: ({ signal }) => employeeService.listResponsibilities(id, includeEnded, signal),
  })
}

export function useReporting(id: string, asOf: string | undefined) {
  return useQuery({
    queryKey: employeeQueryKeys.reporting(id, asOf),
    queryFn: ({ signal }) => employeeService.getReporting(id, asOf, signal),
  })
}

export function useEmployeeAccount(id: string) {
  return useQuery({
    queryKey: employeeQueryKeys.account(id),
    queryFn: ({ signal }) => employeeService.getAccount(id, signal),
  })
}

export function useEmployeeHistory(id: string, enabled = true) {
  return useInfiniteQuery({
    queryKey: employeeQueryKeys.history(id),
    queryFn: ({ pageParam, signal }) => employeeService.listHistory(id, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    enabled,
  })
}

export function useDataQuality(asOf: string | undefined, check: DataQualityCheck | null) {
  return useInfiniteQuery({
    queryKey: employeeQueryKeys.dataQuality(asOf, check),
    queryFn: ({ pageParam, signal }) =>
      employeeService.getDataQuality(asOf, check, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    // Keep the counts on screen while another check or date loads.
    placeholderData: keepPreviousData,
  })
}

export function useReportingTypes(enabled = true) {
  return useQuery({
    queryKey: employeeQueryKeys.reportingTypes(),
    queryFn: ({ signal }) => employeeService.listReportingTypes(signal),
    enabled,
  })
}

/** Server-side employee search for pickers (first page only). */
export function useEmployeePicker(q: string, enabled: boolean) {
  return useQuery({
    queryKey: employeeQueryKeys.picker(q),
    queryFn: ({ signal }) =>
      employeeService.list({ q: q || undefined }, null, signal, EMPLOYEE_PICKER_SIZE),
    enabled,
  })
}

/**
 * Unlinked login accounts the caller may manage, for the account picker
 * (`user_accounts.view`). The server applies the same rule it enforces on every
 * link, so accounts that would be refused are not offered.
 */
export function useUnlinkedAccounts(q: string, enabled: boolean) {
  return useQuery({
    queryKey: ['admin', 'users', 'unlinked-picker', q] as const,
    queryFn: ({ signal }) =>
      adminService.listUsers({ q: q || undefined, linked: false, manageable: true }, null, signal),
    enabled,
  })
}

/** Active designations matching `q` (server search) for assignment pickers. */
export function useDesignationPicker(q: string, enabled = true) {
  return useQuery({
    queryKey: ['org', 'designations', 'employee-picker', q] as const,
    queryFn: ({ signal }) =>
      organisationService.listDesignations({ q: q || undefined }, null, signal, PICKER_PAGE_SIZE),
    enabled,
  })
}

/** Active responsibilities matching `q` (server search, first page). */
export function useResponsibilityPicker(q: string, enabled = true) {
  return useQuery({
    queryKey: ['org', 'responsibilities', 'employee-picker', q] as const,
    queryFn: ({ signal }) => organisationService.listResponsibilities({ q: q || undefined }, null, signal),
    enabled,
  })
}

/**
 * Read-only separation impact (`employees.manage`). Always fetched fresh: the
 * last working day is sent unchanged and nothing is cached between attempts.
 */
export function useSeparationPreview(id: string, lastWorkingDay: string, enabled: boolean) {
  return useQuery({
    queryKey: employeeQueryKeys.separationPreview(id, lastWorkingDay),
    queryFn: ({ signal }) => employeeService.previewSeparation(id, lastWorkingDay, signal),
    enabled,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })
}

/**
 * After a version conflict: reload every employee view and close the dialog, so
 * the user starts again from the current data (nothing is overwritten).
 */
export function useReloadEmployeesAndClose(onClose: () => void) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: employeeQueryKeys.all })
    onClose()
  }
}

/**
 * A change through the audited backend services. On success every employee query
 * is refreshed (and, for account links, the user-account lists); on failure
 * nothing is retried automatically.
 */
export function useEmployeeMutation<TVariables, TResult>(
  mutationFn: (variables: TVariables) => Promise<TResult>,
  { alsoInvalidateUsers = false }: { alsoInvalidateUsers?: boolean } = {},
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: employeeQueryKeys.all })
      if (alsoInvalidateUsers) await queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
}
