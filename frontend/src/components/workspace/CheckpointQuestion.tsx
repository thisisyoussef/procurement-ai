'use client'

import { ContextQuestion } from '@/types/pipeline'

interface CheckpointQuestionProps {
  question: ContextQuestion
  value: unknown
  onChange: (value: unknown) => void
}

export default function CheckpointQuestion({
  question,
  value,
  onChange,
}: CheckpointQuestionProps) {
  const normalizedValue =
    typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean'
      ? String(value)
      : ''

  return (
    <div className="rounded-xl border border-surface-3 bg-white px-3 py-3">
      <p className="text-[12px] font-semibold text-ink">{question.question}</p>
      <p className="mt-1 text-[11px] text-ink-4">{question.context}</p>

      {question.options && question.options.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {question.options.map((option) => {
            const selected = normalizedValue.toLowerCase() === option.toLowerCase()
            return (
              <button
                key={option}
                type="button"
                onClick={() => onChange(option)}
                className={`rounded-full border px-2.5 py-1 text-[11px] transition-colors ${
                  selected
                    ? 'border-teal bg-teal/10 text-teal'
                    : 'border-surface-3 text-ink-4 hover:border-teal hover:text-teal'
                }`}
              >
                {option}
              </button>
            )
          })}
        </div>
      ) : (
        <input
          type="text"
          value={normalizedValue}
          onChange={(event) => onChange(event.target.value)}
          placeholder={question.default || 'Type your answer'}
          className="mt-2 w-full rounded-lg border border-surface-3 px-2.5 py-1.5 text-[12px] text-ink placeholder:text-ink-4 focus:outline-none focus:ring-1 focus:ring-teal/25 focus:border-teal/40"
        />
      )}
    </div>
  )
}
