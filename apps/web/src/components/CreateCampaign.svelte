<script lang="ts">
  import { untrack } from 'svelte'
  import { api, type Config, type DomainSummary, type OfferSummary } from '../lib/api'
  import { parseOfferId } from '../lib/offers'
  import { notify, notifyError } from '../lib/toasts.svelte'
  import CountryPicker from './CountryPicker.svelte'
  import OfferPicker from './OfferPicker.svelte'

  let {
    config,
    offers,
    domains,
    oncreated,
  }: {
    config: Config
    offers: OfferSummary[]
    domains: DomainSummary[] | null // null — ещё грузятся
    oncreated: (id: number) => void
  } = $props()

  // Стартовые значения формы: дальше их меняет пользователь, а не props.
  let suffix = $state('')
  let countries = $state<string[]>(untrack(() => [...config.default_geo]))
  let offerText = $state(untrack(() => (offers.length === 1 ? String(offers[0].id) : '')))
  let busy = $state(false)
  // Домены грузятся отдельно: пока пользователь не выбрал сам, выбран первый из пришедших.
  let domainId = $derived<number | undefined>(domains?.[0]?.id)

  const offerId = $derived(parseOfferId(offerText))
  const ready = $derived(
    suffix.trim() !== '' && domainId !== undefined && countries.length > 0 && offerId !== null,
  )

  async function submit(event: SubmitEvent): Promise<void> {
    event.preventDefault()
    if (!ready || offerId === null || domainId === undefined) return
    busy = true
    try {
      const { id } = await api.createCampaign({
        name_suffix: suffix.trim(),
        countries,
        offer_id: offerId,
        domain_id: domainId,
      })
      notify('success', `Кампания ${config.name_prefix}${suffix.trim()} создана`)
      oncreated(id)
    } catch (error) {
      notifyError(error)
    } finally {
      busy = false
    }
  }
</script>

<form class="flex max-w-xl flex-col gap-6" onsubmit={submit}>
  <header>
    <h1 class="text-2xl font-semibold">Новая кампания</h1>
    <p class="mt-1 text-muted">
      Создаст кампанию с двумя потоками: трафик из выбранных стран уйдёт на google.com, остальной —
      на оффер.
    </p>
  </header>

  <div>
    <label for="name" class="mb-1.5 block font-medium">Название</label>
    <div class="flex rounded-md border border-line bg-white focus-within:border-cobalt">
      <span class="py-2 pl-3 text-muted select-none">{config.name_prefix}</span>
      <input
        id="name"
        class="min-w-0 flex-1 bg-transparent py-2 pr-3 outline-none"
        placeholder="au_summer"
        autocomplete="off"
        spellcheck="false"
        bind:value={suffix}
      />
    </div>
    <p class="mt-1 text-sm text-muted">Латиница в нижнем регистре, цифры и _</p>
  </div>

  <div>
    <label for="domain" class="mb-1.5 block font-medium">Домен</label>
    <select
      id="domain"
      class="w-full rounded-md border border-line bg-white px-3 py-2 outline-none focus:border-cobalt"
      disabled={!domains?.length}
      bind:value={domainId}
    >
      <!-- Без <option>-заглушки: Svelte записал бы её текст в domainId -->
      {#each domains ?? [] as domain (domain.id)}
        <option value={domain.id}>{domain.name}</option>
      {/each}
    </select>
    {#if domains === null}
      <p class="mt-1 text-sm text-muted">Загружаю домены…</p>
    {:else if domains.length === 0}
      <p class="mt-1 text-sm text-muted">Доменов нет: кампанию создать нельзя</p>
    {/if}
  </div>

  <div>
    <label for="countries" class="mb-1.5 block font-medium">Страны для редиректа на Google</label>
    <CountryPicker id="countries" countries={config.countries} bind:selected={countries} />
  </div>

  <div>
    <label for="offer" class="mb-1.5 block font-medium">Оффер</label>
    <OfferPicker id="offer" {offers} bind:value={offerText} />
  </div>

  <div>
    <button type="submit" class="btn-primary" disabled={!ready || busy}>
      {busy ? 'Создаю кампанию…' : 'Создать кампанию'}
    </button>
  </div>
</form>
