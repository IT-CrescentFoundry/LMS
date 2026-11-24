import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { importRoutes, job, PROFILE } from '../../test/importFixtures'
import { BASELINE_NODES, DEPT_NODE, structureRoutes, SUB_NODE } from '../../test/orgFixtures'
import { HR_ADMIN, mockSignedIn, renderApp, reply } from '../../test/renderApp'
import { TRAINING_ADMIN } from '../../test/trainingFixtures'
import type { TreeNode } from '../../types/organisation'
import { buildForest } from './chart'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Organisation chart', () => {
  it('draws the structure top-down and collapses a branch', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    const user = userEvent.setup()
    renderApp('/organisation/chart')
    const chart = await screen.findByRole('list', { name: 'Organisation units, top level first' })
    expect(within(chart).getByText('Operation')).toBeInTheDocument()
    expect(within(chart).getByText('Test Melting')).toBeInTheDocument()
    expect(within(chart).getByText('Test Furnace Upkeep')).toBeInTheDocument()

    await user.click(within(chart).getByRole('button', { name: 'Hide units under Operation' }))
    expect(within(chart).queryByText('Test Melting')).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Org chart' })).toHaveAttribute('aria-current', 'page')
  })

  it('builds a forest without dropping units whose parent is missing', () => {
    const orphan = { ...DEPT_NODE, public_id: 'orphan', parent_id: 'missing' }
    const forest = buildForest([...BASELINE_NODES, SUB_NODE, orphan] as TreeNode[])
    expect(forest.map((entry) => entry.node.public_id)).toContain('orphan')
    const operation = forest.find((entry) => entry.node.public_id === 'unit-ops')
    expect(operation?.children.map((c) => c.node.public_id)).toEqual(['unit-melt'])
  })

  it('links a unit to its employees in the directory', async () => {
    mockSignedIn(HR_ADMIN, structureRoutes())
    renderApp('/organisation/chart')
    const chart = await screen.findByRole('list', { name: 'Organisation units, top level first' })
    const links = within(chart).getAllByRole('link', { name: 'Employees' })
    expect(links.some((link) => link.getAttribute('href') === '/employees?unit=unit-ops')).toBe(true)
  })
})

describe('Import profile picker', () => {
  const ORG_PROFILE = {
    ...PROFILE,
    code: 'organisation',
    sections: [
      {
        kind: 'units',
        sheet_aliases: ['Organisation Units'],
        natural_key: ['unit_code'],
        fields: [{ name: 'unit_code', type: 'text', required: true, aliases: ['Unit Code'], reference: null }],
      },
    ],
  }

  it('preselects the organisation profile from the link and uploads with it', async () => {
    const created = job({ profile_code: 'organisation' })
    const api = mockSignedIn(
      TRAINING_ADMIN,
      importRoutes(created, {
        'GET /imports/profiles': reply([PROFILE, ORG_PROFILE]),
        'POST /imports': reply(created, 201),
      }),
    )
    const user = userEvent.setup()
    renderApp('/imports/new?profile=organisation')
    const choice = await screen.findByRole('radio', { name: /Organisation units/ })
    expect(choice).toBeChecked()
    expect(screen.getByRole('radio', { name: /Employees, assignments and reporting lines/ })).not.toBeChecked()
    expect(screen.getByText(/Existing units are matched by unit code/)).toBeInTheDocument()

    const file = new File(['synthetic'], 'units.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    })
    await user.upload(screen.getByLabelText('Excel workbook (.xlsx)'), file)
    await user.click(screen.getByRole('button', { name: 'Upload and inspect' }))
    await vi.waitFor(() => expect(api.requestsTo('POST /imports')[0]?.query.get('profile')).toBe('organisation'))
  })

  it('offers the structure page link only to users who may run the organisation import', async () => {
    mockSignedIn(TRAINING_ADMIN, structureRoutes())
    renderApp('/organisation')
    expect(await screen.findByRole('link', { name: 'Import units from Excel' })).toHaveAttribute(
      'href',
      '/imports/new?profile=organisation',
    )
  })
})
