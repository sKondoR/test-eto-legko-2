<script lang="ts">
  // Создаётся заново на каждую кампанию ({#key} в App.svelte), поэтому campaignId не меняется.
  import { api, ApiError, type Editor, type OfferSummary } from '../lib/api'
  import { pct, regionName } from '../lib/format'
  import {
    addOffer,
    compareRows,
    hasChanges,
    MAX_OFFERS,
    parseOfferId,
    previewShares,
    segmentColors,
  } from '../lib/offers'
  import { notify, notifyError } from '../lib/toasts.svelte'
  import History from './History.svelte'
  import OfferPicker from './OfferPicker.svelte'
  import SplitBar from './SplitBar.svelte'

  let {
    campaignId,
    prefix,
    offers,
  }: { campaignId: number; prefix: string; offers: OfferSummary[] } = $props()

  let data = $state<Editor | null>(null)
  let offerIds = $state<number[]>([])
  let offerText = $state('')
  let saving = $state(false)

  // Set: в потоке, правленом вручную, оффер может повторяться; сохранение это починит.
  const original = $derived([...new Set(data?.offers.map((s) => s.offer_id))])
  const preview = $derived(previewShares(offerIds))
  // Без правки показываем доли как есть: ровные 34/33/33 сохранение не трогает.
  const rows = $derived.by(() => {
    if (!data) return []
    if (changed) return compareRows(data.offers, offerIds)
    return data.offers.map((s) => ({
      ...s,
      before: s.share,
      after: s.share,
      status: 'kept' as const,
    }))
  })
  const changed = $derived(data !== null && hasChanges(data.offers, offerIds))
  // Пользователь менял список: только тогда есть что отменять.
  const edited = $derived(offerIds.join() !== original.join())
  const colors = $derived(segmentColors([...original, ...offerIds]))
  const offerNames = $derived(new Map(offers.map((o) => [o.id, o.name])))
  const warning = $derived.by(() => {
    const disabled = data?.disabled_offer_ids ?? []
    if (disabled.length === 1)
      return `Оффер ${disabled[0]} выключен в Keitaro: доля у него есть, а трафик он не получает. Включить оффер можно только в админке Keitaro.`
    if (disabled.length > 1)
      return `Офферы ${disabled.join(', ')} выключены в Keitaro: доля у них есть, а трафик они не получают. Включить оффер можно только в админке Keitaro.`
    if (data && !data.is_even)
      return 'Доли в Keitaro неравные — их правили вручную. При сохранении они станут равными.'
    return null
  })

  /** keepEdits — после 409 оставить правку пользователя поверх свежих данных. */
  async function load(keepEdits = false): Promise<void> {
    try {
      data = await api.editor(campaignId)
      if (!keepEdits) offerIds = original
    } catch (error) {
      notifyError(error)
    }
  }

  function add(event: SubmitEvent): void {
    event.preventDefault()
    const id = parseOfferId(offerText)
    if (id === null) {
      notify('error', 'Введите ID оффера: целое число, например 18813')
    } else if (offerIds.length >= MAX_OFFERS) {
      notify('error', `В потоке не больше ${MAX_OFFERS} офферов: каждому нужен хотя бы 1%`)
    } else if (offerIds.includes(id)) {
      notify('error', `Оффер ${id} уже в потоке`)
    } else {
      offerIds = addOffer(offerIds, id)
      offerText = ''
    }
  }

  function toggle(id: number, removed: boolean): void {
    offerIds = removed ? addOffer(offerIds, id) : offerIds.filter((i) => i !== id)
  }

  async function save(): Promise<void> {
    if (!data) return
    saving = true
    try {
      await api.saveOffers(campaignId, { expected: data.offers, offer_ids: offerIds })
      notify('success', 'Офферы сохранены')
      // Ждём свежие данные: иначе повторный клик уйдёт со старым expected и получит 409.
      await load()
    } catch (error) {
      notifyError(error)
      if (error instanceof ApiError && error.status === 409) await load(true)
    } finally {
      saving = false
    }
  }

  load()
</script>

