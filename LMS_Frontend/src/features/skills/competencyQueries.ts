import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { isEmployeeNotLinked } from '../../lib/featureErrors'
import { competencyService } from '../../services/competencyService'
import type { CompetencyStatus } from '../../types/competency'
import { retryTransient } from '../training/trainingQueries'

/** Every competency key starts with `competency`; one invalidation refreshes all views. */
export const competencyKeys = {
  all: ['competency'] as const,
  scales: () => [...competencyKeys.all, 'scales'] as const,
  competencies: (filters: object, offset: number) => [...competencyKeys.all, 'list', filters, offset] as const,
  categories: () => [...competencyKeys.all, 'categories'] as const,
  matrices: (filters: object) => [...competencyKeys.all, 'matrices', filters] as const,
  grid: (id: string) => [...competencyKeys.all, 'grid', id] as const,
  assessments: (employee: string, competency: string | undefined) =>
    [...competencyKeys.all, 'assessments', employee, competency] as const,
  mySkills: () => [...competencyKeys.all, 'my-skills'] as const,
}

export function useScales() {
  return useQuery({
    queryKey: competencyKeys.scales(),
    queryFn: ({ signal }) => competencyService.listScales(signal),
    retry: retryTransient,
  })
}

export function useCompetencies(
  filters: { q?: string; category?: string; include_inactive?: boolean; status?: CompetencyStatus },
  offset: number,
  limit?: number,
) {
  return useQuery({
    queryKey: [...competencyKeys.competencies(filters, offset), limit],
    queryFn: ({ signal }) => competencyService.listCompetencies(filters, offset, signal, limit),
    placeholderData: keepPreviousData,
    retry: retryTransient,
  })
}

export function useCategories() {
  return useQuery({
    queryKey: competencyKeys.categories(),
    queryFn: ({ signal }) => competencyService.categories(signal),
    retry: retryTransient,
  })
}

export function useMatrices(filters: { q?: string; unit?: string; location?: string; include_inactive?: boolean }) {
  return useQuery({
    queryKey: competencyKeys.matrices(filters),
    queryFn: ({ signal }) => competencyService.listMatrices(filters, signal),
    retry: retryTransient,
  })
}

export function useGrid(id: string) {
  return useQuery({
    queryKey: competencyKeys.grid(id),
    queryFn: ({ signal }) => competencyService.grid(id, signal),
    retry: retryTransient,
  })
}

export function useAssessments(employee: string, competency: string | undefined, enabled = true) {
  return useQuery({
    queryKey: competencyKeys.assessments(employee, competency),
    queryFn: ({ signal }) => competencyService.assessments(employee, competency, signal),
    retry: retryTransient,
    enabled,
  })
}

/**
 * Asks again unless the last answer was `404 employee_not_linked`. That answer is
 * expected for accounts without an employee record and stays true for the whole
 * session (linkage changes only by an administrator; the cache is purged at
 * sign-out), so re-requesting it on every mount or focus only repeats the 404.
 * Every other failure keeps the normal refetch behaviour.
 */
function unlessEmployeeNotLinked(query: { state: { error: unknown } }): boolean {
  return !isEmployeeNotLinked(query.state.error)
}

export function useMySkills(enabled = true) {
  return useQuery({
    queryKey: competencyKeys.mySkills(),
    queryFn: ({ signal }) => competencyService.mySkills(signal),
    retry: retryTransient,
    retryOnMount: unlessEmployeeNotLinked,
    refetchOnWindowFocus: unlessEmployeeNotLinked,
    refetchOnReconnect: unlessEmployeeNotLinked,
    enabled,
  })
}

export function useCompetencyMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => client.invalidateQueries({ queryKey: competencyKeys.all }),
  })
}
