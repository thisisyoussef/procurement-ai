'use client'

import { useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'

interface StageProgressData {
  events: Array<{ stage: string; substep: string; detail: string; progress_pct: number | null; timestamp: number }>
  latestDetail: string
  regions: string[]
  supplierNames: string[]
  progressPct: number | null
  supplierCount: number
}

/** Extract region name from progress event detail strings */
function extractRegions(
  events: Array<{ detail: string; substep: string }>,
  regionalSearches?: Array<{ region: string }>,
): string[] {
  const regionSet = new Set<string>()

  // From parsed_requirements.regional_searches (available upfront)
  if (regionalSearches) {
    for (const rs of regionalSearches) {
      regionSet.add(rs.region)
    }
  }

  // From progress event details
  for (const event of events) {
    // "Searching in Chinese for China-based manufacturers..."
    const regionalMatch = event.detail.match(/for (.+?)-based manufacturers/)
    if (regionalMatch) regionSet.add(regionalMatch[1])

    // "Identified N sourcing regions: China, Turkey, Vietnam"
    const identifiedMatch = event.detail.match(/sourcing regions?: (.+)/)
    if (identifiedMatch) {
      identifiedMatch[1].split(',').forEach((r) => {
        const trimmed = r.trim()
        if (trimmed) regionSet.add(trimmed)
      })
    }
  }

  return Array.from(regionSet)
}

/** Extract supplier names from verification events */
function extractSupplierNames(events: Array<{ detail: string; substep: string }>): string[] {
  const names: string[] = []
  for (const event of events) {
    // "Verifying supplier 1/20: Acme Manufacturing..."
    const match = event.detail.match(/Verifying supplier \d+\/\d+: (.+?)\.\.\./)
    if (match) names.push(match[1])
  }
  return names
}

export function useStageProgress(stage: string): StageProgressData {
  const { status } = useWorkspace()

  const allEvents = status?.progress_events || []
  const suppliers = status?.discovery_results?.suppliers || []
  const regionalSearches = (status?.parsed_requirements as any)?.regional_searches

  return useMemo(() => {
    const events = allEvents.filter((e) => e.stage === stage)
    const latest = events.length > 0 ? events[events.length - 1] : null
    const latestPct = events.reduce<number | null>((acc, e) => e.progress_pct ?? acc, null)

    return {
      events,
      latestDetail: latest?.detail?.trim() || '',
      regions: extractRegions(allEvents, regionalSearches),
      supplierNames: extractSupplierNames(events),
      progressPct: latestPct,
      supplierCount: suppliers.length,
    }
  }, [allEvents, stage, suppliers.length, regionalSearches])
}
