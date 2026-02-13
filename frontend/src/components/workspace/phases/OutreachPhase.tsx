'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import { useOutreach, OutreachTab } from '@/hooks/useOutreach'

export default function OutreachPhase() {
  const { projectId, status, refreshStatus } = useWorkspace()

  const recommendations = status?.recommendation || null
  const discoveryResults = status?.discovery_results || null

  const o = useOutreach(projectId, recommendations, discoveryResults, {
    onResultsUpdated: refreshStatus,
  })

  if (!projectId || !recommendations || !discoveryResults) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
        <p className="text-[13px] text-ink-4">
          Complete the Search phase to begin supplier outreach.
        </p>
      </div>
    )
  }

  // Stats
  const sentCount = o.outreachState?.supplier_statuses?.filter((s) => s.email_sent).length ?? 0
  const awaitingCount = o.outreachState?.supplier_statuses?.filter((s) => s.email_sent && !s.response_received).length ?? 0
  const responseCount = o.outreachState?.supplier_statuses?.filter((s) => s.response_received).length ?? 0

  const tabs: { key: OutreachTab; label: string; show: boolean }[] = [
    { key: 'select', label: 'Select', show: true },
    { key: 'drafts', label: 'Drafts', show: !!o.outreachState?.draft_emails?.length },
    { key: 'tracking', label: 'Tracking', show: !!o.outreachState?.supplier_statuses?.length },
    { key: 'responses', label: 'Responses', show: !!o.outreachState },
    { key: 'quotes', label: 'Quotes', show: !!o.outreachState?.parsed_quotes?.length },
    { key: 'followups', label: 'Follow-ups', show: !!o.outreachState },
    { key: 'auto', label: 'Auto', show: true },
    { key: 'phone', label: 'Phone', show: true },
  ]

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Hero */}
      <h2 className="font-heading text-2xl text-ink mb-1">Reaching out to the world.</h2>
      {o.outreachState && (
        <div className="flex gap-4 text-[11px] text-ink-4 mb-6">
          <span>{sentCount} quoted</span>
          <span>{awaitingCount} awaiting</span>
          <span>{responseCount} responded</span>
        </div>
      )}

      {/* Sub-tabs */}
      <div className="flex gap-0 border-b border-surface-3 mb-6 overflow-x-auto">
        {tabs.filter((t) => t.show).map((t) => (
          <button
            key={t.key}
            onClick={() => o.setTab(t.key)}
            className={`relative px-4 py-3 text-[11px] font-medium tracking-[0.3px] transition-colors whitespace-nowrap ${
              o.tab === t.key ? 'text-ink' : 'text-ink-4 hover:text-ink-3'
            }`}
          >
            {t.label}
            {o.tab === t.key && (
              <span className="absolute bottom-0 left-4 right-4 h-[1.5px] bg-teal rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Error */}
      {o.error && (
        <div className="mb-4 card border-l-[3px] border-l-red-400 px-5 py-3 flex items-center justify-between">
          <span className="text-[12px] text-ink-2">{o.error}</span>
          <button onClick={() => o.setError(null)} className="text-ink-4 hover:text-ink-2 text-[12px]">
            Dismiss
          </button>
        </div>
      )}

      {/* ── Select Suppliers ─────────────────────── */}
      {o.tab === 'select' && (
        <div>
          <p className="text-[12px] text-ink-3 mb-4">
            Select suppliers to contact with RFQ emails:
          </p>
          <div className="space-y-2">
            {recommendations.recommendations.map((rec: any) => (
              <label
                key={rec.supplier_index}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-colors ${
                  o.selectedIndices.includes(rec.supplier_index)
                    ? 'border-teal/40 bg-teal/[0.03]'
                    : 'border-surface-3 hover:bg-surface-2/50'
                }`}
              >
                <input
                  type="checkbox"
                  checked={o.selectedIndices.includes(rec.supplier_index)}
                  onChange={() => o.toggleSupplier(rec.supplier_index)}
                  className="rounded border-surface-3 accent-teal"
                />
                <div className="flex-1 min-w-0">
                  <span className="text-[13px] font-medium text-ink">
                    #{rec.rank} {rec.supplier_name}
                  </span>
                  <span className="ml-2 text-[11px] text-ink-4">
                    Score: {Math.round(rec.overall_score)}
                  </span>
                </div>
                {discoveryResults.suppliers[rec.supplier_index]?.email && (
                  <span className="status-dot bg-teal" title="Has email" />
                )}
              </label>
            ))}
          </div>
          <button
            onClick={o.startOutreach}
            disabled={o.selectedIndices.length === 0 || o.loading}
            className="mt-4 px-5 py-2.5 bg-teal text-white rounded-lg text-[13px] font-medium
                       hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {o.loading ? 'Drafting...' : `Draft RFQ Emails (${o.selectedIndices.length})`}
          </button>
        </div>
      )}

      {/* ── Draft Emails ─────────────────────────── */}
      {o.tab === 'drafts' && o.outreachState && (
        <div className="space-y-4">
          {o.outreachState.draft_emails.map((draft, i) => (
            <div key={i} className="card p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[13px] font-semibold text-ink">{draft.supplier_name}</h3>
                <span className="flex items-center gap-1.5 text-[10px] text-ink-4">
                  <span className={`status-dot ${
                    draft.status === 'sent' ? 'bg-teal' : draft.status === 'failed' ? 'bg-red-400' : 'bg-ink-4/30'
                  }`} />
                  {draft.status}
                </span>
              </div>

              {o.editingDraft === i ? (
                <>
                  <input
                    value={o.editSubject}
                    onChange={(e) => o.setEditSubject(e.target.value)}
                    className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink mb-2 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none"
                  />
                  <textarea
                    value={o.editBody}
                    onChange={(e) => o.setEditBody(e.target.value)}
                    rows={8}
                    className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none resize-none"
                  />
                </>
              ) : (
                <>
                  <p className="text-[11px] text-ink-4 mb-1">
                    Subject: <span className="text-ink-2">{draft.subject}</span>
                  </p>
                  <pre className="text-[11px] text-ink-3 whitespace-pre-wrap bg-cream rounded-lg p-3 max-h-40 overflow-y-auto border border-surface-3">
                    {draft.body}
                  </pre>
                </>
              )}

              {draft.status === 'draft' && (
                <div className="flex gap-2 mt-3">
                  {o.editingDraft === i ? (
                    <button
                      onClick={() => o.setEditingDraft(null)}
                      className="text-[11px] px-3 py-1.5 border border-surface-3 rounded-lg text-ink-4 hover:bg-surface-2 transition-colors"
                    >
                      Cancel
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        o.setEditingDraft(i)
                        o.setEditSubject(draft.subject)
                        o.setEditBody(draft.body)
                      }}
                      className="text-[11px] px-3 py-1.5 border border-surface-3 rounded-lg text-ink-4 hover:bg-surface-2 transition-colors"
                    >
                      Edit
                    </button>
                  )}
                  <button
                    onClick={() => o.approveAndSend(i)}
                    disabled={o.loading}
                    className="text-[11px] px-3 py-1.5 bg-teal text-white rounded-lg hover:bg-teal-600 disabled:opacity-30 transition-colors"
                  >
                    {o.loading ? 'Sending...' : 'Approve & Send'}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Tracking ─────────────────────────────── */}
      {o.tab === 'tracking' && o.outreachState && (
        <div>
          <div className="space-y-2">
            {o.outreachState.supplier_statuses.map((s, i) => (
              <div key={i} className="card px-5 py-3 flex items-center gap-4">
                <span className="text-[13px] text-ink flex-1">{s.supplier_name}</span>
                <span className="flex items-center gap-1.5 text-[10px] text-ink-4">
                  <span className={`status-dot ${s.email_sent ? 'bg-teal' : 'bg-ink-4/30'}`} />
                  {s.email_sent ? 'Sent' : 'Pending'}
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-ink-4">
                  <span className={`status-dot ${
                    s.response_received ? 'bg-teal' : s.email_sent ? 'bg-warm' : 'bg-ink-4/30'
                  }`} />
                  {s.response_received ? 'Received' : s.email_sent ? 'Awaiting' : '--'}
                </span>
                <span className="text-[10px] text-ink-4">
                  {s.follow_ups_sent} follow-ups
                </span>
              </div>
            ))}
          </div>
          <button
            onClick={o.generateFollowUps}
            disabled={o.loading}
            className="mt-4 text-[11px] px-4 py-2 border border-surface-3 rounded-lg text-ink-4
                       hover:bg-surface-2 disabled:opacity-30 transition-colors"
          >
            {o.loading ? 'Generating...' : 'Generate Follow-ups'}
          </button>
        </div>
      )}

      {/* ── Parse Responses ──────────────────────── */}
      {o.tab === 'responses' && o.outreachState && (
        <div>
          <p className="text-[12px] text-ink-3 mb-3">
            Paste a supplier&apos;s email response to extract structured quote data:
          </p>
          <select
            value={o.parseSupplierIdx ?? ''}
            onChange={(e) => o.setParseSupplierIdx(Number(e.target.value))}
            className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink mb-3
                       focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none"
          >
            <option value="">Select a supplier...</option>
            {o.outreachState.supplier_statuses.map((s) => (
              <option key={s.supplier_index} value={s.supplier_index}>{s.supplier_name}</option>
            ))}
          </select>
          <textarea
            value={o.responseText}
            onChange={(e) => o.setResponseText(e.target.value)}
            placeholder="Paste the supplier's email response here..."
            rows={8}
            className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink
                       placeholder:text-ink-4 resize-none focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none"
          />
          <button
            onClick={o.parseResponse}
            disabled={o.parseSupplierIdx === null || !o.responseText.trim() || o.loading}
            className="mt-3 px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium
                       hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {o.loading ? 'Parsing...' : 'Parse Quote'}
          </button>
        </div>
      )}

      {/* ── Quotes ───────────────────────────────── */}
      {o.tab === 'quotes' && o.outreachState && (
        <div>
          {o.outreachState.parsed_quotes.length === 0 ? (
            <p className="text-[13px] text-ink-4 text-center py-8">
              No quotes parsed yet. Go to Responses to add one.
            </p>
          ) : (
            <>
              <div className="space-y-3">
                {o.outreachState.parsed_quotes.map((q, i) => (
                  <div key={i} className="card p-5">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-[13px] font-semibold text-ink">{q.supplier_name}</h3>
                      <span className="text-[10px] text-ink-4">
                        {Math.round(q.confidence_score)}% confidence
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-[11px]">
                      <div><span className="text-ink-4">Unit Price:</span> <span className="text-ink-2 font-medium">{q.unit_price || 'N/A'}</span></div>
                      <div><span className="text-ink-4">MOQ:</span> <span className="text-ink-2">{q.moq || 'N/A'}</span></div>
                      <div><span className="text-ink-4">Lead Time:</span> <span className="text-ink-2">{q.lead_time || 'N/A'}</span></div>
                      <div><span className="text-ink-4">Payment:</span> <span className="text-ink-2">{q.payment_terms || 'N/A'}</span></div>
                      <div><span className="text-ink-4">Shipping:</span> <span className="text-ink-2">{q.shipping_terms || 'N/A'}</span></div>
                      <div><span className="text-ink-4">Currency:</span> <span className="text-ink-2">{q.currency}</span></div>
                    </div>
                    {q.notes && (
                      <p className="mt-2 text-[11px] text-ink-4 bg-cream rounded-lg p-2 border border-surface-3">
                        {q.notes}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              <button
                onClick={o.recompare}
                disabled={o.loading}
                className="mt-4 px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium
                           hover:bg-teal-600 disabled:opacity-30 transition-colors"
              >
                {o.loading ? 'Re-comparing...' : 'Re-compare with Real Quotes'}
              </button>
            </>
          )}
        </div>
      )}

      {/* ── Follow-ups ───────────────────────────── */}
      {o.tab === 'followups' && o.outreachState && (
        <div>
          {(!o.outreachState.follow_up_emails || o.outreachState.follow_up_emails.length === 0) ? (
            <div className="text-center py-8">
              <p className="text-[13px] text-ink-4 mb-3">No follow-ups generated yet.</p>
              <button
                onClick={o.generateFollowUps}
                disabled={o.loading}
                className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium
                           hover:bg-teal-600 disabled:opacity-30 transition-colors"
              >
                {o.loading ? 'Generating...' : 'Generate Follow-ups'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {o.outreachState.follow_up_emails.map((fu, i) => (
                <div key={i} className="card p-5">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-[13px] font-semibold text-ink">{fu.supplier_name}</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] text-ink-4">#{fu.follow_up_number}</span>
                      <span className="flex items-center gap-1.5 text-[10px] text-ink-4">
                        <span className={`status-dot ${fu.status === 'sent' ? 'bg-teal' : 'bg-ink-4/30'}`} />
                        {fu.status}
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-ink-4 mb-1">
                    Subject: <span className="text-ink-2">{fu.subject}</span>
                  </p>
                  <pre className="text-[11px] text-ink-3 whitespace-pre-wrap bg-cream rounded-lg p-3 max-h-32 overflow-y-auto border border-surface-3">
                    {fu.body}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Auto-Outreach ────────────────────────── */}
      {o.tab === 'auto' && (
        <div>
          <div className="flex items-center gap-2 mb-4">
            <h3 className="text-[13px] font-semibold text-ink">Auto-Outreach</h3>
            <span className="text-[9px] font-bold text-warm tracking-wider uppercase">Beta</span>
          </div>
          <p className="text-[12px] text-ink-3 mb-4">
            Automatically draft and queue RFQ emails for suppliers above a minimum verification score.
          </p>
          <div className="mb-4">
            <label className="text-[11px] text-ink-4 mb-1 block">
              Min score: <span className="font-medium text-ink-2">{o.autoThreshold}</span>
            </label>
            <input
              type="range" min={40} max={100} step={5}
              value={o.autoThreshold}
              onChange={(e) => o.setAutoThreshold(Number(e.target.value))}
              className="w-full accent-teal"
            />
            <div className="flex justify-between text-[9px] text-ink-4 mt-0.5">
              <span>40 (more suppliers)</span>
              <span>100 (top only)</span>
            </div>
          </div>
          <div className="flex gap-2 mb-4">
            <button
              onClick={o.configureAutoOutreach}
              disabled={o.loading}
              className="px-4 py-2 border border-surface-3 rounded-lg text-[11px] text-ink-4 hover:bg-surface-2 disabled:opacity-30 transition-colors"
            >
              {o.loading ? 'Saving...' : 'Save Config'}
            </button>
            <button
              onClick={o.startAutoOutreach}
              disabled={o.loading}
              className="px-4 py-2 bg-teal text-white rounded-lg text-[11px] font-medium hover:bg-teal-600 disabled:opacity-30 transition-colors"
            >
              {o.loading ? 'Drafting...' : 'Draft & Queue'}
            </button>
          </div>
          {o.autoStatus?.enabled && (
            <div className="card p-4">
              <div className="grid grid-cols-2 gap-3 text-[12px]">
                <div><span className="text-ink-4">Queued:</span> <span className="text-ink font-medium">{o.autoStatus.queued_count}</span></div>
                <div><span className="text-ink-4">Sent:</span> <span className="text-ink font-medium">{o.autoStatus.sent_count}</span></div>
              </div>
              {o.autoStatus.queued_suppliers.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {o.autoStatus.queued_suppliers.map((name) => (
                    <span key={name} className="text-[10px] bg-teal/5 text-teal px-2 py-0.5 rounded-full border border-teal/15">{name}</span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Phone Calls ──────────────────────────── */}
      {o.tab === 'phone' && (
        <div>
          {/* Config */}
          <div className="card p-5 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h3 className="text-[13px] font-semibold text-ink">AI Phone Calling</h3>
                <span className="text-[9px] font-bold text-ink-4 tracking-wider uppercase">Retell AI</span>
              </div>
              <button
                onClick={() => o.setPhoneConfig((prev) => ({ ...prev, enabled: !prev.enabled }))}
                className={`relative w-9 h-5 rounded-full transition-colors ${o.phoneConfig.enabled ? 'bg-teal' : 'bg-surface-3'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${o.phoneConfig.enabled ? 'translate-x-4' : ''}`} />
              </button>
            </div>

            {o.phoneConfig.enabled && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[10px] text-ink-4 mb-1 block">Voice</label>
                    <select
                      value={o.phoneConfig.voice_id}
                      onChange={(e) => o.setPhoneConfig((prev) => ({ ...prev, voice_id: e.target.value }))}
                      className="w-full border border-surface-3 rounded-lg px-3 py-1.5 text-[12px] text-ink focus:ring-1 focus:ring-teal/30 focus:outline-none"
                    >
                      <option value="11labs-Adrian">Adrian (Male)</option>
                      <option value="11labs-Myra">Myra (Female)</option>
                      <option value="11labs-Phoenix">Phoenix (Neutral)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-ink-4 mb-1 block">Max Duration</label>
                    <select
                      value={o.phoneConfig.max_call_duration_seconds}
                      onChange={(e) => o.setPhoneConfig((prev) => ({ ...prev, max_call_duration_seconds: Number(e.target.value) }))}
                      className="w-full border border-surface-3 rounded-lg px-3 py-1.5 text-[12px] text-ink focus:ring-1 focus:ring-teal/30 focus:outline-none"
                    >
                      <option value={180}>3 min</option>
                      <option value={300}>5 min</option>
                      <option value={600}>10 min</option>
                    </select>
                  </div>
                </div>
                <button onClick={o.savePhoneConfig} disabled={o.loading}
                  className="text-[11px] px-3 py-1.5 bg-teal text-white rounded-lg hover:bg-teal-600 disabled:opacity-30 transition-colors">
                  {o.loading ? 'Saving...' : 'Save Config'}
                </button>
              </div>
            )}
          </div>

          {/* Make a call */}
          {o.phoneConfig.enabled && (
            <div className="card p-5 mb-6">
              <h3 className="text-[13px] font-semibold text-ink mb-3">Make a Call</h3>
              <div className="space-y-3">
                <select
                  value={o.callSupplierIdx ?? ''}
                  onChange={(e) => {
                    const idx = Number(e.target.value)
                    o.setCallSupplierIdx(idx)
                    const supplier = discoveryResults.suppliers[idx]
                    if (supplier?.phone) o.setCallPhoneNumber(supplier.phone)
                  }}
                  className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink focus:ring-1 focus:ring-teal/30 focus:outline-none"
                >
                  <option value="">Select supplier...</option>
                  {recommendations.recommendations.map((rec: any) => (
                    <option key={rec.supplier_index} value={rec.supplier_index}>
                      #{rec.rank} {rec.supplier_name}
                    </option>
                  ))}
                </select>
                <input
                  type="tel"
                  value={o.callPhoneNumber}
                  onChange={(e) => o.setCallPhoneNumber(e.target.value)}
                  placeholder="+1 (555) 123-4567"
                  className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:outline-none"
                />
                <textarea
                  value={o.callQuestions}
                  onChange={(e) => o.setCallQuestions(e.target.value)}
                  placeholder="Custom questions (one per line)..."
                  rows={3}
                  className="w-full border border-surface-3 rounded-lg px-3 py-2 text-[12px] text-ink placeholder:text-ink-4 resize-none focus:ring-1 focus:ring-teal/30 focus:outline-none"
                />
                <button
                  onClick={o.startPhoneCall}
                  disabled={o.callSupplierIdx === null || !o.callPhoneNumber.trim() || o.loading}
                  className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  {o.loading ? 'Calling...' : 'Start AI Call'}
                </button>
              </div>
            </div>
          )}

          {/* Call history */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-[13px] font-semibold text-ink">Call History</h3>
              <button onClick={o.fetchPhoneCalls} className="text-[11px] text-teal hover:underline">Refresh</button>
            </div>
            {o.phoneCalls.length === 0 ? (
              <p className="text-[13px] text-ink-4 text-center py-6">
                No calls yet.
              </p>
            ) : (
              <div className="space-y-3">
                {o.phoneCalls.map((call) => {
                  const parsed = o.parsedCallResults.find((r) => r.call_id === call.call_id)

                  return (
                    <div key={call.call_id} className="card p-5">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-[13px] font-medium text-ink">{call.supplier_name}</h4>
                        <div className="flex items-center gap-2">
                          {call.duration_seconds > 0 && (
                            <span className="text-[10px] text-ink-4">
                              {Math.floor(call.duration_seconds / 60)}m {Math.round(call.duration_seconds % 60)}s
                            </span>
                          )}
                          <span className="flex items-center gap-1.5 text-[10px] text-ink-4">
                            <span className={`status-dot ${
                              call.status === 'completed' ? 'bg-teal'
                              : call.status === 'in_progress' ? 'bg-teal animate-pulse-dot'
                              : call.status === 'failed' ? 'bg-red-400'
                              : 'bg-ink-4/30'
                            }`} />
                            {call.status}
                          </span>
                        </div>
                      </div>

                      <div className="flex gap-2 flex-wrap">
                        {(call.status === 'pending' || call.status === 'in_progress') && (
                          <button onClick={() => o.refreshCallStatus(call.call_id)}
                            className="text-[11px] px-3 py-1.5 border border-surface-3 rounded-lg text-ink-4 hover:bg-surface-2 transition-colors">
                            Check Status
                          </button>
                        )}
                        {call.transcript && (
                          <button
                            onClick={() => o.setExpandedTranscript(o.expandedTranscript === call.call_id ? null : call.call_id)}
                            className="text-[11px] px-3 py-1.5 border border-surface-3 rounded-lg text-ink-4 hover:bg-surface-2 transition-colors"
                          >
                            {o.expandedTranscript === call.call_id ? 'Hide' : 'Transcript'}
                          </button>
                        )}
                        {call.status === 'completed' && call.transcript && !parsed && (
                          <button onClick={() => o.parseCallTranscript(call.call_id)} disabled={o.loading}
                            className="text-[11px] px-3 py-1.5 bg-teal text-white rounded-lg hover:bg-teal-600 disabled:opacity-30 transition-colors">
                            {o.loading ? 'Parsing...' : 'Parse'}
                          </button>
                        )}
                      </div>

                      {o.expandedTranscript === call.call_id && call.transcript && (
                        <pre className="mt-3 text-[11px] text-ink-3 whitespace-pre-wrap bg-cream rounded-lg p-3 max-h-60 overflow-y-auto border border-surface-3">
                          {call.transcript}
                        </pre>
                      )}

                      {parsed && (
                        <div className="mt-3 border-t border-surface-3 pt-3">
                          <p className="text-[9px] uppercase tracking-wider text-ink-4 mb-2">Extracted</p>
                          <div className="grid grid-cols-2 gap-2 text-[11px]">
                            {parsed.pricing_info && <div><span className="text-ink-4">Price:</span> <span className="text-ink-2 font-medium">{parsed.pricing_info}</span></div>}
                            {parsed.moq && <div><span className="text-ink-4">MOQ:</span> <span className="text-ink-2">{parsed.moq}</span></div>}
                            {parsed.lead_time && <div><span className="text-ink-4">Lead:</span> <span className="text-ink-2">{parsed.lead_time}</span></div>}
                          </div>
                          {parsed.key_findings.length > 0 && (
                            <div className="mt-2 space-y-0.5">
                              {parsed.key_findings.map((f: string, j: number) => (
                                <p key={j} className="text-[11px] text-ink-3 flex items-start gap-1.5">
                                  <span className="text-teal mt-0.5 shrink-0">·</span> {f}
                                </p>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
