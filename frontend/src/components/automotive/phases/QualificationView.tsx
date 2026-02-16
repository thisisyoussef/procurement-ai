'use client'

import { useState } from 'react'
import type { QualifiedSupplier, QualificationEmailStatus } from '@/types/automotive'
import { m, StaggerList, StaggerItem, AnimatePresence, DURATION, expandCollapse } from '@/lib/motion'
import { automotiveClient } from '@/lib/automotive/client'
import StageActionButton from '@/components/automotive/shared/StageActionButton'
import Tooltip from '@/components/automotive/shared/Tooltip'
import ProcessingState from '@/components/automotive/shared/ProcessingState'
import QualificationTimeline from '@/components/automotive/shared/QualificationTimeline'

interface Props {
  data: Record<string, unknown> | null
  isActive: boolean
  onApprove: (overrides?: Record<string, string>) => void
  projectId: string
}

const STATUS_STYLES: Record<string, string> = {
  qualified: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  conditional: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  disqualified: 'bg-red-500/15 text-red-400 border-red-500/30',
}

const STATUS_TOOLTIPS: Record<string, string> = {
  qualified: 'Meets all requirements. Ready for comparison and scoring.',
  conditional: 'Partially meets requirements. Review concerns below — you can override the status or send a verification email.',
  disqualified: 'Does not meet minimum requirements. Will be excluded from comparison.',
}

const CHECK_DISPLAY: Record<string, { icon: string; label: string; color: string }> = {
  verified_active: { icon: '✅', label: 'Verified', color: 'text-emerald-400' },
  evidence_found: { icon: '✅', label: 'Verified', color: 'text-emerald-400' },
  found: { icon: '✅', label: 'Found', color: 'text-emerald-400' },
  low: { icon: '✅', label: 'Low Risk', color: 'text-emerald-400' },
  moderate: { icon: '⚠️', label: 'Moderate', color: 'text-amber-400' },
  high: { icon: '❌', label: 'High Risk', color: 'text-red-400' },
  expired: { icon: '⚠️', label: 'Expired', color: 'text-amber-400' },
  suspended: { icon: '❌', label: 'Suspended', color: 'text-red-400' },
  not_found: { icon: '❌', label: 'Not Found', color: 'text-red-400' },
  data_unavailable: { icon: '❓', label: 'Unavailable', color: 'text-zinc-500' },
  check_failed: { icon: '❓', label: 'Check Failed', color: 'text-zinc-500' },
  unknown: { icon: '❓', label: 'Unavailable', color: 'text-zinc-500' },
}

const EMAIL_STATUS_FLOW: { key: QualificationEmailStatus; label: string; icon: string }[] = [
  { key: 'sent', label: 'Sent', icon: '✉️' },
  { key: 'delivered', label: 'Delivered', icon: '📬' },
  { key: 'opened', label: 'Opened', icon: '👁' },
  { key: 'responded', label: 'Replied', icon: '✅' },
]

function CheckCell({ label, status }: { label: string; status: string }) {
  const display = CHECK_DISPLAY[status] || CHECK_DISPLAY.unknown
  return (
    <div className="text-xs">
      <span className="text-zinc-500 block">{label}</span>
      <p className={`mt-0.5 ${display.color}`}>
        {display.icon} {display.label}
      </p>
    </div>
  )
}

