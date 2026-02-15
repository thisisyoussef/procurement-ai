/** Automotive procurement pipeline types. */

export type PipelineStage =
  | 'parse'
  | 'discover'
  | 'qualify'
  | 'compare'
  | 'report'
  | 'rfq'
  | 'quote_ingest'
  | 'complete'

export const STAGE_LABELS: Record<PipelineStage, string> = {
  parse: 'Requirements',
  discover: 'Discovery',
  qualify: 'Qualification',
  compare: 'Comparison',
  report: 'Intelligence',
  rfq: 'RFQ & Outreach',
  quote_ingest: 'Quotes',
  complete: 'Complete',
}

export const STAGE_ORDER: PipelineStage[] = [
  'parse', 'discover', 'qualify', 'compare', 'report', 'rfq', 'quote_ingest', 'complete',
]

export interface DiscoveredSupplier {
  supplier_id: string
  company_name: string
  headquarters: string
  website?: string
  phone?: string
  email?: string
  sources: string[]
  initial_score: number
  capability_match: number
  certification_match: number
  geographic_fit: number
  scale_fit: number
  data_richness: number
  known_processes: string[]
  known_materials: string[]
  known_certifications: string[]
  employee_count?: number
  estimated_revenue?: string
}

export interface QualifiedSupplier extends DiscoveredSupplier {
  qualification_status: 'qualified' | 'conditional' | 'disqualified'
  iatf_status: string
  financial_risk: string
  corporate_status: string
  strengths: string[]
  concerns: string[]
  overall_confidence: number
  google_rating?: number
  review_count?: number
}

export interface SupplierComparison {
  supplier_id: string
  company_name: string
  capability_score: number
  quality_score: number
  geographic_score: number
  financial_score: number
  scale_score: number
  reputation_score: number
  composite_score: number
  unique_strengths: string[]
  notable_risks: string[]
  best_fit_for: string
}

export interface ParsedQuote {
  supplier_id: string
  supplier_name: string
  piece_price: number
  tooling_cost?: number
  production_lead_time_weeks?: number
  moq?: number
  estimated_annual_tco_usd: number
  extraction_confidence: number
  low_confidence_fields: string[]
}
