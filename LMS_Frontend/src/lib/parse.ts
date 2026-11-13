/**
 * Small runtime guards used by the response parsers in `src/services/`.
 *
 * Parsers copy only the fields they know about, so an unexpected field in a
 * response (for example a hash that should never have been sent) is dropped
 * and never reaches the cache or the UI. Error messages name the field, never
 * its value (values may contain personal data).
 */

import { isRecord } from './apiClient'

export function expectRecord(value: unknown, what: string): Record<string, unknown> {
  if (!isRecord(value)) throw new TypeError(`${what}: expected an object`)
  return value
}

export function expectString(record: Record<string, unknown>, key: string): string {
  const value = record[key]
  if (typeof value !== 'string') throw new TypeError(`${key}: expected a string`)
  return value
}

export function expectNullableString(record: Record<string, unknown>, key: string): string | null {
  const value = record[key]
  if (value === undefined || value === null) return null
  if (typeof value !== 'string') throw new TypeError(`${key}: expected a string or null`)
  return value
}

export function expectBoolean(record: Record<string, unknown>, key: string): boolean {
  const value = record[key]
  if (typeof value !== 'boolean') throw new TypeError(`${key}: expected a boolean`)
  return value
}

export function expectStringArray(record: Record<string, unknown>, key: string): string[] {
  const value = record[key]
  if (!Array.isArray(value) || !value.every((item) => typeof item === 'string')) {
    throw new TypeError(`${key}: expected a list of strings`)
  }
  return [...value]
}

function isDateString(value: string): boolean {
  return !Number.isNaN(Date.parse(value))
}

export function expectDateString(record: Record<string, unknown>, key: string): string {
  const value = expectString(record, key)
  if (!isDateString(value)) throw new TypeError(`${key}: expected a date-time`)
  return value
}

export function expectNullableDateString(
  record: Record<string, unknown>,
  key: string,
): string | null {
  const value = expectNullableString(record, key)
  if (value !== null && !isDateString(value)) throw new TypeError(`${key}: expected a date-time`)
  return value
}

export function expectOneOf<T extends string>(
  record: Record<string, unknown>,
  key: string,
  allowed: readonly T[],
): T {
  const value = record[key]
  if (typeof value !== 'string' || !(allowed as readonly string[]).includes(value)) {
    throw new TypeError(`${key}: unexpected value`)
  }
  return value as T
}
