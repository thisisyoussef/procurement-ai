'use client'

import { useState, useEffect, useCallback } from 'react'
import SearchForm from '@/components/SearchForm'
import PipelineProgress from '@/components/PipelineProgress'
import ClarifyingQuestions from '@/components/ClarifyingQuestions'
import RequirementsCard from '@/components/RequirementsCard'
import SupplierResults from '@/components/SupplierResults'
import ComparisonView from '@/components/ComparisonView'
import RecommendationView from '@/components/RecommendationView'
import ChatPanel from '@/components/ChatPanel'
import OutreachPanel from '@/components/OutreachPanel'
import LogViewer from '@/components/LogViewer'
import ExperienceToggle from '@/features/tamkin/components/ExperienceToggle'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface ProgressEvent {
  stage: string
  substep: string
  detail: string
  progress_pct: number | null
  timestamp: number
}

interface ClarifyingQuestion {
  field: string
  question: string
  importance: string
  suggestions: string[]
}

interface PipelineStatus {
  project_id: string
  status: string
  current_stage: string
  error: string | null
  parsed_requirements: any
  discovery_results: any
  verification_results: any
  comparison_result: any
  recommendation: any
  progress_events?: ProgressEvent[]
  clarifying_questions?: ClarifyingQuestion[] | null
}

interface LegacyHomeProps {
  experienceEnabled: boolean
}

export default function Home({ experienceEnabled }: LegacyHomeProps) {
  const [projectId, setProjectId] = useState<string | null>(null)
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  // Check backend health on mount
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
        setBackendOk(res.ok)
      } catch {
        setBackendOk(false)
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  const pollStatus = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/projects/${id}/status`)
      if (!res.ok) return
      const data: PipelineStatus = await res.json()
      setStatus(data)

      if (data.status === 'complete' || data.status === 'failed') {
        setPolling(false)
        setLoading(false)
      }

      // Pause polling when waiting for user input (clarifying questions)
      if (data.status === 'clarifying') {
        setPolling(false)
        // Keep loading=true so progress bar stays visible
      }
    } catch (err) {
      console.error('Poll error:', err)
    }
  }, [])

  useEffect(() => {
    if (!polling || !projectId) return
    const interval = setInterval(() => pollStatus(projectId), 1000)
    return () => clearInterval(interval)
  }, [polling, projectId, pollStatus])

  const handleSearch = async (description: string) => {
    setLoading(true)
    setStatus(null)
    setErrorMessage(null)

    try {
      const res = await fetch(`${API_BASE}/api/v1/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: description.slice(0, 80),
          product_description: description,
        }),
      })

      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const errBody = await res.json()
          detail = errBody.detail || JSON.stringify(errBody)
        } catch {
          detail += ` — ${res.statusText || 'Unknown error'}`
        }
        throw new Error(detail)
      }

      const data = await res.json()
      setProjectId(data.project_id)
      setPolling(true)
    } catch (err: any) {
      const msg = err?.message || 'Unknown error'
      console.error('Search error:', msg)
      setErrorMessage(
        msg.includes('fetch') || msg.includes('NetworkError') || msg.includes('Failed to fetch')
          ? 'Cannot reach the backend API at ' + (API_BASE || 'this origin') + '. Make sure the backend is running: uvicorn app.main:app --reload --port 8000'
          : msg
      )
      setLoading(false)
    }
  }

  const handleClarifyingAnswered = () => {
    // Resume polling after user answers or skips clarifying questions
    setPolling(true)
  }

  const currentStage = status?.current_stage || 'idle'
  const isClarifying = status?.current_stage === 'clarifying'
  const hasClarifyingQuestions = !!(status?.clarifying_questions && status.clarifying_questions.length > 0)

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <ExperienceToggle enabled={experienceEnabled} />
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">P</span>
            </div>
            <span className="font-semibold text-lg text-slate-900">ProcureAI</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-500">AI-Powered Supplier Discovery</span>
            {backendOk === true && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                API connected
              </span>
            )}
            {backendOk === false && (
              <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span>
                API offline
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {/* Backend offline warning */}
        {backendOk === false && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">Backend API is not reachable</p>
            <p className="text-red-600 text-sm mt-1">
              Start the backend server in a terminal:
            </p>
            <code className="block mt-2 text-sm bg-red-100 text-red-800 px-3 py-2 rounded font-mono">
              cd ~/Development/procurement-ai && uvicorn app.main:app --reload --port 8000
            </code>
            <p className="text-red-500 text-xs mt-2">
              Connecting to: {API_BASE || window.location.origin}
            </p>
          </div>
        )}

        {/* Hero + Search */}
        {!status && !loading && (
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold text-slate-900 mb-3">
              Find the right suppliers, faster
            </h1>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Describe what you need. Our AI searches multiple directories, verifies
              suppliers, and gives you a ranked comparison — in minutes, not weeks.
            </p>
          </div>
        )}

        <SearchForm onSearch={handleSearch} loading={loading} />

        {/* Connection / Request Error */}
        {errorMessage && (
          <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-amber-800 font-medium">Error</p>
            <p className="text-amber-700 text-sm mt-1">{errorMessage}</p>
          </div>
        )}

        {/* Pipeline Progress */}
        {(loading || isClarifying) && (
          <PipelineProgress
            stage={currentStage}
            error={status?.error ?? null}
            progressEvents={status?.progress_events}
            hasClarifyingQuestions={hasClarifyingQuestions}
          />
        )}

        {/* Clarifying Questions — shown when pipeline is paused */}
        {isClarifying && hasClarifyingQuestions && projectId && (
          <ClarifyingQuestions
            projectId={projectId}
            questions={status!.clarifying_questions!}
            onAnswered={handleClarifyingAnswered}
          />
        )}

        {/* Pipeline Error Display */}
        {status?.error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">Pipeline Error</p>
            <p className="text-red-600 text-sm mt-1">{status.error}</p>
          </div>
        )}

        {/* Results — shown progressively as each stage completes */}
        <div className="mt-8 space-y-8">
          {status?.parsed_requirements && (
            <RequirementsCard requirements={status.parsed_requirements} />
          )}

          {status?.discovery_results && (
            <SupplierResults
              discovery={status.discovery_results}
              verifications={status.verification_results}
            />
          )}

          {status?.comparison_result && (
            <ComparisonView comparison={status.comparison_result} />
          )}

          {status?.recommendation && (
            <RecommendationView
              recommendation={status.recommendation}
              suppliers={status.discovery_results?.suppliers}
              verifications={status.verification_results}
              comparisons={status.comparison_result}
              projectId={projectId ?? undefined}
            />
          )}

          {/* Chat + Outreach — shown after pipeline completes */}
          {status?.recommendation && projectId && (
            <>
              <ChatPanel
                projectId={projectId}
                onResultsUpdated={() => pollStatus(projectId)}
              />
              <OutreachPanel
                projectId={projectId}
                recommendations={status.recommendation}
                discoveryResults={status.discovery_results}
                onResultsUpdated={() => pollStatus(projectId)}
              />
            </>
          )}
        </div>

        {/* Live Log Viewer */}
        <LogViewer projectId={projectId} isActive={loading} />
      </div>
    </main>
  )
}
