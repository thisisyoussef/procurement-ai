'use client'

interface SupplierMiniCardProps {
  name: string
  score: number
  riskLevel?: string
  isRecommended?: boolean
}

export default function SupplierMiniCard({
  name,
  score,
  riskLevel,
  isRecommended,
}: SupplierMiniCardProps) {
  const dotColor =
    riskLevel === 'low'
      ? 'bg-green-400'
      : riskLevel === 'medium'
      ? 'bg-amber-400'
      : riskLevel === 'high'
      ? 'bg-red-400'
      : 'bg-workspace-muted/50'

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-workspace-hover transition-colors group">
      {/* Status dot */}
      <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor}`} />

      {/* Name */}
      <span className="text-xs text-workspace-text truncate flex-1 group-hover:text-white">
        {name}
      </span>

      {/* Score */}
      <span className="text-[10px] font-medium text-workspace-muted shrink-0">
        {Math.round(score)}
      </span>

      {/* Recommended badge */}
      {isRecommended && (
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-gold/10 text-gold border border-gold/20">
          ★
        </span>
      )}
    </div>
  )
}
