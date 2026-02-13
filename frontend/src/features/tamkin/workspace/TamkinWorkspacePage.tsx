'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertTriangle,
  ArrowLeft,
  Check,
  ChevronRight,
  Clock3,
  Inbox,
  Loader2,
  MessageSquare,
  Save,
  Send,
  ShieldCheck,
  Sparkles,
  Timer,
  X,
} from 'lucide-react'

import ExperienceToggle from '@/features/tamkin/components/ExperienceToggle'
import {
  getChatHistory,
  getMissionStatus,
  getOutreachPlan,
  getOutreachTimeline,
  listSavedMissions,
  loadApprovalStates,
  saveApprovalStates,
  skipClarifyingQuestions,
  streamMissionChat,
  submitClarifyingAnswers,
  upsertSavedMission,
} from '@/lib/api/tamkinClient'
import type {
  AgentTimelineEvent,
  ApprovalRequest,
  ApprovalStatus,
  ChatHistoryMessage,
  ClarifyingQuestion,
  MissionSummary,
  OutreachPlanResponse,
  OutreachTimelineResponse,
  PipelineStatusResponse,
  PipelineProgressEvent,
} from '@/lib/contracts/tamkin'
import { TAMKIN_COPY, TAMKIN_CORE_LINE } from '@/features/tamkin/copy/voice'

interface WorkspaceProps {
  projectId: string
  experienceEnabled: boolean
}

type TimelineMode = 'inbox' | 'timeline'
type FilterPreset = 'all' | 'decisions' | 'supplier' | 'risk'

function asArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

function toMessageFromProgress(event: PipelineProgressEvent, idx: number): AgentTimelineEvent {
  const severity = event.stage === 'failed' ? 'error' : event.progress_pct === 100 ? 'success' : 'info'

  return {
    id: `progress-${event.timestamp}-${idx}`,
    type: event.substep || event.stage,
    at: event.timestamp,
    stage: event.stage,
    message: event.detail || event.substep || `Pipeline stage: ${event.stage}`,
    source: 'pipeline',
    severity,
  }
}

function severityForOutreachType(type: string): AgentTimelineEvent['severity'] {
  if (type.includes('failed') || type.includes('error') || type.includes('bounce')) return 'error'
  if (type.includes('approval') || type.includes('intent') || type.includes('draft')) return 'warning'
  if (type.includes('sent') || type.includes('completed') || type.includes('parsed')) return 'success'
  return 'info'
}

function toMessageFromOutreachEvent(
  event: OutreachTimelineResponse['events'][number],
  idx: number
): AgentTimelineEvent {
  const details = event.details || {}
  const supplier = event.supplier_name ? ` (${event.supplier_name})` : ''
  const detailText = Object.entries(details)
    .slice(0, 2)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(' · ')

  return {
    id: `outreach-${event.timestamp}-${idx}`,
    type: event.event_type,
    at: event.timestamp,
    stage: 'outreach',
    message: `${event.event_type.replace(/_/g, ' ')}${supplier}${detailText ? ` · ${detailText}` : ''}`,
    source: 'outreach',
    severity: severityForOutreachType(event.event_type),
  }
}

function buildTimeline(
  status: PipelineStatusResponse | null,
  outreachTimeline: OutreachTimelineResponse | null
): AgentTimelineEvent[] {
  const progressEvents = asArray<PipelineProgressEvent>(status?.progress_events).map(toMessageFromProgress)
  const outreachEvents = asArray<OutreachTimelineResponse['events'][number]>(outreachTimeline?.events).map(
    toMessageFromOutreachEvent
  )

  return [...progressEvents, ...outreachEvents].sort((a, b) => b.at - a.at)
}

function mapCurrentStageToMissionStatus(stage: string): MissionSummary['status'] {
  if (stage === 'complete') return 'complete'
  if (stage === 'failed') return 'failed'
  if (stage === 'clarifying') return 'waiting_approval'
  return 'running'
}

