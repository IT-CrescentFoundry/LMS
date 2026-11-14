import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import { organisationService, PICKER_PAGE_SIZE } from '../../services/organisationService'
import type { ListFilters, RankedKind, TreeFilters } from '../../types/organisation'

/**
 * Server state for the organisation pages. Every key starts with `org`, so one
 * invalidation after a successful change refreshes all organisation views (the
 * tree, details, history and pickers stay consistent with the server).
 */
export const orgQueryKeys = {
  all: ['org'] as const,
  unitTypes: () => [...orgQueryKeys.all, 'unit-types'] as const,
  tree: (filters: TreeFilters) => [...orgQueryKeys.all, 'tree', filters] as const,
  unit: (id: string, asOf: string | undefined) => [...orgQueryKeys.all, 'unit', id, asOf] as const,
  history: (id: string) => [...orgQueryKeys.all, 'history', id] as const,
  locations: (includeInactive: boolean) => [...orgQueryKeys.all, 'locations', includeInactive] as const,
  jobFamilies: (includeInactive: boolean) =>
    [...orgQueryKeys.all, 'job-families', includeInactive] as const,
  ranked: (kind: RankedKind, includeInactive: boolean) =>
    [...orgQueryKeys.all, kind, includeInactive] as const,
  designations: (filters: ListFilters) => [...orgQueryKeys.all, 'designations', filters] as const,
  mappings: (designationId: string, includeEnded: boolean) =>
    [...orgQueryKeys.all, 'mappings', designationId, includeEnded] as const,
  functionalRoles: (filters: ListFilters) =>
    [...orgQueryKeys.all, 'functional-roles', filters] as const,
  rolePicker: () => [...orgQueryKeys.all, 'functional-roles', 'picker'] as const,
  responsibilities: (filters: ListFilters) =>
    [...orgQueryKeys.all, 'responsibilities', filters] as const,
}

export function useUnitTypes() {
  return useQuery({
    queryKey: orgQueryKeys.unitTypes(),
    queryFn: ({ signal }) => organisationService.listUnitTypes(signal),
  })
}

export function useOrgTree(filters: TreeFilters) {
  return useQuery({
    queryKey: orgQueryKeys.tree(filters),
    queryFn: ({ signal }) => organisationService.getTree(filters, signal),
  })
}

export function useOrgUnit(id: string | null, asOf: string | undefined) {
  return useQuery({
    queryKey: orgQueryKeys.unit(id ?? '', asOf),
    queryFn: ({ signal }) => organisationService.getUnit(id ?? '', asOf, signal),
    enabled: id !== null,
  })
}

export function useUnitHistory(id: string | null) {
  return useQuery({
    queryKey: orgQueryKeys.history(id ?? ''),
    queryFn: ({ signal }) => organisationService.getUnitHistory(id ?? '', signal),
    enabled: id !== null,
  })
}

export function useLocations(includeInactive: boolean) {
  return useQuery({
    queryKey: orgQueryKeys.locations(includeInactive),
    queryFn: ({ signal }) => organisationService.listLocations(includeInactive, signal),
  })
}

export function useJobFamilies(includeInactive: boolean) {
  return useQuery({
    queryKey: orgQueryKeys.jobFamilies(includeInactive),
    queryFn: ({ signal }) => organisationService.listJobFamilies(includeInactive, signal),
  })
}

export function useRanked(kind: RankedKind, includeInactive: boolean) {
  return useQuery({
    queryKey: orgQueryKeys.ranked(kind, includeInactive),
    queryFn: ({ signal }) => organisationService.listRanked(kind, includeInactive, signal),
  })
}

export function useDesignations(filters: ListFilters) {
  return useInfiniteQuery({
    queryKey: orgQueryKeys.designations(filters),
    queryFn: ({ pageParam, signal }) =>
      organisationService.listDesignations(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

export function useMappings(designationId: string, includeEnded: boolean) {
  return useQuery({
    queryKey: orgQueryKeys.mappings(designationId, includeEnded),
    queryFn: ({ signal }) => organisationService.listMappings(designationId, includeEnded, signal),
  })
}

export function useFunctionalRoles(filters: ListFilters) {
  return useInfiniteQuery({
    queryKey: orgQueryKeys.functionalRoles(filters),
    queryFn: ({ pageParam, signal }) =>
      organisationService.listFunctionalRoles(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

/** Active functional roles for pickers (first page of up to 200, by code). */
export function useRolePicker(enabled: boolean) {
  return useQuery({
    queryKey: orgQueryKeys.rolePicker(),
    queryFn: ({ signal }) =>
      organisationService.listFunctionalRoles({}, null, signal, PICKER_PAGE_SIZE),
    enabled,
  })
}

export function useResponsibilities(filters: ListFilters) {
  return useInfiniteQuery({
    queryKey: orgQueryKeys.responsibilities(filters),
    queryFn: ({ pageParam, signal }) =>
      organisationService.listResponsibilities(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

/**
 * After a version conflict: reload every organisation view and close the dialog,
 * so the user starts again from the current data (nothing is overwritten).
 */
export function useReloadAndClose(onClose: () => void) {
  const queryClient = useQueryClient()
  return () => {
    void queryClient.invalidateQueries({ queryKey: orgQueryKeys.all })
    onClose()
  }
}

/**
 * A change through the audited backend services. On success every organisation
 * query is refreshed; on failure nothing is retried automatically (a version
 * conflict must be resolved by reloading, never by overwriting).
 */
export function useOrgMutation<TVariables, TResult>(
  mutationFn: (variables: TVariables) => Promise<TResult>,
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: orgQueryKeys.all }),
  })
}
