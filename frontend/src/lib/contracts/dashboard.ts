export interface DashboardGreeting {
  time_label: string
  user_first_name: string
  active_projects: number
  headline: string
  body: string
}

export interface DashboardAttentionItem {
  id: string
  kind: string
  priority: string
  title: string
  subtitle: string
  project_id: string
  cta: string
  target_phase?: string | null
}

export interface DashboardProjectStats {
  quotes_count: number
  best_price?: string | null
  samples_sent: number
}

export interface DashboardProjectCard {
  id: string
  name: string
  description: string
  phase_label: string
  status: string
  progress_step: number
  progress_total: number
  stats: DashboardProjectStats
  status_note: string
  visual_variant: number
}

export interface DashboardActivityItem {
  id: string
  at: number
  time_label: string
  title: string
  description: string
  project_id?: string | null
  project_name?: string | null
  type: string
  priority: string
  payload: Record<string, unknown>
}

export interface DashboardSummaryResponse {
  greeting: DashboardGreeting
  attention: DashboardAttentionItem[]
  projects: DashboardProjectCard[]
  recent_activity: DashboardActivityItem[]
}

export interface DashboardActivityResponse {
  events: DashboardActivityItem[]
  next_cursor?: string | null
}

export interface DashboardProjectStartRequest {
  title?: string
  description: string
  auto_outreach?: boolean
  source?: string
}

export interface DashboardProjectStartResponse {
  project_id: string
  status: string
  redirect_path: string
}

export interface DashboardSupplierContact {
  supplier_id: string
  name: string
  website?: string | null
  email?: string | null
  phone?: string | null
  city?: string | null
  country?: string | null
  interaction_count: number
  project_count: number
  last_interaction_at?: number | null
  last_project_id?: string | null
}

export interface DashboardContactsResponse {
  suppliers: DashboardSupplierContact[]
  count: number
}
