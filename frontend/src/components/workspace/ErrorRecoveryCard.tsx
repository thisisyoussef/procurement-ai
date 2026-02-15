'use client'

/* ────────────────────────────────────────────────────────
 * ErrorRecoveryCard — contextual error display with
 * recovery actions instead of a generic red card.
 * ──────────────────────────────────────────────────────── */

interface ErrorRecoveryCardProps {
  error: string
  stage: string
  onRetry?: () => void
  onEditBrief?: () => void
  retrying?: boolean
}

interface RecoveryGuidance {
  title: string
  explanation: string
  retryLabel: string
  showEditBrief?: boolean
}

function getRecoveryGuidance(error: string, stage: string): RecoveryGuidance {
  const errorLower = error.toLowerCase()

  if (errorLower.includes('rate_limit') || errorLower.includes('rate limit')) {
    return {
      title: 'Search temporarily throttled',
      explanation:
        'I hit a rate limit on one of the supplier databases. This usually resolves in a minute.',
      retryLabel: 'Retry now',
    }
  }

  if (
    errorLower.includes('no_suppliers_found') ||
    errorLower.includes('no suppliers') ||
    errorLower.includes('0 suppliers')
  ) {
    return {
      title: 'No suppliers matched your criteria',
      explanation:
        'This usually means the product description is too specific or the category is niche. Try broadening your requirements.',
      retryLabel: 'Broaden search and retry',
      showEditBrief: true,
    }
  }

  if (errorLower.includes('timeout') || errorLower.includes('timed out')) {
    return {
      title: 'Search took too long',
      explanation:
        'One of the supplier databases took longer than expected to respond. This is usually temporary.',
      retryLabel: 'Try again',
    }
  }

  if (errorLower.includes('api') || errorLower.includes('llm') || errorLower.includes('anthropic')) {
    return {
      title: 'AI processing error',
      explanation:
        'The AI model encountered an issue while analyzing your request. This is usually temporary.',
      retryLabel: 'Retry',
    }
  }

  if (stage === 'discovering') {
    return {
      title: 'Search encountered an issue',
      explanation: 'Something went wrong while finding suppliers. I can retry the search.',
      retryLabel: 'Retry search',
      showEditBrief: true,
    }
  }

  if (stage === 'verifying') {
    return {
      title: 'Verification hit a snag',
      explanation:
        'I had trouble verifying some suppliers. I can retry with the suppliers already found.',
      retryLabel: 'Retry verification',
    }
  }

  return {
    title: 'Something went wrong',
    explanation: error || 'An unexpected error occurred during this run.',
    retryLabel: 'Retry this run',
    showEditBrief: true,
  }
}

export default function ErrorRecoveryCard({
  error,
  stage,
  onRetry,
  onEditBrief,
  retrying,
}: ErrorRecoveryCardProps) {
  const recovery = getRecoveryGuidance(error, stage)

  return (
    <div className="card border-l-[3px] border-l-red-400 px-5 py-4">
      <p className="text-[13px] font-semibold text-ink-2">{recovery.title}</p>
      <p className="text-[12px] text-ink-3 mt-1 leading-relaxed">{recovery.explanation}</p>
      <div className="mt-3 flex items-center gap-3">
        {onRetry && (
          <button
            onClick={onRetry}
            disabled={retrying}
            className="px-4 py-2 bg-teal text-white rounded-lg text-[12px] font-medium
                       hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {retrying ? 'Retrying\u2026' : recovery.retryLabel}
          </button>
        )}
        {recovery.showEditBrief && onEditBrief && (
          <button
            onClick={onEditBrief}
            className="px-4 py-2 border border-surface-3 text-ink-3 rounded-lg text-[12px]
                       hover:bg-surface-2 transition-colors"
          >
            Edit brief
          </button>
        )}
      </div>
    </div>
  )
}
