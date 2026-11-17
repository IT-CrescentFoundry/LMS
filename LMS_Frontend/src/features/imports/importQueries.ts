import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { importService } from '../../services/importService'
import type { ImportJob, IssueFilters, JobFilters, MappingFilters, RowFilters } from '../../types/imports'
import { employeeQueryKeys } from '../employees/employeeQueries'

/**
 * Server state for the Import Control Room. Every key starts with `imports`, so
 * one invalidation after a change refreshes the job, its rows and issues, the
 * history and the mapping queue together.
 */
export const importQueryKeys = {
  all: ['imports'] as const,
  profiles: () => [...importQueryKeys.all, 'profiles'] as const,
  jobs: (filters: JobFilters) => [...importQueryKeys.all, 'jobs', filters] as const,
  job: (id: string) => [...importQueryKeys.all, 'job', id] as const,
  rows: (id: string, filters: RowFilters) => [...importQueryKeys.all, 'rows', id, filters] as const,
  issues: (id: string, filters: IssueFilters) => [...importQueryKeys.all, 'issues', id, filters] as const,
  mappings: (filters: MappingFilters) => [...importQueryKeys.all, 'mappings', filters] as const,
}

export function useImportProfiles() {
  return useQuery({
    queryKey: importQueryKeys.profiles(),
    queryFn: ({ signal }) => importService.listProfiles(signal),
  })
}

export function useImportJobs(filters: JobFilters) {
  return useInfiniteQuery({
    queryKey: importQueryKeys.jobs(filters),
    queryFn: ({ pageParam, signal }) => importService.listJobs(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

export function useImportJob(id: string) {
  return useQuery({
    queryKey: importQueryKeys.job(id),
    queryFn: ({ signal }) => importService.getJob(id, signal),
  })
}

export function useImportRows(id: string, filters: RowFilters, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: importQueryKeys.rows(id, filters),
    queryFn: ({ pageParam, signal }) => importService.listRows(id, filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    placeholderData: keepPreviousData,
    enabled,
  })
}

export function useImportIssues(id: string, filters: IssueFilters, enabled: boolean) {
  return useInfiniteQuery({
    queryKey: importQueryKeys.issues(id, filters),
    queryFn: ({ pageParam, signal }) => importService.listIssues(id, filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
    placeholderData: keepPreviousData,
    enabled,
  })
}

export function useValueMappings(filters: MappingFilters) {
  return useInfiniteQuery({
    queryKey: importQueryKeys.mappings(filters),
    queryFn: ({ pageParam, signal }) => importService.listMappings(filters, pageParam, signal),
    initialPageParam: null as string | null,
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  })
}

/**
 * A job action (map, validate, decide, commit, cancel). On success the returned
 * job replaces the cached one and every import view is refreshed; after a commit
 * the employee screens are refreshed too. Nothing is retried automatically.
 */
export function useJobMutation<TVariables>(
  mutationFn: (variables: TVariables) => Promise<ImportJob>,
  { refreshEmployees = false }: { refreshEmployees?: boolean } = {},
) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: async (job) => {
      queryClient.setQueryData(importQueryKeys.job(job.public_id), job)
      await queryClient.invalidateQueries({ queryKey: importQueryKeys.all })
      if (refreshEmployees) await queryClient.invalidateQueries({ queryKey: employeeQueryKeys.all })
    },
  })
}

/** A reference-mapping decision: refreshes the queue and every job (staleness). */
export function useMappingMutation<TVariables, TResult>(mutationFn: (variables: TVariables) => Promise<TResult>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: importQueryKeys.all })
    },
  })
}
