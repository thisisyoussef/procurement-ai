'use client'

import { useWorkspace } from '@/contexts/WorkspaceContext'
import SearchForm from '@/components/SearchForm'
import RequirementsCard from '@/components/RequirementsCard'
import ClarifyingQuestions from '@/components/ClarifyingQuestions'

export default function BriefPhase() {
  const {
    projectId,
    status,
    loading,
    errorMessage,
    handleSearch,
    handleClarifyingAnswered,
  } = useWorkspace()

  const currentStage = status?.current_stage || 'idle'
  const isClarifying = currentStage === 'clarifying'
  const hasClarifyingQuestions = !!(
    status?.clarifying_questions && status.clarifying_questions.length > 0
  )

  // ─── State 1: No project yet ─────────────────────
  if (!projectId && !loading) {
    return (
      <div>
        <div className="text-center mb-8">
          <h1 className="text-3xl font-heading text-workspace-text mb-3">
            What do you need made?
          </h1>
          <p className="text-workspace-muted max-w-xl mx-auto">
            Describe your product. Tamkin will find suppliers, verify them,
            compare options, and recommend the best path forward.
          </p>
        </div>

        <div className="dark-override">
          <SearchForm onSearch={handleSearch} loading={loading} />
        </div>

        {errorMessage && (
          <div className="mt-6 p-4 glass-card border-red-500/30">
            <p className="text-red-400 font-medium text-sm">Error</p>
            <p className="text-red-300 text-sm mt-1">{errorMessage}</p>
          </div>
        )}
      </div>
    )
  }

  // ─── State 2: Parsing / waiting ──────────────────
  if (loading && !status?.parsed_requirements && !isClarifying) {
    return (
      <div className="text-center py-16">
        <div className="inline-flex items-center gap-3 px-6 py-3 glass-card">
          <span className="w-2 h-2 rounded-full bg-teal animate-pulse" />
          <span className="text-sm text-workspace-text">
            {currentStage === 'parsing'
              ? 'Analyzing your requirements...'
              : currentStage === 'discovering'
              ? 'Brief parsed. Searching for suppliers...'
              : 'Processing...'}
          </span>
        </div>

        {status?.progress_events && status.progress_events.length > 0 && (
          <p className="mt-4 text-xs text-workspace-muted italic">
            {status.progress_events[status.progress_events.length - 1]?.detail}
          </p>
        )}

        {/* Show search form so user can see what they entered */}
        <div className="mt-8 dark-override">
          <SearchForm onSearch={handleSearch} loading={loading} />
        </div>
      </div>
    )
  }

  // ─── State 3: Clarifying questions ───────────────
  // ─── State 4: Requirements parsed ────────────────
  return (
    <div className="space-y-6">
      {/* Always show search form at top */}
      <div className="dark-override">
        <SearchForm onSearch={handleSearch} loading={loading} />
      </div>

      {errorMessage && (
        <div className="p-4 glass-card border-red-500/30">
          <p className="text-red-400 font-medium text-sm">Error</p>
          <p className="text-red-300 text-sm mt-1">{errorMessage}</p>
        </div>
      )}

      {/* Clarifying Questions */}
      {isClarifying && hasClarifyingQuestions && projectId && (
        <div className="dark-override">
          <ClarifyingQuestions
            projectId={projectId}
            questions={status!.clarifying_questions!}
            onAnswered={handleClarifyingAnswered}
          />
        </div>
      )}

      {/* Parsed Requirements */}
      {status?.parsed_requirements && (
        <div className="dark-override">
          <RequirementsCard requirements={status.parsed_requirements} />
        </div>
      )}

      {/* Error state */}
      {status?.error && (
        <div className="p-4 glass-card border-red-500/30">
          <p className="text-red-400 font-medium text-sm">Pipeline Error</p>
          <p className="text-red-300 text-sm mt-1">{status.error}</p>
        </div>
      )}
    </div>
  )
}
