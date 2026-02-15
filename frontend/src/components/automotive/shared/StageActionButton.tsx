'use client'

import type { PipelineStage } from '@/types/automotive'

interface StageActionButtonProps {
  stage: PipelineStage
  onClick: () => void
  disabled?: boolean
  loading?: boolean
  supplierCount?: number
  editCount?: number
}

interface ButtonConfig {
  label: string
  labelWithEdits?: string  // template with {n}
  labelWithCount?: string  // template with {n}
  next: string
}

const BUTTON_CONFIG: Record<string, ButtonConfig> = {
  parse: {
    label: 'Approve Requirements → Start Supplier Search',
    labelWithEdits: 'Save {n} Edit(s) → Start Supplier Search',
    next: 'AI will search Thomasnet, Google Places, and trade databases',
  },
  discover: {
    label: 'Approve Suppliers → Begin Verification',
    labelWithCount: 'Approve {n} Supplier(s) → Begin Verification',
    next: 'AI checks IATF certification, financials, corporate status',
  },
  qualify: {
    label: 'Approve Shortlist → Start Scoring',
    next: 'Suppliers scored across 6 dimensions',
  },
  compare: {
    label: 'Approve Rankings → Generate Intel Reports',
    next: 'Deep research briefs generated for each supplier',
  },
  report: {
    label: 'Approve Reports → Draft RFQ Packages',
    next: 'Professional RFQ documents generated for outreach',
  },
  rfq: {
    label: 'Review & Send RFQs',
    labelWithCount: 'Review & Send RFQs to {n} Supplier(s)',
    next: 'Emails will be sent to selected suppliers',
  },
  quote_ingest: {
    label: 'Finalize Selection → Complete Pipeline',
    next: 'Final procurement summary with recommendations',
  },
}

export default function StageActionButton({
  stage,
  onClick,
  disabled = false,
  loading = false,
  supplierCount,
  editCount,
}: StageActionButtonProps) {
  const config = BUTTON_CONFIG[stage]
  if (!config) return null

  let label = config.label
  if (editCount && editCount > 0 && config.labelWithEdits) {
    label = config.labelWithEdits.replace('{n}', String(editCount))
  } else if (supplierCount !== undefined && config.labelWithCount) {
    label = config.labelWithCount.replace('{n}', String(supplierCount))
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={onClick}
        disabled={disabled || loading}
        className="px-5 py-2 text-sm bg-amber-500 text-zinc-950 font-semibold rounded-lg hover:bg-amber-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
      >
        {loading && (
          <div className="w-3.5 h-3.5 border-2 border-zinc-800 border-t-transparent rounded-full animate-spin" />
        )}
        {loading ? 'Processing...' : label}
      </button>
      <span className="text-[10px] text-zinc-600 max-w-xs text-right">
        Next: {config.next}
      </span>
    </div>
  )
}
