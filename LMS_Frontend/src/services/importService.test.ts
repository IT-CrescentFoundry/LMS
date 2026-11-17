import { afterEach, describe, expect, it, vi } from 'vitest'

import { setCsrfToken } from '../lib/apiClient'
import { ERROR_ROW, job, JOB_ID } from '../test/importFixtures'
import { importService, parseJob, parseRow } from './importService'

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('import parsers', () => {
  it('copy known fields only', () => {
    const parsed = parseJob({ ...job(), stored_path: 'C:/secret/path.xlsx', extra: 1 })
    expect(parsed).not.toHaveProperty('stored_path')
    expect(parsed).not.toHaveProperty('extra')
    expect(parsed.workbook[0].headers[2]).toEqual({
      column: 'C',
      index: 3,
      text: 'CTC',
      excluded: true,
      suggested_field: null,
    })
  })

  it('reduce row values to plain values', () => {
    const row = parseRow({ ...ERROR_ROW, values: { full_name: 'Test Person Two', nested: { a: 1 } } })
    expect(row.values).toEqual({ full_name: 'Test Person Two', nested: null })
  })

  it('reject an unknown job status', () => {
    expect(() => parseJob({ ...job(), status: 'published' })).toThrow(TypeError)
  })
})

describe('file transfers', () => {
  it('download the error report as a file, sending no request body', async () => {
    const fetchMock = vi.fn(async () => new Response('xlsx-bytes', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    const download = await importService.downloadErrorReport(JOB_ID)
    expect(download.filename).toBe(`lms-import-${JOB_ID}-issues.xlsx`)
    expect(download.blob.size).toBe('xlsx-bytes'.length)
    expect(fetchMock.mock.calls[0]).toEqual([`/api/v1/imports/${JOB_ID}/error-report`, expect.objectContaining({ method: 'GET', body: undefined })])
  })

  it('report a failed download by its error code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ error: { code: 'import_job_not_found', message: 'x' } }), { status: 404 })),
    )
    await expect(importService.downloadErrorReport(JOB_ID)).rejects.toMatchObject({ status: 404, code: 'import_job_not_found' })
  })

  it('never let extra headers replace the CSRF token', async () => {
    setCsrfToken('real-token')
    const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(
      async () => new Response(JSON.stringify(job()), { status: 201 }),
    )
    vi.stubGlobal('fetch', fetchMock)
    await importService.upload('employees', new File(['x'], 'a.xlsx'))
    const headers = fetchMock.mock.calls[0][1]?.headers as Record<string, string>
    expect(headers['X-CSRF-Token']).toBe('real-token')
    expect(headers['X-File-Name']).toBe('a.xlsx')
  })
})
