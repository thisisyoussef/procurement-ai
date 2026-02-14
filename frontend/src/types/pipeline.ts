export interface ProgressEvent {
  stage: string
  substep: string
  detail: string
  progress_pct: number | null
  timestamp: number
}

export interface ClarifyingQuestion {
  field: string
  question: string
  importance: string
  suggestions: string[]
}

export interface PipelineStatus {
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

export type Phase = 'brief' | 'search' | 'outreach' | 'compare' | 'samples' | 'order'

export const PHASE_ORDER: Phase[] = ['brief', 'search', 'compare', 'outreach', 'samples', 'order']

export function stageToPhase(stage: string): Phase {
  switch (stage) {
    case 'parsing':
    case 'clarifying':
      return 'brief'
    case 'discovering':
    case 'verifying':
      return 'search'
    case 'comparing':
    case 'recommending':
      return 'compare'
    case 'outreaching':
    case 'complete':
      return 'outreach'
    default:
      return 'brief'
  }
}

export function phaseIndex(phase: Phase): number {
  return PHASE_ORDER.indexOf(phase)
}

export function isPhaseAccessible(
  phase: Phase,
  highestReached: Phase,
  status: PipelineStatus | null
): boolean {
  // Samples and Order are always accessible (placeholder)
  if (phase === 'samples' || phase === 'order') return true
  // Outreach is accessible once search is complete
  if (phase === 'outreach') {
    return !!status?.recommendation
  }
  return phaseIndex(phase) <= phaseIndex(highestReached)
}

export function isPhaseComplete(phase: Phase, status: PipelineStatus | null): boolean {
  if (!status) return false
  switch (phase) {
    case 'brief':
      return (
        !!status.parsed_requirements &&
        status.current_stage !== 'parsing' &&
        status.current_stage !== 'clarifying'
      )
    case 'search':
      return (
        !!status.discovery_results &&
        !!status.verification_results &&
        !['discovering', 'verifying'].includes(status.current_stage)
      )
    case 'compare':
      return !!status.recommendation && status.current_stage === 'complete'
    default:
      return false
  }
}
