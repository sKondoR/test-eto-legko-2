<script lang="ts">
  import { dismiss, toasts } from '../lib/toasts.svelte'
</script>

<div
  class="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col items-end gap-2 sm:left-auto"
>
  {#each toasts as toast (toast.id)}
    <div
      role={toast.kind === 'error' ? 'alert' : 'status'}
      class={[
        'pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-md px-4 py-3 text-sm text-white shadow-lg',
        toast.kind === 'error' ? 'bg-danger' : 'bg-ink',
      ]}
    >
      <p class="flex-1">{toast.text}</p>
      <button
        type="button"
        class="-mr-1 rounded px-1 text-white/80 hover:text-white"
        aria-label="Закрыть уведомление"
        onclick={() => dismiss(toast.id)}
      >
        ✕
      </button>
    </div>
  {/each}
</div>
