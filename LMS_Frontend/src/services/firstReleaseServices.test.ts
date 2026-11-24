import { describe, expect, it } from 'vitest'

import { CHANNELS, competency, GRID, notification, participation, PREFERENCES, SUMMARY, trainingEvent } from '../test/trainingFixtures'
import { parseCompetency, parseGrid } from './competencyService'
import { parseChannels, parseNotificationList, parsePreferences } from './notificationService'
import { parseEvent, parseOffsetPage, parseParticipation, parseSummary } from './trainingService'

describe('training parsers', () => {
  it('parses an event and keeps planned and actual dates apart', () => {
    const event = parseEvent(trainingEvent({ actual_start_date: '2026-12-03', unexpected: 'dropped' }))
    expect(event.planned_start_date).toBe('2026-12-03')
    expect(event.actual_start_date).toBe('2026-12-03')
    expect(event.planned_manhours).toBe(24)
    expect(event.sessions[0].venue).toBe('Training Room 1')
    expect('unexpected' in event).toBe(false)
  })

  it('rejects unknown statuses and malformed dates', () => {
    expect(() => parseEvent(trainingEvent({ status: 'happened' }))).toThrow('status')
    expect(() => parseEvent(trainingEvent({ planned_start_date: '03/12/2026' }))).toThrow('planned_start_date')
  })

  it('parses participation with unrecorded attendance as null', () => {
    const row = parseParticipation(participation())
    expect(row.attendance_status).toBeNull()
    expect(row.completion_status).toBeNull()
    expect(() => parseParticipation(participation({ attendance_status: 'maybe' }))).toThrow('attendance_status')
  })

  it('parses offset pages and the register summary', () => {
    const page = parseOffsetPage(parseEvent)({ items: [trainingEvent()], total: 9, limit: 25, offset: 0 })
    expect(page.total).toBe(9)
    expect(parseSummary(SUMMARY).scope).toBe('global')
  })
})

describe('competency parsers', () => {
  it('parses a grid with gaps, plan flags and item statistics', () => {
    const grid = parseGrid(GRID)
    expect(grid.rows[0].cells[0].gap).toEqual({ status: 'below', gap_steps: 2, gap_value: null })
    expect(grid.rows[0].cells[0].needs_plan).toBe(true)
    expect(grid.item_stats?.[0].risk).toBe('high')
    expect(grid.item_stats?.[0].counts_by_rank['2']).toBe(1)
    expect(() => parseGrid({ ...GRID, item_stats: [{ ...GRID.item_stats[0], risk: 'severe' }] })).toThrow('risk')
  })

  it('parses a competency with its scale reference', () => {
    expect(parseCompetency(competency()).scale?.code).toBe('SYN_SCALE_1_5')
  })
})

describe('notification parsers', () => {
  it('parses the list, preferences and channels', () => {
    expect(parseNotificationList({ items: [notification()], unread_count: 1 }).items[0].read_at).toBeNull()
    expect(parsePreferences(PREFERENCES).mandatory).toContain('training.cancelled')
    const channels = parseChannels(CHANNELS)
    expect(channels.channels.find((c) => c.code === 'outlook')?.connected).toBe(false)
    expect(channels.reminder_offsets_days).toEqual([1, 7])
  })
})
