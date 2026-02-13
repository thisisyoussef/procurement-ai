'use client'

import { useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import SupplierMiniCard from './SupplierMiniCard'
import LogViewer from '@/components/LogViewer'

export default function LeftRail() {
  const { status, projectId, loading } = useWorkspace()

  const parsed = status?.parsed_requirements
  const suppliers = status?.discovery_results?.suppliers
  const verifications = status?.verification_results?.verifications
  const recommendations = status?.recommendation?.recommendations

  // Build verification map
  const verificationMap = useMemo(() => {
    const map = new Map<string, { composite_score: number; risk_level: string }>()
    if (verifications) {
      for (const v of verifications) {
        map.set(v.supplier_name, v)
      }
    }
    return map
  }, [verifications])

  // Build recommended set
  const recommendedSet = useMemo(() => {
    const set = new Set<number>()
    if (recommendations) {
      for (const r of recommendations) {
        set.add(r.supplier_index)
      }
    }
    return set
  }, [recommendations])

  return (
    <div className="flex flex-col h-full">
      {/* ── Project Brief ──────────────────────────── */}
      <div className="px-4 py-4 border-b border-workspace-border">
        <h3 className="text-[10px] font-medium text-workspace-muted uppercase tracking-wider mb-2">
          Project Brief
        </h3>
        {parsed ? (
          <div className="space-y-1.5">
            {parsed.product_type && (
              <p className="text-xs text-workspace-text font-medium truncate">
                {parsed.product_type}
              </p>
            )}
            {parsed.quantity && (
              <p className="text-[11px] text-workspace-muted">
                Qty: {parsed.quantity}
              </p>
            )}
            {parsed.delivery_location && (
              <p className="text-[11px] text-workspace-muted truncate">
                📍 {parsed.delivery_location}
              </p>
            )}
            {parsed.budget_range && (
              <p className="text-[11px] text-workspace-muted">
                💰 {parsed.budget_range}
              </p>
            )}
          </div>
        ) : (
          <p className="text-xs text-workspace-muted/60 italic">
            {loading ? 'Analyzing...' : 'No active project'}
          </p>
        )}
      </div>

      {/* ── Supplier Shortlist ─────────────────────── */}
      <div className="flex-1 overflow-y-auto border-b border-workspace-border">
        <div className="px-4 py-3">
          <h3 className="text-[10px] font-medium text-workspace-muted uppercase tracking-wider mb-2">
            Suppliers
            {suppliers && (
              <span className="ml-1 text-workspace-muted/60">
                ({suppliers.length})
              </span>
            )}
          </h3>
        </div>
        {suppliers ? (
          <div className="px-1 pb-2 space-y-0.5">
            {suppliers.slice(0, 20).map(
              (
                s: { name: string; relevance_score: number },
                i: number
              ) => {
                const v = verificationMap.get(s.name)
                return (
                  <SupplierMiniCard
                    key={`${s.name}-${i}`}
                    name={s.name}
                    score={s.relevance_score}
                    riskLevel={v?.risk_level}
                    isRecommended={recommendedSet.has(i)}
                  />
                )
              }
            )}
          </div>
        ) : (
          <p className="px-4 pb-3 text-xs text-workspace-muted/60 italic">
            {loading ? 'Searching...' : 'No suppliers yet'}
          </p>
        )}
      </div>

      {/* ── Activity Log ───────────────────────────── */}
      <div className="h-48 shrink-0 overflow-hidden">
        <div className="px-4 py-2">
          <h3 className="text-[10px] font-medium text-workspace-muted uppercase tracking-wider">
            Activity Log
          </h3>
        </div>
        <div className="px-2 h-[calc(100%-32px)] overflow-y-auto">
          {projectId ? (
            <div className="dark-override [&>div]:mt-0 [&>div]:border-0 [&>div]:rounded-none [&>div]:shadow-none text-[10px]">
              <LogViewer projectId={projectId} isActive={loading} />
            </div>
          ) : (
            <p className="px-2 text-[10px] text-workspace-muted/60 italic">
              Logs appear here when a project starts
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
