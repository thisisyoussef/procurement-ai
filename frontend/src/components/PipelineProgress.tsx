'use client'

interface ProgressEvent {
  stage: string
  substep: string
  detail: string
  progress_pct: number | null
  timestamp: number
}

interface PipelineProgressProps {
  stage: string
  error: string | null
  progressEvents?: ProgressEvent[]
  hasClarifyingQuestions?: boolean
}

const STAGES = [
  { key: 'parsing', label: 'Analyzing Requirements', icon: '1' },
  { key: 'clarifying', label: 'Clarifying Details', icon: '?', optional: true },
  { key: 'discovering', label: 'Discovering Suppliers', icon: '2' },
  { key: 'verifying', label: 'Verifying Suppliers', icon: '3' },
  { key: 'comparing', label: 'Comparing Options', icon: '4' },
  { key: 'recommending', label: 'Final Recommendations', icon: '5' },
]

function getVisibleStages(hasClarifying: boolean) {
  return STAGES.filter((s) => !s.optional || hasClarifying)
}

function getStageIndex(stage: string, visibleStages: typeof STAGES): number {
  const idx = visibleStages.findIndex((s) => s.key === stage)
  if (stage === 'complete') return visibleStages.length
  return idx >= 0 ? idx : 0
}

function getLatestEventForStage(
  stage: string,
  events: ProgressEvent[]
): ProgressEvent | null {
  const stageEvents = events.filter((e) => e.stage === stage)
  if (stageEvents.length === 0) return null
  return stageEvents[stageEvents.length - 1]
}

export default function PipelineProgress({
  stage,
  error,
  progressEvents = [],
  hasClarifyingQuestions = false,
}: PipelineProgressProps) {
  const showClarifying = hasClarifyingQuestions || stage === 'clarifying'
  const visibleStages = getVisibleStages(showClarifying)
  const currentIdx = getStageIndex(stage, visibleStages)
  const isComplete = stage === 'complete'
  const isFailed = stage === 'failed' || !!error

  return (
    <div className="max-w-3xl mx-auto mt-8">
      <div className="flex items-center justify-between">
        {visibleStages.map((s, i) => {
          const isDone = i < currentIdx
          const isActive = i === currentIdx && !isComplete && !isFailed
          const isPending = i > currentIdx
          const latestEvent = getLatestEventForStage(s.key, progressEvents)

          return (
            <div key={s.key} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold transition-all
                    ${isDone ? 'bg-green-500 text-white' : ''}
                    ${isActive && s.key === 'clarifying' ? 'bg-amber-500 text-white ring-4 ring-amber-100 animate-pulse' : ''}
                    ${isActive && s.key !== 'clarifying' ? 'bg-blue-600 text-white ring-4 ring-blue-100 animate-pulse' : ''}
                    ${isPending ? 'bg-slate-200 text-slate-400' : ''}
                    ${isFailed && isActive ? 'bg-red-500 text-white ring-4 ring-red-100' : ''}`}
                >
                  {isDone ? '✓' : s.icon}
                </div>
                <span
                  className={`mt-2 text-xs text-center max-w-20
                    ${isDone ? 'text-green-600 font-medium' : ''}
                    ${isActive && s.key === 'clarifying' ? 'text-amber-600 font-medium' : ''}
                    ${isActive && s.key !== 'clarifying' ? 'text-blue-600 font-medium' : ''}
                    ${isPending ? 'text-slate-400' : ''}`}
                >
                  {s.label}
                </span>
                {/* Substep detail text */}
                {isActive && latestEvent && (
                  <span className="mt-1 text-[10px] text-slate-500 text-center max-w-24 truncate animate-fade-in">
                    {latestEvent.detail}
                  </span>
                )}
                {/* Summary stats for completed stages */}
                {isDone && latestEvent && (
                  <span className="mt-1 text-[10px] text-green-600 text-center max-w-24 truncate">
                    {latestEvent.detail}
                  </span>
                )}
              </div>
              {i < visibleStages.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-2 mt-[-1.5rem]
                    ${i < currentIdx ? 'bg-green-400' : 'bg-slate-200'}`}
                />
              )}
            </div>
          )
        })}
      </div>

      {isComplete && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-center">
          <span className="text-green-700 font-medium">Analysis complete!</span>
        </div>
      )}

      {/* Active substep detail banner */}
      {!isComplete && !isFailed && progressEvents.length > 0 && (
        <div className="mt-3 text-center">
          <span className="text-xs text-slate-500 italic">
            {progressEvents[progressEvents.length - 1]?.detail}
          </span>
        </div>
      )}
    </div>
  )
}
