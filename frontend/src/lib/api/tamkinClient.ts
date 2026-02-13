import type {
  AnalyticsEventRequest,
  AnalyticsEventResponse,
  IntakeStartRequest,
  IntakeStartResponse,
  LeadCreateRequest,
  LeadCreateResponse,
} from '@/lib/contracts/tamkin'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const payload = await res.json()
      detail = payload.detail || JSON.stringify(payload)
    } catch {
      // Ignore JSON parse failures and keep generic HTTP detail.
    }
    throw new Error(detail)
  }

  return (await res.json()) as T
}

export const tamkinClient = {
  startIntake(body: IntakeStartRequest) {
    return postJson<IntakeStartResponse>('/api/v1/intake/start', body)
  },
  submitLead(body: LeadCreateRequest) {
    return postJson<LeadCreateResponse>('/api/v1/leads', body)
  },
  trackEvent(body: AnalyticsEventRequest) {
    return postJson<AnalyticsEventResponse>('/api/v1/events', body)
  },
}
