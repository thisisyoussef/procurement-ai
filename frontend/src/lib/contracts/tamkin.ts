export type ApprovalKind = 'shortlist_lock' | 'outbound_send' | 'final_selection'
export type ApprovalStatus = 'pending' | 'approved' | 'rejected'

export interface MissionSummary {
  id: string
  title: string
  status: 'active' | 'waiting_approval' | 'running' | 'complete' | 'failed'
  updatedAt: number
  sourceBreakdown: { web: number; directories: number; supplierMemory: number }
}

export interface AgentTimelineEvent {
  id: string
  type: string
  at: number
  stage: string
  message: string
  source: 'pipeline' | 'chat_action' | 'outreach' | 'system'
  severity: 'info' | 'success' | 'warning' | 'error'
}

export interface ApprovalRequest {
  id: string
  kind: ApprovalKind
  title: string
  context: string
  recommendedAction: string
  status: ApprovalStatus
}

export interface PipelineProgressEvent {
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

export interface DraftEmail {
  supplier_name: string
  supplier_index: number
  recipient_email: string | null
  subject: string
  body: string
  status: string
}

export interface ParsedQuote {
  supplier_name: string
  supplier_index: number
  unit_price: string | null
  currency: string
  moq: string | null
  lead_time: string | null
  payment_terms: string | null
  shipping_terms: string | null
  notes: string | null
  confidence_score: number
}

export interface OutreachStateSummary {
  selected_suppliers?: number[]
  draft_emails?: DraftEmail[]
  parsed_quotes?: ParsedQuote[]
}

export interface PipelineStatusResponse {
  project_id: string
  status: string
  current_stage: string
  error: string | null
  parsed_requirements: Record<string, unknown> | null
  discovery_results: Record<string, unknown> | null
  verification_results: Record<string, unknown> | null
  comparison_result: Record<string, unknown> | null
  recommendation: Record<string, unknown> | null
  progress_events?: PipelineProgressEvent[]
  clarifying_questions?: ClarifyingQuestion[] | null
  outreach_state?: OutreachStateSummary | null
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant' | string
  content: string
  timestamp?: number
  metadata?: Record<string, unknown>
}

export interface OutreachPlanResponse {
  selected_suppliers: number
  funnel: {
    intent: number
    rfq_sent: number
    responses: number
    quotes_parsed: number
  }
  friction_risks: Record<string, number>
  plans: Array<Record<string, unknown>>
}

export interface OutreachTimelineEvent {
  event_type: string
  supplier_index?: number | null
  supplier_name?: string | null
  details?: Record<string, unknown>
  timestamp: number
}

export interface OutreachTimelineResponse {
  events: OutreachTimelineEvent[]
  count: number
}

export type StreamEvent =
  | { type: 'token'; content: string }
  | { type: 'done'; action?: Record<string, unknown> | null }
  | { type: 'action_result'; result: string }
  | { type: 'error'; message: string }
