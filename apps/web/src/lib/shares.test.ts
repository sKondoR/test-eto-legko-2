import { describe, expect, it } from 'vitest'
import { distributeShares } from './shares'

describe('distributeShares', () => {
  it.each([
    [1, [100]],
    [2, [50, 50]],
    [3, [33, 33, 34]],
    [7, [14, 14, 14, 14, 14, 14, 16]],
  ])('splits %i offers evenly with remainder on last', (count, expected) => {
    expect(distributeShares(count)).toEqual(expected)
  })

  it('always sums to 100', () => {
    for (let count = 1; count <= 100; count++) {
      expect(distributeShares(count).reduce((a, b) => a + b, 0)).toBe(100)
    }
  })

  it('rejects empty offer list', () => {
    expect(() => distributeShares(0)).toThrow()
  })

  it('rejects more offers than percent points', () => {
    expect(distributeShares(100)).toEqual(Array(100).fill(1))
    expect(() => distributeShares(101)).toThrow()
  })
})
