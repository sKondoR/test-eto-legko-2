<script lang="ts">
  import type { OfferShare } from '../lib/api'

  let {
    shares,
    colors,
    label,
    size = 'lg',
  }: {
    shares: OfferShare[]
    colors: Map<number, string>
    label: string
    size?: 'lg' | 'sm'
  } = $props()
</script>

<figure class="m-0">
  <figcaption class={['mb-1.5 text-muted', size === 'lg' ? 'text-sm' : 'text-xs']}>
    {label}
  </figcaption>
  {#if shares.length === 0}
    <div
      class={[
        'flex items-center justify-center rounded-md border border-dashed border-line text-sm text-muted',
        size === 'lg' ? 'h-14' : 'h-6',
      ]}
    >
      В потоке нет офферов
    </div>
  {:else}
    <div
      class={['flex gap-0.5 overflow-hidden rounded-md', size === 'lg' ? 'h-14' : 'h-6']}
      role="img"
      aria-label={`${label}: ${shares.map((s) => `оффер ${s.offer_id} — ${s.share}%`).join(', ')}`}
    >
      {#each shares as s (s.offer_id)}
        <div
          class="flex min-w-0 items-center justify-center text-white transition-[flex-grow] duration-300 ease-out"
          style:flex-grow={s.share}
          style:flex-basis="0"
          style:background-color={colors.get(s.offer_id)}
        >
          {#if size === 'lg' && s.share >= 8}
            <span class="text-lg font-semibold tabular-nums">{s.share}%</span>
          {/if}
        </div>
      {/each}
    </div>
  {/if}
</figure>
