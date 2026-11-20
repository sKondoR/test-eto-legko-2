// Уведомления: успех гаснет быстрее, ошибка и предупреждение висят дольше, чтобы их успели прочитать.
export interface Toast {
  id: number
  kind: 'success' | 'warning' | 'error'
  text: string
}

export const toasts = $state<Toast[]>([])

let nextId = 1

export function notify(kind: Toast['kind'], text: string): void {
  const id = nextId++
  toasts.push({ id, kind, text })
  setTimeout(() => dismiss(id), kind === 'success' ? 4000 : 8000)
}

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export function notifyError(error: unknown): void {
  notify('error', errorText(error))
}

export function dismiss(id: number): void {
  const index = toasts.findIndex((t) => t.id === id)
  if (index >= 0) toasts.splice(index, 1)
}
