'use client'

import { type ReactNode } from 'react'

interface TooltipProps {
  content: string
  children: ReactNode
  side?: 'top' | 'bottom' | 'right'
}

export default function Tooltip({ content, children, side = 'top' }: TooltipProps) {
  const positionClasses = {
    top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
    bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
    right: 'left-full top-1/2 -translate-y-1/2 ml-2',
  }

  return (
    <span className="relative group/tip inline-flex">
      {children}
      <span
        className={`
          absolute z-50 ${positionClasses[side]}
          px-3 py-2 text-xs text-zinc-200 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl
          max-w-[280px] w-max leading-relaxed
          opacity-0 scale-95 pointer-events-none
          group-hover/tip:opacity-100 group-hover/tip:scale-100
          transition-all duration-150
        `}
      >
        {content}
      </span>
    </span>
  )
}