function deriveMissionSummary(projectId: string, status: PipelineStatusResponse | null): MissionSummary {
  const reqs = (status?.parsed_requirements || {}) as Record<string, unknown>
  const discovery = (status?.discovery_results || {}) as Record<string, unknown>
  const suppliers = asArray<Record<string, unknown>>(discovery.suppliers)

  const sourceBreakdown = suppliers.reduce<{ web: number; directories: number; supplierMemory: number }>(
    (acc, supplier) => {
      const source = String(supplier.source || '').toLowerCase()
      if (source.includes('google') || source.includes('firecrawl')) {
        acc.web += 1
      } else if (source.includes('marketplace') || source.includes('regional')) {
        acc.directories += 1
      } else {
        acc.supplierMemory += 1
      }
      return acc
    },
    { web: 0, directories: 0, supplierMemory: 0 }
  )

  const title = String(reqs.product_type || reqs.material || `Mission ${projectId.slice(0, 6)}`)

  return {
    id: projectId,
    title,
    status: mapCurrentStageToMissionStatus(status?.current_stage || 'running'),
    updatedAt: Date.now(),
    sourceBreakdown,
  }
}

function generateApprovalRequests(
  projectId: string,
  status: PipelineStatusResponse | null,
  approvalStates: Record<string, Exclude<ApprovalStatus, 'pending'>>
): ApprovalRequest[] {
  const recommendation = status?.recommendation || null
  const outreachState = status?.outreach_state || null

  const approvals: Omit<ApprovalRequest, 'status'>[] = []

  if (recommendation) {
    approvals.push({
      id: `${projectId}-shortlist_lock`,
      kind: 'shortlist_lock',
      title: 'Lock supplier shortlist',
      context: 'Your agent produced ranked options. Lock shortlist before advancing to outreach.',
      recommendedAction: 'Approve shortlist lock-in',
    })
  }

  const draftCount = asArray<Record<string, unknown>>(outreachState?.draft_emails).filter(
    (draft) => String(draft.status || '').toLowerCase() === 'draft'
  ).length

  if (draftCount > 0) {
    approvals.push({
      id: `${projectId}-outbound_send`,
      kind: 'outbound_send',
      title: 'Approve outbound outreach',
      context: `${draftCount} draft message${draftCount > 1 ? 's are' : ' is'} ready for supplier contact.`,
      recommendedAction: 'Approve send sequence',
    })
  }

  const parsedQuotesCount = asArray<Record<string, unknown>>(outreachState?.parsed_quotes).length
  if (parsedQuotesCount > 0) {
    approvals.push({
      id: `${projectId}-final_selection`,
      kind: 'final_selection',
      title: 'Approve final supplier decision',
      context: `Quotes have been parsed from ${parsedQuotesCount} supplier${parsedQuotesCount > 1 ? 's' : ''}.`,
      recommendedAction: 'Approve final selection',
    })
  }

  return approvals.map((item) => ({
    ...item,
    status: approvalStates[item.id] || 'pending',
  }))
}

function isAttentionEvent(event: AgentTimelineEvent): boolean {
  return event.severity === 'error' || event.severity === 'warning'
}

function formatTimestamp(timestamp: number): string {
  if (!timestamp) return 'Just now'
  return new Date(timestamp * 1000 > Date.now() + 1000 ? timestamp : timestamp * 1000).toLocaleString()
}

const FILTER_PRESETS: { key: FilterPreset; label: string }[] = [
  { key: 'all', label: 'All activity' },
  { key: 'decisions', label: 'Decision points' },
  { key: 'supplier', label: 'Supplier updates' },
  { key: 'risk', label: 'Risk alerts' },
]

