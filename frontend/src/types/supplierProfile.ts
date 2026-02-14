export interface SupplierProfileHeroStats {
  unit_price: string | null
  unit_price_source: 'estimate' | 'quoted'
  moq: string | null
  lead_time: string | null
  google_rating: number | null
  google_review_count: number | null
  response_time_hours: number | null
}

export interface SupplierProfileQuote {
  unit_price: string | null
  currency: string
  moq: string | null
  lead_time: string | null
  payment_terms: string | null
  shipping_terms: string | null
  validity_period: string | null
  notes: string | null
  source: 'estimate' | 'parsed_response'
  confidence_score: number
  quantity: number | null
}

export interface SupplierProfileAssessment {
  reasoning: string
  confidence: string
  best_for: string
  rank: number | null
  overall_score: number
  strengths: string[]
  weaknesses: string[]
}

export interface SupplierProfileVerificationCheck {
  check_type: string
  status: string
  score: number
  details: string
}

export interface SupplierProfileVerification {
  composite_score: number
  risk_level: string
  recommendation: string
  summary: string
  checks: SupplierProfileVerificationCheck[]
}

export interface SupplierProfileCompanyDetails {
  address: string | null
  city: string | null
  country: string | null
  website: string | null
  email: string | null
  phone: string | null
  preferred_contact_method: string
  language: string | null
  categories: string[]
  certifications: string[]
  source: string
  is_intermediary: boolean
}

export interface SupplierProfileCommMessage {
  message_key: string
  direction: string
  channel: string
  subject: string | null
  body_preview: string | null
  delivery_status: string
  created_at: number
  source: string | null
}

export interface SupplierProfileOutreachStatus {
  email_sent: boolean
  response_received: boolean
  delivery_status: string
  follow_ups_sent: number
  excluded: boolean
  exclusion_reason: string | null
}

export interface SupplierProfileResponse {
  supplier_index: number
  name: string
  description: string | null
  hero_stats: SupplierProfileHeroStats
  quote: SupplierProfileQuote | null
  assessment: SupplierProfileAssessment | null
  verification: SupplierProfileVerification | null
  company: SupplierProfileCompanyDetails
  outreach: SupplierProfileOutreachStatus | null
  communication_log: SupplierProfileCommMessage[]
  images: string[]
  score_breakdown: Record<string, number> | null
}
