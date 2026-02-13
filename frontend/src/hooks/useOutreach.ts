'use client'

import { useState, useEffect, useCallback } from 'react'
import { authFetch } from '@/lib/auth'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

// ─── Types ──────────────────────────────────────────────

export interface DraftEmail {
  supplier_name: string
  supplier_index: number
  recipient_email: string | null
  subject: string
  body: string
  status: string
}

export interface SupplierOutreachStatus {
  supplier_name: string
  supplier_index: number
  email_sent: boolean
  response_received: boolean
  follow_ups_sent: number
  parsed_quote: ParsedQuote | null
}

export interface ParsedQuote {
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

export interface FollowUpEmail {
  supplier_name: string
  supplier_index: number
  subject: string
  body: string
  follow_up_number: number
  status: string
}

export interface OutreachState {
  selected_suppliers: number[]
  supplier_statuses: SupplierOutreachStatus[]
  draft_emails: DraftEmail[]
  follow_up_emails: FollowUpEmail[]
  parsed_quotes: ParsedQuote[]
}

export interface PhoneCallStatus {
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

export interface ParsedCallResult {
  supplier_name: string
  call_id: string
  pricing_info: string | null
  moq: string | null
  lead_time: string | null
  key_findings: string[]
  follow_up_needed: boolean
}

export interface PhoneConfig {
  enabled: boolean
  voice_id: string
  max_call_duration_seconds: number
  questions_to_ask: string[]
}

export interface Recommendation {
  rank: number
  supplier_name: string
  supplier_index: number
  overall_score: number
  best_for: string
}

export interface Supplier {
  name: string
  email: string | null
  phone: string | null
}

export type OutreachTab =
  | 'select'
  | 'drafts'
  | 'tracking'
  | 'responses'
  | 'quotes'
  | 'followups'
  | 'auto'
  | 'phone'

// ─── Hook ───────────────────────────────────────────────

interface UseOutreachOptions {
  onResultsUpdated?: () => void
}

export function useOutreach(
  projectId: string | null,
  recommendations: { recommendations: Recommendation[] } | null,
  discoveryResults: { suppliers: Supplier[] } | null,
  options?: UseOutreachOptions
) {
  const [tab, setTab] = useState<OutreachTab>('select')
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
        recommendations.recommendations.slice(0, 3).map((r) => r.supplier_index)
      )
    }
  }, [recommendations])

  // ─── API Calls ──────────────────────────────────────────

  const fetchOutreachStatus = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await authFetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/status`
      )
      if (res.ok) {
        const data = await res.json()
        if (!data.error) setOutreachState(data)
      }
    } catch {}
  }, [projectId])

  useEffect(() => {
    if (projectId) fetchOutreachStatus()
  }, [projectId, fetchOutreachStatus])

  const toggleSupplier = useCallback((idx: number) => {
    setSelectedIndices((prev) =>
      prev.includes(idx) ? prev.filter((i) => i !== idx) : [...prev, idx]
    )
  }, [])

  const startOutreach = useCallback(async () => {
    if (selectedIndices.length === 0 || !projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
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
  }, [selectedIndices, projectId, fetchOutreachStatus])

  const approveAndSend = useCallback(
    async (draftIndex: number) => {
      if (!projectId) return
      setLoading(true)
      setError(null)
      try {
        const body: any = { draft_index: draftIndex }
        if (editingDraft === draftIndex) {
          body.edited_subject = editSubject
          body.edited_body = editBody
          setEditingDraft(null)
        }
        const res = await authFetch(
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
    },
    [projectId, editingDraft, editSubject, editBody, fetchOutreachStatus]
  )

  const parseResponse = useCallback(async () => {
    if (parseSupplierIdx === null || !responseText.trim() || !projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
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
  }, [parseSupplierIdx, responseText, projectId, fetchOutreachStatus])

  const generateFollowUps = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
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
  }, [projectId, fetchOutreachStatus])

  const recompare = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/recompare`,
        { method: 'POST' }
      )
      if (!res.ok) throw new Error(await res.text())
      options?.onResultsUpdated?.()
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [projectId, options?.onResultsUpdated])

  const fetchAutoStatus = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await authFetch(
        `${API_BASE}/api/v1/projects/${projectId}/outreach/auto-status`
      )
      if (res.ok) {
        const data = await res.json()
        setAutoStatus(data)
      }
    } catch {}
  }, [projectId])

  const configureAutoOutreach = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
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
  }, [projectId, autoThreshold, fetchAutoStatus])

  const startAutoOutreach = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
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
  }, [projectId, fetchOutreachStatus, fetchAutoStatus])

  // ─── Phone Calling ────────────────────────────────────

  const fetchPhoneCalls = useCallback(async () => {
    if (!projectId) return
    try {
      const res = await authFetch(
        `${API_BASE}/api/v1/projects/${projectId}/phone/calls`
      )
      if (res.ok) {
        const data = await res.json()
        setPhoneCalls(data.calls || [])
        if (data.config) setPhoneConfig(data.config)
      }
    } catch {}
  }, [projectId])

  const savePhoneConfig = useCallback(async () => {
    if (!projectId) return
    setLoading(true)
    setError(null)
    try {
      const res = await authFetch(
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
  }, [projectId, phoneConfig])

  const startPhoneCall = useCallback(async () => {
    if (callSupplierIdx === null || !callPhoneNumber.trim() || !projectId) return
    setLoading(true)
    setError(null)
    try {
      const questions = callQuestions.trim()
        ? callQuestions.split('\n').filter((q) => q.trim())
        : []
      const res = await authFetch(
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
  }, [callSupplierIdx, callPhoneNumber, callQuestions, projectId, fetchPhoneCalls])

  const refreshCallStatus = useCallback(
    async (callId: string) => {
      if (!projectId) return
      try {
        const res = await authFetch(
          `${API_BASE}/api/v1/projects/${projectId}/phone/calls/${callId}`
        )
        if (res.ok) {
          await fetchPhoneCalls()
        }
      } catch {}
    },
    [projectId, fetchPhoneCalls]
  )

  const parseCallTranscript = useCallback(
    async (callId: string) => {
      if (!projectId) return
      setLoading(true)
      setError(null)
      try {
        const res = await authFetch(
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
    },
    [projectId, fetchPhoneCalls]
  )

  // Fetch phone calls when switching to phone tab
  useEffect(() => {
    if (tab === 'phone' && projectId) {
      fetchPhoneCalls()
    }
  }, [tab, projectId, fetchPhoneCalls])

  return {
    // Tab
    tab,
    setTab,
    // Selection
    selectedIndices,
    toggleSupplier,
    // State
    outreachState,
    loading,
    error,
    setError,
    // Draft editing
    editingDraft,
    setEditingDraft,
    editSubject,
    setEditSubject,
    editBody,
    setEditBody,
    // Response parsing
    parseSupplierIdx,
    setParseSupplierIdx,
    responseText,
    setResponseText,
    // Auto outreach
    autoThreshold,
    setAutoThreshold,
    autoStatus,
    // Phone
    phoneCalls,
    phoneConfig,
    setPhoneConfig,
    callPhoneNumber,
    setCallPhoneNumber,
    callSupplierIdx,
    setCallSupplierIdx,
    callQuestions,
    setCallQuestions,
    expandedTranscript,
    setExpandedTranscript,
    parsedCallResults,
    // Actions
    startOutreach,
    approveAndSend,
    parseResponse,
    generateFollowUps,
    recompare,
    configureAutoOutreach,
    startAutoOutreach,
    fetchOutreachStatus,
    fetchAutoStatus,
    // Phone actions
    fetchPhoneCalls,
    savePhoneConfig,
    startPhoneCall,
    refreshCallStatus,
    parseCallTranscript,
  }
}
