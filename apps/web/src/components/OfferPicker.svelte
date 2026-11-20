<script lang="ts">
  import type { OfferSummary } from '../lib/api'

  // Поле принимает ID оффера или строку из подсказок вида «18813 Flexacil…».
  let {
    id,
    offers,
    value = $bindable(),
  }: {
    id: string
    offers: OfferSummary[]
    value: string
  } = $props()
</script>

<input
  {id}
  class="w-full rounded-md border border-line bg-white px-3 py-2 outline-none focus:border-cobalt"
  list={`${id}-list`}
  inputmode="numeric"
  placeholder="ID оффера или начало названия"
  autocomplete="off"
  bind:value
/>
<datalist id={`${id}-list`}>
  {#each offers as offer (offer.id)}
    <option value={offer.name.startsWith(`${offer.id} `) ? offer.name : `${offer.id} ${offer.name}`}
    ></option>
  {/each}
</datalist>
