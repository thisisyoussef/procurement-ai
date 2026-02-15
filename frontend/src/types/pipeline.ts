export interface ProgressEvent {
  stage: string
  substep: string
  detail: string
  progress_pct: number | null
  timestamp: number
}

export type CheckpointType =
  | 'confirm_requirements'
  | 'review_suppliers'
  | 'set_confidence_gate'
  | 'adjust_weights'
  | 'outreach_preferences'

export interface ContextQuestion {
  field: string
  question: string
  context: string
  options?: string[]
  default?: string | null
}

export interface CheckpointEvent {
  checkpoint_type: CheckpointType
  summary: string
  next_stage_preview: string
  context_questions: ContextQuestion[]
  adjustable_parameters: Record<string, unknown>
  auto_continue_seconds: number
  requires_explicit_approval: boolean
  timestamp: number
}

export type DecisionLane =
  | 'best_overall'
  | 'best_low_risk'
  | 'best_speed_to_order'
  | 'alternative'

export interface ClarifyingQuestion {
  field: string
  question: string
  importance: string
  suggestions: string[]
  why_this_question?: string | null
  if_skipped_impact?: string | null
  suggested_default?: string | null
}

export interface ParsedRequirements {
  product_type?: string
  material?: string | null
  dimensions?: string | null
  quantity?: number | null
  customization?: string | null
  delivery_location?: string | null
  deadline?: string | null
  certifications_needed?: string[]
  budget_range?: string | null
  missing_fields?: string[]
  search_queries?: string[]
  risk_tolerance?: string | null
  priority_tradeoff?: string | null
  minimum_supplier_count?: number | null
  evidence_strictness?: string | null
  clarifying_questions?: ClarifyingQuestion[]
  [key: string]: unknown
}

export interface SupplierRecommendation {
  rank: number
  supplier_name: string
  supplier_index: number
  overall_score: number
  confidence: string
  reasoning: string
  best_for: string
  lane?: DecisionLane | null
  why_trust?: string[]
  uncertainty_notes?: string[]
  verify_before_po?: string[]
  needs_manual_verification?: boolean
  manual_verification_reason?: string | null
}

export interface RecommendationResult {
  recommendations: SupplierRecommendation[]
  executive_summary?: string
  caveats?: string[]
  decision_checkpoint_summary?: string
  elimination_rationale?: string | null
  lane_coverage?: Record<string, number>
}

export interface PipelineStatus {
  project_id: string
  status: string
  current_stage: string
  error: string | null
  parsed_requirements: ParsedRequirements | null
  discovery_results: any
  verification_results: any
  comparison_result: any
  recommendation: RecommendationResult | null
  progress_events?: ProgressEvent[]
  clarifying_questions?: ClarifyingQuestion[] | null
  decision_preference?: DecisionLane | null
  buyer_context?: Record<string, unknown> | null
  active_checkpoint?: CheckpointEvent | null
  proactive_alerts?: Array<{
    id: string
    title: string
    message: string
    severity?: string
    created_at?: number
  }>
}

export type Phase = 'brief' | 'search' | 'outreach' | 'compare' | 'samples' | 'order'

export const PHASE_ORDER: Phase[] = ['brief', 'search', 'compare', 'outreach', 'samples', 'order']

export function stageToPhase(stage: string): Phase {
  switch (stage) {
    case 'parsing':
    case 'clarifying':
    case 'steering':
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
