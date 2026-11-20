// Уведомления: успех гаснет быстрее, ошибка висит дольше, чтобы её успели прочитать.
export interface Toast {
  id: number
  kind: 'success' | 'error'
  text: string
}

export const toasts = $state<Toast[]>([])

let nextId = 1

export function notify(kind: Toast['kind'], text: string): void {
  const id = nextId++
  toasts.push({ id, kind, text })
  setTimeout(() => dismiss(id), kind === 'error' ? 8000 : 4000)
}

export function notifyError(error: unknown): void {
  notify('error', error instanceof Error ? error.message : String(error))
}

export function dismiss(id: number): void {
  const index = toasts.findIndex((t) => t.id === id)
  if (index >= 0) toasts.splice(index, 1)
}
