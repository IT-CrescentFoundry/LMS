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
