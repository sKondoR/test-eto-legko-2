// Форматирование для интерфейса на русском.
const regions = new Intl.DisplayNames(['ru'], { type: 'region' })

export function regionName(code: string): string {
  return regions.of(code) ?? code
}

export const formatDateTime = new Intl.DateTimeFormat('ru', {
  dateStyle: 'medium',
  timeStyle: 'short',
}).format

export function pct(share: number | null): string {
  return share === null ? '—' : `${share}%`
}
