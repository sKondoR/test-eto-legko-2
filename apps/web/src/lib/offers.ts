// Логика редактора офферов без UI: превью долей, добавление, сравнение «было → станет».
import type { OfferShare } from './api'
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

export function addOffer(offerIds: number[], id: number): number[] {
  if (offerIds.includes(id)) throw new Error(`Оффер ${id} уже в потоке`)
  return [...offerIds, id]
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

/** Сохранение что-то поменяет в Keitaro: другой состав, порядок или неравные доли. */
export function hasChanges(current: OfferShare[], offerIds: number[]): boolean {
  const next = previewShares(offerIds)
  return (
    next.length !== current.length ||
    next.some((s, i) => s.offer_id !== current[i].offer_id || s.share !== current[i].share)
  )
}
