// Списки офферов кампании в sessionStorage, переживают перезагрузку вкладки (F5):
// - draft — несохранённая правка. Пустой список — тоже правка: пользователь убрал все офферы
//   (сохранить её нельзя, но и терять тоже);
// - seen — все офферы, которые редактор видел в потоке с последнего сохранения: кого из них
//   нет в потоке сейчас, того удалили в Keitaro (см. goneRows).
// sessionStorage может быть недоступен (приватный режим, запрет сайта): тогда списков просто нет.
import { MAX_OFFERS } from './offers'

type List = 'draft' | 'seen'

const key = (list: List, campaignId: number) => `offer-${list}:${campaignId}`

function readIds(list: List, campaignId: number): number[] | null {
  try {
    const ids: unknown = JSON.parse(sessionStorage.getItem(key(list, campaignId)) ?? 'null')
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

/** null — списка нет, он удаляется. */
function writeIds(list: List, campaignId: number, offerIds: number[] | null): void {
  try {
    if (offerIds) sessionStorage.setItem(key(list, campaignId), JSON.stringify(offerIds))
    else sessionStorage.removeItem(key(list, campaignId))
  } catch {
    // Без хранилища списки живут до перезагрузки.
  }
}

export const readDraft = (campaignId: number) => readIds('draft', campaignId)
export const writeDraft = (campaignId: number, ids: number[] | null) =>
  writeIds('draft', campaignId, ids)
export const readSeen = (campaignId: number) => readIds('seen', campaignId)
export const writeSeen = (campaignId: number, ids: number[]) => writeIds('seen', campaignId, ids)
