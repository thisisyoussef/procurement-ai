'use client'

import { useMemo } from 'react'

import { useWorkspace } from '@/contexts/WorkspaceContext'

export default function ProactiveAlerts() {
  const { status } = useWorkspace()

  const alerts = useMemo(() => status?.proactive_alerts || [], [status?.proactive_alerts])
  if (!alerts.length) return null

  return (
    <div className="space-y-2">
      {alerts.slice(0, 4).map((alert) => (
        <div
          key={alert.id}
          className="rounded-2xl border border-[#e7dcc7] bg-[#fff8ea] px-4 py-3"
        >
          <p className="text-[11px] uppercase tracking-[0.12em] text-[#9b7a3f]">Proactive Alert</p>
          <h4 className="mt-1 text-[14px] font-semibold text-ink">{alert.title}</h4>
          <p className="mt-1 text-[12px] text-ink-3">{alert.message}</p>
        </div>
      ))}
    </div>
  )
}
