'use client'

import { useMemo } from 'react'
import { useWorkspace } from '@/contexts/WorkspaceContext'

type RawEvent = { stage: string; substep: string; detail: string; progress_pct: number | null; timestamp: number }

export interface StageProgressData {
  events: RawEvent[]
  latestDetail: string
  latestSubstep: string
  regions: string[]
  activeRegion: string | null
  supplierNames: string[]
  progressPct: number | null
  supplierCount: number
  /** Product type extracted from parsing events */
  productType: string | null
  /** Quantity extracted from parsing events */
  quantity: string | null
  /** Search queries count from parsing */
  searchQueryCount: number
  /** Comparison: best_value supplier name */
  bestValue: string | null
  /** Comparison: best_quality supplier name */
  bestQuality: string | null
  /** Recommendation: top pick supplier name */
  topPick: string | null
  /** Recommendation count */
  recommendationCount: number
  /** Verified counts: { low, medium, high } risk */
  riskBreakdown: { low: number; high: number }
  /** Is stage complete? */
  isComplete: boolean
}

/** Extract region name from progress event detail strings */
function extractRegions(
  events: RawEvent[],
  regionalSearches?: Array<{ region: string }>,
): string[] {
  const regionSet = new Set<string>()

  if (regionalSearches) {
    for (const rs of regionalSearches) {
      regionSet.add(rs.region)
    }
  }

  for (const event of events) {
    const regionalMatch = event.detail.match(/for (.+?)-based manufacturers/)
    if (regionalMatch) regionSet.add(regionalMatch[1])

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

/** Get the region currently being searched (from the latest regional event) */
function extractActiveRegion(events: RawEvent[]): string | null {
  for (let i = events.length - 1; i >= 0; i--) {
    const event = events[i]
    if (event.substep === 'searching_regional') {
      const match = event.detail.match(/for (.+?)-based/)
      if (match) return match[1]
    }
  }
  return null
}

/** Extract supplier names from verification events */
function extractSupplierNames(events: RawEvent[]): string[] {
  const names: string[] = []
  for (const event of events) {
    const match = event.detail.match(/Verifying supplier \d+\/\d+: (.+?)\.\.\./)
    if (match) names.push(match[1])
  }
  return names
}

/** Extract product type from parsing events */
function extractProductType(events: RawEvent[]): string | null {
  for (const event of events) {
    const match = event.detail.match(/Product type: (.+?)(?:,|$)/)
    if (match) return match[1].trim()
  }
  return null
}

/** Extract quantity from parsing events */
function extractQuantity(events: RawEvent[]): string | null {
  for (const event of events) {
    const match = event.detail.match(/quantity: (.+?)(?:\.|$)/)
    if (match) return match[1].trim()
  }
  return null
}

/** Extract search query count from parsing events */
function extractSearchQueryCount(events: RawEvent[]): number {
  for (const event of events) {
    const match = event.detail.match(/Generated (\d+) search quer/)
    if (match) return parseInt(match[1])
  }
  return 0
}

/** Extract comparison winners */
function extractComparisonWinners(events: RawEvent[]): { bestValue: string | null; bestQuality: string | null } {
  for (const event of events) {
    if (event.substep === 'complete' && event.stage === 'comparing') {
      const valueMatch = event.detail.match(/Best value: (.+?)\. Best quality: (.+?)\./)
      if (valueMatch) {
        return { bestValue: valueMatch[1], bestQuality: valueMatch[2] }
      }
    }
  }
  return { bestValue: null, bestQuality: null }
}

/** Extract recommendation top pick and count */
function extractRecommendationData(events: RawEvent[]): { topPick: string | null; count: number } {
  for (const event of events) {
    if (event.substep === 'complete' && event.stage === 'recommending') {
      const match = event.detail.match(/(\d+) ranked suppliers\. Top pick: (.+?)\./)
      if (match) return { count: parseInt(match[1]), topPick: match[2] }
    }
  }
  return { topPick: null, count: 0 }
}

/** Extract risk breakdown from verification completion */
function extractRiskBreakdown(events: RawEvent[]): { low: number; high: number } {
  for (let i = events.length - 1; i >= 0; i--) {
    const event = events[i]
    if (event.substep === 'complete' && event.stage === 'verifying') {
      const lowMatch = event.detail.match(/(\d+) low risk/)
      const highMatch = event.detail.match(/(\d+) high risk/)
      return {
        low: lowMatch ? parseInt(lowMatch[1]) : 0,
        high: highMatch ? parseInt(highMatch[1]) : 0,
      }
    }
  }
  return { low: 0, high: 0 }
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
    const isComplete = events.some((e) => e.substep === 'complete')

    const comparisonWinners = stage === 'comparing' ? extractComparisonWinners(events) : { bestValue: null, bestQuality: null }
    const recData = stage === 'recommending' ? extractRecommendationData(events) : { topPick: null, count: 0 }

    return {
      events,
      latestDetail: latest?.detail?.trim() || '',
      latestSubstep: latest?.substep || '',
      regions: extractRegions(allEvents, regionalSearches),
      activeRegion: extractActiveRegion(allEvents),
      supplierNames: extractSupplierNames(events),
      progressPct: latestPct,
      supplierCount: suppliers.length,
      productType: extractProductType(allEvents),
      quantity: extractQuantity(allEvents),
      searchQueryCount: extractSearchQueryCount(allEvents),
      bestValue: comparisonWinners.bestValue,
      bestQuality: comparisonWinners.bestQuality,
      topPick: recData.topPick,
      recommendationCount: recData.count,
      riskBreakdown: extractRiskBreakdown(allEvents),
      isComplete,
    }
  }, [allEvents, stage, suppliers.length, regionalSearches])
}
