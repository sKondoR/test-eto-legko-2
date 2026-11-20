<script lang="ts">
  import type { Editor } from '../lib/api'
  import { formatDateTime } from '../lib/format'

  let { entries }: { entries: Editor['history'] } = $props()

  function shareLine(shares: { share: number }[]): string {
    return shares.length ? shares.map((s) => s.share).join(' / ') : 'пусто'
  }
</script>

<section aria-labelledby="history-title">
  <h2 id="history-title" class="mb-3 text-lg font-semibold">История правок</h2>
  {#if entries.length === 0}
    <p class="text-sm text-muted">Через приложение офферы этой кампании ещё не меняли.</p>
  {:else}
    <ol class="flex flex-col">
      {#each entries as entry (entry.changed_at)}
        <li
          class="flex flex-wrap items-baseline gap-x-4 gap-y-1 border-b border-line py-2.5 text-sm"
        >
          <time
            class="w-44 shrink-0 whitespace-nowrap text-muted tabular-nums"
            datetime={entry.changed_at}
          >
            {formatDateTime(new Date(entry.changed_at))}
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
