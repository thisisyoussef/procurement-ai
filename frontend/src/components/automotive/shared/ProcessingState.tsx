'use client'

import { m } from '@/lib/motion'
import type { PipelineStage } from '@/types/automotive'

interface ProcessingStateProps {
  stage: PipelineStage
  variant: 'processing' | 'waiting' | 'empty'
}

const STAGE_MESSAGES: Record<PipelineStage, { processing: string; detail: string; waiting: string }> = {
  parse: {
    processing: 'Analyzing your requirements with AI...',
    detail: 'Extracting part specs, materials, volumes, tolerances, and constraints from your description.',
    waiting: 'Waiting for requirements analysis to begin.',
  },
  discover: {
    processing: 'Searching supplier databases...',
    detail: 'Querying Thomasnet, Google Places, trade registries, and the open web for matching suppliers.',
    waiting: 'Supplier discovery will begin after requirements are approved.',
  },
  qualify: {
    processing: 'Verifying supplier credentials...',
    detail: 'Checking IATF 16949 certification, financial health, corporate registration, and customer reviews.',
    waiting: 'Qualification will begin after the supplier longlist is approved.',
  },
  compare: {
    processing: 'Building comparison matrix...',
    detail: 'Scoring each supplier across 6 dimensions: capability, quality, geography, financial health, scale, and reputation.',
    waiting: 'Comparison will begin after the shortlist is approved.',
  },
  report: {
    processing: 'Generating intelligence reports...',
    detail: 'Deep-diving into each qualified supplier — capabilities, risks, competitive positioning, and strategic fit.',
    waiting: 'Intelligence reports will be generated after rankings are approved.',
  },
  rfq: {
    processing: 'Preparing RFQ packages...',
    detail: 'Generating professional Request for Quotation documents with line items, quality requirements, and delivery terms.',
    waiting: 'RFQ packages will be drafted after intelligence reports are approved.',
  },
  quote_ingest: {
    processing: 'Processing supplier quotes...',
    detail: 'Extracting pricing, tooling costs, lead times, and calculating total cost of ownership from supplier responses.',
    waiting: 'Quote analysis will begin after RFQs are sent to suppliers.',
  },
  complete: {
    processing: 'Finalizing procurement package...',
    detail: 'Compiling final summary with recommendations, quote rankings, and next steps.',
    waiting: 'Pipeline completion pending.',
  },
}

export default function ProcessingState({ stage, variant }: ProcessingStateProps) {
  const msgs = STAGE_MESSAGES[stage] || STAGE_MESSAGES.parse

  if (variant === 'empty') {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <p className="text-sm text-zinc-500">No data available for this stage yet.</p>
        <p className="text-xs text-zinc-600 mt-1">{msgs.waiting}</p>
      </div>
    )
  }

  if (variant === 'waiting') {
    return (
      <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8 text-center">
        <div className="w-10 h-10 mx-auto mb-4 rounded-full bg-zinc-800 flex items-center justify-center">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="8" stroke="#52525b" strokeWidth="1.5" />
            <path d="M10 6v4l2.5 2.5" stroke="#71717a" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </div>
        <p className="text-sm text-zinc-400">{msgs.waiting}</p>
      </div>
    )
  }

  // processing variant
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-8">
      <div className="flex items-center justify-center gap-3 mb-3">
        {/* Animated bouncing dot loader */}
        <div className="flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <m.span
              key={i}
              className="w-2 h-2 rounded-full bg-amber-500"
              animate={{ y: [0, -6, 0] }}
              transition={{
                duration: 0.6,
                repeat: Infinity,
                delay: i * 0.15,
                ease: 'easeInOut',
              }}
            />
          ))}
        </div>
        <span className="text-zinc-300 font-medium">{msgs.processing}</span>
      </div>
      <p className="text-xs text-zinc-500 text-center max-w-md mx-auto leading-relaxed">{msgs.detail}</p>
    </div>
  )
}
