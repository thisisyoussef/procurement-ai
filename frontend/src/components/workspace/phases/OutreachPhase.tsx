'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { authFetch } from '@/lib/auth'
import { useWorkspace } from '@/contexts/WorkspaceContext'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface OutreachEvent {
  event_type: string
  supplier_name?: string | null
  timestamp?: number
  details?: Record<string, unknown>
}

interface SupplierOutreachStatus {
  supplier_name: string
  supplier_index: number
  email_sent: boolean
  response_received: boolean
  delivery_status?: string
  excluded?: boolean
  exclusion_reason?: string | null
}

interface OutreachState {
  selected_suppliers: number[]
  supplier_statuses: SupplierOutreachStatus[]
  excluded_suppliers?: number[]
  quick_approval_decision?: 'approved' | 'declined' | null
  events?: OutreachEvent[]
}

function eventLabel(eventType: string) {
  switch (eventType) {
    case 'quick_outreach_approved':
      return 'Outreach approved and sent'
    case 'quick_outreach_declined':
      return 'Outreach declined'
    case 'supplier_excluded':
      return 'Supplier removed (cannot fulfill)'
    case 'email_sent':
    case 'auto_email_sent':
      return 'Email sent'
    case 'send_failed':
      return 'Send failed'
    case 'quote_parsed':
    case 'auto_response_parsed':
      return 'Response parsed'
    default:
      return eventType.replace(/_/g, ' ')
  }
}

