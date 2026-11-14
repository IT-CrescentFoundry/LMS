/** Locale-aware formatting helpers (the UI language decides digits and order). */

export function formatDateTime(
  iso: string,
  language: string | undefined,
  options: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' },
): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return new Intl.DateTimeFormat(language, options).format(date)
}

/** Parses a business date ("YYYY-MM-DD") as a local calendar date. */
export function parseIsoDate(value: string): Date | undefined {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return undefined
  const [, year, month, day] = match
  const date = new Date(Number(year), Number(month) - 1, Number(day))
  return Number.isNaN(date.getTime()) ? undefined : date
}

/** Formats a business date ("YYYY-MM-DD") without any time-zone shift. */
export function formatDate(value: string, language: string | undefined): string {
  const date = parseIsoDate(value)
  return date ? new Intl.DateTimeFormat(language, { dateStyle: 'medium' }).format(date) : value
}

/** Today's local calendar date as "YYYY-MM-DD". */
export function todayIsoDate(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

/**
 * Converts a local calendar date from an `<input type="date">` ("YYYY-MM-DD")
 * to the ISO instant of local midnight, optionally shifted by whole days.
 * Returns undefined for blank or malformed input.
 */
export function localDayStartIso(value: string, offsetDays = 0): string | undefined {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value)
  if (!match) return undefined
  const [, year, month, day] = match
  const date = new Date(Number(year), Number(month) - 1, Number(day) + offsetDays)
  return Number.isNaN(date.getTime()) ? undefined : date.toISOString()
}
