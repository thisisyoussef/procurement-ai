'use client'

interface ScoreBarProps {
  value: number
  max?: number
  size?: 'sm' | 'md'
  showLabel?: boolean
  thresholds?: { good: number; fair: number }
}

export default function ScoreBar({
  value,
  max = 100,
  size = 'sm',
  showLabel = true,
  thresholds = { good: 80, fair: 60 },
}: ScoreBarProps) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100))
  const rounded = Math.round(value)

  const fillColor =
    value >= thresholds.good
      ? 'bg-emerald-500'
      : value >= thresholds.fair
        ? 'bg-amber-500'
        : 'bg-red-500'

  const textColor =
    value >= thresholds.good
      ? 'text-emerald-400'
      : value >= thresholds.fair
        ? 'text-amber-400'
        : 'text-red-400'

  return (
    <div className="flex items-center gap-2 min-w-0">
      <div
        className={`flex-1 rounded-full bg-zinc-800 overflow-hidden ${
          size === 'md' ? 'h-2' : 'h-1.5'
        }`}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ${fillColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      {showLabel && (
        <span
          className={`text-xs font-mono tabular-nums shrink-0 ${textColor} ${
            size === 'md' ? 'w-8 font-semibold' : 'w-6'
          }`}
        >
          {rounded}
        </span>
      )}
    </div>
  )
}
