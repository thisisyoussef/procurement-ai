export interface IntakeStartRequest {
  message: string
  source?: string
  session_id?: string
}

export interface IntakeStartResponse {
  project_id: string
  status: string
  redirect_path: string
}

export interface LeadCreateRequest {
  email: string
  sourcing_note?: string
  source?: string
}

export interface LeadCreateResponse {
  ok: boolean
  lead_id: string
  deduped: boolean
}

export interface AnalyticsEventRequest {
  event_name: string
  session_id?: string
  path?: string
  project_id?: string
  payload?: Record<string, unknown>
}

export interface AnalyticsEventResponse {
  ok: boolean
  event_id: string
}
