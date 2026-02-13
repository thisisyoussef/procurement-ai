'use client'

import { useState, useEffect } from 'react'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface DraftEmail {
  supplier_name: string
  supplier_index: number
  recipient_email: string | null
  subject: string
  body: string
  status: string
}

interface SupplierOutreachStatus {
  supplier_name: string
  supplier_index: number
  email_sent: boolean
  response_received: boolean
  follow_ups_sent: number
  parsed_quote: ParsedQuote | null
}

interface ParsedQuote {
  supplier_name: string
  unit_price: string | null
  currency: string
  moq: string | null
  lead_time: string | null
  payment_terms: string | null
  shipping_terms: string | null
  notes: string | null
  confidence_score: number
}

interface FollowUpEmail {
  supplier_name: string
  supplier_index: number
  subject: string
  body: string
  follow_up_number: number
  status: string
}

interface OutreachState {
  selected_suppliers: number[]
  supplier_statuses: SupplierOutreachStatus[]
  draft_emails: DraftEmail[]
  follow_up_emails: FollowUpEmail[]
  parsed_quotes: ParsedQuote[]
}

interface Recommendation {
  rank: number
  supplier_name: string
  supplier_index: number
  overall_score: number
  best_for: string
}

interface Supplier {
  name: string
  email: string | null
  phone: string | null
}

interface PhoneCallStatus {
  call_id: string
  supplier_name: string
  supplier_index: number
  status: string
  duration_seconds: number
  transcript: string | null
  recording_url: string | null
  started_at: string | null
  ended_at: string | null
}

interface ParsedCallResult {
  supplier_name: string
  call_id: string
  pricing_info: string | null
  moq: string | null
  lead_time: string | null
  key_findings: string[]
  follow_up_needed: boolean
}

interface PhoneConfig {
  enabled: boolean
  voice_id: string
  max_call_duration_seconds: number
  questions_to_ask: string[]
}

interface OutreachPanelProps {
  projectId: string
  recommendations: {
    recommendations: Recommendation[]
  }
  discoveryResults: {
    suppliers: Supplier[]
  }
  onResultsUpdated: () => void
}

type Tab = 'select' | 'drafts' | 'tracking' | 'responses' | 'quotes' | 'followups' | 'auto' | 'phone'

