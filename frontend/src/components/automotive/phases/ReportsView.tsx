'use client'

import { useState } from 'react'
import { automotiveClient } from '@/lib/automotive/client'
import StageActionButton from '@/components/automotive/shared/StageActionButton'
import ScoreBar from '@/components/automotive/shared/ScoreBar'
import ProcessingState from '@/components/automotive/shared/ProcessingState'

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

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 }

type SectionKey = 'summary' | 'capabilities' | 'quality' | 'financial' | 'geographic' | 'competitive' | 'risks'

const SECTION_TABS: { key: SectionKey; label: string; reportKey?: string }[] = [
  { key: 'summary', label: 'Summary', reportKey: 'executive_summary' },
  { key: 'capabilities', label: 'Capabilities', reportKey: 'capability_assessment' },
  { key: 'quality', label: 'Quality', reportKey: 'quality_credentials' },
  { key: 'financial', label: 'Financial', reportKey: 'financial_health' },
  { key: 'geographic', label: 'Geographic', reportKey: 'geographic_analysis' },
  { key: 'competitive', label: 'Competitive', reportKey: 'competitive_positioning' },
  { key: 'risks', label: 'Risks' },
]

export default function ReportsView({ data, projectId, isActive, onApprove }: Props) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState<Record<string, SectionKey>>({})
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [detailReport, setDetailReport] = useState<Report | null>(null)

  if (!data) {
    return <ProcessingState stage="report" variant={isActive ? 'processing' : 'waiting'} />
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

  const getRiskCounts = (risks: Risk[]) => {
    const counts = { high: 0, medium: 0, low: 0 }
    risks.forEach(r => {
      if (r.severity in counts) counts[r.severity as keyof typeof counts]++
    })
    return counts
  }

  const getSection = (supplierId: string): SectionKey => activeSection[supplierId] || 'summary'

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <div>
          <h3 className="font-semibold">Intelligence Reports</h3>
          <p className="text-xs text-zinc-500 mt-1">{reports.length} supplier briefs generated</p>
        </div>
        {isActive && (
          <StageActionButton stage="report" onClick={onApprove} />
        )}
      </div>

      {marketSummary && (
        <div className="px-6 py-3 bg-zinc-800/30 border-b border-zinc-800">
          <p className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Market Summary</p>
          <p className="text-sm text-zinc-300 leading-relaxed">{marketSummary}</p>
        </div>
      )}

      {/* Summary cards — always visible */}
      <div className="divide-y divide-zinc-800">
        {reports.map((r) => {
          const isExpanded = expandedId === r.supplier_id
          const detail = isExpanded ? (detailReport || r) : r
          const riskCounts = getRiskCounts(r.risks)
          const section = getSection(r.supplier_id)

          return (
            <div key={r.supplier_id}>
              {/* Collapsed summary card */}
              <div className="px-6 py-4">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3">
                      <h4 className="font-medium text-zinc-200">{r.company_name}</h4>
                      {/* Risk count badges */}
                      <div className="flex items-center gap-1.5">
                        {riskCounts.high > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
                            {riskCounts.high} high
                          </span>
                        )}
                        {riskCounts.medium > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
                            {riskCounts.medium} med
                          </span>
                        )}
                        {riskCounts.low > 0 && (
                          <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                            {riskCounts.low} low
                          </span>
                        )}
                      </div>
                    </div>
                    {/* Executive summary preview */}
                    <p className="text-xs text-zinc-500 mt-1 line-clamp-2 leading-relaxed">
                      {r.executive_summary}
                    </p>
                  </div>
                  <button
                    onClick={() => loadDetail(r.supplier_id)}
                    className="ml-4 px-3 py-1.5 text-xs bg-zinc-800 text-zinc-300 rounded-lg hover:bg-zinc-700 flex-shrink-0"
                  >
                    {isExpanded ? 'Collapse' : 'View Full Report →'}
                  </button>
                </div>

                {/* Always-visible actionable items */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
                  {r.recommended_questions?.length > 0 && (
                    <div className="bg-zinc-800/40 rounded-lg p-3">
                      <p className="text-[10px] text-amber-500 uppercase tracking-wider mb-1.5 font-medium">Questions to Ask</p>
                      <ul className="text-xs text-zinc-400 space-y-1">
                        {r.recommended_questions.slice(0, 3).map((q, i) => <li key={i}>• {q}</li>)}
                        {r.recommended_questions.length > 3 && (
                          <li className="text-zinc-600">+{r.recommended_questions.length - 3} more…</li>
                        )}
                      </ul>
                    </div>
                  )}
                  {r.rfq_focus_areas?.length > 0 && (
                    <div className="bg-zinc-800/40 rounded-lg p-3">
                      <p className="text-[10px] text-amber-500 uppercase tracking-wider mb-1.5 font-medium">RFQ Focus Areas</p>
                      <ul className="text-xs text-zinc-400 space-y-1">
                        {r.rfq_focus_areas.slice(0, 3).map((f, i) => <li key={i}>• {f}</li>)}
                        {r.rfq_focus_areas.length > 3 && (
                          <li className="text-zinc-600">+{r.rfq_focus_areas.length - 3} more…</li>
                        )}
                      </ul>
                    </div>
                  )}
                </div>

                {/* Strength pills */}
                {r.areas_to_probe?.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {r.areas_to_probe.slice(0, 4).map((a, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500">
                        {a}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Expanded full report */}
              {isExpanded && (
                <div className="px-6 pb-6 border-t border-zinc-800/50">
                  {loadingDetail ? (
                    <div className="flex items-center gap-2 py-6">
                      <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
                      <span className="text-xs text-zinc-500">Loading full report...</span>
                    </div>
                  ) : (
                    <div>
                      {/* Section tabs */}
                      <div className="flex gap-1 overflow-x-auto py-3 -mx-1">
                        {SECTION_TABS.map(({ key, label }) => (
                          <button
                            key={key}
                            onClick={() => setActiveSection(prev => ({ ...prev, [r.supplier_id]: key }))}
                            className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap transition-colors ${
                              section === key
                                ? 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50'
                            }`}
                          >
                            {label}
                            {key === 'risks' && detail.risks.length > 0 && (
                              <span className="ml-1 text-red-400">({detail.risks.length})</span>
                            )}
                          </button>
                        ))}
                      </div>

                      {/* Section content */}
                      <div className="mt-3">
                        {section === 'risks' ? (
                          <div className="space-y-2">
                            {detail.risks.length === 0 ? (
                              <p className="text-sm text-zinc-500">No significant risks identified.</p>
                            ) : (
                              [...detail.risks]
                                .sort((a, b) => (SEVERITY_ORDER[a.severity] ?? 2) - (SEVERITY_ORDER[b.severity] ?? 2))
                                .map((risk, i) => (
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
                              ))
                            )}
                          </div>
                        ) : (
                          <div>
                            {(() => {
                              const tab = SECTION_TABS.find(t => t.key === section)
                              const content = tab?.reportKey ? (detail as any)[tab.reportKey] as string : ''
                              if (!content) return <p className="text-sm text-zinc-500">No data available for this section.</p>
                              return <p className="text-sm text-zinc-300 leading-relaxed whitespace-pre-line">{content}</p>
                            })()}
                          </div>
                        )}
                      </div>

                      {/* Questions, focus areas, probes — full list in expanded */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-5 pt-4 border-t border-zinc-800/50">
                        {detail.recommended_questions?.length > 0 && (
                          <div>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">All Questions to Ask</h5>
                            <ul className="text-xs text-zinc-400 space-y-1">
                              {detail.recommended_questions.map((q, i) => <li key={i}>• {q}</li>)}
                            </ul>
                          </div>
                        )}
                        {detail.areas_to_probe?.length > 0 && (
                          <div>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">Areas to Probe</h5>
                            <ul className="text-xs text-zinc-400 space-y-1">
                              {detail.areas_to_probe.map((a, i) => <li key={i}>• {a}</li>)}
                            </ul>
                          </div>
                        )}
                        {detail.rfq_focus_areas?.length > 0 && (
                          <div>
                            <h5 className="text-xs text-zinc-500 uppercase tracking-wider mb-1">All RFQ Focus Areas</h5>
                            <ul className="text-xs text-zinc-400 space-y-1">
                              {detail.rfq_focus_areas.map((f, i) => <li key={i}>• {f}</li>)}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* Contact info */}
                      {(detail.contact_email || detail.contact_phone || detail.website) && (
                        <div className="pt-3 mt-4 border-t border-zinc-800">
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
