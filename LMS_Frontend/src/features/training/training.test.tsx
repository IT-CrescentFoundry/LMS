import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { parseCalendarItem } from '../../services/trainingService'
import { EMPLOYEE, errorBody, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import {
  calendarItem,
  eventPage,
  participation,
  schemaPending,
  SUMMARY,
  TRAINING_ADMIN,
  trainingEvent,
} from '../../test/trainingFixtures'
import { addMonths, itemsOnDay, monthGridDays, startOfWeek, weekDays } from './calendarDates'

afterEach(() => {
  vi.unstubAllGlobals()
})

const REGISTER_ROUTES = {
  'GET /training/summary': reply(SUMMARY),
  'GET /training/events': reply(eventPage([trainingEvent()])),
  'GET /training/calendar-labels': reply(['Synthetic calendar 2026-27']),
  'GET /training/programmes': reply([]),
}

describe('Training navigation', () => {
  it('shows the training and skill links only to users holding a matching permission', async () => {
    mockSignedIn({ ...EMPLOYEE, roles: ['custom'], permissions: ['audit.view'] })
    renderApp()
    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).queryByRole('link', { name: 'Training Records' })).not.toBeInTheDocument()
    expect(within(nav).queryByRole('link', { name: 'Skill Matrix' })).not.toBeInTheDocument()
    expect(within(nav).getByRole('link', { name: 'Notifications' })).toBeInTheDocument()
  })

  it('opens the register for a training administrator and keeps the calendar link separate', async () => {
    mockSignedIn(TRAINING_ADMIN, REGISTER_ROUTES)
    renderApp('/training/calendar')
    const nav = await screen.findByRole('navigation', { name: 'Main navigation' })
    expect(within(nav).getByRole('link', { name: 'Training Calendar' })).toHaveAttribute('aria-current', 'page')
    expect(within(nav).getByRole('link', { name: 'Training Records' })).not.toHaveAttribute('aria-current')
  })
})

describe('Training register', () => {
  it('shows recorded facts, lists events and sends the chosen filters', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, REGISTER_ROUTES)
    const user = userEvent.setup()
    renderApp('/training')

    expect(await screen.findByRole('heading', { level: 1, name: 'Training records' })).toBeInTheDocument()
    expect(await screen.findByText('Showing all employees’ records'.replace('’', "'"))).toBeInTheDocument()
    expect(screen.getByText('Completions recorded')).toBeInTheDocument()
    const table = await screen.findByRole('table', { name: 'Training events' })
    expect(within(table).getByRole('link', { name: 'Synthetic fire safety basics' })).toHaveAttribute(
      'href',
      '/training/events/event-1',
    )
    expect(within(table).getByText('Scheduled')).toBeInTheDocument()
    expect(within(table).getByText('Upcoming')).toBeInTheDocument()

    const filters = screen.getByRole('search', { name: 'Filter training events' })
    await user.selectOptions(within(filters).getByLabelText('Status'), 'completed')
    await user.selectOptions(within(filters).getByLabelText('Timeframe'), 'past')
    await user.type(within(filters).getByLabelText('Search title or code'), 'fire')
    await user.click(within(filters).getByRole('button', { name: 'Apply' }))

    await waitFor(() => {
      const last = api.requestsTo('GET /training/events').at(-1)
      expect(last?.query.get('status')).toBe('completed')
      expect(last?.query.get('timeframe')).toBe('past')
      expect(last?.query.get('q')).toBe('fire')
    })
  })

  it('creates a planned event with only the fields entered', async () => {
    const created = trainingEvent({ public_id: 'event-new', status: 'planned' })
    const api = mockSignedIn(TRAINING_ADMIN, {
      ...REGISTER_ROUTES,
      'POST /training/events': reply(created, 201),
      'GET /training/events/event-new': reply(created),
      'GET /training/events/event-new/participants': reply([]),
    })
    const user = userEvent.setup()
    const { router } = renderApp('/training')
    await user.click(await screen.findByRole('button', { name: 'New training event' }))
    const dialog = await screen.findByRole('dialog', { name: 'New training event' })
    await user.type(within(dialog).getByLabelText('Title'), 'Synthetic forklift refresher')
    await user.type(within(dialog).getByLabelText('Planned start date'), '2027-01-15')
    await user.type(within(dialog).getByLabelText('Planned participants'), '10')
    await user.click(within(dialog).getByRole('button', { name: 'Create event' }))

    await waitFor(() => expect(router.state.location.pathname).toBe('/training/events/event-new'))
    const [post] = api.requestsTo('POST /training/events')
    expect(post.body).toEqual({
      title: 'Synthetic forklift refresher',
      planned_start_date: '2027-01-15',
      planned_participant_count: 10,
      status: 'planned',
    })
  })

  it('shows a friendly notice while the database update is pending', async () => {
    mockSignedIn(TRAINING_ADMIN, {
      'GET /training/summary': reply(schemaPending(), 503),
      'GET /training/events': reply(schemaPending(), 503),
      'GET /training/calendar-labels': reply(schemaPending(), 503),
    })
    renderApp('/training')
    const notices = await screen.findAllByText(
      'This module is installed but its database update (migration 0011) is awaiting administrator approval.',
    )
    expect(notices.length).toBeGreaterThan(0)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })
})

