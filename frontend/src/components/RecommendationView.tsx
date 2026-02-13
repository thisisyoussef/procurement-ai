'use client'

import StarRating from './StarRating'

interface Recommendation {
  rank: number
  supplier_name: string
  supplier_index: number
  overall_score: number
  confidence: string
  reasoning: string
  best_for: string
}

interface Supplier {
  name: string
  website: string | null
  email: string | null
  phone: string | null
  certifications: string[]
  estimated_shipping_cost: string | null
}

interface Verification {
  supplier_name: string
  composite_score: number
  risk_level: string
}

interface Comparison {
  supplier_name: string
  estimated_unit_price: string | null
  estimated_shipping_cost: string | null
  estimated_landed_cost: string | null
  price_score?: number
  quality_score?: number
  shipping_score?: number
  review_score?: number
  lead_time_score?: number
}

interface RecommendationViewProps {
  recommendation: {
    recommendations: Recommendation[]
    executive_summary: string
    caveats: string[]
  }
  suppliers?: Supplier[]
  verifications?: { verifications: Verification[] } | null
  comparisons?: { comparisons: Comparison[] } | null
  projectId?: string
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const styles: Record<string, string> = {
    high: 'bg-green-100 text-green-800',
    medium: 'bg-amber-100 text-amber-800',
    low: 'bg-red-100 text-red-800',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${styles[confidence] || styles.low}`}>
      {confidence} confidence
    </span>
  )
}

function RiskBadge({ risk }: { risk: string }) {
  const styles: Record<string, string> = {
    low: 'bg-green-50 text-green-700 border-green-200',
    medium: 'bg-amber-50 text-amber-700 border-amber-200',
    high: 'bg-red-50 text-red-700 border-red-200',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full border ${styles[risk] || 'bg-slate-50 text-slate-600 border-slate-200'}`}>
      {risk} risk
    </span>
  )
}