export default function TamkinWorkspacePage({ projectId, experienceEnabled }: WorkspaceProps) {
  const router = useRouter()
  const [status, setStatus] = useState<PipelineStatusResponse | null>(null)
  const [chatHistory, setChatHistory] = useState<ChatHistoryMessage[]>([])
  const [outreachPlan, setOutreachPlan] = useState<OutreachPlanResponse | null>(null)
  const [outreachTimeline, setOutreachTimeline] = useState<OutreachTimelineResponse | null>(null)
  const [savedMissions, setSavedMissions] = useState<MissionSummary[]>([])
  const [approvalStates, setApprovalStates] = useState<Record<string, 'approved' | 'rejected'>>({})

  const [timelineMode, setTimelineMode] = useState<TimelineMode>('inbox')
  const [filterPreset, setFilterPreset] = useState<FilterPreset>('all')

  const [composerValue, setComposerValue] = useState('')
  const [streamingText, setStreamingText] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [actionStatus, setActionStatus] = useState<string | null>(null)

  const [clarifyingAnswers, setClarifyingAnswers] = useState<Record<string, string>>({})
  const [clarifyingBusy, setClarifyingBusy] = useState(false)

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadWorkspaceData = useCallback(async () => {
    try {
      const [statusData, historyData, planData, timelineData] = await Promise.all([
        getMissionStatus(projectId),
        getChatHistory(projectId),
        getOutreachPlan(projectId).catch(() => null),
        getOutreachTimeline(projectId).catch(() => null),
      ])

      setStatus(statusData)
      setChatHistory(historyData)
      setOutreachPlan(planData)
      setOutreachTimeline(timelineData)
      setError(null)
    } catch (err: any) {
      setError(err?.message || 'Could not load mission workspace.')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    setSavedMissions(listSavedMissions())
    setApprovalStates(loadApprovalStates(projectId))
    void loadWorkspaceData()
  }, [projectId, loadWorkspaceData])

  useEffect(() => {
    if (!status) return
    if (status.current_stage === 'complete' || status.current_stage === 'failed') return

    const interval = setInterval(() => {
      void loadWorkspaceData()
    }, 2500)

    return () => clearInterval(interval)
  }, [status, loadWorkspaceData])

  const timelineEvents = useMemo(() => buildTimeline(status, outreachTimeline), [status, outreachTimeline])

  const approvals = useMemo(
    () => generateApprovalRequests(projectId, status, approvalStates),
    [projectId, status, approvalStates]
  )

  const missionSummary = useMemo(() => deriveMissionSummary(projectId, status), [projectId, status])

  const visibleEvents = useMemo(() => {
    let events = timelineMode === 'inbox' ? timelineEvents.filter(isAttentionEvent) : [...timelineEvents]

    if (filterPreset === 'decisions') {
      events = events.filter(
        (event) =>
          event.stage.includes('recommend') ||
          event.stage.includes('compare') ||
          event.type.includes('approve') ||
          event.type.includes('decision')
      )
    }

    if (filterPreset === 'supplier') {
      events = events.filter((event) => event.source === 'outreach')
    }

    if (filterPreset === 'risk') {
      events = events.filter((event) => event.severity === 'warning' || event.severity === 'error')
    }

    return events.slice(0, 80)
  }, [timelineMode, timelineEvents, filterPreset])

  const recommendationList = asArray<Record<string, unknown>>((status?.recommendation || {}).recommendations)
  const clarifyingQuestions = asArray<ClarifyingQuestion>(status?.clarifying_questions)

  const persistApprovals = (nextState: Record<string, 'approved' | 'rejected'>) => {
    setApprovalStates(nextState)
    saveApprovalStates(projectId, nextState)
  }

  const updateApproval = (approval: ApprovalRequest, decision: 'approved' | 'rejected') => {
    persistApprovals({ ...approvalStates, [approval.id]: decision })
  }

  const saveCurrentMission = () => {
    const next = upsertSavedMission(missionSummary)
    setSavedMissions(next)
  }

  const sendMessage = async () => {
    const message = composerValue.trim()
    if (!message || isStreaming) return

    setComposerValue('')
    setActionStatus(null)
    setError(null)
    setIsStreaming(true)
    setStreamingText('')
    setChatHistory((prev) => [...prev, { role: 'user', content: message, timestamp: Date.now() / 1000 }])

    let fullText = ''

    try {
      await streamMissionChat(projectId, message, (event) => {
        if (event.type === 'token') {
          fullText += event.content
          setStreamingText(fullText)
          return
        }

        if (event.type === 'action_result') {
          setActionStatus(event.result)
          return
        }

        if (event.type === 'error') {
          setActionStatus(event.message)
        }
      })

      if (fullText.trim()) {
        setChatHistory((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: fullText,
            timestamp: Date.now() / 1000,
          },
        ])
      }

      await loadWorkspaceData()
    } catch (err: any) {
      setError(err?.message || 'Could not send message to Tamkin.')
    } finally {
      setIsStreaming(false)
      setStreamingText('')
    }
  }

  const submitClarifying = async () => {
    const filtered = Object.fromEntries(
      Object.entries(clarifyingAnswers).filter(([, value]) => value.trim().length > 0)
    )

    setClarifyingBusy(true)
    try {
      if (Object.keys(filtered).length > 0) {
        await submitClarifyingAnswers(projectId, filtered)
      } else {
        await skipClarifyingQuestions(projectId)
      }
      setClarifyingAnswers({})
      await loadWorkspaceData()
    } catch (err: any) {
      setError(err?.message || 'Could not submit clarifying answers.')
    } finally {
      setClarifyingBusy(false)
    }
  }

  const currentStage = status?.current_stage || 'loading'
  const stageLabel = currentStage.replace(/_/g, ' ')

  return (
    <main className="tamkin-shell min-h-screen px-4 pb-8 pt-4 lg:px-6">
      <ExperienceToggle enabled={experienceEnabled} />
      <div className="tamkin-bg-orbs" aria-hidden />

      <header className="mb-4 rounded-2xl border border-white/10 bg-[rgba(8,16,24,0.84)] px-4 py-3 backdrop-blur-xl">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push('/')}
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-[#dce7f3] transition hover:bg-white/10"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Landing
            </button>
            <div>
              <p className="tamkin-display text-xl text-[#fff4dc]">Tamkin</p>
              <p className="text-xs text-[#94a9bf]">Mission {projectId.slice(0, 8)}</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full border border-[#f3cb8b55] bg-[#f3cb8b1c] px-3 py-1 text-[#f5d9ab]">
              Stage: {stageLabel}
            </span>
            <span className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[#dce6f2]">
              {TAMKIN_CORE_LINE}
            </span>
          </div>
        </div>
      </header>

      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
        <aside className="space-y-4">
          <section className="rounded-2xl border border-white/10 bg-white/[0.045] p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-[#f8f1e6]">Current mission</h2>
              <span className="rounded-full border border-white/15 px-2 py-0.5 text-[11px] text-[#9fb4ca]">
                {missionSummary.status}
              </span>
            </div>
            <p className="mt-2 text-sm text-[#d6e0eb]">{missionSummary.title}</p>

            <div className="mt-3 grid grid-cols-3 gap-2 text-center text-[11px]">
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="font-semibold text-[#f4d09a]">{missionSummary.sourceBreakdown.web}</p>
                <p className="text-[#8ea4bb]">Web</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="font-semibold text-[#f4d09a]">{missionSummary.sourceBreakdown.directories}</p>
                <p className="text-[#8ea4bb]">Directories</p>
              </div>
              <div className="rounded-lg border border-white/10 bg-black/20 p-2">
                <p className="font-semibold text-[#f4d09a]">{missionSummary.sourceBreakdown.supplierMemory}</p>
                <p className="text-[#8ea4bb]">Memory</p>
              </div>
            </div>

            <button
              onClick={saveCurrentMission}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 bg-white/5 px-3 py-2 text-xs text-[#d7e2ee] transition hover:bg-white/10"
            >
              <Save className="h-3.5 w-3.5" />
              Save mission snapshot
            </button>
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <h3 className="text-sm font-semibold text-[#f8f1e6]">Saved missions</h3>
            <div className="mt-3 space-y-2">
              {savedMissions.length === 0 && <p className="text-xs text-[#91a6bc]">No saved missions yet.</p>}
              {savedMissions.map((mission) => (
                <button
                  key={mission.id}
                  onClick={() => router.push(`/workspace/${mission.id}`)}
                  className="flex w-full items-start justify-between rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-left transition hover:border-[#f3cb8b55] hover:bg-black/30"
                >
                  <span>
                    <span className="block text-xs font-medium text-[#e8eef6]">{mission.title}</span>
                    <span className="block text-[11px] text-[#8ea4bb]">{mission.id.slice(0, 8)}</span>
                  </span>
                  <ChevronRight className="h-4 w-4 text-[#91a7be]" />
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <h3 className="text-sm font-semibold text-[#f8f1e6]">Filter presets</h3>
            <div className="mt-3 grid gap-2">
              {FILTER_PRESETS.map((preset) => (
                <button
                  key={preset.key}
                  onClick={() => setFilterPreset(preset.key)}
                  className={`rounded-xl px-3 py-2 text-left text-xs transition ${
                    filterPreset === preset.key
                      ? 'border border-[#f3cb8b88] bg-[#f3cb8b1c] text-[#f7dfba]'
                      : 'border border-white/10 bg-black/20 text-[#c6d3e1] hover:bg-black/30'
                  }`}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </section>
        </aside>

        <section className="rounded-2xl border border-white/10 bg-[linear-gradient(165deg,#0f1824,#0b141d)] p-4 md:p-5">
          <header className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
            <div>
              <h1 className="tamkin-display text-3xl text-[#fff2db]">{TAMKIN_COPY.workspaceTitle}</h1>
              <p className="text-sm text-[#a8bdd3]">{TAMKIN_COPY.workspaceSubtitle}</p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1.5 text-xs text-[#d8e4f0]">
              <Timer className="h-3.5 w-3.5 text-[#f5d9ab]" />
              Live mission thread
            </div>
          </header>

          {isLoading ? (
            <div className="flex h-[420px] items-center justify-center text-[#ced9e5]">
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading mission workspace...
            </div>
          ) : (
            <>
              {status?.current_stage === 'clarifying' && clarifyingQuestions.length > 0 && (
                <div className="mb-4 rounded-2xl border border-amber-300/30 bg-amber-500/10 p-4">
                  <p className="text-sm font-semibold text-amber-100">Quick clarifying questions</p>
                  <p className="mt-1 text-xs text-amber-50/90">
                    Tamkin needs a couple details before searching. Answer what you can.
                  </p>

                  <div className="mt-3 space-y-3">
                    {clarifyingQuestions.map((question) => (
                      <label key={question.field} className="block space-y-1">
                        <span className="text-xs text-[#f8ebcf]">{question.question}</span>
                        <input
                          value={clarifyingAnswers[question.field] || ''}
                          onChange={(event) =>
                            setClarifyingAnswers((prev) => ({
                              ...prev,
                              [question.field]: event.target.value,
                            }))
                          }
                          placeholder={question.suggestions?.[0] || 'Type your answer'}
                          className="w-full rounded-xl border border-amber-200/40 bg-black/20 px-3 py-2 text-sm text-[#fff4e1] placeholder:text-[#ceb88e]"
                        />
                      </label>
                    ))}
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      onClick={submitClarifying}
                      disabled={clarifyingBusy}
                      className="rounded-full bg-[#f3cb8b] px-4 py-2 text-xs font-semibold text-[#302010] disabled:opacity-60"
                    >
                      {clarifyingBusy ? 'Submitting...' : 'Continue mission'}
                    </button>
                    <button
                      onClick={async () => {
                        setClarifyingBusy(true)
                        try {
                          await skipClarifyingQuestions(projectId)
                          await loadWorkspaceData()
                        } finally {
                          setClarifyingBusy(false)
                        }
                      }}
                      disabled={clarifyingBusy}
                      className="rounded-full border border-amber-200/40 px-4 py-2 text-xs text-amber-100 disabled:opacity-60"
                    >
                      Skip for now
                    </button>
                  </div>
                </div>
              )}

              <div className="mb-4 flex h-[430px] flex-col gap-3 overflow-y-auto pr-1">
                {chatHistory.length === 0 && !streamingText && (
                  <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-sm text-[#9fb2c8]">
                    Start with your next question. Tamkin will explain what it is doing and ask for approvals only when needed.
                  </div>
                )}

                {chatHistory.map((message, idx) => {
                  const isUser = message.role === 'user'
                  return (
                    <div key={`${idx}-${message.timestamp || idx}`} className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
                      <article
                        className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                          isUser
                            ? 'border border-[#f3cb8b5c] bg-[#f3cb8b22] text-[#fff2dd]'
                            : 'border border-white/10 bg-white/[0.045] text-[#d6e2ef]'
                        }`}
                      >
                        {message.content}
                      </article>
                    </div>
                  )
                })}

                {streamingText && (
                  <div className="flex justify-start">
                    <article className="max-w-[88%] rounded-2xl border border-[#73b9ff55] bg-[#73b9ff1a] px-4 py-3 text-sm text-[#eaf5ff]">
                      {streamingText}
                      <span className="ml-1 inline-block h-4 w-1 animate-pulse rounded bg-[#9fd1ff] align-middle" />
                    </article>
                  </div>
                )}
              </div>

              {actionStatus && (
                <div className="mb-3 rounded-xl border border-[#f3cb8b66] bg-[#f3cb8b20] px-3 py-2 text-xs text-[#f8e1bd]">
                  {actionStatus}
                </div>
              )}

              {error && (
                <div className="mb-3 rounded-xl border border-red-300/40 bg-red-500/15 px-3 py-2 text-xs text-red-100">
                  {error}
                </div>
              )}

              <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
                <div className="mb-2 flex flex-wrap gap-2">
                  {['Why this ranking?', 'Prioritize speed over price', 'Draft outreach for top 3'].map((chip) => (
                    <button
                      key={chip}
                      onClick={() => setComposerValue(chip)}
                      className="rounded-full border border-white/15 bg-white/5 px-3 py-1 text-[11px] text-[#d2deeb] hover:bg-white/10"
                    >
                      {chip}
                    </button>
                  ))}
                </div>

                <div className="flex items-end gap-2">
                  <textarea
                    value={composerValue}
                    onChange={(event) => setComposerValue(event.target.value)}
                    placeholder="Tell Tamkin what you need next..."
                    rows={2}
                    className="min-h-[72px] flex-1 resize-none rounded-xl border border-white/15 bg-white/[0.05] px-3 py-2 text-sm text-[#e9f1fb] placeholder:text-[#8aa0b9] focus:border-[#f3cb8b88] focus:outline-none"
                  />
                  <button
                    onClick={sendMessage}
                    disabled={isStreaming || !composerValue.trim()}
                    className="tamkin-cta inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isStreaming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                    Send
                  </button>
                </div>
              </div>
            </>
          )}
        </section>

        <aside className="space-y-4">
          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <div className="mb-3 flex gap-2">
              <button
                onClick={() => setTimelineMode('inbox')}
                className={`inline-flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-1.5 text-xs ${
                  timelineMode === 'inbox'
                    ? 'border border-[#f3cb8b8c] bg-[#f3cb8b20] text-[#f7deba]'
                    : 'border border-white/15 bg-white/5 text-[#cad8e7]'
                }`}
              >
                <Inbox className="h-3.5 w-3.5" />
                Inbox
              </button>
              <button
                onClick={() => setTimelineMode('timeline')}
                className={`inline-flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-1.5 text-xs ${
                  timelineMode === 'timeline'
                    ? 'border border-[#f3cb8b8c] bg-[#f3cb8b20] text-[#f7deba]'
                    : 'border border-white/15 bg-white/5 text-[#cad8e7]'
                }`}
              >
                <Clock3 className="h-3.5 w-3.5" />
                Timeline
              </button>
            </div>

            <h3 className="text-sm font-semibold text-[#f8f1e6]">{TAMKIN_COPY.approvalsTitle}</h3>
            <div className="mt-3 space-y-2">
              {approvals.length === 0 && (
                <p className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs text-[#93a8be]">
                  No pending decisions right now.
                </p>
              )}

              {approvals.map((approval) => (
                <article key={approval.id} className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <p className="text-xs font-semibold text-[#f4e2c2]">{approval.title}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-[#adbdd0]">{approval.context}</p>

                  <div className="mt-2 flex items-center justify-between">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-wide ${
                        approval.status === 'approved'
                          ? 'bg-emerald-500/20 text-emerald-100'
                          : approval.status === 'rejected'
                          ? 'bg-red-500/20 text-red-100'
                          : 'bg-amber-500/20 text-amber-100'
                      }`}
                    >
                      {approval.status}
                    </span>

                    {approval.status === 'pending' && (
                      <div className="flex gap-1">
                        <button
                          onClick={() => updateApproval(approval, 'approved')}
                          className="rounded-full border border-emerald-300/50 bg-emerald-500/20 p-1 text-emerald-100"
                          aria-label="Approve"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                        <button
                          onClick={() => updateApproval(approval, 'rejected')}
                          className="rounded-full border border-red-300/50 bg-red-500/20 p-1 text-red-100"
                          aria-label="Reject"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
            <h3 className="text-sm font-semibold text-[#f8f1e6]">{TAMKIN_COPY.timelineTitle}</h3>

            {outreachPlan && (
              <div className="mt-3 grid grid-cols-2 gap-2 rounded-xl border border-white/10 bg-black/20 p-3 text-[11px] text-[#b8c6d6]">
                <div>
                  <p className="text-[#8ea4bb]">Intent</p>
                  <p className="font-semibold text-[#f5dfbc]">{outreachPlan.funnel.intent}</p>
                </div>
                <div>
                  <p className="text-[#8ea4bb]">RFQs sent</p>
                  <p className="font-semibold text-[#f5dfbc]">{outreachPlan.funnel.rfq_sent}</p>
                </div>
                <div>
                  <p className="text-[#8ea4bb]">Responses</p>
                  <p className="font-semibold text-[#f5dfbc]">{outreachPlan.funnel.responses}</p>
                </div>
                <div>
                  <p className="text-[#8ea4bb]">Quotes parsed</p>
                  <p className="font-semibold text-[#f5dfbc]">{outreachPlan.funnel.quotes_parsed}</p>
                </div>
              </div>
            )}

            <div className="mt-3 max-h-[430px] space-y-2 overflow-y-auto pr-1">
              {visibleEvents.length === 0 && (
                <p className="rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-xs text-[#91a6bc]">
                  No events for this view yet.
                </p>
              )}

              {visibleEvents.map((event) => (
                <article key={event.id} className="rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-medium text-[#e4edf8]">{event.message}</p>
                    <span
                      className={`mt-0.5 inline-flex rounded-full px-2 py-0.5 text-[10px] ${
                        event.severity === 'error'
                          ? 'bg-red-500/20 text-red-100'
                          : event.severity === 'warning'
                          ? 'bg-amber-500/20 text-amber-100'
                          : event.severity === 'success'
                          ? 'bg-emerald-500/20 text-emerald-100'
                          : 'bg-sky-500/20 text-sky-100'
                      }`}
                    >
                      {event.severity}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[10px] text-[#8fa5bc]">
                    <span className="inline-flex items-center gap-1"><Sparkles className="h-3 w-3" /> {event.source}</span>
                    <span>{formatTimestamp(event.at)}</span>
                  </div>
                </article>
              ))}
            </div>

            {timelineMode === 'inbox' && (
              <p className="mt-3 text-[11px] text-[#91a6bc]">
                Inbox view surfaces risk and decision signals first.
              </p>
            )}
          </section>

          <section className="rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-xs text-[#afbed0]">
            <p className="mb-1 font-semibold text-[#f2dfbc]">Tamkin voice check</p>
            <p className="flex items-start gap-2"><MessageSquare className="mt-0.5 h-3.5 w-3.5 text-[#73b9ff]" /> Plain language first. Specific actions always visible.</p>
            <p className="mt-2 flex items-start gap-2"><ShieldCheck className="mt-0.5 h-3.5 w-3.5 text-[#77d8a2]" /> Approvals only on high-impact decisions.</p>
            <p className="mt-2 flex items-start gap-2"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 text-[#f5d091]" /> Risk events stay pinned in inbox mode.</p>
          </section>
        </aside>
      </div>
    </main>
  )
}
