'use client'

import type { SupplierProfileAssessment } from '@/types/supplierProfile'

interface Props {
  assessment: SupplierProfileAssessment
}

export default function ProfileAssessment({ assessment }: Props) {
  const { reasoning, confidence, best_for, strengths, weaknesses } = assessment

  // Split reasoning into paragraphs for editorial feel
  const paragraphs = reasoning.split(/\n\n|\n/).filter(Boolean)

  return (
    <div className="grid grid-cols-[2px_1fr] gap-6">
      <div className="bg-teal rounded-sm opacity-40" />
      <div className="max-w-[640px]">
        {/* Label + confidence */}
        <div className="flex items-center gap-3 mb-3">
          <span className="text-[9px] font-bold text-teal tracking-[1.5px] uppercase">
            {best_for || 'Why I recommend them'}
          </span>
          <ConfidenceBadge confidence={confidence} />
        </div>

        {/* Reasoning paragraphs */}
        {paragraphs.map((p, i) => (
          <p key={i} className="text-[14px] text-ink-2 leading-[1.75] mb-3">
            {p}
          </p>
        ))}

        {/* Strengths & Weaknesses */}
        {(strengths.length > 0 || weaknesses.length > 0) && (
          <div className="mt-5 flex gap-8 flex-wrap">
            {strengths.length > 0 && (
              <div>
                <div className="text-[10px] font-bold text-teal/70 tracking-wider uppercase mb-2">Strengths</div>
                <ul className="space-y-1">
                  {strengths.map((s, i) => (
                    <li key={i} className="text-[12.5px] text-ink-3 flex items-start gap-2">
                      <span className="w-1 h-1 rounded-full bg-teal mt-[7px] shrink-0" />
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {weaknesses.length > 0 && (
              <div>
                <div className="text-[10px] font-bold text-ink-4/70 tracking-wider uppercase mb-2">Watch for</div>
                <ul className="space-y-1">
                  {weaknesses.map((w, i) => (
                    <li key={i} className="text-[12.5px] text-ink-3 flex items-start gap-2">
                      <span className="w-1 h-1 rounded-full bg-warm mt-[7px] shrink-0" />
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ConfidenceBadge({ confidence }: { confidence: string }) {
  const colors: Record<string, string> = {
    high: 'bg-teal/10 text-teal',
    medium: 'bg-warm/10 text-warm',
    low: 'bg-ink-4/10 text-ink-4',
  }
  const cls = colors[confidence] || colors.low
  return (
    <span className={`text-[8px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${cls}`}>
      {confidence} confidence
    </span>
  )
}
