// Логика редактора офферов без UI: превью долей, добавление, сравнение «было → станет».
import type { Editor, OfferShare } from './api'
import { distributeShares } from './shares'

export type RowStatus = 'kept' | 'added' | 'removed'

export interface Row {
  offer_id: number
  before: number | null
  after: number | null
  status: RowStatus
}

export function previewShares(offerIds: number[]): OfferShare[] {
  if (offerIds.length === 0) return []
  const split = distributeShares(offerIds.length)
  return offerIds.map((offer_id, i) => ({ offer_id, share: split[i] }))
}

/** Оффер, который уже в потоке, не добавляется второй раз. */
export function addOffer(offerIds: number[], id: number): number[] {
  return offerIds.includes(id) ? offerIds : [...offerIds, id]
}

const PALETTE_SIZE = 5
/** Больше офферов не делится: каждому нужен хотя бы 1% (distributeShares). */
export const MAX_OFFERS = 100

/** Цвет закреплён за оффером в порядке первого появления: один и тот же в полосах и таблице. */
export function segmentColors(offerIds: number[]): Map<number, string> {
  const order = [...new Set(offerIds)]
  return new Map(order.map((id, i) => [id, `var(--color-seg-${(i % PALETTE_SIZE) + 1})`]))
}

/** ID из поля ввода: число или строка списка офферов вида «18813 Flexacil…». */
export function parseOfferId(text: string): number | null {
  const match = /^\s*(\d+)(\s|$)/.exec(text)
  const id = match ? Number(match[1]) : 0
  return id > 0 ? id : null
}

export function compareRows(current: OfferShare[], offerIds: number[]): Row[] {
  const before = new Map(current.map((s) => [s.offer_id, s.share]))
  const kept = previewShares(offerIds).map(({ offer_id, share }) => ({
    offer_id,
    before: before.get(offer_id) ?? null,
    after: share,
    status: (before.has(offer_id) ? 'kept' : 'added') as RowStatus,
  }))
  const removed = current
    .filter((s) => !offerIds.includes(s.offer_id))
    .map((s) => ({
      offer_id: s.offer_id,
      before: s.share,
      after: null,
      status: 'removed' as const,
    }))
  return [...kept, ...removed]
}

/** Доли поровну, остаток у любого оффера — копия is_even_split бэкенда. */
export function isEvenSplit(shares: OfferShare[]): boolean {
  const ids = new Set(shares.map((s) => s.offer_id))
  if (shares.length < 1 || shares.length > MAX_OFFERS || ids.size !== shares.length) return false
  const sorted = (xs: number[]) => [...xs].sort((a, b) => a - b).join()
  return sorted(shares.map((s) => s.share)) === sorted(distributeShares(shares.length))
}

/** Сохранение что-то поменяет: другой состав или порядок офферов, либо доли не поровну. */
/** Поток в Keitaro тот же: офферы с долями, выключенные офферы и страны потока 1. История
 *  меняется только вместе с офферами, поэтому её не сравниваем. */
export function sameFlow(
  a: Pick<Editor, 'offers' | 'disabled_offer_ids' | 'geo'>,
  b: Pick<Editor, 'offers' | 'disabled_offer_ids' | 'geo'>,
): boolean {
  const key = (e: typeof a) => JSON.stringify([e.offers, e.disabled_offer_ids, e.geo])
  return key(a) === key(b)
}

export function hasChanges(current: OfferShare[], offerIds: number[]): boolean {
  const sameIds =
    current.length === offerIds.length && current.every((s, i) => s.offer_id === offerIds[i])
  return !sameIds || !isEvenSplit(current)
}
