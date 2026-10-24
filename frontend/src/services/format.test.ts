import { describe, expect, it } from 'vitest'
import { labelName, pct, timeAgo } from './format'

describe('format helpers', () => {
  it('formats percentages and missing values', () => {
    expect(pct(0.9672)).toBe('96.7%')
    expect(pct(null)).toBe('–')
  })
  it('describes elapsed time', () => {
    const now = Date.parse('2026-01-01T00:10:00Z')
    expect(timeAgo('2026-01-01T00:09:30Z', now)).toBe('30s ago')
    expect(timeAgo('2026-01-01T00:00:00Z', now)).toBe('10m ago')
    expect(timeAgo(null, now)).toBe('no activity yet')
  })
  it('names known labels and falls back for unknown ones', () => {
    expect(labelName('brute_force')).toBe('Credential brute force')
    expect(labelName('some_new_label')).toBe('some new label')
  })
})
