<script lang="ts">
  import { api, ApiError, type Editor, type OfferSummary } from '../lib/api'
  import { addOffer, compareRows, hasChanges, parseOfferId, previewShares } from '../lib/offers'
  import { notify, notifyError } from '../lib/toasts.svelte'
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

  const offerNames = $derived(new Map(offers.map((o) => [o.id, o.name])))
  const rows = $derived(data ? compareRows(data.offers, offerIds) : [])
  const changed = $derived(data !== null && hasChanges(data.offers, offerIds))
  // Цвет закреплён за оффером: один и тот же в обеих полосах и в таблице.
  const colors = $derived.by(() => {
    const order = [...new Set([...(data?.offers.map((s) => s.offer_id) ?? []), ...offerIds])]
    return new Map(order.map((id, i) => [id, `var(--seg-${(i % 5) + 1})`]))
  })
  const names = new Intl.DisplayNames(['ru'], { type: 'region' })
  const dateFormat = new Intl.DateTimeFormat('ru', { dateStyle: 'medium', timeStyle: 'short' })

  /** keepEdits — после 409 оставить правку пользователя поверх свежих данных. */
  async function load(keepEdits = false): Promise<void> {
    const id = campaignId
    try {
      const fresh = await api.editor(id)
      if (id !== campaignId) return // пока грузилось, выбрали другую кампанию
      data = fresh
      if (!keepEdits) offerIds = fresh.offers.map((s) => s.offer_id)
    } catch (error) {
      notifyError(error)
    }
  }

  $effect(() => {
    void campaignId
    data = null
    offerText = ''
    load()
  })

  function add(): void {
    const id = parseOfferId(offerText)
    if (id === null) {
      notify('error', 'Введите ID оффера: целое число, например 18813')
      return
    }
    try {
      offerIds = addOffer(offerIds, id)
      offerText = ''
    } catch (error) {
      notifyError(error)
    }
  }

  async function save(): Promise<void> {
    if (!data) return
    saving = true
    try {
      await api.saveOffers(campaignId, { expected: data.offers, offer_ids: offerIds })
      notify('success', 'Офферы сохранены')
      await load()
    } catch (error) {
      notifyError(error)
      if (error instanceof ApiError && error.status === 409) await load(true)
    } finally {
      saving = false
    }
  }

  function shareLine(shares: { share: number }[]): string {
    return shares.length ? shares.map((s) => s.share).join(' / ') : 'пусто'
  }
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
            title={names.of(code)}
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
        shares={previewShares(offerIds)}
        {colors}
        label={changed ? 'После сохранения' : 'Сейчас в Keitaro'}
      />

      {#if data.disabled_offer_ids.length > 0}
        <p class="rounded-md border-l-4 border-amber bg-white px-4 py-3 text-sm">
          {#if data.disabled_offer_ids.length === 1}
            Оффер {data.disabled_offer_ids[0]} выключен в Keitaro: доля у него есть, а трафик он не получает.
          {:else}
            Офферы {data.disabled_offer_ids.join(', ')} выключены в Keitaro: доля у них есть, а трафик
            они не получают.
          {/if}
          Включить оффер можно только в админке Keitaro.
        </p>
      {:else if !data.is_even}
        <p class="rounded-md border-l-4 border-amber bg-white px-4 py-3 text-sm">
          Доли в Keitaro неравные — их правили вручную. При сохранении они станут равными.
        </p>
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
            <tr class={['border-b border-line', row.status === 'removed' && 'text-muted']}>
              <td class="max-w-0 py-2.5">
                <span class="flex items-center gap-2.5">
                  <span
                    class="size-3 shrink-0 rounded-sm"
                    style:background-color={row.status === 'removed'
                      ? 'var(--color-line)'
                      : colors.get(row.offer_id)}
                  ></span>
                  <span
                    class={['min-w-0 truncate', row.status === 'removed' && 'line-through']}
                    title={name}
                  >
                    {name}
                  </span>
                  {#if row.status === 'added'}<span class="text-sm text-cobalt">новый</span>{/if}
                  {#if data.disabled_offer_ids.includes(row.offer_id)}
                    <span class="text-sm text-amber">выключен</span>
                  {/if}
                </span>
              </td>
              <td class="py-2.5 pl-3 text-right whitespace-nowrap tabular-nums">
                {row.before ?? '—'}{row.before === null ? '' : '%'}
              </td>
              <td class="py-2.5 pl-3 text-right font-semibold whitespace-nowrap tabular-nums">
                {row.after ?? '—'}{row.after === null ? '' : '%'}
              </td>
              <td class="py-2.5 pl-3 text-right">
                {#if row.status === 'removed'}
                  <button
                    type="button"
                    class="text-sm text-cobalt hover:underline"
                    onclick={() => (offerIds = addOffer(offerIds, row.offer_id))}
                  >
                    Вернуть
                  </button>
                {:else}
                  <button
                    type="button"
                    class="text-sm text-danger hover:underline"
                    onclick={() => (offerIds = offerIds.filter((id) => id !== row.offer_id))}
                  >
                    Убрать
                  </button>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>

      <div class="flex gap-2">
        <div class="flex-1">
          <label for="add-offer" class="sr-only">Добавить оффер</label>
          <OfferPicker
            id="add-offer"
            {offers}
            bind:value={offerText}
            onkeydown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                add()
              }
            }}
          />
        </div>
        <button
          type="button"
          class="rounded-md border border-line bg-white px-4 py-2 font-medium hover:bg-fog disabled:opacity-50"
          disabled={offerText.trim() === ''}
          onclick={add}
        >
          Добавить
        </button>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="rounded-md bg-cobalt px-5 py-2.5 font-medium text-white hover:bg-cobalt-dark disabled:cursor-not-allowed disabled:opacity-50"
          disabled={!changed || offerIds.length === 0 || saving}
          onclick={save}
        >
          {saving ? 'Сохраняю…' : 'Сохранить офферы'}
        </button>
        {#if changed}
          <button
            type="button"
            class="rounded-md px-3 py-2.5 text-muted hover:text-ink"
            disabled={saving}
            onclick={() => data && (offerIds = data.offers.map((s) => s.offer_id))}
          >
            Отменить правку
          </button>
        {/if}
        {#if offerIds.length === 0}
          <p class="text-sm text-danger">Оставьте в потоке хотя бы один оффер</p>
        {/if}
      </div>
    </section>

    <section aria-labelledby="history-title">
      <h2 id="history-title" class="mb-3 text-lg font-semibold">История правок</h2>
      {#if data.history.length === 0}
        <p class="text-sm text-muted">Через приложение офферы этой кампании ещё не меняли.</p>
      {:else}
        <ol class="flex flex-col">
          {#each data.history as entry (entry.changed_at)}
            <li
              class="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-line py-2.5 text-sm"
            >
              <time
                class="w-44 shrink-0 whitespace-nowrap text-muted tabular-nums"
                datetime={entry.changed_at}
              >
                {dateFormat.format(new Date(entry.changed_at))}
              </time>
              <span class="tabular-nums">
                {shareLine(entry.before)} <span class="text-muted">→</span>
                <span class="font-medium">{shareLine(entry.after)}</span>
              </span>
              <span class="flex gap-2">
                {#each entry.added as id (id)}<span class="text-cobalt">+{id}</span>{/each}
                {#each entry.removed as id (id)}<span class="text-danger">−{id}</span>{/each}
              </span>
            </li>
          {/each}
        </ol>
      {/if}
    </section>
  </article>
{/if}
