<script lang="ts">
  import type { ClassValue } from 'svelte/elements'

  // Иконки одной толщины линии (stroke 2 на сетке 24): вместо символов ✕ и стрелок браузера.
  const PATHS = {
    close: ['M18 6 6 18', 'm6 6 12 12'],
    plus: ['M12 5v14', 'M5 12h14'],
    refresh: ['M21 12a9 9 0 1 1-2.64-6.36L21 8', 'M21 3v5h-5'],
    chevron: ['m6 9 6 6 6-6'],
    alert: [
      'M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z',
      'M12 9v4',
      'M12 17h.01',
    ],
  }

  let { name, class: className = 'size-4' }: { name: keyof typeof PATHS; class?: ClassValue } =
    $props()
</script>

<svg
  class={['shrink-0', className]}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="2"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
>
  {#each PATHS[name] as d (d)}<path {d} />{/each}
</svg>
