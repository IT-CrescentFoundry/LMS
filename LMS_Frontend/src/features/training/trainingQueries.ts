import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiError } from '../../lib/apiClient'
import { notificationService } from '../../services/notificationService'
import { trainingService } from '../../services/trainingService'
import type { CalendarFilters, EventFilters, ParticipationFilters } from '../../types/training'

/**
 * Server state of the training register, calendar and notifications. Every training
 * key starts with `training`, so one invalidation after a change refreshes the register,
 * event details, participants, calendar and summary together.
 */
export const trainingKeys = {
  all: ['training'] as const,
  summary: (filters: object) => [...trainingKeys.all, 'summary', filters] as const,
  events: (filters: EventFilters, offset: number) => [...trainingKeys.all, 'events', filters, offset] as const,
  event: (id: string) => [...trainingKeys.all, 'event', id] as const,
  participants: (id: string) => [...trainingKeys.all, 'participants', id] as const,
  participations: (filters: ParticipationFilters, offset: number) =>
    [...trainingKeys.all, 'participations', filters, offset] as const,
  calendar: (filters: CalendarFilters) => [...trainingKeys.all, 'calendar', filters] as const,
  labels: () => [...trainingKeys.all, 'labels'] as const,
  programmes: (filters: object) => [...trainingKeys.all, 'programmes', filters] as const,
}

export const notificationKeys = {
  all: ['notifications'] as const,
  list: (unreadOnly: boolean) => [...notificationKeys.all, 'list', unreadOnly] as const,
  preferences: () => [...notificationKeys.all, 'preferences'] as const,
  channels: () => [...notificationKeys.all, 'channels'] as const,
}

/** Do not retry errors that will not change on retry (403, 404, 503 migration pending). */
export function retryTransient(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.kind === 'http') return false
  return failureCount < 2
}

export function useRegisterSummary(filters: { unit?: string; location?: string }, enabled = true) {
  return useQuery({
    queryKey: trainingKeys.summary(filters),
    queryFn: ({ signal }) => trainingService.summary(filters, signal),
    retry: retryTransient,
    enabled,
  })
}

export function useEvents(filters: EventFilters, offset: number) {
  return useQuery({
    queryKey: trainingKeys.events(filters, offset),
    queryFn: ({ signal }) => trainingService.listEvents(filters, offset, signal),
    placeholderData: keepPreviousData,
    retry: retryTransient,
  })
}

export function useEvent(id: string) {
  return useQuery({
    queryKey: trainingKeys.event(id),
    queryFn: ({ signal }) => trainingService.getEvent(id, signal),
    retry: retryTransient,
  })
}

export function useParticipants(id: string) {
  return useQuery({
    queryKey: trainingKeys.participants(id),
    queryFn: ({ signal }) => trainingService.participants(id, signal),
    retry: retryTransient,
  })
}

export function useParticipations(filters: ParticipationFilters, offset: number, enabled = true) {
  return useQuery({
    queryKey: trainingKeys.participations(filters, offset),
    queryFn: ({ signal }) => trainingService.listParticipations(filters, offset, signal),
    placeholderData: keepPreviousData,
    retry: retryTransient,
    enabled,
  })
}

export function useCalendar(filters: CalendarFilters, enabled = true) {
  return useQuery({
    queryKey: trainingKeys.calendar(filters),
    queryFn: ({ signal }) => trainingService.calendar(filters, signal),
    placeholderData: keepPreviousData,
    retry: retryTransient,
    enabled,
  })
}

export function useCalendarLabels() {
  return useQuery({
    queryKey: trainingKeys.labels(),
    queryFn: ({ signal }) => trainingService.calendarLabels(signal),
    retry: retryTransient,
  })
}

export function useProgrammes(filters: { q?: string; category?: string; include_inactive?: boolean }) {
  return useQuery({
    queryKey: trainingKeys.programmes(filters),
    queryFn: ({ signal }) => trainingService.listProgrammes(filters, signal),
    retry: retryTransient,
  })
}

/** A mutation that refreshes every training view on success. */
export function useTrainingMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () =>
      Promise.all([
        client.invalidateQueries({ queryKey: trainingKeys.all }),
        client.invalidateQueries({ queryKey: notificationKeys.all }),
      ]),
  })
}

// ---------------------------------------------------------------------- notifications

export const NOTIFICATION_POLL_MS = 60_000

export function useNotifications(unreadOnly: boolean, options: { poll?: boolean } = {}) {
  return useQuery({
    queryKey: notificationKeys.list(unreadOnly),
    queryFn: ({ signal }) => notificationService.list({ unreadOnly, limit: 100 }, signal),
    retry: retryTransient,
    refetchInterval: options.poll
      ? (query) => (query.state.error instanceof ApiError ? false : NOTIFICATION_POLL_MS)
      : false,
  })
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: notificationKeys.preferences(),
    queryFn: ({ signal }) => notificationService.preferences(signal),
    retry: retryTransient,
  })
}

export function useChannels() {
  return useQuery({
    queryKey: notificationKeys.channels(),
    queryFn: ({ signal }) => notificationService.channels(signal),
    retry: retryTransient,
  })
}

export function useNotificationMutation<TArgs, TResult>(fn: (args: TArgs) => Promise<TResult>) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: fn,
    onSuccess: () => client.invalidateQueries({ queryKey: notificationKeys.all }),
  })
}