export default function OutreachPanel({
  projectId,
  recommendations,
  discoveryResults,
  onResultsUpdated,
}: OutreachPanelProps) {
  const [tab, setTab] = useState<Tab>('select')
  const [selectedIndices, setSelectedIndices] = useState<number[]>([])
  const [outreachState, setOutreachState] = useState<OutreachState | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Response parsing state
  const [parseSupplierIdx, setParseSupplierIdx] = useState<number | null>(null)
  const [responseText, setResponseText] = useState('')

  // Editable drafts
  const [editingDraft, setEditingDraft] = useState<number | null>(null)
  const [editSubject, setEditSubject] = useState('')
  const [editBody, setEditBody] = useState('')

  // Auto-outreach state
  const [autoThreshold, setAutoThreshold] = useState(80)
  const [autoStatus, setAutoStatus] = useState<{
    enabled: boolean
    queued_count: number
    sent_count: number
    queued_suppliers: string[]
  } | null>(null)

  // Phone calling state
  const [phoneCalls, setPhoneCalls] = useState<PhoneCallStatus[]>([])
  const [phoneConfig, setPhoneConfig] = useState<PhoneConfig>({
    enabled: false,
    voice_id: '11labs-Adrian',
    max_call_duration_seconds: 300,
    questions_to_ask: [],
  })
  const [callPhoneNumber, setCallPhoneNumber] = useState('')
  const [callSupplierIdx, setCallSupplierIdx] = useState<number | null>(null)
  const [callQuestions, setCallQuestions] = useState('')
  const [expandedTranscript, setExpandedTranscript] = useState<string | null>(null)
  const [parsedCallResults, setParsedCallResults] = useState<ParsedCallResult[]>([])

  // Pre-select recommended suppliers
  useEffect(() => {
    if (recommendations?.recommendations) {
      setSelectedIndices(
        recommendations.recommendations
          .slice(0, 3)
          .map((r) => r.supplier_index)
      )
    }
  }, [recommendations])

  const fetchOutreachStatus = async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/status`
      )
      if (res.ok) {
        const data = await res.json()
        if (!data.error) setOutreachState(data)
      }
    } catch {}
  }

  useEffect(() => {
    fetchOutreachStatus()
  }, [projectId])

  const toggleSupplier = (idx: number) => {
    setSelectedIndices((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx]
    )
  }

  const startOutreach = async () => {
    if (selectedIndices.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/start`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ supplier_indices: selectedIndices }),
        }
      )
      if (!res.ok) throw new Error(await res.text())
      await fetchOutreachStatus()
      setTab('drafts')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const approveAndSend = async (draftIndex: number) => {
    setLoading(true)
    setError(null)
    try {
      const body: any = { draft_index: draftIndex }
      if (editingDraft === draftIndex) {
        body.edited_subject = editSubject
        body.edited_body = editBody
        setEditingDraft(null)
      }
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/approve/${draftIndex}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }
      )
      const data = await res.json()
      if (!data.sent) {
        setError(data.error || 'Failed to send')
      }
      await fetchOutreachStatus()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const parseResponse = async () => {
    if (parseSupplierIdx === null || !responseText.trim()) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/parse-response`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            supplier_index: parseSupplierIdx,
            response_text: responseText,
          }),
        }
      )
      if (!res.ok) throw new Error(await res.text())
      setResponseText('')
      setParseSupplierIdx(null)
      await fetchOutreachStatus()
      setTab('quotes')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const generateFollowUps = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/follow-up`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error(await res.text())
      await fetchOutreachStatus()
      setTab('followups')
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const recompare = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/recompare`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error(await res.text())
      onResultsUpdated()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchAutoStatus = async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/auto-status`
      )
      if (res.ok) {
        const data = await res.json()
        setAutoStatus(data)
      }
    } catch {}
  }

  const configureAutoOutreach = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/auto-config`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            mode: 'auto',
            auto_send_threshold: autoThreshold,
            max_concurrent_outreach: 5,
          }),
        }
      )
      if (!res.ok) throw new Error(await res.text())
      await fetchAutoStatus()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const startAutoOutreach = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/auto-start`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error(await res.text())
      await fetchOutreachStatus()
      await fetchAutoStatus()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Phone calling functions
  const fetchPhoneCalls = async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/phone/calls`
      )
      if (res.ok) {
        const data = await res.json()
        setPhoneCalls(data.calls || [])
        if (data.config) setPhoneConfig(data.config)
      }
    } catch {}
  }

  const savePhoneConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/phone/configure`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            enabled: phoneConfig.enabled,
            voice_id: phoneConfig.voice_id,
            max_call_duration_seconds: phoneConfig.max_call_duration_seconds,
            default_questions: phoneConfig.questions_to_ask,
          }),
        }
      )
      if (!res.ok) throw new Error(await res.text())
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const startPhoneCall = async () => {
    if (callSupplierIdx === null || !callPhoneNumber.trim()) return
    setLoading(true)
    setError(null)
    try {
      const questions = callQuestions.trim()
        ? callQuestions.split('\n').filter((q) => q.trim())
        : []
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/phone/call`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            supplier_index: callSupplierIdx,
            phone_number: callPhoneNumber,
            questions,
          }),
        }
      )
      if (!res.ok) throw new Error(await res.text())
      setCallPhoneNumber('')
      setCallQuestions('')
      await fetchPhoneCalls()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const refreshCallStatus = async (callId: string) => {
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/phone/calls/${callId}`
      )
      if (res.ok) {
        await fetchPhoneCalls()
      }
    } catch {}
  }

  const parseCallTranscript = async (callId: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/projects/${projectId}/phone/calls/${callId}/parse`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setParsedCallResults((prev) => [...prev, data])
      await fetchPhoneCalls()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Fetch phone calls when switching to phone tab
  useEffect(() => {
    if (tab === 'phone') {
      fetchPhoneCalls()
    }
  }, [tab, projectId])

  const tabs: { key: Tab; label: string; show: boolean }[] = [
    { key: 'select', label: 'Select Suppliers', show: true },
    { key: 'drafts', label: 'Draft Emails', show: !!outreachState?.draft_emails?.length },
    { key: 'tracking', label: 'Tracking', show: !!outreachState?.supplier_statuses?.length },
    { key: 'responses', label: 'Parse Responses', show: !!outreachState },
    { key: 'quotes', label: 'Quotes', show: !!outreachState?.parsed_quotes?.length },
    { key: 'followups', label: 'Follow-ups', show: !!outreachState },
    { key: 'auto', label: 'Auto-Outreach', show: true },
    { key: 'phone', label: 'Phone Calls', show: true },
  ]

  return (
    <div data-section="outreach" className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h2 className="text-base font-semibold text-slate-900">
          Supplier Outreach
        </h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Draft RFQ emails, track responses, and collect quotes
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-200 px-6 flex gap-1 overflow-x-auto">
        {tabs
          .filter((t) => t.show)
          .map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-3 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
                tab === t.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              {t.label}
            </button>
          ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mx-6 mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-2 text-red-500 hover:text-red-700"
          >
            Dismiss
          </button>
        </div>
      )}

      <div className="p-6">
        {/* Tab: Select Suppliers */}
        {tab === 'select' && (
          <div>
            <p className="text-sm text-slate-600 mb-4">
              Select suppliers to contact with RFQ emails:
            </p>
            <div className="space-y-2">
              {recommendations.recommendations.map((rec) => (
                <label
                  key={rec.supplier_index}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedIndices.includes(rec.supplier_index)
                      ? 'border-blue-300 bg-blue-50'
                      : 'border-slate-200 hover:bg-slate-50'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedIndices.includes(rec.supplier_index)}
                    onChange={() => toggleSupplier(rec.supplier_index)}
                    className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                  />
                  <div className="flex-1">
                    <span className="text-sm font-medium text-slate-900">
                      #{rec.rank} {rec.supplier_name}
                    </span>
                    <span className="ml-2 text-xs text-slate-500">
                      Score: {Math.round(rec.overall_score)} | {rec.best_for}
                    </span>
                  </div>
                  {discoveryResults.suppliers[rec.supplier_index]?.email && (
                    <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                      Has email
                    </span>
                  )}
                </label>
              ))}
            </div>
            <button
              onClick={startOutreach}
              disabled={selectedIndices.length === 0 || loading}
              className="mt-4 px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Drafting emails...' : `Draft RFQ Emails (${selectedIndices.length} suppliers)`}
            </button>
          </div>
        )}

        {/* Tab: Draft Emails */}
        {tab === 'drafts' && outreachState && (
          <div className="space-y-4">
            {outreachState.draft_emails.map((draft, i) => (
              <div key={i} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-slate-900">
                    {draft.supplier_name}
                  </h3>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      draft.status === 'sent'
                        ? 'bg-green-100 text-green-700'
                        : draft.status === 'failed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-slate-100 text-slate-600'
                    }`}
                  >
                    {draft.status}
                  </span>
                </div>

                {editingDraft === i ? (
                  <>
                    <input
                      value={editSubject}
                      onChange={(e) => setEditSubject(e.target.value)}
                      className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm mb-2 text-slate-900"
                    />
                    <textarea
                      value={editBody}
                      onChange={(e) => setEditBody(e.target.value)}
                      rows={8}
                      className="w-full border border-slate-300 rounded px-3 py-2 text-sm text-slate-900"
                    />
                  </>
                ) : (
                  <>
                    <p className="text-xs text-slate-500 mb-1">
                      Subject: <span className="text-slate-700">{draft.subject}</span>
                    </p>
                    <pre className="text-xs text-slate-600 whitespace-pre-wrap bg-slate-50 rounded p-3 max-h-40 overflow-y-auto">
                      {draft.body}
                    </pre>
                  </>
                )}

                {draft.status === 'draft' && (
                  <div className="flex gap-2 mt-3">
                    {editingDraft === i ? (
                      <button
                        onClick={() => setEditingDraft(null)}
                        className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          setEditingDraft(i)
                          setEditSubject(draft.subject)
                          setEditBody(draft.body)
                        }}
                        className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
                      >
                        Edit
                      </button>
                    )}
                    <button
                      onClick={() => approveAndSend(i)}
                      disabled={loading}
                      className="text-xs px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                    >
                      {loading ? 'Sending...' : 'Approve & Send'}
                    </button>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Tab: Tracking */}
        {tab === 'tracking' && outreachState && (
          <div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 text-xs font-medium text-slate-500">Supplier</th>
                  <th className="text-center py-2 text-xs font-medium text-slate-500">Email Sent</th>
                  <th className="text-center py-2 text-xs font-medium text-slate-500">Response</th>
                  <th className="text-center py-2 text-xs font-medium text-slate-500">Follow-ups</th>
                </tr>
              </thead>
              <tbody>
                {outreachState.supplier_statuses.map((s, i) => (
                  <tr key={i} className="border-b border-slate-100">
                    <td className="py-2.5 text-slate-900">{s.supplier_name}</td>
                    <td className="py-2.5 text-center">
                      {s.email_sent ? (
                        <span className="text-green-600">Sent</span>
                      ) : (
                        <span className="text-slate-400">Pending</span>
                      )}
                    </td>
                    <td className="py-2.5 text-center">
                      {s.response_received ? (
                        <span className="text-green-600">Received</span>
                      ) : s.email_sent ? (
                        <span className="text-amber-600">Awaiting</span>
                      ) : (
                        <span className="text-slate-400">-</span>
                      )}
                    </td>
                    <td className="py-2.5 text-center text-slate-600">{s.follow_ups_sent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex gap-2 mt-4">
              <button
                onClick={generateFollowUps}
                disabled={loading}
                className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50 disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Follow-ups'}
              </button>
            </div>
          </div>
        )}

        {/* Tab: Parse Responses */}
        {tab === 'responses' && outreachState && (
          <div>
            <p className="text-sm text-slate-600 mb-3">
              Paste a supplier&apos;s email response to extract structured quote data:
            </p>
            <div className="mb-3">
              <label className="text-xs text-slate-500 mb-1 block">Supplier:</label>
              <select
                value={parseSupplierIdx ?? ''}
                onChange={(e) => setParseSupplierIdx(Number(e.target.value))}
                className="w-full border border-slate-300 rounded px-3 py-2 text-sm text-slate-900"
              >
                <option value="">Select a supplier...</option>
                {outreachState.supplier_statuses.map((s) => (
                  <option key={s.supplier_index} value={s.supplier_index}>
                    {s.supplier_name}
                  </option>
                ))}
              </select>
            </div>
            <textarea
              value={responseText}
              onChange={(e) => setResponseText(e.target.value)}
              placeholder="Paste the supplier's email response here..."
              rows={8}
              className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm
                         resize-none text-slate-900 placeholder:text-slate-400"
            />
            <button
              onClick={parseResponse}
              disabled={parseSupplierIdx === null || !responseText.trim() || loading}
              className="mt-3 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                         hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Parsing...' : 'Parse Quote'}
            </button>
          </div>
        )}

        {/* Tab: Parsed Quotes */}
        {tab === 'quotes' && outreachState && (
          <div>
            {outreachState.parsed_quotes.length === 0 ? (
              <p className="text-sm text-slate-400 text-center py-6">
                No quotes parsed yet. Go to &quot;Parse Responses&quot; to add one.
              </p>
            ) : (
              <>
                <div className="space-y-3">
                  {outreachState.parsed_quotes.map((q, i) => (
                    <div key={i} className="border border-slate-200 rounded-lg p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-sm font-semibold text-slate-900">{q.supplier_name}</h3>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            q.confidence_score >= 80
                              ? 'bg-green-100 text-green-700'
                              : q.confidence_score >= 50
                              ? 'bg-amber-100 text-amber-700'
                              : 'bg-red-100 text-red-700'
                          }`}
                        >
                          {Math.round(q.confidence_score)}% confidence
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <span className="text-slate-500">Unit Price:</span>{' '}
                          <span className="text-slate-900 font-medium">{q.unit_price || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">MOQ:</span>{' '}
                          <span className="text-slate-900">{q.moq || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Lead Time:</span>{' '}
                          <span className="text-slate-900">{q.lead_time || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Payment:</span>{' '}
                          <span className="text-slate-900">{q.payment_terms || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Shipping:</span>{' '}
                          <span className="text-slate-900">{q.shipping_terms || 'N/A'}</span>
                        </div>
                        <div>
                          <span className="text-slate-500">Currency:</span>{' '}
                          <span className="text-slate-900">{q.currency}</span>
                        </div>
                      </div>
                      {q.notes && (
                        <p className="mt-2 text-xs text-slate-600 bg-slate-50 rounded p-2">
                          {q.notes}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
                <button
                  onClick={recompare}
                  disabled={loading}
                  className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium
                             hover:bg-green-700 disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Re-comparing...' : 'Re-compare with Real Quotes'}
                </button>
              </>
            )}
          </div>
        )}

        {/* Tab: Follow-ups */}
        {tab === 'followups' && outreachState && (
          <div>
            {(!outreachState.follow_up_emails || outreachState.follow_up_emails.length === 0) ? (
              <div className="text-center py-6">
                <p className="text-sm text-slate-400 mb-3">
                  No follow-ups generated yet.
                </p>
                <button
                  onClick={generateFollowUps}
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                             hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {loading ? 'Generating...' : 'Generate Follow-ups'}
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {outreachState.follow_up_emails.map((fu, i) => (
                  <div key={i} className="border border-slate-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="text-sm font-semibold text-slate-900">{fu.supplier_name}</h3>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-slate-500">
                          Follow-up #{fu.follow_up_number}
                        </span>
                        <span
                          className={`text-xs px-2 py-0.5 rounded-full ${
                            fu.status === 'sent'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {fu.status}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-slate-500 mb-1">
                      Subject: <span className="text-slate-700">{fu.subject}</span>
                    </p>
                    <pre className="text-xs text-slate-600 whitespace-pre-wrap bg-slate-50 rounded p-3 max-h-32 overflow-y-auto">
                      {fu.body}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Auto-Outreach */}
        {tab === 'auto' && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <h3 className="text-sm font-semibold text-slate-900">
                Auto-Outreach
              </h3>
              <span className="text-[10px] font-medium bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded">
                Beta
              </span>
            </div>
            <p className="text-sm text-slate-600 mb-4">
              Automatically draft and queue RFQ emails for suppliers that pass
              a minimum verification score. Emails are queued for review before
              sending.
            </p>

            {/* Threshold slider */}
            <div className="mb-4">
              <label className="text-xs text-slate-500 mb-1 block">
                Minimum verification score: <span className="font-medium text-slate-700">{autoThreshold}</span>
              </label>
              <input
                type="range"
                min={40}
                max={100}
                step={5}
                value={autoThreshold}
                onChange={(e) => setAutoThreshold(Number(e.target.value))}
                className="w-full accent-blue-600"
              />
              <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
                <span>40 (more suppliers)</span>
                <span>100 (only top rated)</span>
              </div>
            </div>

            <div className="flex gap-2 mb-4">
              <button
                onClick={configureAutoOutreach}
                disabled={loading}
                className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-700
                           hover:bg-slate-50 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Saving...' : 'Save Config'}
              </button>
              <button
                onClick={startAutoOutreach}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium
                           hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Drafting...' : 'Draft & Queue'}
              </button>
            </div>

            {/* Auto status */}
            {autoStatus && autoStatus.enabled && (
              <div className="border border-slate-200 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-slate-500">Queued:</span>{' '}
                    <span className="font-medium text-slate-900">{autoStatus.queued_count}</span>
                  </div>
                  <div>
                    <span className="text-slate-500">Sent:</span>{' '}
                    <span className="font-medium text-slate-900">{autoStatus.sent_count}</span>
                  </div>
                </div>
                {autoStatus.queued_suppliers.length > 0 && (
                  <div className="mt-3">
                    <span className="text-xs text-slate-500">Queued suppliers:</span>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {autoStatus.queued_suppliers.map((name) => (
                        <span
                          key={name}
                          className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Send Now button */}
            {autoStatus && autoStatus.queued_count > 0 && (
              <button
                onClick={async () => {
                  setLoading(true)
                  try {
                    await fetch(`${API_BASE}/api/v1/projects/${projectId}/outreach/auto-send`, {
                      method: 'POST',
                    })
                    refreshOutreachState()
                  } catch (err) {
                    console.error('Auto-send failed:', err)
                  } finally {
                    setLoading(false)
                  }
                }}
                disabled={loading}
                className="mt-3 w-full px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium
                           hover:bg-green-700 disabled:opacity-50 transition-colors"
              >
                {loading ? 'Sending...' : `Send ${autoStatus.queued_count} Queued Emails Now`}
              </button>
            )}

            {/* Autonomous features status */}
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-blue-700">Autonomous Features</span>
                <span className="text-[10px] bg-blue-200 text-blue-800 px-1.5 py-0.5 rounded">
                  Active
                </span>
              </div>
              <div className="space-y-1.5 text-xs text-blue-600">
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Email queue processor (every 30s)
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Auto follow-ups (Day 3, 7, 14)
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Inbox monitoring (every 5 min)
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  Phone escalation for non-responsive suppliers
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  AI negotiation on received quotes
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab: Phone Calls */}
        {tab === 'phone' && (
          <div>
            {/* Phone Config */}
            <div className="mb-6 border border-slate-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">
                    AI Phone Calling
                  </h3>
                  <span className="text-[10px] font-medium bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                    Retell AI
                  </span>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <span className="text-xs text-slate-500">
                    {phoneConfig.enabled ? 'Enabled' : 'Disabled'}
                  </span>
                  <button
                    onClick={() =>
                      setPhoneConfig((prev) => ({ ...prev, enabled: !prev.enabled }))
                    }
                    className={`relative w-9 h-5 rounded-full transition-colors ${
                      phoneConfig.enabled ? 'bg-blue-600' : 'bg-slate-300'
                    }`}
                  >
                    <span
                      className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                        phoneConfig.enabled ? 'translate-x-4' : ''
                      }`}
                    />
                  </button>
                </label>
              </div>

              {phoneConfig.enabled && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-xs text-slate-500 mb-1 block">Voice</label>
                      <select
                        value={phoneConfig.voice_id}
                        onChange={(e) =>
                          setPhoneConfig((prev) => ({ ...prev, voice_id: e.target.value }))
                        }
                        className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm text-slate-900"
                      >
                        <option value="11labs-Adrian">Adrian (Professional Male)</option>
                        <option value="11labs-Myra">Myra (Professional Female)</option>
                        <option value="11labs-Phoenix">Phoenix (Neutral)</option>
                        <option value="11labs-Sarah">Sarah (Friendly Female)</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs text-slate-500 mb-1 block">Max Duration</label>
                      <select
                        value={phoneConfig.max_call_duration_seconds}
                        onChange={(e) =>
                          setPhoneConfig((prev) => ({
                            ...prev,
                            max_call_duration_seconds: Number(e.target.value),
                          }))
                        }
                        className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm text-slate-900"
                      >
                        <option value={180}>3 minutes</option>
                        <option value={300}>5 minutes</option>
                        <option value={600}>10 minutes</option>
                      </select>
                    </div>
                  </div>
                  <button
                    onClick={savePhoneConfig}
                    disabled={loading}
                    className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : 'Save Config'}
                  </button>
                </div>
              )}
            </div>

            {/* Initiate a Call */}
            {phoneConfig.enabled && (
              <div className="mb-6 border border-slate-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-slate-900 mb-3">
                  Make a Call
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-slate-500 mb-1 block">Supplier</label>
                    <select
                      value={callSupplierIdx ?? ''}
                      onChange={(e) => {
                        const idx = Number(e.target.value)
                        setCallSupplierIdx(idx)
                        // Auto-fill phone if available
                        const supplier = discoveryResults.suppliers[idx]
                        if (supplier?.phone) setCallPhoneNumber(supplier.phone)
                      }}
                      className="w-full border border-slate-300 rounded px-3 py-2 text-sm text-slate-900"
                    >
                      <option value="">Select a supplier...</option>
                      {recommendations.recommendations.map((rec) => (
                        <option key={rec.supplier_index} value={rec.supplier_index}>
                          #{rec.rank} {rec.supplier_name}
                          {discoveryResults.suppliers[rec.supplier_index]?.phone ? ' (has phone)' : ''}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-xs text-slate-500 mb-1 block">Phone Number</label>
                    <input
                      type="tel"
                      value={callPhoneNumber}
                      onChange={(e) => setCallPhoneNumber(e.target.value)}
                      placeholder="+1 (555) 123-4567"
                      className="w-full border border-slate-300 rounded px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400"
                    />
                  </div>
                  <div>
                    <label className="text-xs text-slate-500 mb-1 block">
                      Custom Questions <span className="text-slate-400">(one per line, optional)</span>
                    </label>
                    <textarea
                      value={callQuestions}
                      onChange={(e) => setCallQuestions(e.target.value)}
                      placeholder={"What are your customization options?\nDo you offer samples?"}
                      rows={3}
                      className="w-full border border-slate-300 rounded px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 resize-none"
                    />
                  </div>
                  <button
                    onClick={startPhoneCall}
                    disabled={callSupplierIdx === null || !callPhoneNumber.trim() || loading}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium
                               hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {loading ? 'Initiating call...' : 'Start AI Call'}
                  </button>
                </div>
              </div>
            )}

            {/* Call History */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-900">
                  Call History
                </h3>
                <button
                  onClick={fetchPhoneCalls}
                  className="text-xs text-blue-600 hover:text-blue-700"
                >
                  Refresh
                </button>
              </div>

              {phoneCalls.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">
                  No calls yet. {!phoneConfig.enabled && 'Enable AI Phone Calling above to get started.'}
                </p>
              ) : (
                <div className="space-y-3">
                  {phoneCalls.map((call) => {
                    const statusColors: Record<string, string> = {
                      pending: 'bg-amber-100 text-amber-700',
                      in_progress: 'bg-blue-100 text-blue-700',
                      completed: 'bg-green-100 text-green-700',
                      failed: 'bg-red-100 text-red-700',
                      no_answer: 'bg-slate-100 text-slate-600',
                    }
                    const parsed = parsedCallResults.find((r) => r.call_id === call.call_id)

                    return (
                      <div key={call.call_id} className="border border-slate-200 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="text-sm font-medium text-slate-900">
                            {call.supplier_name}
                          </h4>
                          <div className="flex items-center gap-2">
                            {call.duration_seconds > 0 && (
                              <span className="text-xs text-slate-500">
                                {Math.floor(call.duration_seconds / 60)}m {Math.round(call.duration_seconds % 60)}s
                              </span>
                            )}
                            <span
                              className={`text-xs px-2 py-0.5 rounded-full ${
                                statusColors[call.status] || 'bg-slate-100 text-slate-600'
                              }`}
                            >
                              {call.status}
                            </span>
                          </div>
                        </div>

                        {/* Call times */}
                        {(call.started_at || call.ended_at) && (
                          <div className="flex gap-4 text-xs text-slate-500 mb-2">
                            {call.started_at && (
                              <span>Started: {new Date(call.started_at).toLocaleString()}</span>
                            )}
                            {call.ended_at && (
                              <span>Ended: {new Date(call.ended_at).toLocaleString()}</span>
                            )}
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-2 flex-wrap">
                          {(call.status === 'pending' || call.status === 'in_progress') && (
                            <button
                              onClick={() => refreshCallStatus(call.call_id)}
                              className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
                            >
                              Check Status
                            </button>
                          )}
                          {call.transcript && (
                            <button
                              onClick={() =>
                                setExpandedTranscript(
                                  expandedTranscript === call.call_id ? null : call.call_id
                                )
                              }
                              className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
                            >
                              {expandedTranscript === call.call_id
                                ? 'Hide Transcript'
                                : 'View Transcript'}
                            </button>
                          )}
                          {call.status === 'completed' && call.transcript && !parsed && (
                            <button
                              onClick={() => parseCallTranscript(call.call_id)}
                              disabled={loading}
                              className="text-xs px-3 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                            >
                              {loading ? 'Parsing...' : 'Parse Transcript'}
                            </button>
                          )}
                          {call.recording_url && (
                            <a
                              href={call.recording_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs px-3 py-1.5 border border-slate-300 rounded text-slate-600 hover:bg-slate-50"
                            >
                              Recording &rarr;
                            </a>
                          )}
                        </div>

                        {/* Transcript viewer */}
                        {expandedTranscript === call.call_id && call.transcript && (
                          <div className="mt-3 bg-slate-50 rounded-lg p-3 max-h-60 overflow-y-auto">
                            <pre className="text-xs text-slate-700 whitespace-pre-wrap">
                              {call.transcript}
                            </pre>
                          </div>
                        )}

                        {/* Parsed results */}
                        {parsed && (
                          <div className="mt-3 border-t border-slate-100 pt-3">
                            <h5 className="text-xs font-medium text-slate-700 mb-2">
                              Extracted Data
                            </h5>
                            <div className="grid grid-cols-2 gap-2 text-xs">
                              {parsed.pricing_info && (
                                <div>
                                  <span className="text-slate-500">Pricing:</span>{' '}
                                  <span className="text-slate-900 font-medium">
                                    {parsed.pricing_info}
                                  </span>
                                </div>
                              )}
                              {parsed.moq && (
                                <div>
                                  <span className="text-slate-500">MOQ:</span>{' '}
                                  <span className="text-slate-900">{parsed.moq}</span>
                                </div>
                              )}
                              {parsed.lead_time && (
                                <div>
                                  <span className="text-slate-500">Lead Time:</span>{' '}
                                  <span className="text-slate-900">{parsed.lead_time}</span>
                                </div>
                              )}
                              {parsed.follow_up_needed && (
                                <div>
                                  <span className="text-amber-600 font-medium">
                                    Follow-up needed
                                  </span>
                                </div>
                              )}
                            </div>
                            {parsed.key_findings.length > 0 && (
                              <div className="mt-2">
                                <span className="text-xs text-slate-500">Key Findings:</span>
                                <ul className="mt-1 space-y-0.5">
                                  {parsed.key_findings.map((finding, i) => (
                                    <li key={i} className="text-xs text-slate-700">
                                      &bull; {finding}
                                    </li>
                                  ))}
                                </ul>
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
    </div>
  )
}