function EmailStatusTracker({ status }: { status: QualificationEmailStatus }) {
  const currentIdx = EMAIL_STATUS_FLOW.findIndex((s) => s.key === status)
  return (
    <div className="flex items-center gap-1">
      {EMAIL_STATUS_FLOW.map((step, i) => {
        const isReached = i <= currentIdx
        const isCurrent = i === currentIdx
        return (
          <div key={step.key} className="flex items-center gap-1">
            {i > 0 && (
              <span className={`text-[10px] ${isReached ? 'text-emerald-500/60' : 'text-zinc-700'}`}>→</span>
            )}
            <span
              className={`text-xs px-1.5 py-0.5 rounded ${
                isCurrent
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : isReached
                    ? 'text-emerald-500/60'
                    : 'text-zinc-600'
              }`}
            >
              {step.icon} {step.label}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function QualificationView({ data, isActive, onApprove, projectId }: Props) {
  const [overrides, setOverrides] = useState<Record<string, string>>({})
  const [sendingIds, setSendingIds] = useState<Set<string>>(new Set())
  const [bulkSending, setBulkSending] = useState(false)
  const [pasteTarget, setPasteTarget] = useState<string | null>(null)
  const [pasteText, setPasteText] = useState('')
  const [parsing, setParsing] = useState(false)

  if (!data) {
    return (
      <m.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: DURATION.normal }}>
        <ProcessingState stage="qualify" variant={isActive ? 'processing' : 'waiting'} />
      </m.div>
    )
  }

  const suppliers = (data.suppliers || []) as QualifiedSupplier[]
  const qCount = data.qualified_count as number || 0
  const cCount = data.conditional_count as number || 0
  const dCount = data.disqualified_count as number || 0
  const outreachSent = (data.outreach_sent_count as number) || 0
  const outreachResponded = (data.outreach_responded_count as number) || 0
  const outreachPending = (data.outreach_pending_count as number) || 0

  const getStatus = (s: QualifiedSupplier) => overrides[s.supplier_id] || s.qualification_status
  const hasOverrides = Object.keys(overrides).length > 0

  const conditionalWithoutEmail = suppliers.filter(
    (s) => s.qualification_status === 'conditional' && (!s.qualification_email_status || s.qualification_email_status === 'not_sent') && s.email,
  )

  const handleSendEmail = async (supplierId: string) => {
    setSendingIds((prev) => new Set(prev).add(supplierId))
    try {
      await automotiveClient.sendQualificationEmails(projectId, [supplierId])
    } catch (err) {
      console.error('Failed to send qualification email:', err)
    } finally {
      setSendingIds((prev) => {
        const next = new Set(prev)
        next.delete(supplierId)
        return next
      })
    }
  }

  const handleBulkSend = async () => {
    setBulkSending(true)
    try {
      const ids = conditionalWithoutEmail.map((s) => s.supplier_id)
      await automotiveClient.sendQualificationEmails(projectId, ids)
    } catch (err) {
      console.error('Bulk send failed:', err)
    } finally {
      setBulkSending(false)
    }
  }

  const handleParseResponse = async (supplierId: string) => {
    setParsing(true)
    try {
      await automotiveClient.parseQualificationResponse(projectId, supplierId, pasteText)
      setPasteTarget(null)
      setPasteText('')
    } catch (err) {
      console.error('Parse response failed:', err)
    } finally {
      setParsing(false)
    }
  }

  return (
    <m.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: DURATION.normal, ease: [0.16, 1, 0.3, 1] }}
      className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
    >
      {/* ── Header ── */}
      <div className="px-6 py-4 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Supplier Qualification</h3>
            <p className="text-xs text-zinc-500 mt-1">
              {qCount} qualified · {cCount} conditional · {dCount} disqualified
            </p>
          </div>
          <div className="flex items-center gap-3">
            {hasOverrides && (
              <button onClick={() => setOverrides({})} className="text-xs text-zinc-500 hover:text-zinc-300">
                Reset Overrides
              </button>
            )}
            {isActive && (
              <StageActionButton
                stage="qualify"
                onClick={() => onApprove(hasOverrides ? overrides : undefined)}
              />
            )}
          </div>
        </div>

        {/* Outreach summary + bulk send */}
        {(outreachSent > 0 || conditionalWithoutEmail.length > 0) && (
          <div className="mt-3 flex items-center justify-between">
            {outreachSent > 0 && (
              <div className="flex items-center gap-3 text-xs text-zinc-500">
                <span>{outreachSent} sent</span>
                <span className="text-zinc-700">·</span>
                <span className={outreachResponded > 0 ? 'text-emerald-400' : ''}>{outreachResponded} responded</span>
                <span className="text-zinc-700">·</span>
                <span>{outreachPending} awaiting</span>
              </div>
            )}
            {isActive && conditionalWithoutEmail.length > 0 && (
              <button
                onClick={handleBulkSend}
                disabled={bulkSending}
                className="text-xs px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-400 border border-blue-500/30 hover:bg-blue-500/25 transition-colors disabled:opacity-50"
              >
                {bulkSending ? 'Sending...' : `Send to All Conditional (${conditionalWithoutEmail.length})`}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Override summary */}
      {hasOverrides && (
        <div className="px-6 py-2.5 bg-amber-500/5 border-b border-amber-500/10">
          <span className="text-xs text-amber-400">
            {Object.keys(overrides).length} status override{Object.keys(overrides).length > 1 ? 's' : ''} applied
          </span>
        </div>
      )}

      {/* ── Supplier Cards ── */}
      <StaggerList className="divide-y divide-zinc-800">
        {suppliers.map((s) => {
          const status = getStatus(s)
          const isOverridden = s.supplier_id in overrides
          const emailStatus = s.qualification_email_status || 'not_sent'
          const events = s.qualification_events || []
          const isSending = sendingIds.has(s.supplier_id)
          const isPasteOpen = pasteTarget === s.supplier_id

          return (
            <StaggerItem key={s.supplier_id}>
              <div className="px-6 py-5">
                {/* ── Row 1: Name + Status + Confidence ── */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h4 className="font-medium text-zinc-200">{s.company_name}</h4>
                    <Tooltip content={STATUS_TOOLTIPS[status] || ''}>
                      <span className={`text-xs px-2 py-0.5 rounded-full border inline-flex items-center gap-1 ${STATUS_STYLES[status] || STATUS_STYLES.conditional}`}>
                        {isOverridden && <span className="line-through text-zinc-500 mr-1">{s.qualification_status.toUpperCase()}</span>}
                        {status.toUpperCase()}
                      </span>
                    </Tooltip>
                    {isActive && (
                      <select
                        value={overrides[s.supplier_id] || ''}
                        onChange={(e) => {
                          if (e.target.value === '' || e.target.value === s.qualification_status) {
                            setOverrides((prev) => { const n = { ...prev }; delete n[s.supplier_id]; return n })
                          } else {
                            setOverrides((prev) => ({ ...prev, [s.supplier_id]: e.target.value }))
                          }
                        }}
                        className="bg-zinc-800 border border-zinc-700 rounded px-1.5 py-0.5 text-[10px] text-zinc-400"
                      >
                        <option value="">Override…</option>
                        <option value="qualified">→ Qualified</option>
                        <option value="conditional">→ Conditional</option>
                        <option value="disqualified">→ Disqualified</option>
                      </select>
                    )}
                  </div>
                  <span className="text-xs text-zinc-500 font-mono">
                    Confidence: {Math.round((s.overall_confidence || 0) * 100)}%
                  </span>
                </div>

                {/* ── Row 2: Auto-Checks ── */}
                <div className="bg-zinc-800/30 rounded-lg p-3 mb-3">
                  <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Auto-Checks</p>
                  <div className="grid grid-cols-5 gap-3">
                    <CheckCell label="IATF 16949" status={s.iatf_status} />
                    <CheckCell label="Financial" status={s.financial_risk} />
                    <CheckCell label="Registration" status={s.corporate_status} />
                    <div className="text-xs">
                      <span className="text-zinc-500 block">Rating</span>
                      <p className="text-zinc-300 mt-0.5">
                        {s.google_rating ? `${s.google_rating}/5 (${s.review_count})` : '❓ No data'}
                      </p>
                    </div>
                    <div className="text-xs">
                      <span className="text-zinc-500 block">Location</span>
                      <Tooltip content={s.headquarters || ''} side="top">
                        <p className="text-zinc-300 mt-0.5 truncate">{s.headquarters || '—'}</p>
                      </Tooltip>
                    </div>
                  </div>
                </div>

                {/* ── Row 3: Email Verification ── */}
                <div className="bg-zinc-800/30 rounded-lg p-3 mb-3">
                  <p className="text-[10px] text-zinc-600 uppercase tracking-wider mb-2">Email Verification</p>

                  {emailStatus === 'not_sent' && (
                    <div className="flex items-center gap-2">
                      {s.email && isActive ? (
                        <>
                          <button
                            onClick={() => handleSendEmail(s.supplier_id)}
                            disabled={isSending}
                            className="text-xs px-3 py-1.5 rounded-lg bg-blue-500/15 text-blue-400 border border-blue-500/30 hover:bg-blue-500/25 transition-colors disabled:opacity-50"
                          >
                            {isSending ? (
                              <span className="flex items-center gap-1.5">
                                <m.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="inline-block">⟳</m.span>
                                Sending...
                              </span>
                            ) : 'Send Questionnaire'}
                          </button>
                          <span className="text-[10px] text-zinc-600">or</span>
                          <button
                            onClick={() => setPasteTarget(isPasteOpen ? null : s.supplier_id)}
                            className="text-xs px-2.5 py-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 transition-colors"
                          >
                            Paste response
                          </button>
                        </>
                      ) : (
                        <span className="text-xs text-zinc-600">
                          {s.email ? 'Not yet sent' : 'No email address available'}
                        </span>
                      )}
                    </div>
                  )}

                  {emailStatus === 'skipped' && (
                    <span className="text-xs text-zinc-600">⏭ Skipped — no email sent</span>
                  )}

                  {emailStatus === 'bounced' && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-red-400">❌ Email bounced</span>
                      {isActive && s.email && (
                        <button
                          onClick={() => handleSendEmail(s.supplier_id)}
                          disabled={isSending}
                          className="text-xs px-2.5 py-1 rounded text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  )}

                  {(['sent', 'delivered', 'opened'] as QualificationEmailStatus[]).includes(emailStatus as QualificationEmailStatus) && (
                    <div className="space-y-2">
                      <EmailStatusTracker status={emailStatus as QualificationEmailStatus} />
                      {isActive && (
                        <button
                          onClick={() => setPasteTarget(isPasteOpen ? null : s.supplier_id)}
                          className="text-[10px] text-zinc-500 hover:text-zinc-300 transition-colors"
                        >
                          {isPasteOpen ? 'Cancel' : 'Paste response manually'}
                        </button>
                      )}
                    </div>
                  )}

                  {emailStatus === 'responded' && s.qual_response && (
                    <div className="space-y-2">
                      <EmailStatusTracker status="responded" />
                      <div className="bg-emerald-500/5 border border-emerald-500/15 rounded-lg p-2.5 mt-2">
                        <p className="text-[10px] text-emerald-500/70 uppercase tracking-wider mb-1.5">Response Summary</p>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                          {s.qual_response.iatf_confirmed !== undefined && (
                            <p className="text-zinc-400">
                              IATF: {s.qual_response.iatf_confirmed ? '✅ Confirmed' : '❌ Not held'}
                              {s.qual_response.iatf_cert_number && ` (#${s.qual_response.iatf_cert_number})`}
                            </p>
                          )}
                          {s.qual_response.capacity_description && (
                            <p className="text-zinc-400">Capacity: {s.qual_response.capacity_description}</p>
                          )}
                          {s.qual_response.lead_time_estimate && (
                            <p className="text-zinc-400">Lead time: {s.qual_response.lead_time_estimate}</p>
                          )}
                          {s.qual_response.similar_projects && (
                            <p className="text-zinc-400">Experience: {s.qual_response.similar_projects}</p>
                          )}
                          {s.qual_response.additional_certifications && s.qual_response.additional_certifications.length > 0 && (
                            <p className="text-zinc-400 col-span-2">Certs: {s.qual_response.additional_certifications.join(', ')}</p>
                          )}
                        </div>
                        {s.qual_response.confidence !== undefined && (
                          <p className="text-[10px] text-zinc-600 mt-1.5">Parse confidence: {Math.round(s.qual_response.confidence * 100)}%</p>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Paste response form */}
                  <AnimatePresence>
                    {isPasteOpen && (
                      <m.div
                        variants={expandCollapse}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        className="overflow-hidden"
                      >
                        <div className="mt-2 space-y-2">
                          <textarea
                            value={pasteText}
                            onChange={(e) => setPasteText(e.target.value)}
                            placeholder="Paste the supplier's email response here..."
                            className="w-full h-24 bg-zinc-800 border border-zinc-700 rounded-lg p-2.5 text-xs text-zinc-300 placeholder:text-zinc-600 resize-none focus:outline-none focus:border-zinc-600"
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleParseResponse(s.supplier_id)}
                              disabled={parsing || !pasteText.trim()}
                              className="text-xs px-3 py-1.5 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-colors disabled:opacity-50"
                            >
                              {parsing ? 'Parsing...' : 'Parse Response'}
                            </button>
                            <button
                              onClick={() => { setPasteTarget(null); setPasteText('') }}
                              className="text-xs px-3 py-1.5 rounded-lg text-zinc-500 hover:text-zinc-300 transition-colors"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      </m.div>
                    )}
                  </AnimatePresence>
                </div>

                {/* ── Row 4: Strengths & Concerns ── */}
                <div className="flex gap-6">
                  {s.strengths?.length > 0 && (
                    <div className="flex-1">
                      <p className="text-xs text-emerald-500 mb-1">Strengths</p>
                      <ul className="text-xs text-zinc-400 space-y-0.5">
                        {s.strengths.map((str, i) => <li key={i}>+ {str}</li>)}
                      </ul>
                    </div>
                  )}
                  {s.concerns?.length > 0 && (
                    <div className="flex-1">
                      <p className="text-xs text-amber-500 mb-1">Concerns</p>
                      <ul className="text-xs text-zinc-400 space-y-0.5">
                        {s.concerns.map((c, i) => <li key={i}>- {c}</li>)}
                      </ul>
                    </div>
                  )}
                </div>

                {/* ── Row 5: Timeline ── */}
                <QualificationTimeline events={events} />
              </div>
            </StaggerItem>
          )
        })}
      </StaggerList>
    </m.div>
  )
}
