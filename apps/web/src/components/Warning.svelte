<script lang="ts">
  import type { Snippet } from 'svelte'
  import Icon from './Icon.svelte'

  let { children }: { children: Snippet } = $props()
</script>

<p class="flex gap-2.5 rounded-md bg-amber/10 px-4 py-3 text-sm ring-1 ring-amber/30 ring-inset">
  <Icon name="alert" class="mt-0.5 size-4 text-amber" />
  <span>{@render children()}</span>
</p>
