// Типизированный доступ к нашему /api. Типы генерируются из OpenAPI бэкенда (pnpm gen:api).
import type { components } from '@app/api-types'

type Schemas = components['schemas']
export type Config = Schemas['ConfigOut']
export type OfferSummary = Schemas['OfferSummary']
export type CampaignSummary = Schemas['CampaignSummary']
export type OfferShare = Schemas['OfferShare']
export type Editor = Schemas['EditorOut']

/** Ошибка API: detail — готовый текст для пользователя, status — HTTP-код. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError('Нет связи с бэкендом. Проверьте, что он запущен', 0)
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail : null
    throw new ApiError(detail ?? `Бэкенд ответил ошибкой ${response.status}`, response.status)
  }
  return data as T
}

export const api = {
  config: () => request<Config>('GET', '/config'),
  offers: () => request<OfferSummary[]>('GET', '/offers'),
  campaigns: () => request<CampaignSummary[]>('GET', '/campaigns'),
  createCampaign: (body: Schemas['CampaignCreateIn']) =>
    request<Schemas['CampaignCreatedOut']>('POST', '/campaigns', body),
  editor: (id: number) => request<Editor>('GET', `/campaigns/${id}`),
  saveOffers: (id: number, body: Schemas['OffersSaveIn']) =>
    request<Schemas['OffersSavedOut']>('PUT', `/campaigns/${id}/offers`, body),
}
