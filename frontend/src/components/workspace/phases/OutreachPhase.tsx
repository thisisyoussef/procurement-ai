'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'

import { authFetch } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'
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
  send_error?: string | null
  excluded?: boolean
  exclusion_reason?: string | null
}

interface CommunicationStatusEvent {
  event_type: string
  status: string
  timestamp?: number
  source?: string
  details?: Record<string, unknown>
}

interface CommunicationMessage {
  message_key: string
  direction: 'outbound' | 'inbound' | string
  supplier_index?: number | null
  supplier_name?: string | null
  to_email?: string | null
  from_email?: string | null
  cc_emails?: string[]
  subject?: string | null
  body_preview?: string | null
  resend_email_id?: string | null
  inbox_message_id?: string | null
  source?: string | null
  delivery_status?: string
  parsed_response?: boolean
  created_at?: number
  updated_at?: number
  events?: CommunicationStatusEvent[]
}

interface CommunicationMonitorState {
  owner_email?: string | null
  last_inbox_check_at?: number | null
  last_inbox_check_source?: string | null
  last_inbox_message_count?: number
  total_outbound?: number
  total_inbound?: number
  total_replies?: number
  total_failures?: number
  messages?: CommunicationMessage[]
}

interface OutreachState {
  selected_suppliers: number[]
  supplier_statuses: SupplierOutreachStatus[]
  draft_emails?: { supplier_index: number; supplier_name: string; status: string }[]
  excluded_suppliers?: number[]
  quick_approval_decision?: 'approved' | 'declined' | null
  events?: OutreachEvent[]
  communication_monitor?: CommunicationMonitorState
}

function formatTimeAgo(timestamp?: number | null) {
  if (!timestamp) return 'Never'
  const diff = Math.max(0, Date.now() - timestamp * 1000)
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
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
    case 'retry_attempted':
      return 'Retry attempted'
    case 'retry_failed':
      return 'Retry failed'
    case 'send_canceled':
      return 'Pending send canceled'
    case 'quote_parsed':
    case 'auto_response_parsed':
      return 'Response parsed'
    default:
      return eventType.replace(/_/g, ' ')
  }
}

