import type { DatasetInfo, EventPage, EventStatus, Health, MetricsResponse, ModelStatus, Overview, PredictResponse, SecEvent, SimulationState } from '../types/api'

/** Empty in development (Vite proxies /api). On Vercel it must be the public backend URL. */
export const API_BASE = ((import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '').replace(/\/+$/, '')

export class ApiError extends Error {
  code: string
  status: number
  details?: unknown
  constructor(code: string, message: string, status = 0, details?: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.details = details
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE && !import.meta.env.DEV) {
    throw new ApiError('not_configured', 'VITE_API_BASE_URL is not set for this deployment.')
  }
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new ApiError('unreachable', 'Cannot reach the backend API.')
  }
  const text = await res.text()
  let body: unknown = null
  try { body = text ? JSON.parse(text) : null } catch { /* non-JSON body */ }
  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error
    throw new ApiError(err?.code ?? 'http_error', err?.message ?? `Request failed (${res.status})`, res.status, err?.details)
  }
  return body as T
}

const post = <T,>(path: string) => request<T>(path, { method: 'POST' })

export interface EventQuery {
  q?: string; device_id?: string; event_type?: string; label?: string; severity?: string; status?: string
  since?: string; until?: string; limit?: number; offset?: number
}
const qs = (p: object) => {
  const u = new URLSearchParams()
  Object.entries(p).forEach(([k, v]) => { if (v !== undefined && v !== '') u.set(k, String(v)) })
  const s = u.toString()
  return s ? `?${s}` : ''
}

export const api = {
  health: () => request<Health>('/api/health'),
  overview: () => request<Overview>('/api/overview'),
  events: (p: EventQuery) => request<EventPage>(`/api/events${qs(p)}`),
  deviceEvents: (id: string) => request<EventPage>(`/api/devices/${encodeURIComponent(id)}/events?limit=40`),
  setEventStatus: (id: number, status: EventStatus) =>
    request<SecEvent>(`/api/events/${id}/status`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }) }),
  sim: (action: 'start' | 'pause' | 'resume' | 'reset' | 'step') => post<SimulationState>(`/api/simulation/${action}`),
  modelStatus: () => request<ModelStatus>('/api/model/status'),
  modelMetrics: () => request<MetricsResponse>('/api/model/metrics'),
  datasetInfo: () => request<DatasetInfo>('/api/dataset/info'),
  predictCsv: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<PredictResponse>('/api/predict', { method: 'POST', body: form })
  },
  reportUrl: (name: string) => `${API_BASE}/api/reports/${name}`,
}
