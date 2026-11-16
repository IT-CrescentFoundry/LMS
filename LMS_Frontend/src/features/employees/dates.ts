/**
 * Date conventions for the employee screens (decided in C3b planning).
 *
 * The API stores half-open periods: `effective_to` is EXCLUSIVE - the first day a
 * record no longer applies. People think in "last day", so:
 *
 * - end dates are entered and shown as the LAST DAY IN EFFECT and converted here,
 *   and only here: `lastDayToEnd` (+1 day) for requests, `endToLastDay` (-1 day)
 *   for display;
 * - start dates (`effective_from`, change dates) are sent unchanged;
 * - the separation date is the LAST WORKING DAY and is ALSO sent unchanged - the
 *   server adds the day itself (`records_end_on`). Never pass it through
 *   `lastDayToEnd`, or the day would be added twice.
 *
 * All arithmetic is on calendar dates (UTC), so no time zone can shift a day.
 */

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

function shift(isoDate: string, days: number): string {
  const match = ISO_DATE.exec(isoDate)
  if (!match) throw new RangeError(`not a YYYY-MM-DD date: ${isoDate}`)
  const [, year, month, day] = match
  const date = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)))
  if (
    date.getUTCFullYear() !== Number(year) ||
    date.getUTCMonth() !== Number(month) - 1 ||
    date.getUTCDate() !== Number(day)
  ) {
    throw new RangeError(`not a calendar date: ${isoDate}`)
  }
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

/** Request value: the exclusive `effective_to` for an entered last day in effect. */
export function lastDayToEnd(lastDay: string): string {
  return shift(lastDay, 1)
}

/** Display value: the last day in effect for an exclusive `effective_to` (null = open). */
export function endToLastDay(effectiveTo: string | null): string | null {
  return effectiveTo === null ? null : shift(effectiveTo, -1)
}

/** Display only: the day after the last working day, when separated records stop. */
export function dayAfter(isoDate: string): string {
  return shift(isoDate, 1)
}
