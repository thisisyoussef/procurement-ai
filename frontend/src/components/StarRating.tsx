'use client'

import { useId } from 'react'

interface StarRatingProps {
  score: number        // 0.0 - 5.0
  label?: string
  size?: 'sm' | 'md'   // sm = 14px, md = 18px
  showNumber?: boolean  // show numeric score next to stars
}

export default function StarRating({
  score,
  label,
  size = 'sm',
  showNumber = true,
}: StarRatingProps) {
  const uniqueId = useId()
  const px = size === 'sm' ? 14 : 18
  const clamped = Math.max(0, Math.min(5, score))

  // Determine full, half, empty counts
  const fullStars = Math.floor(clamped)
  const remainder = clamped - fullStars
  const hasHalf = remainder >= 0.25 && remainder < 0.75
  const roundedFull = remainder >= 0.75 ? fullStars + 1 : fullStars
  const emptyStars = 5 - roundedFull - (hasHalf ? 1 : 0)

  const starPath =
    'M10 1l2.39 4.84 5.34.78-3.87 3.77.91 5.34L10 13.27l-4.77 2.51.91-5.34L2.27 6.62l5.34-.78L10 1z'

  return (
    <div className="flex items-center gap-1">
      {label && (
        <span className="text-xs text-slate-500 mr-0.5 min-w-[52px]">{label}</span>
      )}
      <div className="flex items-center gap-px">
        {/* Full stars */}
        {Array.from({ length: roundedFull }).map((_, i) => (
          <svg key={`f${i}`} width={px} height={px} viewBox="0 0 20 20">
            <path d={starPath} fill="#f59e0b" />
          </svg>
        ))}
        {/* Half star */}
        {hasHalf && (
          <svg width={px} height={px} viewBox="0 0 20 20">
            <defs>
              <linearGradient id={`hg-${uniqueId}`}>
                <stop offset="50%" stopColor="#f59e0b" />
                <stop offset="50%" stopColor="#e2e8f0" />
              </linearGradient>
            </defs>
            <path d={starPath} fill={`url(#hg-${uniqueId})`} />
          </svg>
        )}
        {/* Empty stars */}
        {Array.from({ length: Math.max(0, emptyStars) }).map((_, i) => (
          <svg key={`e${i}`} width={px} height={px} viewBox="0 0 20 20">
            <path d={starPath} fill="#e2e8f0" />
          </svg>
        ))}
      </div>
      {showNumber && (
        <span className="text-xs text-slate-600 font-medium ml-0.5">
          {clamped.toFixed(1)}
        </span>
      )}
    </div>
  )
}
