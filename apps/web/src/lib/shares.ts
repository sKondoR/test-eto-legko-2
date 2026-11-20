// Копия backend/app/domain/shares.py для мгновенного предпросмотра; тесты у обеих версий одинаковые.
export function distributeShares(count: number): number[] {
  if (count < 1) throw new Error('В потоке должен быть хотя бы один оффер')
  const base = Math.floor(100 / count)
  return [...Array<number>(count - 1).fill(base), 100 - base * (count - 1)]
}