export default function RecommendationView({
  recommendation,
  suppliers,
  verifications,
  comparisons,
  projectId,
}: RecommendationViewProps) {
  // Build lookup maps
  const verificationMap = new Map<string, Verification>()
  if (verifications?.verifications) {
    for (const v of verifications.verifications) {
      verificationMap.set(v.supplier_name, v)
    }
  }

  const comparisonMap = new Map<string, Comparison>()
  if (comparisons?.comparisons) {
    for (const c of comparisons.comparisons) {
      comparisonMap.set(c.supplier_name, c)
    }
  }

  return (
    <div className="bg-white border-2 border-blue-200 rounded-xl p-6 shadow-sm">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
          <span className="text-white text-sm font-bold">AI</span>
        </div>
        <h2 className="text-lg font-semibold text-slate-900">
          AI Recommendation
        </h2>
      </div>

      {/* Executive Summary */}
      {recommendation.executive_summary && (
        <div className="p-4 bg-blue-50 rounded-lg mb-6">
          <p className="text-sm text-blue-900 leading-relaxed">
            {recommendation.executive_summary}
          </p>
        </div>
      )}

      {/* Ranked Recommendations */}
      <div className="space-y-4">
        {recommendation.recommendations.map((rec) => {
          const supplier = suppliers?.[rec.supplier_index]
          const verification = verificationMap.get(rec.supplier_name)
          const comp = comparisonMap.get(rec.supplier_name)

          return (
            <div
              key={rec.rank}
              className={`border rounded-lg p-5 ${
                rec.rank === 1
                  ? 'border-green-300 bg-green-50/50'
                  : 'border-slate-200'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                      rec.rank === 1
                        ? 'bg-green-600 text-white'
                        : rec.rank === 2
                        ? 'bg-slate-700 text-white'
                        : 'bg-slate-300 text-slate-700'
                    }`}
                  >
                    #{rec.rank}
                  </div>
                  <div>
                    <h3 className="font-semibold text-slate-900 text-lg">{rec.supplier_name}</h3>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full">
                        {rec.best_for}
                      </span>
                      <ConfidenceBadge confidence={rec.confidence} />
                      {verification && <RiskBadge risk={verification.risk_level} />}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-3xl font-bold text-slate-900">
                    {Math.round(rec.overall_score)}
                  </div>
                  <div className="text-xs text-slate-500">/ 100</div>
                </div>
              </div>

              <p className="mt-3 text-sm text-slate-700 leading-relaxed">{rec.reasoning}</p>

              {/* Cost Breakdown */}
              {comp && (comp.estimated_unit_price || comp.estimated_shipping_cost || comp.estimated_landed_cost) && (
                <div className="mt-3 flex flex-wrap gap-4 text-xs">
                  {comp.estimated_unit_price && (
                    <div>
                      <span className="text-slate-500">Unit Price: </span>
                      <span className="font-medium text-slate-900">{comp.estimated_unit_price}</span>
                    </div>
                  )}
                  {comp.estimated_shipping_cost && (
                    <div>
                      <span className="text-slate-500">Shipping: </span>
                      <span className="font-medium text-emerald-700">{comp.estimated_shipping_cost}</span>
                    </div>
                  )}
                  {comp.estimated_landed_cost && (
                    <div>
                      <span className="text-slate-500">Landed Cost: </span>
                      <span className="font-bold text-slate-900">{comp.estimated_landed_cost}</span>
                    </div>
                  )}
                </div>
              )}

              {/* Star Ratings */}
              {comp && (comp.price_score || comp.quality_score || comp.shipping_score || comp.review_score || comp.lead_time_score) && (
                <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
                  {comp.price_score ? <StarRating score={comp.price_score} label="Price" size="sm" /> : null}
                  {comp.quality_score ? <StarRating score={comp.quality_score} label="Quality" size="sm" /> : null}
                  {comp.shipping_score ? <StarRating score={comp.shipping_score} label="Shipping" size="sm" /> : null}
                  {comp.review_score ? <StarRating score={comp.review_score} label="Reviews" size="sm" /> : null}
                  {comp.lead_time_score ? <StarRating score={comp.lead_time_score} label="Speed" size="sm" /> : null}
                </div>
              )}

              {/* Certifications */}
              {supplier?.certifications && supplier.certifications.length > 0 && (
                <div className="mt-2 flex gap-1 flex-wrap">
                  {supplier.certifications.slice(0, 5).map((cert) => (
                    <span key={cert} className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
                      {cert}
                    </span>
                  ))}
                </div>
              )}

              {/* Contact Info & Actions */}
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                {supplier?.website && (
                  <a
                    href={supplier.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs px-3 py-1.5 bg-slate-100 text-slate-700 rounded-lg
                               hover:bg-slate-200 transition-colors"
                  >
                    Visit Website &rarr;
                  </a>
                )}
                {supplier?.email && (
                  <span className="text-xs text-slate-500">
                    {supplier.email}
                  </span>
                )}
                {supplier?.phone && (
                  <span className="text-xs text-slate-500">
                    {supplier.phone}
                  </span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Caveats */}
      {recommendation.caveats.length > 0 && (
        <div className="mt-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <h4 className="text-sm font-medium text-amber-800 mb-2">Important Caveats</h4>
          <ul className="space-y-1">
            {recommendation.caveats.map((caveat, i) => (
              <li key={i} className="text-sm text-amber-700 flex items-start gap-2">
                <span className="mt-1 shrink-0">&#9888;</span>
                <span>{caveat}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Next Steps Guidance */}
      <div className="mt-6 p-5 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
        <h4 className="text-sm font-semibold text-blue-900 mb-3">What to do next</h4>
        <ol className="space-y-2 text-sm text-blue-800">
          <li className="flex items-start gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold shrink-0 mt-0.5">1</span>
            <span>Select suppliers to contact in the <strong>Supplier Outreach</strong> section below</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold shrink-0 mt-0.5">2</span>
            <span>Review and send AI-drafted RFQ emails to your selected suppliers</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold shrink-0 mt-0.5">3</span>
            <span>Track responses and paste supplier replies for automatic quote extraction</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="flex items-center justify-center w-5 h-5 rounded-full bg-blue-600 text-white text-xs font-bold shrink-0 mt-0.5">4</span>
            <span>Use <strong>AI Phone Calling</strong> for suppliers best reached by phone</span>
          </li>
        </ol>
        <button
          onClick={() => {
            const el = document.querySelector('[data-section="outreach"]')
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
          }}
          className="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg
                     hover:bg-blue-700 transition-colors"
        >
          Go to Supplier Outreach &darr;
        </button>
      </div>
    </div>
  )
}
