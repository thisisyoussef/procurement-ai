'use client'

import { FormEvent, useState } from 'react'

import { authFetch } from '@/lib/auth'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import ProactiveAlerts from '@/components/workspace/ProactiveAlerts'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

export default function OrderPhase() {
  const { projectId } = useWorkspace()
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleRetrospective(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!projectId || submitting) return

    const form = new FormData(event.currentTarget)
    const payload = {
      supplier_chosen: String(form.get('supplier_chosen') || '').trim() || null,
      overall_satisfaction: Number(form.get('overall_satisfaction') || 0) || null,
      communication_rating: Number(form.get('communication_rating') || 0) || null,
      pricing_accuracy: String(form.get('pricing_accuracy') || '').trim() || null,
      what_went_well: String(form.get('what_went_well') || '').trim() || null,
      what_went_wrong: String(form.get('what_went_wrong') || '').trim() || null,
    }

    setSubmitting(true)
    setError(null)
    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects/${projectId}/retrospective`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const body = await res.json()
          detail = body?.detail || detail
        } catch {
          // keep fallback
        }
        throw new Error(detail)
      }
      setSubmitted(true)
    } catch (err: any) {
      setError(err?.message || 'Failed to submit retrospective')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-6 py-6">
      <ProactiveAlerts />

      <div className="card px-6 py-5">
        <h2 className="font-heading text-2xl text-ink">Order & Retrospective</h2>
        <p className="mt-2 text-[13px] text-ink-3">
          Capture outcome feedback so Tamkin can learn your preferences and supplier reliability patterns.
        </p>

        {submitted ? (
          <div className="mt-5 rounded-xl border border-[#d3e9d4] bg-[#f3fff4] px-4 py-3 text-[13px] text-[#2f6b31]">
            Retrospective submitted. Future sourcing runs will use this feedback.
          </div>
        ) : (
          <form className="mt-5 grid gap-3" onSubmit={handleRetrospective}>
            <label className="grid gap-1">
              <span className="text-[12px] font-semibold text-ink">Supplier chosen</span>
              <input
                name="supplier_chosen"
                className="rounded-md border border-ink/15 px-3 py-2 text-[13px]"
                placeholder="Supplier name"
              />
            </label>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="grid gap-1">
                <span className="text-[12px] font-semibold text-ink">Overall satisfaction (1-5)</span>
                <input
                  type="number"
                  min={1}
                  max={5}
                  name="overall_satisfaction"
                  className="rounded-md border border-ink/15 px-3 py-2 text-[13px]"
                />
              </label>
              <label className="grid gap-1">
                <span className="text-[12px] font-semibold text-ink">Communication rating (1-5)</span>
                <input
                  type="number"
                  min={1}
                  max={5}
                  name="communication_rating"
                  className="rounded-md border border-ink/15 px-3 py-2 text-[13px]"
                />
              </label>
            </div>

            <label className="grid gap-1">
              <span className="text-[12px] font-semibold text-ink">Pricing accuracy</span>
              <select
                name="pricing_accuracy"
                className="rounded-md border border-ink/15 px-3 py-2 text-[13px]"
                defaultValue=""
              >
                <option value="">Select</option>
                <option value="as_expected">As expected</option>
                <option value="higher">Higher than expected</option>
                <option value="lower">Lower than expected</option>
              </select>
            </label>

            <label className="grid gap-1">
              <span className="text-[12px] font-semibold text-ink">What went well</span>
              <textarea
                name="what_went_well"
                rows={3}
                className="rounded-md border border-ink/15 px-3 py-2 text-[13px]"
              />
            </label>

            <label className="grid gap-1">
              <span className="text-[12px] font-semibold text-ink">What went wrong</span>
              <textarea
                name="what_went_wrong"
                rows={3}
                className="rounded-md border border-ink/15 px-3 py-2 text-[13px]"
              />
            </label>

            {error && <p className="text-[12px] text-red-600">{error}</p>}

            <button
              type="submit"
              disabled={submitting || !projectId}
              className="mt-2 w-fit rounded-full bg-ink px-5 py-2 text-[12px] font-semibold text-white disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Submit Retrospective'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
