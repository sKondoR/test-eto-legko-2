<script lang="ts">
  let health = $state('…')

  fetch('/api/health')
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((d: { status: string }) => (health = d.status))
    .catch(() => (health = 'нет связи с бэкендом'))
</script>

<main class="mx-auto max-w-3xl p-6">
  <h1 class="text-2xl font-semibold">Кампании Keitaro</h1>
  <p class="mt-2 text-sm text-gray-500">Бэкенд: {health}</p>
</main>
