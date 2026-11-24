/**
 * Pure date helpers for the training calendar. Weeks start on Monday. All values are
 * local calendar dates as "YYYY-MM-DD" (business dates), never instants.
 */

import type { CalendarItem } from '../../types/training'

export function toIso(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export function fromIso(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function addDays(value: string, days: number): string {
  const date = fromIso(value)
  date.setDate(date.getDate() + days)
  return toIso(date)
}

export function addMonths(value: string, months: number): string {
  const date = fromIso(value)
  return toIso(new Date(date.getFullYear(), date.getMonth() + months, 1))
}

/** Monday of the week containing `value`. */
export function startOfWeek(value: string): string {
  const date = fromIso(value)
  const offset = (date.getDay() + 6) % 7
  return addDays(value, -offset)
}

export function startOfMonth(value: string): string {
  const date = fromIso(value)
  return toIso(new Date(date.getFullYear(), date.getMonth(), 1))
}

export function endOfMonth(value: string): string {
  const date = fromIso(value)
  return toIso(new Date(date.getFullYear(), date.getMonth() + 1, 0))
}

/** Every day shown by a month grid: whole weeks from Monday to Sunday (35 or 42 days). */
export function monthGridDays(anchor: string): string[] {
  const first = startOfWeek(startOfMonth(anchor))
  const last = addDays(startOfWeek(endOfMonth(anchor)), 6)
  const days: string[] = []
  for (let day = first; day <= last; day = addDays(day, 1)) days.push(day)
  return days
}

export function weekDays(anchor: string): string[] {
  const first = startOfWeek(anchor)
  return Array.from({ length: 7 }, (_, index) => addDays(first, index))
}

/** Items occurring on `day` (multi-day items appear on every day; month-only items never). */
export function itemsOnDay(items: readonly CalendarItem[], day: string): CalendarItem[] {
  return items.filter((item) => {
    if (item.month_only || !item.start_date) return false
    const end = item.end_date ?? item.start_date
    return item.start_date <= day && day <= end
  })
}

/** Items planned for a month without a fixed date. */
export function monthOnlyItems(items: readonly CalendarItem[]): CalendarItem[] {
  return items.filter((item) => item.month_only)
}
