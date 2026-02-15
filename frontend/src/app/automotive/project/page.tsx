'use client'

import { useEffect, useState, useCallback, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { automotiveClient, type ProjectDetail } from '@/lib/automotive/client'
import { STAGE_LABELS, STAGE_ORDER, type PipelineStage } from '@/types/automotive'
import PipelineNav from '@/components/automotive/workspace/PipelineNav'
import RequirementsView from '@/components/automotive/phases/RequirementsView'
import DiscoveryView from '@/components/automotive/phases/DiscoveryView'
import QualificationView from '@/components/automotive/phases/QualificationView'
import ComparisonView from '@/components/automotive/phases/ComparisonView'
import ReportsView from '@/components/automotive/phases/ReportsView'
import RFQView from '@/components/automotive/phases/RFQView'
import QuotesView from '@/components/automotive/phases/QuotesView'
import CompleteView from '@/components/automotive/phases/CompleteView'
import ActivityConsole from '@/components/automotive/workspace/ActivityConsole'

function ProjectContent() {
  const params = useSearchParams()
  const router = useRouter()
  const projectId = params.get('id')
  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [activeTab, setActiveTab] = useState<PipelineStage>('parse')
  const [error, setError] = useState<string | null>(null)

  const loadProject = useCallback(async () => {
    if (!projectId) return
    try {
      const data = await automotiveClient.getProject(projectId)
      setProject(data)
      setActiveTab(data.current_stage as PipelineStage)
    } catch (e: any) {
      setError(e.message)
    }
  }, [projectId])

  useEffect(() => {
    loadProject()
    const interval = setInterval(loadProject, 5000)
    return () => clearInterval(interval)
  }, [loadProject])

  const handleApprove = async (stage: string, decision: Record<string, unknown>) => {
    if (!projectId) return
    try {
      await automotiveClient.approveStage(projectId, {
        stage,
        approved: true,
        ...decision,
      })
      await loadProject()
    } catch (e: any) {
      setError(e.message)
    }
  }

  if (!projectId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <p className="text-zinc-500">No project ID specified.</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-12">
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
          <h2 className="text-red-400 font-semibold mb-2">Error</h2>
          <p className="text-red-300 text-sm">{error}</p>
          <button
            onClick={() => { setError(null); loadProject() }}
            className="mt-3 text-sm text-red-400 hover:text-red-300 underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Loading project...</span>
        </div>
      </div>
    )
  }

  const currentStageIdx = STAGE_ORDER.indexOf(project.current_stage as PipelineStage)

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <button
            onClick={() => router.push('/automotive')}
            className="text-sm text-zinc-500 hover:text-zinc-300 mb-1"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-xl font-bold">
            <span className="text-amber-400">Tamkin</span> Automotive
          </h1>
        </div>
        <div className="text-right">
          {project.buyer_company && (
            <p className="text-sm text-zinc-400">{project.buyer_company}</p>
          )}
          <p className="text-xs text-zinc-600 font-mono">{project.project_id.slice(0, 8)}</p>
        </div>
      </div>

      {/* Original request */}
      <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl px-5 py-3 mb-6">
        <p className="text-sm text-zinc-400 leading-relaxed">{project.raw_request}</p>
      </div>

      {/* Pipeline navigation */}
      <PipelineNav
        stages={STAGE_ORDER}
        labels={STAGE_LABELS}
        currentStage={project.current_stage as PipelineStage}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        completedUpTo={currentStageIdx}
      />

      {/* Stage content */}
      <div className="mt-6">
        {activeTab === 'parse' && (
          <RequirementsView
            data={project.parsed_requirement}
            isActive={project.current_stage === 'parse'}
            onApprove={(edits) => handleApprove('parse', { edits })}
          />
        )}
        {activeTab === 'discover' && (
          <DiscoveryView
            data={project.discovery_result}
            isActive={project.current_stage === 'discover'}
            onApprove={(removedIds) => handleApprove('discover', { removed_supplier_ids: removedIds })}
          />
        )}
        {activeTab === 'qualify' && (
          <QualificationView
            data={project.qualification_result}
            isActive={project.current_stage === 'qualify'}
            onApprove={(overrides) => handleApprove('qualify', { status_overrides: overrides })}
          />
        )}
        {activeTab === 'compare' && (
          <ComparisonView
            data={project.comparison_matrix}
            isActive={project.current_stage === 'compare'}
            onApprove={(weights) => handleApprove('compare', { weight_adjustments: weights })}
          />
        )}
        {activeTab === 'report' && (
          <ReportsView
            data={project.intelligence_reports}
            projectId={project.project_id}
            isActive={project.current_stage === 'report'}
            onApprove={() => handleApprove('report', {})}
          />
        )}
        {activeTab === 'rfq' && (
          <RFQView
            data={project.rfq_result}
            isActive={project.current_stage === 'rfq'}
            onApprove={() => handleApprove('rfq_send', {})}
          />
        )}
        {activeTab === 'quote_ingest' && (
          <QuotesView
            data={project.quote_ingestion}
            isActive={project.current_stage === 'quote_ingest'}
            onApprove={() => handleApprove('quotes', {})}
          />
        )}
        {activeTab === 'complete' && (
          <CompleteView project={project} />
        )}
      </div>

      {/* Live activity console */}
      <div className="mt-6">
        <ActivityConsole projectId={project.project_id} />
      </div>
    </div>
  )
}

export default function ProjectPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-[60vh]">
        <div className="w-5 h-5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
      </div>
    }>
      <ProjectContent />
    </Suspense>
  )
}