export default function OutreachPhase() {
  const { projectId, status, refreshStatus, setActivePhase, restartCurrentProject } = useWorkspace()
  const [outreachState, setOutreachState] = useState<OutreachState | null>(null)
  const [loading, setLoading] = useState(false)
  const [checkingInbox, setCheckingInbox] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [restartContext, setRestartContext] = useState('')
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
    const failed = statuses.filter((s) => s.delivery_status === 'failed').length
    return { sent, responded, excluded, awaiting, failed }
  }, [outreachState])

  const pendingDraftCount = useMemo(() => {
    const drafts = outreachState?.draft_emails || []
    return drafts.filter((draft) => ['draft', 'auto_queued'].includes(String(draft.status || '').toLowerCase())).length
  }, [outreachState?.draft_emails])

  const topRecommended = useMemo(() => {
    const recs = status?.recommendation?.recommendations || []
    const excluded = new Set(outreachState?.excluded_suppliers || [])
    return recs.filter((r: any) => !excluded.has(r.supplier_index)).slice(0, 3)
  }, [outreachState?.excluded_suppliers, status?.recommendation?.recommendations])

  const runQuickDecision = useCallback(
    async (approve: boolean) => {
      if (!projectId) return
      trackTraceEvent(
        'outreach_quick_decision_attempt',
        { project_id: projectId, approve },
        { projectId }
      )
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
        const payload = await res.json().catch(() => ({}))
        trackTraceEvent(
          'outreach_quick_decision_success',
          {
            project_id: projectId,
            approve,
            status: payload?.status,
            sent_count: payload?.sent_count,
            failed_count: payload?.failed_count,
          },
          { projectId }
        )
        await fetchOutreachStatus()
        refreshStatus()
      } catch (err: any) {
        setError(err?.message || 'Failed to update outreach approval.')
        trackTraceEvent(
          'outreach_quick_decision_error',
          {
            project_id: projectId,
            approve,
            detail: err?.message || 'unknown',
          },
          { projectId, level: 'warn' }
        )
      } finally {
        setLoading(false)
      }
    },
    [projectId, fetchOutreachStatus, refreshStatus]
  )

  const refreshCommunicationMonitor = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/monitor`)
      if (!res.ok) return
      const monitor = (await res.json()) as CommunicationMonitorState
      setOutreachState((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          communication_monitor: monitor,
        }
      })
    } catch {
      // Ignore monitor refresh failures.
    }
  }, [projectId])

  const runInboxCheck = useCallback(async () => {
    if (!projectId) return
    setCheckingInbox(true)
    setError(null)
    trackTraceEvent('outreach_inbox_check_attempt', { project_id: projectId }, { projectId })
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/check-inbox`, {
        method: 'POST',
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
      const payload = await res.json().catch(() => ({}))
      trackTraceEvent(
        'outreach_inbox_check_success',
        {
          project_id: projectId,
          messages_found: payload?.messages_found,
          new_messages: payload?.new_messages,
          parsed_quotes: payload?.parsed_quotes,
          parse_failures: payload?.parse_failures,
        },
        { projectId }
      )
      await fetchOutreachStatus()
      await refreshCommunicationMonitor()
      refreshStatus()
    } catch (err: any) {
      setError(err?.message || 'Inbox check failed.')
      trackTraceEvent(
        'outreach_inbox_check_error',
        { project_id: projectId, detail: err?.message || 'unknown' },
        { projectId, level: 'warn' }
      )
    } finally {
      setCheckingInbox(false)
    }
  }, [projectId, fetchOutreachStatus, refreshCommunicationMonitor, refreshStatus])

  const runRetryFailed = useCallback(async () => {
    if (!projectId) return
    setActionLoading('retry')
    setError(null)
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/retry-failed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
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
      const payload = await res.json().catch(() => ({}))
      trackTraceEvent(
        'outreach_retry_failed_processed',
        {
          project_id: projectId,
          retried_count: payload?.retried_count,
          sent_count: payload?.sent_count,
          failed_count: payload?.failed_count,
        },
        { projectId }
      )
      await fetchOutreachStatus()
      await refreshCommunicationMonitor()
      refreshStatus()
    } catch (err: any) {
      setError(err?.message || 'Could not retry failed emails.')
    } finally {
      setActionLoading(null)
    }
  }, [projectId, fetchOutreachStatus, refreshCommunicationMonitor, refreshStatus])

  const runCancelPending = useCallback(async () => {
    if (!projectId) return
    setActionLoading('cancel_pending')
    setError(null)
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/cancel-pending`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
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
      const payload = await res.json().catch(() => ({}))
      trackTraceEvent(
        'outreach_cancel_pending_processed',
        {
          project_id: projectId,
          canceled_count: payload?.canceled_count,
          skipped_count: payload?.skipped_count,
        },
        { projectId }
      )
      await fetchOutreachStatus()
      refreshStatus()
    } catch (err: any) {
      setError(err?.message || 'Could not cancel pending outreach.')
    } finally {
      setActionLoading(null)
    }
  }, [projectId, fetchOutreachStatus, refreshStatus])

  const runResearchSuppliers = useCallback(async () => {
    if (!projectId) return
    setActionLoading('research')
    setError(null)
    const ok = await restartCurrentProject({ fromStage: 'discovering' })
    if (ok) {
      setActivePhase('search')
      await fetchOutreachStatus()
      refreshStatus()
    } else {
      setError('Could not restart supplier search.')
    }
    setActionLoading(null)
  }, [projectId, fetchOutreachStatus, refreshStatus, restartCurrentProject, setActivePhase])

  const runRestartWithContext = useCallback(async () => {
    const context = restartContext.trim()
    if (!projectId || !context) return
    setActionLoading('restart_context')
    setError(null)
    const ok = await restartCurrentProject({
      fromStage: 'parsing',
      additionalContext: context,
    })
    if (ok) {
      setRestartContext('')
      setActivePhase('brief')
      await fetchOutreachStatus()
      refreshStatus()
    } else {
      setError('Could not restart with additional context.')
    }
    setActionLoading(null)
  }, [
    projectId,
    restartContext,
    fetchOutreachStatus,
    refreshStatus,
    restartCurrentProject,
    setActivePhase,
  ])

  useEffect(() => {
    if (!projectId) return
    void refreshCommunicationMonitor()
  }, [projectId, refreshCommunicationMonitor])

  const monitor = outreachState?.communication_monitor || null
  const recentMessages = useMemo(
    () =>
      [...(monitor?.messages || [])]
        .sort((a, b) => (b.updated_at || b.created_at || 0) - (a.updated_at || a.created_at || 0))
        .slice(0, 8),
    [monitor?.messages]
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
          <div className="rounded-lg bg-teal/[0.05] border border-teal/20 px-4 py-3 space-y-3">
            <p className="text-[12px] font-medium text-teal">Outreach is active.</p>
            <p className="text-[11px] text-ink-3 mt-1">
              Sent: {summary.sent} · Awaiting: {summary.awaiting} · Responded: {summary.responded} · Failed: {summary.failed} · Removed: {summary.excluded}
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => void runRetryFailed()}
                disabled={actionLoading !== null || summary.failed === 0}
                className="px-3 py-1.5 border border-surface-3 rounded-lg text-[11px] text-ink-3 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'retry' ? 'Retrying…' : 'Retry failed emails'}
              </button>
              <button
                onClick={() => void runCancelPending()}
                disabled={actionLoading !== null || pendingDraftCount === 0}
                className="px-3 py-1.5 border border-surface-3 rounded-lg text-[11px] text-ink-3 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'cancel_pending' ? 'Canceling…' : 'Cancel pending sends'}
              </button>
              <button
                onClick={() => void runResearchSuppliers()}
                disabled={actionLoading !== null}
                className="px-3 py-1.5 border border-surface-3 rounded-lg text-[11px] text-ink-3 hover:bg-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {actionLoading === 'research' ? 'Restarting search…' : 'Search for more suppliers'}
              </button>
            </div>
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

      <div className="card p-5 space-y-3">
        <div>
          <p className="text-[11px] font-semibold text-ink-2">Add context and restart sourcing</p>
          <p className="text-[11px] text-ink-4 mt-1">
            If outreach quality is off, add more detail and rerun from the brief.
          </p>
        </div>
        <textarea
          value={restartContext}
          onChange={(e) => setRestartContext(e.target.value)}
          rows={3}
          placeholder="Example: only include suppliers with in-house embroidery and full garment manufacturing."
          className="w-full resize-none bg-cream/50 border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink placeholder:text-ink-4 focus:outline-none focus:ring-1 focus:ring-teal/30 focus:border-teal/50"
        />
        <div className="flex items-center gap-2">
          <button
            onClick={() => void runRestartWithContext()}
            disabled={actionLoading !== null || !restartContext.trim()}
            className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {actionLoading === 'restart_context' ? 'Restarting…' : 'Restart with context'}
          </button>
          <p className="text-[10px] text-ink-4">Tamkin will restart parsing and supplier search.</p>
        </div>
      </div>

      {decision === 'approved' && (
        <div className="card p-5 space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-[11px] font-semibold text-ink-2">Communication monitor</p>
              <p className="text-[11px] text-ink-4 mt-1">
                Track sent emails, inbox checks, and supplier replies in one feed.
              </p>
            </div>
            <button
              onClick={() => void runInboxCheck()}
              disabled={loading || checkingInbox}
              className="px-3 py-1.5 rounded-lg border border-surface-3 text-[11px] text-ink-3 hover:bg-surface-2 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {checkingInbox ? 'Checking inbox…' : 'Check inbox now'}
            </button>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            <div className="rounded-lg border border-surface-3 px-3 py-2">
              <p className="text-[10px] text-ink-4">Outbound</p>
              <p className="text-[15px] font-medium text-ink">{monitor?.total_outbound || 0}</p>
            </div>
            <div className="rounded-lg border border-surface-3 px-3 py-2">
              <p className="text-[10px] text-ink-4">Inbound</p>
              <p className="text-[15px] font-medium text-ink">{monitor?.total_inbound || 0}</p>
            </div>
            <div className="rounded-lg border border-surface-3 px-3 py-2">
              <p className="text-[10px] text-ink-4">Replies parsed</p>
              <p className="text-[15px] font-medium text-ink">{monitor?.total_replies || 0}</p>
            </div>
            <div className="rounded-lg border border-surface-3 px-3 py-2">
              <p className="text-[10px] text-ink-4">Failures</p>
              <p className="text-[15px] font-medium text-red-600">{monitor?.total_failures || 0}</p>
            </div>
          </div>

          <div className="rounded-lg border border-surface-3 px-3 py-2 text-[11px] text-ink-4">
            Last inbox check: {formatTimeAgo(monitor?.last_inbox_check_at)}{' '}
            {monitor?.last_inbox_check_source ? `(${monitor.last_inbox_check_source})` : ''}
            {monitor?.owner_email ? ` · CC owner: ${monitor.owner_email}` : ''}
          </div>

          {recentMessages.length > 0 ? (
            <div className="space-y-2">
              {recentMessages.map((msg) => (
                <div key={msg.message_key} className="rounded-lg border border-surface-3 px-3 py-2">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded-full ${
                        msg.direction === 'outbound'
                          ? 'bg-teal/[0.08] text-teal'
                          : 'bg-warm/10 text-warm'
                      }`}
                    >
                      {msg.direction === 'outbound' ? 'Outbound' : 'Inbound'}
                    </span>
                    <span className="text-[10px] text-ink-4">
                      {msg.delivery_status || 'unknown'} · {formatTimeAgo(msg.updated_at || msg.created_at)}
                    </span>
                  </div>
                  <p className="text-[12px] text-ink truncate">
                    {msg.supplier_name || msg.to_email || msg.from_email || 'Unknown contact'}
                  </p>
                  {msg.subject ? <p className="text-[11px] text-ink-3 truncate">{msg.subject}</p> : null}
                  {msg.body_preview ? <p className="text-[10px] text-ink-4 truncate">{msg.body_preview}</p> : null}
                  {msg.direction === 'outbound' && msg.cc_emails?.length ? (
                    <p className="text-[10px] text-ink-4 mt-1">CC: {msg.cc_emails.join(', ')}</p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="rounded-lg border border-dashed border-surface-3 px-3 py-4 text-[11px] text-ink-4">
              No communication records yet.
            </div>
          )}
        </div>
      )}

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
                  {!supplier.excluded && supplier.delivery_status === 'failed' && supplier.send_error && (
                    <p className="text-[10px] text-red-500 truncate">{supplier.send_error}</p>
                  )}
                </div>
                <span
                  className={`text-[10px] px-2 py-1 rounded-full ${
                    supplier.excluded
                      ? 'bg-red-50 text-red-600'
                      : supplier.delivery_status === 'failed'
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
                    : supplier.delivery_status === 'failed'
                      ? 'Send failed'
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
