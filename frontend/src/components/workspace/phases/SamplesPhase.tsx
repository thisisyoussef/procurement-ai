'use client'

export default function SamplesPhase() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-6">
      {/* Package icon */}
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
        <path d="M16.5 9.4 7.55 4.24" />
        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
        <polyline points="3.29 7 12 12 20.71 7" />
        <line x1="12" y1="22" x2="12" y2="12" />
      </svg>

      <h2 className="font-heading text-2xl text-ink mb-2">Sample Tracking</h2>
      <p className="text-[13px] text-ink-3 text-center max-w-md mb-6 leading-relaxed">
        Once you have shortlisted suppliers, request product samples to evaluate
        quality, finish, and consistency before committing to a full order.
      </p>

      <div className="text-[11px] text-ink-4 border border-surface-3 rounded-full px-3 py-1">
        Coming soon
      </div>
    </div>
  )
}
