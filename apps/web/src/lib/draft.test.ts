import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readDraft, writeDraft } from './draft'

function fakeStorage(): Storage {
  const items = new Map<string, string>()
  return {
    getItem: (key) => items.get(key) ?? null,
    setItem: (key, value) => void items.set(key, value),
    removeItem: (key) => void items.delete(key),
    clear: () => items.clear(),
    key: (i) => [...items.keys()][i] ?? null,
    get length() {
      return items.size
    },
  }
}

describe('draft', () => {
  beforeEach(() => vi.stubGlobal('sessionStorage', fakeStorage()))
  afterEach(() => vi.unstubAllGlobals())

  it('keeps the offer list per campaign', () => {
    writeDraft(1, [18813, 2])
    writeDraft(2, [5])

    expect(readDraft(1)).toEqual([18813, 2])
    expect(readDraft(2)).toEqual([5])
  })

  it('keeps an empty list: the user removed every offer', () => {
    writeDraft(1, [])

    expect(readDraft(1)).toEqual([])
  })

  it('null removes the draft', () => {
    writeDraft(1, [18813])
    writeDraft(1, null)

    expect(readDraft(1)).toBeNull()
  })

  it.each(['not json', '"18813"', 'null', '[1, 1]', '[0]', '[1.5]', '{"a": 1}'])(
    'ignores a broken draft %s',
    (raw) => {
      sessionStorage.setItem('offer-draft:1', raw)

      expect(readDraft(1)).toBeNull()
    },
  )

  it('works without storage', () => {
    vi.stubGlobal('sessionStorage', undefined)

    expect(() => writeDraft(1, [1])).not.toThrow()
    expect(readDraft(1)).toBeNull()
  })
})
