// Черновик несохранённой правки офферов: переживает перезагрузку вкладки (F5).
// Пустой список — тоже правка: пользователь убрал все офферы (сохранить её нельзя, но и терять тоже).
// sessionStorage может быть недоступен (приватный режим, запрет сайта): тогда черновика просто нет.
import { MAX_OFFERS } from './offers'

const key = (campaignId: number) => `offer-draft:${campaignId}`

export function readDraft(campaignId: number): number[] | null {
  try {
    const ids: unknown = JSON.parse(sessionStorage.getItem(key(campaignId)) ?? 'null')
    const valid =
      Array.isArray(ids) &&
      ids.length <= MAX_OFFERS &&
      ids.every((id) => Number.isInteger(id) && id > 0) &&
      new Set(ids).size === ids.length
    return valid ? ids : null
  } catch {
    return null
  }
}

/** null — правки нет, черновик удаляется. */
export function writeDraft(campaignId: number, offerIds: number[] | null): void {
  try {
    if (offerIds) sessionStorage.setItem(key(campaignId), JSON.stringify(offerIds))
    else sessionStorage.removeItem(key(campaignId))
  } catch {
    // Без хранилища правка живёт до перезагрузки, как раньше.
  }
}
