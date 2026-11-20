// Форматирование для интерфейса на русском.
const regions = new Intl.DisplayNames(['ru'], { type: 'region' })

/** Код из Keitaro не проверяется: на неверном коде Intl бросает RangeError — тогда сам код. */
export function regionName(code: string): string {
  try {
    return regions.of(code) ?? code
  } catch {
    return code
  }
}

export const formatDateTime = new Intl.DateTimeFormat('ru', {
  dateStyle: 'medium',
  timeStyle: 'short',
}).format

export function pct(share: number | null): string {
  return share === null ? '—' : `${share}%`
}
