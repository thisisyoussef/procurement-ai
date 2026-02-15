'use client'

import { useState } from 'react'
import { automotiveClient } from '@/lib/automotive/client'

interface Props {
  data: Record<string, unknown> | null
  projectId: string
  isActive: boolean
  onApprove: () => void
}

interface Risk {
  risk_type: string
  description: string
  severity: string
  mitigation: string
}

interface Report {
  supplier_id: string
  company_name: string
  executive_summary: string
  company_profile: string
  capability_assessment: string
  quality_credentials: string
  financial_health: string
  geographic_analysis: string
  competitive_positioning: string
  risks: Risk[]
  recommended_questions: string[]
  areas_to_probe: string[]
  rfq_focus_areas: string[]
  contact_name: string
  contact_email: string
  contact_phone: string
  website: string
  address: string
}

const SEVERITY_STYLES: Record<string, string> = {
  high: 'bg-red-500/15 text-red-400 border-red-500/30',
  medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  low: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
}

export default function ReportsView({ data, projectId, isActive, onApprove }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailReport, setDetailReport] = useState<Report | null>(null)

  if (!data) {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-zinc-400">Generating intelligence reports...</span>
        </div>
        <p className="text-xs text-zinc-600">Deep research on each qualified supplier</p>
      </div>
    )
  }

  const reports = (data.reports || []) as Report[]
  const marketSummary = data.overall_market_summary as string || ''

  const loadDetail = async (supplierId: string) => {
    if (expandedId === supplierId) {
      setExpandedId(null)
      setDetailReport(null)
      return
    }
    setExpandedId(supplierId)
    setLoadingDetail(true)
    try {
      const detail = await automotiveClient.getReport(projectId, supplierId) as unknown as Report
      setDetailReport(detail)
    } catch {
      setDetailReport(reports.find((r) => r.supplier_id === supplierId) || null)
    } finally {
      setLoadingDetail(false)
    }
  }

  const SECTIONS = [
    { key: 'executive_summary', label: 'Executive Summary' },
    { key: 'company_profile', label: 'Company Profile' },
    { key: 'capability_assessment', label: 'Capability Assessment' },
    { key: 'quality_credentials', label: 'Quality & Certifications' },
    { key: 'financial_health', label: 'Financial Health' },
    { key: 'geographic_analysis', label: 'Geographic Analysis' },
    { key: 'competitive_positioning', label: 'Competitive Positioning' },
  ] as const

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Intelligence Reports</h3>
          <p className="text-xs text-zinc-500 mt-1">{reports.length} supplier briefs generated</p>
        </div>
        {isActive && (
          <button
            onClick={onApprove}
            className="px-4 py-1.5 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400"
          >
            Approve & Generate RFQ
          </button>
        )}
      </div>

      {marketSummary && (
        <div className="px-6 py-3 bg-zinc-800/30 border-b border-zinc-800">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Market Summary</p>
          <p className="text-sm text-zinc-300 leading-relaxed">{marketSummary}</p>
        </div>
      )}

      <div className="divide-y divide-zinc-800">
        {reports.map((r) => {
          const isExpanded = expandedId === r.supplier_id
          const detail = isExpanded ? (detailReport || r) : r

          return (
            <div key={r.supplier_id}>
              <button
                onClick={() => loadDetail(r.supplier_id)}
                className="w-full px-6 py-4 flex items-center justify-between hover:bg-zinc-800/30 transition-colors text-left"
              >
                <div>
                  <h4 className="font-medium text-zinc-200">{r.company_name}</h4>
                  <p className="text-xs text-zinc-500 mt-0.5 line-clamp-1">{r.executive_summary}</p>
                </div>
                <div className="flex items-center gap-3">
                  {r.risks.length > 0 && (
                    <span className="text-xs text-red-400">{r.risks.length} risks</span>
                  )}
                  <span className="text-zinc-500 text-sm">{isExpanded ? '▼' : '▶'}</span>
                </div>
              </button>

              {isExpanded && (
                <div className="px-6 pb-6">
                  {loadingDetail ? (
                    <div className="flex items-center gap-2 py-4">
                      <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                      <span className="text-xs text-zinc-500">Loading full report...</span>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      {/* Report sections */}
                      {SECTIONS.map(({ key, label }) => {
                        const content = (detail as any)[key] as string
                        if (!content) return null
                        return (
                          <div key={key}>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">{label}</h5>
                            <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">{content}</p>
                          </div>
                        )
                      })}

                      {/* Risks */}
                      {detail.risks.length > 0 && (
                        <div>
                          <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-2">Risk Assessment</h5>
                          <div className="space-y-2">
                            {detail.risks.map((risk, i) => (
                              <div key={i} className={`p-3 rounded-lg border ${SEVERITY_STYLES[risk.severity] || SEVERITY_STYLES.low}`}>
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-semibold">{risk.risk_type}</span>
                                  <span className="text-[10px] uppercase">{risk.severity}</span>
                                </div>
                                <p className="text-xs opacity-80">{risk.description}</p>
                                {risk.mitigation && (
                                  <p className="text-xs opacity-60 mt-1">Mitigation: {risk.mitigation}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Questions & focus areas */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {detail.recommended_questions.length > 0 && (
                          <div>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Questions to Ask</h5>
                            <ul className="text-xs text-zinc-400 space-y-1">
                              {detail.recommended_questions.map((q, i) => <li key={i}>• {q}</li>)}
                            </ul>
                          </div>
                        )}
                        {detail.areas_to_probe.length > 0 && (
                          <div>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Areas to Probe</h5>
                            <ul className="text-xs text-zinc-400 space-y-1">
                              {detail.areas_to_probe.map((a, i) => <li key={i}>• {a}</li>)}
                            </ul>
                          </div>
                        )}
                        {detail.rfq_focus_areas.length > 0 && (
                          <div>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">RFQ Focus Areas</h5>
                            <ul className="text-xs text-zinc-400 space-y-1">
                              {detail.rfq_focus_areas.map((f, i) => <li key={i}>• {f}</li>)}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* Contact */}
                      {(detail.contact_email || detail.contact_phone || detail.website) && (
                        <div className="pt-3 border-t border-zinc-800">
                          <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Contact</h5>
                          <div className="flex gap-4 text-xs text-zinc-400">
                            {detail.contact_name && <span>{detail.contact_name}</span>}
                            {detail.contact_email && <span>{detail.contact_email}</span>}
                            {detail.contact_phone && <span>{detail.contact_phone}</span>}
                            {detail.website && (
                              <a href={detail.website} target="_blank" rel="noopener noreferrer" className="text-amber-400 hover:text-amber-300">
                                Website →
                              </a>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
