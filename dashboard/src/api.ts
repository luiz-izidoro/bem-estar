export type DaySummary = {
  date: string
  derived: Record<string, number | null>
  raw: Record<string, number | null>
  versions: Record<string, string>
  components: Record<string, unknown>
  workouts: Array<{id: string; name: string; start: string; duration_seconds: number; distance_km?: number | null; avg_hr?: number | null}>
}

export type Ingestion = {
  id: string
  received_at: string
  stream: string
  status: string
  records_received: number
  records_inserted: number
  records_ignored: number
  error?: string | null
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {...options, credentials: 'include', headers: {'Content-Type': 'application/json', ...(options.headers || {})}})
  if (!response.ok) {
    const body = await response.json().catch(() => ({detail: response.statusText}))
    throw new Error(body.detail || `HTTP ${response.status}`)
  }
  return response.json() as Promise<T>
}

export const getCsrf = () => document.cookie.split('; ').find(x => x.startsWith('bemestar_csrf='))?.split('=')[1] || ''

export type Profile = {
  hr_max: number | null
  hr_rest: number | null
  trimp_exponential_coefficient: number
  target_sleep_hours: number
  locale: 'pt-BR' | 'en'
}
