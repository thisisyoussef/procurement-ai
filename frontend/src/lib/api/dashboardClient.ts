import { authFetch } from '@/lib/auth'
import type {
  DashboardActivityResponse,
  DashboardContactsResponse,
  DashboardProjectStartRequest,
  DashboardProjectStartResponse,
  DashboardSummaryResponse,
} from '@/lib/contracts/dashboard'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

async function parseJsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const payload = (await res.json()) as { detail?: string }
      detail = payload.detail || detail
    } catch {
      // Keep default HTTP detail.
    }
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export const dashboardClient = {
  async getSummary(statuses: string[] = []): Promise<DashboardSummaryResponse> {
    const params = new URLSearchParams()
    for (const status of statuses) {
      if (status.trim()) params.append('status', status.trim().toLowerCase())
    }
    const path = params.toString()
      ? `${API_BASE}/api/v1/dashboard/summary?${params.toString()}`
      : `${API_BASE}/api/v1/dashboard/summary`
    const res = await authFetch(path)
    return parseJsonOrThrow<DashboardSummaryResponse>(res)
  },

  async getActivity(limit = 30, cursor?: string): Promise<DashboardActivityResponse> {
    const params = new URLSearchParams()
    params.set('limit', String(limit))
    if (cursor) params.set('cursor', cursor)
    const res = await authFetch(`${API_BASE}/api/v1/dashboard/activity?${params.toString()}`)
    return parseJsonOrThrow<DashboardActivityResponse>(res)
  },

  async getContacts(limit = 50): Promise<DashboardContactsResponse> {
    const params = new URLSearchParams({ limit: String(limit) })
    const res = await authFetch(`${API_BASE}/api/v1/dashboard/contacts?${params.toString()}`)
    return parseJsonOrThrow<DashboardContactsResponse>(res)
  },

  async startProject(body: DashboardProjectStartRequest): Promise<DashboardProjectStartResponse> {
    const res = await authFetch(`${API_BASE}/api/v1/dashboard/projects/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return parseJsonOrThrow<DashboardProjectStartResponse>(res)
  },
}