export default function OutreachPhase() {
  const { projectId, status, refreshStatus } = useWorkspace()
  const [outreachState, setOutreachState] = useState<OutreachState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchOutreachStatus = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/status`)
      if (!res.ok) return
      const data = await res.json()
      if (data?.error) {
        setOutreachState(null)
        return
      }
      setOutreachState(data as OutreachState)
    } catch {
      // Ignore polling errors.
    }
  }, [projectId])

  useEffect(() => {
    if (!projectId) return
    void fetchOutreachStatus()
    const interval = setInterval(() => {
      void fetchOutreachStatus()
    }, 8000)
    return () => clearInterval(interval)
  }, [projectId, fetchOutreachStatus])

  const decision = useMemo(() => {
    if (outreachState?.quick_approval_decision) {
      return outreachState.quick_approval_decision
    }
    const events = outreachState?.events || []
    if (events.some((e) => e.event_type === 'quick_outreach_declined')) return 'declined'
    if (events.some((e) => e.event_type === 'quick_outreach_approved')) return 'approved'
    return null
  }, [outreachState])

  const summary = useMemo(() => {
    const statuses = outreachState?.supplier_statuses || []
    const sent = statuses.filter((s) => s.email_sent).length
    const responded = statuses.filter((s) => s.response_received).length
    const excluded = statuses.filter((s) => s.excluded).length
    const awaiting = statuses.filter((s) => s.email_sent && !s.response_received && !s.excluded).length
    return { sent, responded, excluded, awaiting }
  }, [outreachState])

  const topRecommended = useMemo(() => {
    const recs = status?.recommendation?.recommendations || []
    const excluded = new Set(outreachState?.excluded_suppliers || [])
    return recs.filter((r: any) => !excluded.has(r.supplier_index)).slice(0, 3)
  }, [outreachState?.excluded_suppliers, status?.recommendation?.recommendations])

  const runQuickDecision = useCallback(
    async (approve: boolean) => {
      if (!projectId) return
      setLoading(true)
      setError(null)
      try {
        const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/quick-approval`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ approve, max_suppliers: 3 }),
        })
        if (!res.ok) {
          let detail = `HTTP ${res.status}`
          try {
            const payload = await res.json()
            detail = payload.detail || JSON.stringify(payload)
          } catch {
            // Keep HTTP detail.
          }
          throw new Error(detail)
        }
        await fetchOutreachStatus()
        refreshStatus()
      } catch (err: any) {
        setError(err?.message || 'Failed to update outreach approval.')
      } finally {
        setLoading(false)
      }
    },
    [projectId, fetchOutreachStatus, refreshStatus]
  )

  if (!projectId || !status?.recommendation) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
        <p className="text-[13px] text-ink-4">
          Finish comparison first. Outreach approval appears right after recommendations.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <div>
        <h2 className="font-heading text-2xl text-ink mb-1">Outreach approval</h2>
        <p className="text-[12px] text-ink-3">
          One decision only. Tamkin drafts and sends outreach to top manufacturers automatically.
        </p>
      </div>

      <div className="card p-5 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {topRecommended.map((rec: any) => (
            <div key={rec.supplier_index} className="rounded-lg border border-surface-3 px-3 py-2">
              <p className="text-[12px] font-medium text-ink truncate">{rec.supplier_name}</p>
              <p className="text-[10px] text-ink-4">Score {Math.round(rec.overall_score)}</p>
            </div>
          ))}
        </div>

        {decision === null && (
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => runQuickDecision(true)}
              disabled={loading}
              className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Sending…' : 'Yes, send outreach'}
            </button>
            <button
              onClick={() => runQuickDecision(false)}
              disabled={loading}
              className="px-4 py-2 border border-surface-3 text-ink-4 rounded-lg text-[12px] hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Not now
            </button>
          </div>
        )}

        {decision === 'approved' && (
          <div className="rounded-lg bg-teal/[0.05] border border-teal/20 px-4 py-3">
            <p className="text-[12px] font-medium text-teal">Outreach is active.</p>
            <p className="text-[11px] text-ink-3 mt-1">
              Sent: {summary.sent} · Awaiting: {summary.awaiting} · Responded: {summary.responded} · Removed: {summary.excluded}
            </p>
          </div>
        )}

        {decision === 'declined' && (
          <div className="rounded-lg bg-surface-2 border border-surface-3 px-4 py-3 flex items-center justify-between gap-3">
            <p className="text-[11px] text-ink-3">Outreach was skipped. You can trigger it any time.</p>
            <button
              onClick={() => runQuickDecision(true)}
              disabled={loading}
              className="px-3 py-1.5 bg-teal text-white rounded-lg text-[11px] font-medium hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Send now
            </button>
          </div>
        )}

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2">
            <p className="text-[11px] text-red-700">{error}</p>
          </div>
        )}
      </div>

      {outreachState?.supplier_statuses?.length ? (
        <div className="card p-5">
          <p className="text-[11px] font-semibold text-ink-2 mb-3">Supplier status</p>
          <div className="space-y-2">
            {outreachState.supplier_statuses.map((supplier) => (
              <div key={supplier.supplier_index} className="rounded-lg border border-surface-3 px-3 py-2 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-[12px] text-ink truncate">{supplier.supplier_name}</p>
                  {supplier.excluded && supplier.exclusion_reason && (
                    <p className="text-[10px] text-red-500 truncate">{supplier.exclusion_reason}</p>
                  )}
                </div>
                <span
                  className={`text-[10px] px-2 py-1 rounded-full ${
                    supplier.excluded
                      ? 'bg-red-50 text-red-600'
                      : supplier.response_received
                        ? 'bg-teal/[0.1] text-teal'
                        : supplier.email_sent
                          ? 'bg-warm/10 text-warm'
                          : 'bg-surface-2 text-ink-4'
                  }`}
                >
                  {supplier.excluded
                    ? 'Removed'
                    : supplier.response_received
                      ? 'Responded'
                      : supplier.email_sent
                        ? 'Awaiting reply'
                        : 'Queued'}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {outreachState?.events?.length ? (
        <div className="card p-5">
          <p className="text-[11px] font-semibold text-ink-2 mb-3">Activity</p>
          <div className="space-y-2">
            {outreachState.events
              .slice(-8)
              .reverse()
              .map((event, idx) => (
                <div key={`${event.event_type}-${idx}`} className="text-[11px] text-ink-3 flex items-center gap-2">
                  <span className="status-dot bg-teal/60" />
                  <span>{eventLabel(event.event_type)}</span>
                  {event.supplier_name ? <span className="text-ink-4">· {event.supplier_name}</span> : null}
                </div>
              ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
