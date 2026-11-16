import { describe, expect, it } from 'vitest'

import { dayAfter, endToLastDay, lastDayToEnd } from './dates'

describe('employee date conventions', () => {
  it('converts a last day in effect to the exclusive end the API expects', () => {
    expect(lastDayToEnd('2026-06-30')).toBe('2026-07-01')
    expect(lastDayToEnd('2026-12-31')).toBe('2027-01-01') // year boundary
    expect(lastDayToEnd('2028-02-28')).toBe('2028-02-29') // leap year
    expect(lastDayToEnd('2026-02-28')).toBe('2026-03-01') // non-leap year
  })

  it('shows the last day in effect for an exclusive end, and nothing for open records', () => {
    expect(endToLastDay('2026-07-01')).toBe('2026-06-30')
    expect(endToLastDay('2027-01-01')).toBe('2026-12-31')
    expect(endToLastDay('2028-03-01')).toBe('2028-02-29')
    expect(endToLastDay(null)).toBeNull()
  })

  it('round-trips without drifting a day', () => {
    for (const day of ['2026-01-01', '2026-03-31', '2028-02-29', '2026-10-25', '2026-03-29']) {
      expect(endToLastDay(lastDayToEnd(day))).toBe(day)
    }
  })

  it('describes the day records stop after a last working day, for display only', () => {
    expect(dayAfter('2026-06-30')).toBe('2026-07-01')
  })

  it('rejects anything that is not a real calendar date', () => {
    for (const bad of ['2026-02-30', '2026-13-01', '30/06/2026', '', '2026-6-30']) {
      expect(() => lastDayToEnd(bad)).toThrow(RangeError)
    }
  })

})
