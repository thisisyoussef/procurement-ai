'use client'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useCallback, useEffect, useMemo, useState } from 'react'

import ChatPanel from '@/components/ChatPanel'
import ClarifyingQuestions from '@/components/ClarifyingQuestions'
import ComparisonView from '@/components/ComparisonView'
import LogViewer from '@/components/LogViewer'
import OutreachPanel from '@/components/OutreachPanel'
import PipelineProgress from '@/components/PipelineProgress'
import RecommendationView from '@/components/RecommendationView'
import RequirementsCard from '@/components/RequirementsCard'
import SearchForm from '@/components/SearchForm'
import SupplierResults from '@/components/SupplierResults'

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

function ProductPageContent() {
  const searchParams = useSearchParams()

  const [projectId, setProjectId] = useState<string | null>(null)
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [polling, setPolling] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [backendOk, setBackendOk] = useState<boolean | null>(null)

  const apiDisplay = useMemo(() => API_BASE || '/api (rewritten to backend)', [])

  useEffect(() => {
    const initialProjectId = searchParams.get('projectId')
    if (initialProjectId) {
      setProjectId(initialProjectId)
      setLoading(true)
      setPolling(true)
    }
  }, [searchParams])

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

      if (data.status === 'clarifying') {
        setPolling(false)
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
          detail += ` - ${res.statusText || 'Unknown error'}`
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
          ? `Cannot reach the backend API at ${API_BASE || 'this origin'}. Make sure the backend is running: uvicorn app.main:app --reload --port 8000`
          : msg
      )
      setLoading(false)
    }
  }

  const handleClarifyingAnswered = () => {
    setPolling(true)
  }

  const currentStage = status?.current_stage || 'idle'
  const isClarifying = status?.current_stage === 'clarifying'
  const hasClarifyingQuestions = !!(status?.clarifying_questions && status.clarifying_questions.length > 0)

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b border-slate-200 bg-white/85 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">T</span>
            </div>
            <div>
              <span className="font-semibold text-lg text-slate-900">Tamkin Product</span>
              <p className="text-xs text-slate-500">Find the right people to make your stuff.</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs px-3 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:border-slate-400"
            >
              Back to landing
            </Link>
            {backendOk === true && (
              <span className="inline-flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                API connected
              </span>
            )}
            {backendOk === false && (
              <span className="inline-flex items-center gap-1 text-xs text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500" />
                API offline
              </span>
            )}
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-10">
        {backendOk === false && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">Backend API is not reachable</p>
            <p className="text-red-600 text-sm mt-1">Start the backend server in a terminal:</p>
            <code className="block mt-2 text-sm bg-red-100 text-red-800 px-3 py-2 rounded font-mono">
              cd ~/Development/procurement-ai && uvicorn app.main:app --reload --port 8000
            </code>
            <p className="text-red-500 text-xs mt-2">Connecting to: {apiDisplay}</p>
          </div>
        )}

        {!status && !loading && (
          <div className="text-center mb-10">
            <h1 className="text-4xl font-bold text-slate-900 mb-3">Start a sourcing mission</h1>
            <p className="text-lg text-slate-600 max-w-2xl mx-auto">
              Tell Tamkin what you need. We discover suppliers, verify them, compare options, and recommend the best path.
            </p>
          </div>
        )}

        <SearchForm onSearch={handleSearch} loading={loading} />

        {errorMessage && (
          <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-amber-800 font-medium">Error</p>
            <p className="text-amber-700 text-sm mt-1">{errorMessage}</p>
          </div>
        )}

        {(loading || isClarifying) && (
          <PipelineProgress
            stage={currentStage}
            error={status?.error ?? null}
            progressEvents={status?.progress_events}
            hasClarifyingQuestions={hasClarifyingQuestions}
          />
        )}

        {isClarifying && hasClarifyingQuestions && projectId && (
          <ClarifyingQuestions
            projectId={projectId}
            questions={status!.clarifying_questions!}
            onAnswered={handleClarifyingAnswered}
          />
        )}

        {status?.error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">Pipeline Error</p>
            <p className="text-red-600 text-sm mt-1">{status.error}</p>
          </div>
        )}

        <div className="mt-8 space-y-8">
          {status?.parsed_requirements && <RequirementsCard requirements={status.parsed_requirements} />}

          {status?.discovery_results && (
            <SupplierResults
              discovery={status.discovery_results}
              verifications={status.verification_results}
            />
          )}

          {status?.comparison_result && <ComparisonView comparison={status.comparison_result} />}

          {status?.recommendation && (
            <RecommendationView
              recommendation={status.recommendation}
              suppliers={status.discovery_results?.suppliers}
              verifications={status.verification_results}
              comparisons={status.comparison_result}
              projectId={projectId ?? undefined}
            />
          )}

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

        <LogViewer projectId={projectId} isActive={loading} />
      </div>
    </main>
  )
}

export default function ProductPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-slate-50" />}>
      <ProductPageContent />
    </Suspense>
  )
}
