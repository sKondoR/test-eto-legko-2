<script lang="ts">
  import { regionName } from '../lib/format'
  import Icon from './Icon.svelte'

  let {
    id,
    countries,
    selected = $bindable(),
  }: { id: string; countries: string[]; selected: string[] } = $props()

  let text = $state('')
  let hint = $state('')

  function add(): void {
    const code = text.trim().toUpperCase()
    if (!code) return
    if (!countries.includes(code)) {
      hint = `Нет страны с кодом ${code}. Нужен код ISO из двух букв, например AU`
      return
    }
    if (!selected.includes(code)) selected = [...selected, code]
    text = ''
    hint = ''
  }

  function onkeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      add()
    } else if (event.key === 'Backspace' && text === '' && selected.length > 0) {
      selected = selected.slice(0, -1)
    }
  }
</script>

<div
  class="flex flex-wrap items-center gap-1.5 rounded-md border border-line bg-white p-1.5 focus-within:border-cobalt"
>
  {#each selected as code (code)}
    <span class="flex items-center gap-1 rounded bg-fog py-1 pr-1 pl-2 text-sm">
      <span class="font-semibold">{code}</span>
      <span class="text-muted">{regionName(code)}</span>
      <button
        type="button"
        class="rounded p-0.5 text-muted hover:text-ink"
        aria-label={`Убрать ${regionName(code)}`}
        onclick={() => (selected = selected.filter((c) => c !== code))}
      >
        <Icon name="close" class="size-3.5" />
      </button>
    </span>
  {/each}
  <input
    {id}
    class="min-w-32 flex-1 border-0 bg-transparent px-1.5 py-1 outline-none"
    list={`${id}-list`}
    placeholder={selected.length ? 'Ещё страна' : 'Код страны, например AU'}
    autocomplete="off"
    bind:value={text}
    {onkeydown}
    oninput={() => (hint = '')}
    onchange={add}
  />
  <datalist id={`${id}-list`}>
    {#each countries as code (code)}
      <option value={code}>{regionName(code)}</option>
    {/each}
  </datalist>
</div>
{#if hint}
  <p class="mt-1 text-sm text-danger">{hint}</p>
{/if}
