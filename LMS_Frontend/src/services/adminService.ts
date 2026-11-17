import { apiRequest, buildQuery, isRecord } from '../lib/apiClient'
import {
  expectDateString,
  expectNullableDateString,
  expectNullableString,
  expectRecord,
  expectString,
  expectStringArray,
} from '../lib/parse'
import type {
  AuditActor,
  AuditEvent,
  AuditFilters,
  LinkedEmployee,
  Page,
  UserFilters,
  UserSummary,
} from '../types/admin'

export function parsePage<T>(parseItem: (data: unknown) => T): (data: unknown) => Page<T> {
  return (data) => {
    const record = expectRecord(data, 'page')
    if (!Array.isArray(record.items)) throw new TypeError('items: expected a list')
    return {
      items: record.items.map(parseItem),
      next_cursor: expectNullableString(record, 'next_cursor'),
    }
  }
}

function parseLinkedEmployee(data: unknown): LinkedEmployee | null {
  if (data === null || data === undefined) return null
  const record = expectRecord(data, 'linked employee')
  return {
    public_id: expectString(record, 'public_id'),
    employee_code: expectString(record, 'employee_code'),
    full_name: expectString(record, 'full_name'),
  }
}

export function parseUserSummary(data: unknown): UserSummary {
  const record = expectRecord(data, 'user')
  return {
    public_id: expectString(record, 'public_id'),
    login_id: expectString(record, 'login_id'),
    display_name: expectString(record, 'display_name'),
    email: expectNullableString(record, 'email'),
    status: expectString(record, 'status'),
    roles: expectStringArray(record, 'roles'),
    last_login_at: expectNullableDateString(record, 'last_login_at'),
    created_at: expectDateString(record, 'created_at'),
    employee: parseLinkedEmployee(record.employee),
  }
}

export function parseActor(data: unknown): AuditActor | null {
  if (data === null || data === undefined) return null
  const record = expectRecord(data, 'actor')
  return {
    public_id: expectString(record, 'public_id'),
    login_id: expectString(record, 'login_id'),
    display_name: expectString(record, 'display_name'),
  }
}

export function parseAuditEvent(data: unknown): AuditEvent {
  const record = expectRecord(data, 'audit event')
  const metadata = record.metadata
  return {
    event_id: expectString(record, 'event_id'),
    occurred_at: expectDateString(record, 'occurred_at'),
    event_type: expectString(record, 'event_type'),
    outcome: expectString(record, 'outcome'),
    actor: parseActor(record.actor),
    target_type: expectNullableString(record, 'target_type'),
    target_id: expectNullableString(record, 'target_id'),
    request_id: expectNullableString(record, 'request_id'),
    source_ip: expectNullableString(record, 'source_ip'),
    user_agent: expectNullableString(record, 'user_agent'),
    metadata: isRecord(metadata) ? { ...metadata } : null,
  }
}

export const USERS_PAGE_SIZE = 25
export const AUDIT_PAGE_SIZE = 50

/** Read-only administration API (permission-guarded by the backend). */
export const adminService = {
  /** `GET /admin/users` - requires `user_accounts.view`. */
  listUsers(
    filters: UserFilters,
    cursor: string | null,
    signal?: AbortSignal,
    limit: number = USERS_PAGE_SIZE,
  ): Promise<Page<UserSummary>> {
    const query = buildQuery({
      status: filters.status,
      q: filters.q,
      linked: filters.linked,
      manageable: filters.manageable ? true : undefined,
      limit,
      cursor,
    })
    return apiRequest(`/admin/users${query}`, { parse: parsePage(parseUserSummary), signal })
  },

  /**
   * `GET /admin/audit-events` - requires `audit.view`.
   * Every call is itself recorded by the backend as an `audit.events.viewed` event.
   */
  listAuditEvents(
    filters: AuditFilters,
    cursor: string | null,
    signal?: AbortSignal,
  ): Promise<Page<AuditEvent>> {
    const query = buildQuery({
      event_type: filters.event_type,
      outcome: filters.outcome,
      occurred_from: filters.occurred_from,
      occurred_to: filters.occurred_to,
      limit: AUDIT_PAGE_SIZE,
      cursor,
    })
    return apiRequest(`/admin/audit-events${query}`, { parse: parsePage(parseAuditEvent), signal })
  },
}
