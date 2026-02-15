/**
 * API client for the automotive procurement project.
 * All calls go to /api/v1/automotive/...
 */
import { authFetch } from '@/lib/auth'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')
const PREFIX = '/api/v1/automotive'

async function getJson<T>(path: string): Promise<T> {
  const res = await authFetch(`${API_BASE}${PREFIX}${path}`)
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try { const p = await res.json(); detail = p.detail || JSON.stringify(p) } catch {}
    throw new Error(detail)
  }
  return (await res.json()) as T
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await authFetch(`${API_BASE}${PREFIX}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try { const p = await res.json(); detail = p.detail || JSON.stringify(p) } catch {}
    throw new Error(detail)
  }
  return (await res.json()) as T
}

export interface CreateProjectPayload {
  raw_request: string
  buyer_company?: string
  buyer_contact_name?: string
  buyer_contact_email?: string
}

export interface ProjectSummary {
  project_id: string
  raw_request: string
  current_stage: string
  status: string
  buyer_company: string
  created_at: string
}

export interface ProjectDetail {
  project_id: string
  raw_request: string
  current_stage: string
  status: string
  parsed_requirement: Record<string, unknown> | null
  discovery_result: Record<string, unknown> | null
  qualification_result: Record<string, unknown> | null
  comparison_matrix: Record<string, unknown> | null
  intelligence_reports: Record<string, unknown> | null
  rfq_result: Record<string, unknown> | null
  quote_ingestion: Record<string, unknown> | null
  approvals: Record<string, unknown>
  weight_profile: Record<string, number>
  buyer_company: string
  created_at: string
}

export interface ApproveStagePayload {
  stage: string
  approved: boolean
  edits?: Record<string, unknown>
  removed_supplier_ids?: string[]
  status_overrides?: Record<string, string>
  weight_adjustments?: Record<string, number>
  corrections?: Record<string, unknown>[]
  reason?: string
  notes?: string
}

export const automotiveClient = {
  createProject(body: CreateProjectPayload) {
    return postJson<{ project_id: string; status: string; current_stage: string }>('/projects', body)
  },

  listProjects() {
    return getJson<ProjectSummary[]>('/projects')
  },

  getProject(projectId: string) {
    return getJson<ProjectDetail>(`/projects/${projectId}`)
  },

  getStageData(projectId: string, stage: string) {
    return getJson<{ stage: string; current_stage: string; data: unknown }>(`/projects/${projectId}/stage/${stage}`)
  },

  approveStage(projectId: string, body: ApproveStagePayload) {
    return postJson<{ status: string; current_stage: string }>(`/projects/${projectId}/approve`, body)
  },

  getSuppliers(projectId: string, stage = 'qualify') {
    return getJson<Record<string, unknown>[]>(`/projects/${projectId}/suppliers?stage=${stage}`)
  },

  getComparison(projectId: string) {
    return getJson<Record<string, unknown>>(`/projects/${projectId}/comparison`)
  },

  getReport(projectId: string, supplierId: string) {
    return getJson<Record<string, unknown>>(`/projects/${projectId}/reports/${supplierId}`)
  },

  getRFQ(projectId: string) {
    return getJson<Record<string, unknown>>(`/projects/${projectId}/rfq`)
  },

  getQuotes(projectId: string) {
    return getJson<Record<string, unknown>>(`/projects/${projectId}/quotes`)
  },
}
