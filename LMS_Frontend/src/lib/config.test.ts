import { describe, expect, it } from 'vitest'

import {
  DEFAULT_API_BASE_URL,
  DEFAULT_HEALTH_POLL_INTERVAL_MS,
  normaliseApiBaseUrl,
  parsePollInterval,
} from './config'

describe('normaliseApiBaseUrl', () => {
  it('defaults to the same-origin API path', () => {
    expect(normaliseApiBaseUrl(undefined)).toBe(DEFAULT_API_BASE_URL)
    expect(normaliseApiBaseUrl('   ')).toBe(DEFAULT_API_BASE_URL)
  })

  it('accepts paths and absolute URLs, removing trailing slashes', () => {
    expect(normaliseApiBaseUrl('/api/v1/')).toBe('/api/v1')
    expect(normaliseApiBaseUrl('http://localhost:8000/api/v1/')).toBe(
      'http://localhost:8000/api/v1',
    )
    expect(normaliseApiBaseUrl('https://lms.example.test/api/v1')).toBe(
      'https://lms.example.test/api/v1',
    )
  })

  it.each(['api/v1', '//evil.example/api', 'ftp://host/api', 'javascript:alert(1)'])(
    'rejects %s',
    (value) => {
      expect(() => normaliseApiBaseUrl(value)).toThrow(/Invalid VITE_API_BASE_URL/)
    },
  )
})

describe('parsePollInterval', () => {
  it('uses the default when unset', () => {
    expect(parsePollInterval(undefined)).toBe(DEFAULT_HEALTH_POLL_INTERVAL_MS)
    expect(parsePollInterval('')).toBe(DEFAULT_HEALTH_POLL_INTERVAL_MS)
  })

  it('accepts integers of at least 5000 ms', () => {
    expect(parsePollInterval('10000')).toBe(10_000)
  })

  it.each(['abc', '1000', '7500.5'])('rejects %s', (value) => {
    expect(() => parsePollInterval(value)).toThrow(/Invalid VITE_HEALTH_POLL_INTERVAL_MS/)
  })
})
