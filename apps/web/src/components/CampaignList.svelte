<script lang="ts">
  import type { CampaignSummary } from '../lib/api'
  import Icon from './Icon.svelte'

  let {
    campaigns,
    prefix,
    selected,
    onselect,
  }: {
    campaigns: CampaignSummary[] | null
    prefix: string
    selected: number | 'new'
    onselect: (target: number | 'new') => void
  } = $props()
</script>

<nav aria-label="Кампании" class="flex flex-col gap-3">
  <h2 class="text-lg font-semibold">Кампании</h2>
  <!-- Главное действие списка: синяя кнопка во всю ширину; открытую форму отмечает кольцо. -->
  <button
    type="button"
    class={[
      'btn-primary flex w-full items-center justify-center gap-2',
      selected === 'new' && 'ring-2 ring-cobalt/30 ring-offset-2 ring-offset-fog',
    ]}
    aria-current={selected === 'new' ? 'page' : undefined}
    onclick={() => onselect('new')}
  >
    <Icon name="plus" />
    Новая кампания
  </button>

  {#if campaigns === null}
    <p class="text-sm text-muted">Загружаю список…</p>
  {:else if campaigns.length === 0}
    <p class="text-sm text-muted">
      Кампаний <span class="font-medium text-ink">{prefix}*</span> пока нет. Создайте первую.
    </p>
  {:else}
    <ul class="flex flex-col gap-0.5">
      {#each campaigns as c (c.id)}
        <li>
          <button
            type="button"
            class={[
              'w-full rounded-md px-3 py-2 text-left',
              selected === c.id ? 'bg-white shadow-sm' : 'hover:bg-white/60',
            ]}
            aria-current={selected === c.id ? 'page' : undefined}
            onclick={() => onselect(c.id)}
          >
            <span class="block truncate font-medium">{c.name.slice(prefix.length)}</span>
            <span class="block text-xs text-muted tabular-nums">ID {c.id}</span>
          </button>
        </li>
      {/each}
    </ul>
  {/if}
</nav>
