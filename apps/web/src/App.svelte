<script lang="ts">
  import CampaignList from './components/CampaignList.svelte'
  import CreateCampaign from './components/CreateCampaign.svelte'
  import OfferEditor from './components/OfferEditor.svelte'
  import Toasts from './components/Toasts.svelte'
  import { api, type CampaignSummary, type Config, type OfferSummary } from './lib/api'
  import { notifyError } from './lib/toasts.svelte'

  let config = $state<Config | null>(null)
  let offers = $state<OfferSummary[]>([])
  let campaigns = $state<CampaignSummary[] | null>(null)
  // Выбор живёт в адресе (#/campaigns/123): переживает перезагрузку, работает «назад».
  function fromHash(): number | 'new' {
    const match = /^#\/campaigns\/(\d+)$/.exec(location.hash)
    return match ? Number(match[1]) : 'new'
  }

  let selected = $state<number | 'new'>(fromHash())

  function select(target: number | 'new'): void {
    location.hash = target === 'new' ? '#/new' : `#/campaigns/${target}`
  }
  let failed = $state(false)

  async function loadCampaigns(): Promise<void> {
    try {
      campaigns = await api.campaigns()
    } catch (error) {
      notifyError(error)
      campaigns = []
    }
  }

  async function start(): Promise<void> {
    failed = false
    try {
      ;[config, offers] = await Promise.all([api.config(), api.offers()])
    } catch (error) {
      notifyError(error)
      failed = true
      return
    }
    await loadCampaigns()
  }

  async function created(id: number): Promise<void> {
    await loadCampaigns()
    select(id)
  }

  start()
</script>

<div
  class="mx-auto grid max-w-6xl content-start items-start gap-8 px-4 py-6 md:grid-cols-[16rem_1fr] md:px-8"
>
  {#if config}
    <aside class="md:sticky md:top-6 md:self-start">
      <CampaignList {campaigns} prefix={config.name_prefix} {selected} onselect={select} />
    </aside>

    <main class="min-w-0 rounded-lg bg-white/70 p-5 md:p-8">
      {#if selected === 'new'}
        <CreateCampaign {config} {offers} oncreated={created} />
      {:else}
        <OfferEditor campaignId={selected} prefix={config.name_prefix} {offers} />
      {/if}
    </main>
  {:else if failed}
    <main class="md:col-span-2">
      <h1 class="text-2xl font-semibold">Не удалось загрузить данные</h1>
      <p class="mt-1 text-muted">Проверьте, что бэкенд запущен и Keitaro доступен.</p>
      <button
        type="button"
        class="mt-4 rounded-md bg-cobalt px-5 py-2.5 font-medium text-white hover:bg-cobalt-dark"
        onclick={start}
      >
        Повторить
      </button>
    </main>
  {:else}
    <p class="text-muted md:col-span-2">Загружаю…</p>
  {/if}
</div>

<svelte:window onhashchange={() => (selected = fromHash())} />

<Toasts />
