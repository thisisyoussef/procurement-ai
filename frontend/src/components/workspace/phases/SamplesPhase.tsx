'use client'

import { useMemo } from 'react'

import { useWorkspace } from '@/contexts/WorkspaceContext'

export default function SamplesPhase() {
  const { status } = useWorkspace()

  const outreachState = status?.outreach_state || null
  const stats = useMemo(() => {
    const supplierStatuses = outreachState?.supplier_statuses || []
    const responded = supplierStatuses.filter((row: any) => row.response_received).length
    const awaiting = supplierStatuses.filter(
      (row: any) => row.email_sent && !row.response_received && !row.excluded
    ).length
    return { responded, awaiting }
  }, [outreachState?.supplier_statuses])

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-6 py-8">
      <div className="card px-6 py-6">
        <h2 className="font-heading text-2xl text-ink">Sample Management</h2>
        <p className="mt-2 text-[13px] text-ink-3">
          Once suppliers respond, this phase helps you request, track, and evaluate samples before placing an order.
        </p>

        <div className="mt-4 rounded-xl border border-surface-3 bg-surface-2/40 px-4 py-3">
          <p className="text-[11px] text-ink-3 leading-relaxed">
            You will be able to compare sample quality side by side, capture defects, and keep supplier feedback in one thread.
          </p>
          <ul className="mt-2 space-y-1 text-[12px] text-ink-3">
            <li>Request and track samples by supplier</li>
            <li>Record quality notes and image evidence</li>
            <li>Approve sample-ready suppliers for PO</li>
          </ul>
        </div>

        <p className="mt-4 text-[12px] text-ink-4">
          Current outreach status: {stats.responded} supplier{stats.responded === 1 ? '' : 's'} responded
          {stats.awaiting > 0 ? `, ${stats.awaiting} awaiting reply.` : '.'}
        </p>
      </div>
    </div>
  )
}
