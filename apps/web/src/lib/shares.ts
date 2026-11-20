// Копия backend/app/domain/shares.py для мгновенного предпросмотра; тесты у обеих версий одинаковые.
export function distributeShares(count: number): number[] {
  if (count < 1) throw new Error('В потоке должен быть хотя бы один оффер')
  if (count > 100) throw new Error('Не больше 100 офферов в потоке: каждому нужен хотя бы 1%')
  const base = Math.floor(100 / count)
  return [...Array<number>(count - 1).fill(base), 100 - base * (count - 1)]
}