{#if data === null}
  <p class="text-muted">Загружаю кампанию…</p>
{:else}
  <article class="flex flex-col gap-8">
    <header>
      <h1 class="text-2xl break-all">
        <span class="text-muted">{prefix}</span><span class="font-semibold">
          {data.name.slice(prefix.length)}
        </span>
      </h1>
      <p class="mt-1 text-muted">
        Поток 1 отправляет трафик из
        {#each data.geo as code, i (code)}{i ? ', ' : ''}<span
            class="text-ink"
            title={regionName(code)}
          >
            {code}
          </span>{/each}
        на google.com. Редактор меняет только поток 2 — офферы.
      </p>
    </header>

    <section class="flex flex-col gap-4" aria-labelledby="offers-title">
      <h2 id="offers-title" class="text-lg font-semibold">Офферы потока 2</h2>

      {#if changed}
        <SplitBar shares={data.offers} {colors} label="Сейчас в Keitaro" size="sm" />
      {/if}
      <SplitBar
        shares={changed ? preview : data.offers}
        {colors}
        label={changed ? 'После сохранения' : 'Сейчас в Keitaro'}
      />

      {#if warning}
        <p class="rounded-md border-l-4 border-amber bg-white px-4 py-3 text-sm">{warning}</p>
      {/if}

      <table class="w-full border-collapse text-left">
        <thead class="text-sm text-muted">
          <tr class="border-b border-line">
            <th class="w-full py-2 font-normal">Оффер</th>
            <th class="py-2 pl-3 text-right font-normal whitespace-nowrap">Было</th>
            <th class="py-2 pl-3 text-right font-normal whitespace-nowrap">Станет</th>
            <th class="py-2"><span class="sr-only">Действие</span></th>
          </tr>
        </thead>
        <tbody>
          {#each rows as row (row.offer_id)}
            {@const name = offerNames.get(row.offer_id) ?? `Оффер ${row.offer_id}`}
            {@const removed = row.status === 'removed'}
            <tr class={['border-b border-line', removed && 'text-muted']}>
              <td class="max-w-0 py-2.5">
                <span class="flex items-center gap-2.5">
                  <span
                    class={['size-3 shrink-0 rounded-sm', removed && 'bg-line']}
                    style:background-color={removed ? undefined : colors.get(row.offer_id)}
                  ></span>
                  <span class={['min-w-0 truncate', removed && 'line-through']} title={name}>
                    {name}
                  </span>
                  {#if row.status === 'added'}<span class="text-sm text-cobalt">новый</span>{/if}
                  {#if data.disabled_offer_ids.includes(row.offer_id)}
                    <span class="text-sm text-amber">выключен</span>
                  {/if}
                </span>
              </td>
              <td class="py-2.5 pl-3 text-right whitespace-nowrap tabular-nums">
                {pct(row.before)}
              </td>
              <td class="py-2.5 pl-3 text-right font-semibold whitespace-nowrap tabular-nums">
                {pct(row.after)}
              </td>
              <td class="py-2.5 pl-3 text-right">
                <button
                  type="button"
                  class={['text-sm hover:underline', removed ? 'text-cobalt' : 'text-danger']}
                  onclick={() => toggle(row.offer_id, removed)}
                >
                  {removed ? 'Вернуть' : 'Убрать'}
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>

      <form class="flex gap-2" onsubmit={add}>
        <div class="flex-1">
          <label for="add-offer" class="sr-only">Добавить оффер</label>
          <OfferPicker id="add-offer" {offers} bind:value={offerText} />
        </div>
        <button
          type="submit"
          class="rounded-md border border-line bg-white px-4 py-2 font-medium hover:bg-fog disabled:opacity-50"
          disabled={offerText.trim() === ''}
        >
          Добавить
        </button>
      </form>

      <div class="flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="btn-primary"
          disabled={!changed || offerIds.length === 0 || saving}
          onclick={save}
        >
          {saving ? 'Сохраняю…' : 'Сохранить офферы'}
        </button>
        {#if edited}
          <button
            type="button"
            class="rounded-md px-3 py-2.5 text-muted hover:text-ink"
            disabled={saving}
            onclick={() => (offerIds = original)}
          >
            Отменить правку
          </button>
        {/if}
        {#if offerIds.length === 0}
          <p class="text-sm text-danger">Оставьте в потоке хотя бы один оффер</p>
        {/if}
      </div>
    </section>

    <History entries={data.history} />
  </article>
{/if}
