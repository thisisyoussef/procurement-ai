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
      <div className="text-center py-16">
        <p className="text-workspace-muted text-sm">
          Complete the Search phase to begin supplier outreach.
        </p>
      </div>
    )
  }

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
    <div>
      <h2 className="text-xl font-heading text-workspace-text mb-4">
        Supplier Outreach
      </h2>

      {/* Sub-tabs */}
      <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
        {tabs.filter((t) => t.show).map((t) => (
          <button
            key={t.key}
            onClick={() => o.setTab(t.key)}
            className={`px-3 py-2 text-xs font-medium rounded-lg transition-colors whitespace-nowrap ${
              o.tab === t.key
                ? 'bg-teal/10 text-teal border border-teal/30'
                : 'text-workspace-muted hover:bg-workspace-hover hover:text-workspace-text border border-transparent'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {o.error && (
        <div className="mb-4 p-3 glass-card border-red-500/30 text-sm text-red-400">
          {o.error}
          <button onClick={() => o.setError(null)} className="ml-2 text-red-300 hover:text-red-200">
            ✕
          </button>
        </div>
      )}

      {/* ── Select Suppliers ─────────────────────── */}
      {o.tab === 'select' && (
        <div>
          <p className="text-sm text-workspace-muted mb-4">
            Select suppliers to contact with RFQ emails:
          </p>
          <div className="space-y-2">
            {recommendations.recommendations.map((rec: any) => (
              <label
                key={rec.supplier_index}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  o.selectedIndices.includes(rec.supplier_index)
                    ? 'border-teal/40 bg-teal/5'
                    : 'border-workspace-border hover:bg-workspace-hover'
                }`}
              >
                <input
                  type="checkbox"
                  checked={o.selectedIndices.includes(rec.supplier_index)}
                  onChange={() => o.toggleSupplier(rec.supplier_index)}
                  className="rounded border-workspace-border accent-teal"
                />
                <div className="flex-1">
                  <span className="text-sm font-medium text-workspace-text">
                    #{rec.rank} {rec.supplier_name}
                  </span>
                  <span className="ml-2 text-xs text-workspace-muted">
                    Score: {Math.round(rec.overall_score)} · {rec.best_for}
                  </span>
                </div>
                {discoveryResults.suppliers[rec.supplier_index]?.email && (
                  <span className="text-[10px] text-teal bg-teal/10 px-2 py-0.5 rounded-full border border-teal/20">
                    Has email
                  </span>
                )}
              </label>
            ))}
          </div>
          <button
            onClick={o.startOutreach}
            disabled={o.selectedIndices.length === 0 || o.loading}
            className="mt-4 px-5 py-2.5 bg-teal text-workspace-bg rounded-lg text-sm font-medium
                       hover:bg-teal-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {o.loading ? 'Drafting...' : `Draft RFQ Emails (${o.selectedIndices.length})`}
          </button>
        </div>
      )}

      {/* ── Draft Emails ─────────────────────────── */}
      {o.tab === 'drafts' && o.outreachState && (
        <div className="space-y-4">
          {o.outreachState.draft_emails.map((draft, i) => (
            <div key={i} className="glass-card p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-workspace-text">{draft.supplier_name}</h3>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                  draft.status === 'sent' ? 'bg-green-400/10 text-green-400 border border-green-400/20'
                  : draft.status === 'failed' ? 'bg-red-400/10 text-red-400 border border-red-400/20'
                  : 'bg-workspace-hover text-workspace-muted border border-workspace-border'
                }`}>
                  {draft.status}
                </span>
              </div>

              {o.editingDraft === i ? (
                <>
                  <input
                    value={o.editSubject}
                    onChange={(e) => o.setEditSubject(e.target.value)}
                    className="w-full bg-workspace-bg border border-workspace-border rounded px-3 py-1.5 text-sm text-workspace-text mb-2"
                  />
                  <textarea
                    value={o.editBody}
                    onChange={(e) => o.setEditBody(e.target.value)}
                    rows={8}
                    className="w-full bg-workspace-bg border border-workspace-border rounded px-3 py-2 text-sm text-workspace-text"
                  />
                </>
              ) : (
                <>
                  <p className="text-xs text-workspace-muted mb-1">
                    Subject: <span className="text-workspace-text">{draft.subject}</span>
                  </p>
                  <pre className="text-xs text-workspace-muted whitespace-pre-wrap bg-workspace-bg rounded p-3 max-h-40 overflow-y-auto border border-workspace-border/50">
                    {draft.body}
                  </pre>
                </>
              )}

              {draft.status === 'draft' && (
                <div className="flex gap-2 mt-3">
                  {o.editingDraft === i ? (
                    <button
                      onClick={() => o.setEditingDraft(null)}
                      className="text-xs px-3 py-1.5 border border-workspace-border rounded text-workspace-muted hover:bg-workspace-hover"
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
                      className="text-xs px-3 py-1.5 border border-workspace-border rounded text-workspace-muted hover:bg-workspace-hover"
                    >
                      Edit
                    </button>
                  )}
                  <button
                    onClick={() => o.approveAndSend(i)}
                    disabled={o.loading}
                    className="text-xs px-3 py-1.5 bg-teal text-workspace-bg rounded hover:bg-teal-400 disabled:opacity-30"
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
          <div className="glass-card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-workspace-border">
                  <th className="text-left py-3 px-4 text-workspace-muted text-xs font-medium">Supplier</th>
                  <th className="text-center py-3 px-4 text-workspace-muted text-xs font-medium">Sent</th>
                  <th className="text-center py-3 px-4 text-workspace-muted text-xs font-medium">Response</th>
                  <th className="text-center py-3 px-4 text-workspace-muted text-xs font-medium">Follow-ups</th>
                </tr>
              </thead>
              <tbody>
                {o.outreachState.supplier_statuses.map((s, i) => (
                  <tr key={i} className="border-b border-workspace-border/50">
                    <td className="py-3 px-4 text-workspace-text">{s.supplier_name}</td>
                    <td className="py-3 px-4 text-center">
                      {s.email_sent ? <span className="text-green-400">Sent</span> : <span className="text-workspace-muted">Pending</span>}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {s.response_received ? <span className="text-green-400">Received</span>
                        : s.email_sent ? <span className="text-amber-400">Awaiting</span>
                        : <span className="text-workspace-muted">—</span>}
                    </td>
                    <td className="py-3 px-4 text-center text-workspace-muted">{s.follow_ups_sent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            onClick={o.generateFollowUps}
            disabled={o.loading}
            className="mt-4 text-xs px-4 py-2 border border-workspace-border rounded-lg text-workspace-muted hover:bg-workspace-hover disabled:opacity-30"
          >
            {o.loading ? 'Generating...' : 'Generate Follow-ups'}
          </button>
        </div>
      )}

      {/* ── Parse Responses ──────────────────────── */}
      {o.tab === 'responses' && o.outreachState && (
        <div>
          <p className="text-sm text-workspace-muted mb-3">
            Paste a supplier&apos;s email response to extract structured quote data:
          </p>
          <select
            value={o.parseSupplierIdx ?? ''}
            onChange={(e) => o.setParseSupplierIdx(Number(e.target.value))}
            className="w-full bg-workspace-bg border border-workspace-border rounded-lg px-3 py-2 text-sm text-workspace-text mb-3"
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
            className="w-full bg-workspace-bg border border-workspace-border rounded-lg px-3 py-2 text-sm text-workspace-text
                       placeholder:text-workspace-muted/50 resize-none"
          />
          <button
            onClick={o.parseResponse}
            disabled={o.parseSupplierIdx === null || !o.responseText.trim() || o.loading}
            className="mt-3 px-4 py-2 bg-teal text-workspace-bg rounded-lg text-sm font-medium
                       hover:bg-teal-400 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {o.loading ? 'Parsing...' : 'Parse Quote'}
          </button>
        </div>
      )}

      {/* ── Quotes ───────────────────────────────── */}
      {o.tab === 'quotes' && o.outreachState && (
        <div>
          {o.outreachState.parsed_quotes.length === 0 ? (
            <p className="text-sm text-workspace-muted text-center py-8">
              No quotes parsed yet. Go to Responses to add one.
            </p>
          ) : (
            <>
              <div className="space-y-3">
                {o.outreachState.parsed_quotes.map((q, i) => (
                  <div key={i} className="glass-card p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-semibold text-workspace-text">{q.supplier_name}</h3>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                        q.confidence_score >= 80 ? 'bg-green-400/10 text-green-400 border-green-400/20'
                        : q.confidence_score >= 50 ? 'bg-amber-400/10 text-amber-400 border-amber-400/20'
                        : 'bg-red-400/10 text-red-400 border-red-400/20'
                      }`}>
                        {Math.round(q.confidence_score)}% confidence
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div><span className="text-workspace-muted">Unit Price:</span> <span className="text-workspace-text font-medium">{q.unit_price || 'N/A'}</span></div>
                      <div><span className="text-workspace-muted">MOQ:</span> <span className="text-workspace-text">{q.moq || 'N/A'}</span></div>
                      <div><span className="text-workspace-muted">Lead Time:</span> <span className="text-workspace-text">{q.lead_time || 'N/A'}</span></div>
                      <div><span className="text-workspace-muted">Payment:</span> <span className="text-workspace-text">{q.payment_terms || 'N/A'}</span></div>
                      <div><span className="text-workspace-muted">Shipping:</span> <span className="text-workspace-text">{q.shipping_terms || 'N/A'}</span></div>
                      <div><span className="text-workspace-muted">Currency:</span> <span className="text-workspace-text">{q.currency}</span></div>
                    </div>
                    {q.notes && (
                      <p className="mt-2 text-xs text-workspace-muted bg-workspace-bg rounded p-2 border border-workspace-border/50">
                        {q.notes}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              <button
                onClick={o.recompare}
                disabled={o.loading}
                className="mt-4 px-4 py-2 bg-teal text-workspace-bg rounded-lg text-sm font-medium
                           hover:bg-teal-400 disabled:opacity-30 transition-colors"
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
              <p className="text-sm text-workspace-muted mb-3">No follow-ups generated yet.</p>
              <button
                onClick={o.generateFollowUps}
                disabled={o.loading}
                className="px-4 py-2 bg-teal text-workspace-bg rounded-lg text-sm font-medium
                           hover:bg-teal-400 disabled:opacity-30 transition-colors"
              >
                {o.loading ? 'Generating...' : 'Generate Follow-ups'}
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {o.outreachState.follow_up_emails.map((fu, i) => (
                <div key={i} className="glass-card p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-workspace-text">{fu.supplier_name}</h3>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-workspace-muted">#{fu.follow_up_number}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border ${
                        fu.status === 'sent' ? 'bg-green-400/10 text-green-400 border-green-400/20'
                        : 'bg-workspace-hover text-workspace-muted border-workspace-border'
                      }`}>{fu.status}</span>
                    </div>
                  </div>
                  <p className="text-xs text-workspace-muted mb-1">
                    Subject: <span className="text-workspace-text">{fu.subject}</span>
                  </p>
                  <pre className="text-xs text-workspace-muted whitespace-pre-wrap bg-workspace-bg rounded p-3 max-h-32 overflow-y-auto border border-workspace-border/50">
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
            <h3 className="text-sm font-semibold text-workspace-text">Auto-Outreach</h3>
            <span className="text-[9px] font-medium bg-gold/10 text-gold px-1.5 py-0.5 rounded border border-gold/20">Beta</span>
          </div>
          <p className="text-sm text-workspace-muted mb-4">
            Automatically draft and queue RFQ emails for suppliers above a minimum verification score.
          </p>
          <div className="mb-4">
            <label className="text-xs text-workspace-muted mb-1 block">
              Min score: <span className="font-medium text-workspace-text">{o.autoThreshold}</span>
            </label>
            <input
              type="range" min={40} max={100} step={5}
              value={o.autoThreshold}
              onChange={(e) => o.setAutoThreshold(Number(e.target.value))}
              className="w-full accent-teal"
            />
            <div className="flex justify-between text-[10px] text-workspace-muted mt-0.5">
              <span>40 (more)</span>
              <span>100 (top only)</span>
            </div>
          </div>
          <div className="flex gap-2 mb-4">
            <button
              onClick={o.configureAutoOutreach}
              disabled={o.loading}
              className="px-4 py-2 border border-workspace-border rounded-lg text-sm text-workspace-muted hover:bg-workspace-hover disabled:opacity-30"
            >
              {o.loading ? 'Saving...' : 'Save Config'}
            </button>
            <button
              onClick={o.startAutoOutreach}
              disabled={o.loading}
              className="px-4 py-2 bg-teal text-workspace-bg rounded-lg text-sm font-medium hover:bg-teal-400 disabled:opacity-30"
            >
              {o.loading ? 'Drafting...' : 'Draft & Queue'}
            </button>
          </div>
          {o.autoStatus?.enabled && (
            <div className="glass-card p-4">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><span className="text-workspace-muted">Queued:</span> <span className="text-workspace-text font-medium">{o.autoStatus.queued_count}</span></div>
                <div><span className="text-workspace-muted">Sent:</span> <span className="text-workspace-text font-medium">{o.autoStatus.sent_count}</span></div>
              </div>
              {o.autoStatus.queued_suppliers.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {o.autoStatus.queued_suppliers.map((name) => (
                    <span key={name} className="text-xs bg-teal/10 text-teal px-2 py-0.5 rounded-full border border-teal/20">{name}</span>
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
          <div className="glass-card p-4 mb-6">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-workspace-text">AI Phone Calling</h3>
                <span className="text-[9px] font-medium bg-purple-400/10 text-purple-400 px-1.5 py-0.5 rounded border border-purple-400/20">Retell AI</span>
              </div>
              <button
                onClick={() => o.setPhoneConfig((prev) => ({ ...prev, enabled: !prev.enabled }))}
                className={`relative w-9 h-5 rounded-full transition-colors ${o.phoneConfig.enabled ? 'bg-teal' : 'bg-workspace-border'}`}
              >
                <span className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${o.phoneConfig.enabled ? 'translate-x-4' : ''}`} />
              </button>
            </div>

            {o.phoneConfig.enabled && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-workspace-muted mb-1 block">Voice</label>
                    <select
                      value={o.phoneConfig.voice_id}
                      onChange={(e) => o.setPhoneConfig((prev) => ({ ...prev, voice_id: e.target.value }))}
                      className="w-full bg-workspace-bg border border-workspace-border rounded px-3 py-1.5 text-sm text-workspace-text"
                    >
                      <option value="11labs-Adrian">Adrian (Male)</option>
                      <option value="11labs-Myra">Myra (Female)</option>
                      <option value="11labs-Phoenix">Phoenix (Neutral)</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-workspace-muted mb-1 block">Max Duration</label>
                    <select
                      value={o.phoneConfig.max_call_duration_seconds}
                      onChange={(e) => o.setPhoneConfig((prev) => ({ ...prev, max_call_duration_seconds: Number(e.target.value) }))}
                      className="w-full bg-workspace-bg border border-workspace-border rounded px-3 py-1.5 text-sm text-workspace-text"
                    >
                      <option value={180}>3 min</option>
                      <option value={300}>5 min</option>
                      <option value={600}>10 min</option>
                    </select>
                  </div>
                </div>
                <button onClick={o.savePhoneConfig} disabled={o.loading}
                  className="text-xs px-3 py-1.5 bg-teal text-workspace-bg rounded hover:bg-teal-400 disabled:opacity-30">
                  {o.loading ? 'Saving...' : 'Save Config'}
                </button>
              </div>
            )}
          </div>

          {/* Make a call */}
          {o.phoneConfig.enabled && (
            <div className="glass-card p-4 mb-6">
              <h3 className="text-sm font-semibold text-workspace-text mb-3">Make a Call</h3>
              <div className="space-y-3">
                <select
                  value={o.callSupplierIdx ?? ''}
                  onChange={(e) => {
                    const idx = Number(e.target.value)
                    o.setCallSupplierIdx(idx)
                    const supplier = discoveryResults.suppliers[idx]
                    if (supplier?.phone) o.setCallPhoneNumber(supplier.phone)
                  }}
                  className="w-full bg-workspace-bg border border-workspace-border rounded-lg px-3 py-2 text-sm text-workspace-text"
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
                  className="w-full bg-workspace-bg border border-workspace-border rounded-lg px-3 py-2 text-sm text-workspace-text placeholder:text-workspace-muted/50"
                />
                <textarea
                  value={o.callQuestions}
                  onChange={(e) => o.setCallQuestions(e.target.value)}
                  placeholder="Custom questions (one per line)..."
                  rows={3}
                  className="w-full bg-workspace-bg border border-workspace-border rounded-lg px-3 py-2 text-sm text-workspace-text placeholder:text-workspace-muted/50 resize-none"
                />
                <button
                  onClick={o.startPhoneCall}
                  disabled={o.callSupplierIdx === null || !o.callPhoneNumber.trim() || o.loading}
                  className="px-4 py-2 bg-teal text-workspace-bg rounded-lg text-sm font-medium hover:bg-teal-400 disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {o.loading ? 'Calling...' : 'Start AI Call'}
                </button>
              </div>
            </div>
          )}

          {/* Call history */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-workspace-text">Call History</h3>
              <button onClick={o.fetchPhoneCalls} className="text-xs text-teal hover:text-teal-300">Refresh</button>
            </div>
            {o.phoneCalls.length === 0 ? (
              <p className="text-sm text-workspace-muted text-center py-6">
                No calls yet.
              </p>
            ) : (
              <div className="space-y-3">
                {o.phoneCalls.map((call) => {
                  const statusColors: Record<string, string> = {
                    pending: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
                    in_progress: 'bg-teal/10 text-teal border-teal/20',
                    completed: 'bg-green-400/10 text-green-400 border-green-400/20',
                    failed: 'bg-red-400/10 text-red-400 border-red-400/20',
                    no_answer: 'bg-workspace-hover text-workspace-muted border-workspace-border',
                  }
                  const parsed = o.parsedCallResults.find((r) => r.call_id === call.call_id)

                  return (
                    <div key={call.call_id} className="glass-card p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="text-sm font-medium text-workspace-text">{call.supplier_name}</h4>
                        <div className="flex items-center gap-2">
                          {call.duration_seconds > 0 && (
                            <span className="text-xs text-workspace-muted">
                              {Math.floor(call.duration_seconds / 60)}m {Math.round(call.duration_seconds % 60)}s
                            </span>
                          )}
                          <span className={`text-[10px] px-2 py-0.5 rounded-full border ${statusColors[call.status] || statusColors.no_answer}`}>
                            {call.status}
                          </span>
                        </div>
                      </div>

                      <div className="flex gap-2 flex-wrap">
                        {(call.status === 'pending' || call.status === 'in_progress') && (
                          <button onClick={() => o.refreshCallStatus(call.call_id)}
                            className="text-xs px-3 py-1.5 border border-workspace-border rounded text-workspace-muted hover:bg-workspace-hover">
                            Check Status
                          </button>
                        )}
                        {call.transcript && (
                          <button
                            onClick={() => o.setExpandedTranscript(o.expandedTranscript === call.call_id ? null : call.call_id)}
                            className="text-xs px-3 py-1.5 border border-workspace-border rounded text-workspace-muted hover:bg-workspace-hover"
                          >
                            {o.expandedTranscript === call.call_id ? 'Hide' : 'Transcript'}
                          </button>
                        )}
                        {call.status === 'completed' && call.transcript && !parsed && (
                          <button onClick={() => o.parseCallTranscript(call.call_id)} disabled={o.loading}
                            className="text-xs px-3 py-1.5 bg-teal text-workspace-bg rounded hover:bg-teal-400 disabled:opacity-30">
                            {o.loading ? 'Parsing...' : 'Parse'}
                          </button>
                        )}
                      </div>

                      {o.expandedTranscript === call.call_id && call.transcript && (
                        <pre className="mt-3 text-xs text-workspace-muted whitespace-pre-wrap bg-workspace-bg rounded p-3 max-h-60 overflow-y-auto border border-workspace-border/50">
                          {call.transcript}
                        </pre>
                      )}

                      {parsed && (
                        <div className="mt-3 border-t border-workspace-border/50 pt-3">
                          <h5 className="text-xs font-medium text-workspace-muted mb-2">Extracted</h5>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            {parsed.pricing_info && <div><span className="text-workspace-muted">Price:</span> <span className="text-workspace-text font-medium">{parsed.pricing_info}</span></div>}
                            {parsed.moq && <div><span className="text-workspace-muted">MOQ:</span> <span className="text-workspace-text">{parsed.moq}</span></div>}
                            {parsed.lead_time && <div><span className="text-workspace-muted">Lead:</span> <span className="text-workspace-text">{parsed.lead_time}</span></div>}
                          </div>
                          {parsed.key_findings.length > 0 && (
                            <ul className="mt-2 space-y-0.5">
                              {parsed.key_findings.map((f: string, j: number) => (
                                <li key={j} className="text-xs text-workspace-muted">• {f}</li>
                              ))}
                            </ul>
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
