'use client'

import StarRating from './StarRating'

interface Comparison {
  supplier_name: string
  supplier_index: number
  verification_score: number
  estimated_unit_price: string | null
  estimated_shipping_cost: string | null
  estimated_landed_cost: string | null
  moq: string | null
  lead_time: string | null
  certifications: string[]
  strengths: string[]
  weaknesses: string[]
  overall_score: number
  price_score?: number
  quality_score?: number
  shipping_score?: number
  review_score?: number
  lead_time_score?: number
}

interface ComparisonViewProps {
  comparison: {
    comparisons: Comparison[]
    analysis_narrative: string
    best_value: string | null
    best_quality: string | null
    best_speed: string | null
  }
}

function ScoreBar({ score, label }: { score: number; label: string }) {
  const color =
    score >= 70 ? 'bg-green-500' : score >= 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium">{Math.round(score)}</span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${score}%` }} />
      </div>
    </div>
  )
}

export default function ComparisonView({ comparison }: ComparisonViewProps) {
  const sorted = [...comparison.comparisons].sort(
    (a, b) => b.overall_score - a.overall_score
  )

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-900 mb-2">
        Supplier Comparison
      </h2>

      {/* Badges */}
      <div className="flex gap-3 mb-4 flex-wrap">
        {comparison.best_value && (
          <span className="text-xs px-3 py-1 bg-green-50 text-green-700 rounded-full border border-green-200">
            Best Value: {comparison.best_value}
          </span>
        )}
        {comparison.best_quality && (
          <span className="text-xs px-3 py-1 bg-blue-50 text-blue-700 rounded-full border border-blue-200">
            Best Quality: {comparison.best_quality}
          </span>
        )}
        {comparison.best_speed && (
          <span className="text-xs px-3 py-1 bg-purple-50 text-purple-700 rounded-full border border-purple-200">
            Fastest: {comparison.best_speed}
          </span>
        )}
      </div>

      {/* Comparison Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 sticky top-0 bg-white">
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Supplier</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Est. Price</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Shipping</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Landed Cost</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">MOQ</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Lead Time</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Ratings</th>
              <th className="text-left py-3 px-2 text-slate-600 font-medium">Score</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((c, i) => (
              <tr
                key={i}
                className={`border-b border-slate-50 ${i === 0 ? 'bg-green-50/50' : ''}`}
              >
                <td className="py-3 px-2 font-medium text-slate-900">
                  {i === 0 && <span className="text-green-600 mr-1">&#9733;</span>}
                  {c.supplier_name}
                </td>
                <td className="py-3 px-2 text-slate-700">
                  <div>{c.estimated_unit_price || '\u2014'}</div>
                  {c.price_score ? <StarRating score={c.price_score} showNumber={false} size="sm" /> : null}
                </td>
                <td className="py-3 px-2 text-slate-700">
                  {c.estimated_shipping_cost ? (
                    <div className="text-emerald-600">{c.estimated_shipping_cost}</div>
                  ) : <div>{'\u2014'}</div>}
                  {c.shipping_score ? <StarRating score={c.shipping_score} showNumber={false} size="sm" /> : null}
                </td>
                <td className="py-3 px-2 text-slate-700">
                  {c.estimated_landed_cost ? (
                    <span className="font-medium">{c.estimated_landed_cost}</span>
                  ) : '\u2014'}
                </td>
                <td className="py-3 px-2 text-slate-700">{c.moq || '\u2014'}</td>
                <td className="py-3 px-2 text-slate-700">
                  <div>{c.lead_time || '\u2014'}</div>
                  {c.lead_time_score ? <StarRating score={c.lead_time_score} showNumber={false} size="sm" /> : null}
                </td>
                <td className="py-3 px-2">
                  <div className="space-y-0.5">
                    {c.quality_score ? <StarRating score={c.quality_score} label="Quality" showNumber={false} size="sm" /> : null}
                    {c.review_score ? <StarRating score={c.review_score} label="Reviews" showNumber={false} size="sm" /> : null}
                  </div>
                </td>
                <td className="py-3 px-2">
                  <span className="font-bold text-lg text-slate-900">
                    {Math.round(c.overall_score)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Certifications Row */}
      {sorted.some(c => c.certifications?.length > 0) && (
        <div className="mt-4 p-3 bg-slate-50 rounded-lg">
          <h4 className="text-xs font-medium text-slate-600 mb-2">Certifications</h4>
          <div className="space-y-1.5">
            {sorted.filter(c => c.certifications?.length > 0).map((c, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-700 min-w-[120px]">
                  {c.supplier_name}:
                </span>
                <div className="flex gap-1 flex-wrap">
                  {c.certifications.map((cert) => (
                    <span key={cert} className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded">
                      {cert}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Strengths/Weaknesses Cards — show all suppliers */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
        {sorted.map((c, i) => (
          <div key={i} className="border border-slate-100 rounded-lg p-4">
            <h4 className="font-medium text-slate-900 mb-2">{c.supplier_name}</h4>
            {(c.price_score || c.quality_score || c.shipping_score || c.review_score || c.lead_time_score) ? (
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 mb-3 pb-3 border-b border-slate-100">
                {c.price_score ? <StarRating score={c.price_score} label="Price" size="sm" /> : null}
                {c.quality_score ? <StarRating score={c.quality_score} label="Quality" size="sm" /> : null}
                {c.shipping_score ? <StarRating score={c.shipping_score} label="Shipping" size="sm" /> : null}
                {c.review_score ? <StarRating score={c.review_score} label="Reviews" size="sm" /> : null}
                {c.lead_time_score ? <StarRating score={c.lead_time_score} label="Speed" size="sm" /> : null}
              </div>
            ) : null}
            {c.strengths.length > 0 && (
              <div className="mb-2">
                <p className="text-xs text-green-600 font-medium mb-1">Strengths</p>
                <ul className="text-xs text-slate-600 space-y-0.5">
                  {c.strengths.map((s, j) => (
                    <li key={j}>+ {s}</li>
                  ))}
                </ul>
              </div>
            )}
            {c.weaknesses.length > 0 && (
              <div>
                <p className="text-xs text-red-600 font-medium mb-1">Weaknesses</p>
                <ul className="text-xs text-slate-600 space-y-0.5">
                  {c.weaknesses.map((w, j) => (
                    <li key={j}>- {w}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Narrative Analysis */}
      {comparison.analysis_narrative && (
        <div className="mt-6 p-4 bg-slate-50 rounded-lg">
          <h4 className="text-sm font-medium text-slate-700 mb-2">Analysis</h4>
          <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
            {comparison.analysis_narrative}
          </p>
        </div>
      )}
    </div>
  )
}