describe('Training event details', () => {
  const routes = (event = trainingEvent()) => ({
    'GET /training/events/event-1': reply(event),
    'GET /training/events/event-1/participants': reply([participation()]),
    'GET /training/programmes': reply([]),
  })

  it('records the event as conducted with its actual dates', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      ...routes(),
      'POST /training/events/event-1/status': reply(trainingEvent({ status: 'completed', actual_start_date: '2026-12-03' })),
    })
    const user = userEvent.setup()
    renderApp('/training/events/event-1')
    expect(await screen.findByRole('heading', { level: 1, name: 'Synthetic fire safety basics' })).toBeInTheDocument()
    expect(screen.getByText(/there is no evidence yet that this training took place/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Mark as conducted' }))
    const dialog = await screen.findByRole('dialog', { name: 'Mark as conducted' })
    const start = within(dialog).getByLabelText('Actual start date')
    await user.clear(start)
    await user.type(start, '2026-12-03')
    await user.click(within(dialog).getByRole('button', { name: 'Mark as conducted' }))

    await waitFor(() => expect(api.requestsTo('POST /training/events/event-1/status')).toHaveLength(1))
    const [post] = api.requestsTo('POST /training/events/event-1/status')
    expect(post.body).toMatchObject({ version: 3, status: 'completed', actual_start_date: '2026-12-03' })
  })

  it('explains in plain words why attendance cannot be recorded yet', async () => {
    mockSignedIn(TRAINING_ADMIN, {
      ...routes(),
      'PATCH /training/events/event-1/participants/part-1': reply(
        errorBody('event_not_started', 'Attendance cannot be recorded before the training starts.'),
        409,
      ),
    })
    const user = userEvent.setup()
    renderApp('/training/events/event-1')
    await user.click(await screen.findByRole('button', { name: 'Record for Synthetic Person A' }))
    const dialog = await screen.findByRole('dialog', { name: 'Training record: Synthetic Person A' })
    await user.selectOptions(within(dialog).getByLabelText('Attendance'), 'present')
    await user.click(within(dialog).getByRole('button', { name: 'Save' }))
    expect(await within(dialog).findByRole('alert')).toHaveTextContent(
      'Attendance cannot be recorded before the training starts.',
    )
  })

  it('asks for confirmation before withdrawing a participant', async () => {
    const api = mockSignedIn(TRAINING_ADMIN, {
      ...routes(),
      'PATCH /training/events/event-1/participants/part-1': reply(participation({ nomination_status: 'withdrawn' })),
    })
    const user = userEvent.setup()
    renderApp('/training/events/event-1')
    await user.click(await screen.findByRole('button', { name: 'Withdraw' }))
    const dialog = await screen.findByRole('dialog', { name: 'Withdraw Synthetic Person A?' })
    expect(api.requestsTo('PATCH /training/events/event-1/participants/part-1')).toHaveLength(0)
    await user.click(within(dialog).getByRole('button', { name: 'Withdraw participant' }))
    await waitFor(() =>
      expect(api.requestsTo('PATCH /training/events/event-1/participants/part-1')[0]?.body).toEqual({
        version: 1,
        nomination_status: 'withdrawn',
      }),
    )
  })
})

describe('Training calendar', () => {
  it('requests whole weeks of the month, moves between months and filters to my schedule', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date(2026, 11, 10, 9, 0))
    const api = mockSignedIn(TRAINING_ADMIN, {
      'GET /training/calendar': reply({ scope: 'global', start: '2026-11-30', end: '2027-01-03', items: [calendarItem()] }),
      'GET /training/calendar-labels': reply([]),
    })
    const user = userEvent.setup()
    renderApp('/training/calendar')
    expect(await screen.findByRole('link', { name: /Synthetic fire safety basics/ })).toBeInTheDocument()
    const first = api.requestsTo('GET /training/calendar')[0]
    expect(first.query.get('start')).toBe('2026-11-30')
    expect(first.query.get('end')).toBe('2027-01-03')
    expect(first.query.get('mine')).toBeNull()

    await user.click(screen.getByRole('button', { name: 'Next period' }))
    await waitFor(() => expect(api.requestsTo('GET /training/calendar').at(-1)?.query.get('start')).toBe('2026-12-28'))

    await user.click(screen.getByLabelText('My schedule only'))
    await waitFor(() => expect(api.requestsTo('GET /training/calendar').at(-1)?.query.get('mine')).toBe('true'))
    vi.useRealTimers()
  })
})

describe('calendar dates', () => {
  it('builds Monday-first month grids, weeks and month steps', () => {
    const days = monthGridDays('2026-12-15')
    expect(days[0]).toBe('2026-11-30')
    expect(days.at(-1)).toBe('2027-01-03')
    expect(days.length % 7).toBe(0)
    expect(startOfWeek('2026-12-06')).toBe('2026-11-30')
    expect(weekDays('2026-12-02')).toHaveLength(7)
    expect(addMonths('2027-01-31', 1)).toBe('2027-02-01')
  })

  it('places multi-day items on every day and never places month-only items on a day', () => {
    const multi = parseCalendarItem(calendarItem({ start_date: '2026-12-03', end_date: '2026-12-05', session: null, all_day: true }))
    const monthOnly = parseCalendarItem(calendarItem({ month_only: true, start_date: '2026-12-01', end_date: '2026-12-31' }))
    expect(itemsOnDay([multi, monthOnly], '2026-12-04')).toEqual([multi])
    expect(itemsOnDay([multi], '2026-12-06')).toEqual([])
  })
})
