'use client'

export default function OrderPhase() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
      {/* Clipboard icon */}
      <svg
        width="48"
        height="48"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-ink-4/50 mb-5"
      >
        <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
        <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
        <path d="M12 11h4" />
        <path d="M12 16h4" />
        <path d="M8 11h.01" />
        <path d="M8 16h.01" />
      </svg>

      <h2 className="font-heading text-2xl text-ink mb-2">No order yet</h2>
      <p className="text-[13px] text-ink-3 text-center max-w-md mb-8 leading-relaxed">
        When you are ready to place a purchase order, Tamkin will guide you through
        the process step by step.
      </p>

      <div className="text-left space-y-3 max-w-sm w-full">
        {[
          'Finalize your supplier selection',
          'Negotiate terms and pricing',
          'Generate purchase order document',
          'Track order fulfillment',
        ].map((step, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="text-[11px] font-heading text-ink-4 w-5 text-right shrink-0 pt-0.5">
              {i + 1}.
            </span>
            <span className="text-[13px] text-ink-3">{step}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
