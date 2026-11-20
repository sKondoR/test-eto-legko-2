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
  let failed = $state(false)

  // Выбор живёт в адресе (#/campaigns/123): переживает перезагрузку, работает «назад».
  let hash = $state(location.hash)
  const selected = $derived.by((): number | 'new' => {
    const match = /^#\/campaigns\/(\d+)$/.exec(hash)
    return match ? Number(match[1]) : 'new'
  })

  function select(target: number | 'new'): void {
    location.hash = target === 'new' ? '#/new' : `#/campaigns/${target}`
  }

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
    // Список кампаний — самый долгий запрос (листает весь трекер): не ждём его для старта.
    void loadCampaigns()
    try {
      ;[config, offers] = await Promise.all([api.config(), api.offers()])
    } catch (error) {
      notifyError(error)
      failed = true
    }
  }

  function created(id: number): void {
    select(id)
    void loadCampaigns()
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
        {#key selected}
          <OfferEditor campaignId={selected} prefix={config.name_prefix} {offers} />
        {/key}
      {/if}
    </main>
  {:else if failed}
    <main class="md:col-span-2">
      <h1 class="text-2xl font-semibold">Не удалось загрузить данные</h1>
      <p class="mt-1 text-muted">Проверьте, что бэкенд запущен и Keitaro доступен.</p>
      <button type="button" class="btn-primary mt-4" onclick={start}>Повторить</button>
    </main>
  {:else}
    <p class="text-muted md:col-span-2">Загружаю…</p>
  {/if}
</div>

<svelte:window onhashchange={() => (hash = location.hash)} />

<Toasts />
