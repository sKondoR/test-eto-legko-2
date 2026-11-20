import { describe, expect, it } from 'vitest'
import {
  addOffer,
  compareRows,
  goneRows,
  hasChanges,
  parseOfferId,
  previewShares,
  sameFlow,
  segmentColors,
} from './offers'

const shares = (...pairs: [number, number][]) =>
  pairs.map(([offer_id, share]) => ({ offer_id, share }))

describe('previewShares', () => {
  it('делит поровну, остаток у последнего', () => {
    expect(previewShares([5, 6, 7])).toEqual(shares([5, 33], [6, 33], [7, 34]))
  })

  it('пустой список — пустое превью', () => {
    expect(previewShares([])).toEqual([])
  })
})

describe('addOffer', () => {
  it('добавляет в конец', () => {
    expect(addOffer([1, 2], 3)).toEqual([1, 2, 3])
  })

  it('повторный оффер не добавляет', () => {
    expect(addOffer([1, 2], 2)).toEqual([1, 2])
  })
})

describe('parseOfferId', () => {
  it.each([
    ['18813', 18813],
    [' 7 ', 7],
    ['18813 Flexacil [JOINT-PE]', 18813],
  ])('%s → %d', (text, id) => {
    expect(parseOfferId(text)).toBe(id)
  })

  it.each(['', 'abc', '0', '-3', '1.5'])('%s → null', (text) => {
    expect(parseOfferId(text)).toBeNull()
  })
})

describe('compareRows', () => {
  it('показывает было → станет, новые и убранные офферы', () => {
    expect(compareRows(shares([1, 70], [2, 30]), [2, 3])).toEqual([
      { offer_id: 2, before: 30, after: 50, status: 'kept' },
      { offer_id: 3, before: null, after: 50, status: 'added' },
      { offer_id: 1, before: 70, after: null, status: 'removed' },
    ])
  })
})

describe('hasChanges', () => {
  it('те же офферы с равными долями — изменений нет', () => {
    expect(hasChanges(shares([1, 50], [2, 50]), [1, 2])).toBe(false)
  })

  it('те же офферы с ручными долями — сохранение их выровняет', () => {
    expect(hasChanges(shares([1, 70], [2, 30]), [1, 2])).toBe(true)
  })

  it('ровные доли с остатком не у последнего — не изменение, как is_even_split на бэкенде', () => {
    expect(hasChanges(shares([1, 34], [2, 33], [3, 33]), [1, 2, 3])).toBe(false)
  })

  it('повтор оффера из Keitaro — изменение: сохранение починит поток', () => {
    expect(hasChanges(shares([1, 50], [1, 50]), [1])).toBe(true)
  })

  it('другой порядок — это изменение: остаток уходит другому офферу', () => {
    expect(hasChanges(shares([1, 33], [2, 33], [3, 34]), [3, 2, 1])).toBe(true)
  })
})

describe('segmentColors', () => {
  it('цвет закреплён за оффером в порядке первого появления, палитра по кругу', () => {
    const colors = segmentColors([1, 2, 3, 4, 5, 6, 2])
    expect(colors.get(1)).toBe('var(--color-seg-1)')
    expect(colors.get(2)).toBe('var(--color-seg-2)')
    expect(colors.get(6)).toBe('var(--color-seg-1)')
    expect(colors.size).toBe(6)
  })
})

describe('sameFlow', () => {
  const flow = { offers: shares([1, 50], [2, 50]), disabled_offer_ids: [] as number[], geo: ['AU'] }

  it('equal flows are the same', () => {
    expect(sameFlow(flow, structuredClone(flow))).toBe(true)
  })

  it.each([
    ['share', { offers: shares([1, 34], [2, 66]) }],
    ['offer order', { offers: shares([2, 50], [1, 50]) }],
    ['disabled offers', { disabled_offer_ids: [2] }],
    ['geo', { geo: ['AU', 'RO'] }],
  ])('a changed %s is a different flow', (_, change) => {
    expect(sameFlow(flow, { ...flow, ...change })).toBe(false)
  })
})

describe('goneRows', () => {
  it('shows seen offers that are neither in Keitaro nor returned by the user', () => {
    expect(goneRows([2, 3, 4], shares([3, 100]), [3, 4])).toEqual([
      { offer_id: 2, before: null, after: null, status: 'gone' },
    ])
  })
})
