'use client'

import { useState } from 'react'
import { m } from '@/lib/motion'
import { staggerContainerFast, cardEntrance } from '@/lib/motion/variants'

/* ────────────────────────────────────────────────────────
 * Conversational first-impression — replaces the old
 * "What do you need made?" search-bar style empty state.
 *
 * Sets the right mental model: you're talking to an expert
 * sourcing agent, not using a search engine.
 * ──────────────────────────────────────────────────────── */

const SUGGESTIONS = [
  'Custom enamel pins for my streetwear brand, ~500 units',
  'Organic cotton tote bags, need samples first',
  'Biodegradable food packaging for a small café',
  'Hand-poured soy candles with custom labels',
]

const PROCESS_STEPS = [
  {
    label: 'Parse your requirements',
    detail: 'I extract specs, constraints, and priorities from your description',
  },
  {
    label: 'Search multiple databases',
    detail: 'Direct manufacturers, marketplaces, regional specialists',
  },
  {
    label: 'Verify each match',
    detail: 'Check websites, reviews, certifications, business registration',
  },
  {
    label: 'Rank and recommend',
    detail: 'Side-by-side comparison with clear reasoning',
  },
]

interface AgentGreetingProps {
  onSubmit: (text: string) => void
  loading: boolean
  errorMessage: string | null
  userName?: string
  hasHistory?: boolean
  lastCategory?: string
}

export default function AgentGreeting({
  onSubmit,
  loading,
  errorMessage,
  userName,
  hasHistory,
  lastCategory,
}: AgentGreetingProps) {
  const [input, setInput] = useState('')

  const handleSubmit = () => {
    const trimmed = input.trim()
    if (!trimmed || loading) return
    onSubmit(trimmed)
    setInput('')
  }

  const firstName = userName?.split(' ')[0]

  const greeting = hasHistory
    ? `Welcome back${firstName ? `, ${firstName}` : ''}. What are we sourcing today?`
    : "I'm your sourcing agent. Tell me what you need — I'll find suppliers, verify them, and recommend the best path forward."

  const subtitle = hasHistory && lastCategory
    ? `Last time you sourced ${lastCategory}. Starting a new category, or continuing?`
    : "This usually takes 2-3 minutes. I'll show you what I'm finding along the way."

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
      {/* ── Agent message bubble ─────────────────── */}
      <div className="max-w-xl w-full mb-6">
        <m.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="bg-surface-2/50 rounded-2xl rounded-tl-sm px-5 py-4"
        >
          <p className="text-[14px] text-ink leading-relaxed">{greeting}</p>
          <p className="text-[12px] text-ink-3 mt-2">{subtitle}</p>
        </m.div>
      </div>

      {/* ── Input card ───────────────────────────── */}
      <div className="w-full max-w-xl">
        <m.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
          className="card p-1.5"
        >
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSubmit()
              }
            }}
            placeholder="Describe what you need manufactured..."
            rows={3}
            disabled={loading}
            className="w-full resize-none bg-transparent px-4 py-3 text-[14px] text-ink
                       placeholder:text-ink-4 focus:outline-none disabled:opacity-50"
          />
          <div className="flex justify-end px-2 pb-2">
            <m.button
              onClick={handleSubmit}
              disabled={!input.trim() || loading}
              whileTap={{ scale: 0.97 }}
              className="px-5 py-2 bg-teal text-white rounded-lg text-[13px] font-medium
                         hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Starting...' : 'Start sourcing'}
            </m.button>
          </div>
        </m.div>

        {/* ── Suggestion chips ───────────────────── */}
        <m.div
          className="flex flex-wrap gap-2 mt-4 justify-center"
          variants={staggerContainerFast}
          initial="hidden"
          animate="visible"
        >
          {SUGGESTIONS.map((s) => (
            <m.button
              key={s}
              variants={cardEntrance}
              onClick={() => onSubmit(s)}
              disabled={loading}
              whileHover={{ scale: 1.04 }}
              whileTap={{ scale: 0.97 }}
              className="text-[11px] px-3 py-1.5 rounded-full border border-surface-3
                         text-ink-4 hover:border-teal hover:text-teal transition-colors
                         disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {s}
            </m.button>
          ))}
        </m.div>
      </div>

      {/* ── What happens next ────────────────────── */}
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.4 }}
        className="max-w-xl w-full mt-10"
      >
        <div className="border border-surface-3 rounded-xl px-5 py-4">
          <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-ink-4 mb-3">
            What happens next
          </p>
          <div className="space-y-2.5">
            {PROCESS_STEPS.map((step, i) => (
              <div key={i} className="flex items-start gap-3">
                <span
                  className="w-5 h-5 rounded-full bg-surface-2 flex items-center justify-center
                             text-[10px] font-bold text-ink-4 shrink-0 mt-0.5"
                >
                  {i + 1}
                </span>
                <div>
                  <p className="text-[12px] text-ink-2 font-medium">{step.label}</p>
                  <p className="text-[10px] text-ink-4">{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </m.div>

      {/* ── Error card ───────────────────────────── */}
      {errorMessage && (
        <div className="mt-6 card border-l-[3px] border-l-red-400 px-5 py-4 max-w-xl w-full">
          <p className="text-[13px] font-semibold text-ink-2">Something went wrong</p>
          <p className="text-[11px] text-ink-3 mt-1">{errorMessage}</p>
        </div>
      )}
    </div>
  )
}
