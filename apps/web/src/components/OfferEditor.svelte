<script lang="ts">
  // Создаётся заново на каждую кампанию ({#key} в App.svelte), поэтому campaignId не меняется.
  import { api, ApiError, type Editor, type OfferSummary } from '../lib/api'
  import { readDraft, writeDraft } from '../lib/draft'
  import { formatTime, pct, regionName } from '../lib/format'
  import {
    addOffer,
    compareRows,
    hasChanges,
    MAX_OFFERS,
    parseOfferId,
    previewShares,
    sameFlow,
    segmentColors,
  } from '../lib/offers'
  import { errorText, notify, notifyError } from '../lib/toasts.svelte'
  import History from './History.svelte'
  import Icon from './Icon.svelte'
  import OfferPicker from './OfferPicker.svelte'
  import SplitBar from './SplitBar.svelte'
  import Warning from './Warning.svelte'

  let {
    campaignId,
    prefix,
    offers,
  }: { campaignId: number; prefix: string; offers: OfferSummary[] } = $props()

  let data = $state<Editor | null>(null)
  let offerIds = $state<number[]>([])
  let offerText = $state('')
  let saving = $state(false)
  // Идёт фоновое обновление (по таймеру или при возврате на вкладку).
  let background = false
  // Иконка «Обновить» крутится только по кнопке: фоновое обновление раз в 10 секунд её не трогает.
  let spinning = $state(false)
  // Поток в Keitaro изменился, пока есть несохранённая правка: фон её не трогает, только сообщает.
  let outdated = $state(false)
  let refreshError = $state<string | null>(null)
  // Номер последнего запроса кампании: ответ более раннего запроса устарел и отбрасывается.
  let latest = 0
  let loadedAt = $state<Date | null>(null)

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

  // Keitaro не сообщает о правках в админке: перечитываем кампанию по таймеру, при возврате
  // на вкладку и по кнопке «Обновить».
  const REFRESH_MS = 10_000

  async function fetchEditor(): Promise<Editor | null> {
    const request = ++latest
    try {
      const fresh = await api.editor(campaignId)
      return request === latest ? fresh : null
    } catch (error) {
      // Ошибка устаревшего запроса тоже не в счёт: более новый запрос уже идёт или прошёл.
      if (request === latest) throw error
      return null
    }
  }

  /** keepEdits — оставить правку пользователя поверх свежих данных. */
  function apply(fresh: Editor, keepEdits: boolean): void {
    const first = data === null
    data = fresh
    loadedAt = new Date()
    outdated = false
    refreshError = null
    if (keepEdits) return
    const draft = first ? readDraft(campaignId) : null
    if (draft && draft.join() !== original.join()) {
      // После F5 возвращаем несохранённую правку. Она ляжет на свежие данные без 409, поэтому
      // просим проверить её перед сохранением.
      offerIds = draft
      notify('warning', 'Восстановлена несохранённая правка — проверьте её перед сохранением')
    } else {
      offerIds = original
    }
  }

  async function load(keepEdits = false): Promise<void> {
    try {
      const fresh = await fetchEditor()
      if (fresh) apply(fresh, keepEdits)
    } catch (error) {
      notifyError(error)
      refreshError = errorText(error)
    }
  }

  /** Несохранённую правку не трогает. Фоновое обновление (manual = false) не подставляет
   *  свежие данные под правку: от data берётся expected, и сохранение должно получить 409.
   *  Ручное обновление идёт и поверх фонового: ответ фонового тогда отбрасывается.
   *  Если первая загрузка не удалась (data === null), обновление загружает кампанию заново. */
  async function refresh(manual: boolean): Promise<void> {
    if (saving || spinning || (!manual && background)) return
    // Первая загрузка ещё идёт: фоновый запрос перебил бы её ответ. Фон подхватывает кампанию,
    // только если первая загрузка упала.
    if (!manual && !data && !refreshError) return
    if (manual) spinning = true
    else background = true
    try {
      const fresh = await fetchEditor()
      if (!fresh || saving) return
      if (!data) return apply(fresh, false)
      refreshError = null
      // Поток тот же: data не трогаем, чтобы тик таймера не перерисовывал редактор.
      if (sameFlow(fresh, data)) {
        loadedAt = new Date()
        outdated = false
        if (manual) notify('success', 'В Keitaro ничего не изменилось')
        return
      }
      if (!manual && edited) {
        outdated = true
        return
      }
      const keepEdits = edited
      apply(fresh, keepEdits)
      if (keepEdits) {
        notify('warning', 'Поток изменили в Keitaro. Ваша правка осталась — проверьте её')
      } else {
        notify('success', 'Офферы обновлены из Keitaro')
      }
    } catch (error) {
      if (manual) notifyError(error)
      else refreshError = errorText(error)
    } finally {
      if (manual) spinning = false
      else background = false
    }
  }

  function refreshIfVisible(): void {
    if (document.visibilityState === 'visible') void refresh(false)
  }

  // Черновик правки в sessionStorage: переживает F5, пропадает после сохранения или отмены.
  $effect(() => {
    if (data) writeDraft(campaignId, edited ? offerIds : null)
  })

  $effect(() => {
    const timer = setInterval(refreshIfVisible, REFRESH_MS)
    return () => clearInterval(timer)
  })

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
  {#if refreshError}
    <p class="text-danger">Не удалось загрузить кампанию: {refreshError}</p>
    <p class="mt-1 text-sm text-muted">Редактор попробует снова через 10 секунд.</p>
    <button
      type="button"
      class="btn-secondary mt-4 px-4 py-2 font-medium"
      disabled={spinning}
      onclick={() => refresh(true)}
    >
      Повторить
    </button>
  {:else}
    <p class="text-muted">Загружаю кампанию…</p>
  {/if}
{:else}
  <article class="flex flex-col gap-8">
    <header>
      <div class="flex items-start justify-between gap-4">
        <h1 class="text-2xl break-all">
          <span class="text-muted">{prefix}</span><span class="font-semibold">
            {data.name.slice(prefix.length)}
          </span>
        </h1>
        <div class="flex shrink-0 flex-col items-end gap-1">
          <button
            type="button"
            class="btn-secondary flex items-center gap-1.5 px-3 py-1.5 text-sm"
            disabled={spinning || saving}
            aria-busy={spinning}
            onclick={() => refresh(true)}
          >
            <Icon name="refresh" class={['size-3.5 text-muted', spinning && 'animate-spin']} />
            Обновить
          </button>
          {#if refreshError}
            <p class="line-clamp-2 max-w-64 text-right text-xs text-danger" title={refreshError}>
              Не обновилось: {refreshError}
            </p>
          {:else if loadedAt}
            <p class="text-xs text-muted tabular-nums">Данные на {formatTime(loadedAt)}</p>
          {/if}
        </div>
      </div>
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

      {#if outdated && edited}
        <Warning>
          Поток изменили в Keitaro, пока вы правили. Нажмите «Обновить», чтобы увидеть свежие
          данные: ваша правка останется.
        </Warning>
      {/if}
      {#if warning}
        <Warning>{warning}</Warning>
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
            <!-- Жёлтый фон — строка изменится при сохранении: оффер добавлен, убран или его доля станет другой -->
            <tr
              class={[
                'border-b border-line',
                row.before !== row.after && 'bg-amber/15',
                removed && 'text-muted',
              ]}
            >
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
          class="btn-secondary px-4 py-2 font-medium"
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

<svelte:document onvisibilitychange={refreshIfVisible} />
