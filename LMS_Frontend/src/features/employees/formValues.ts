/** Plain value helpers for the employee forms (kept apart from the components). */

/** Same rule as the server: trimmed, capitals, letters/digits and / . _ - (max 30). */
const EMPLOYEE_CODE = /^[A-Z0-9][A-Z0-9/._-]{0,29}$/
const WORK_EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

/** The code as the server will store it (leading zeros kept: codes are text). */
export function normaliseEmployeeCode(raw: string): string {
  return raw.trim().toUpperCase()
}

export function isValidEmployeeCode(raw: string): boolean {
  return EMPLOYEE_CODE.test(normaliseEmployeeCode(raw))
}

export function isValidWorkEmail(raw: string): boolean {
  return WORK_EMAIL.test(raw.trim())
}

export function blankToNull(value: string): string | null {
  const trimmed = value.trim()
  return trimmed === '' ? null : trimmed
}

/** Last day before the start (ISO strings compare as dates). */
export function lastDayBeforeStart(from: string, lastDay: string): boolean {
  return from !== '' && lastDay !== '' && lastDay < from
}
