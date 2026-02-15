'use client'

import { useEffect, useMemo, useState } from 'react'

import StageAnimationRouter from '@/components/animation/StageAnimationRouter'

interface SmartLoaderProps {
  stage: string
  loading: boolean
}

function SupplierListSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-3">
      {Array.from({ length: count }).map((_, idx) => (
        <div key={idx} className="rounded-xl border border-surface-3 bg-white px-4 py-4">
          <div className="h-3 w-44 animate-pulse rounded bg-surface-3" />
          <div className="mt-2 h-2 w-72 animate-pulse rounded bg-surface-3" />
          <div className="mt-3 h-2 w-full animate-pulse rounded bg-surface-3" />
        </div>
      ))}
    </div>
  )
}

function ComparisonSkeleton() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-4">
      <div className="rounded-xl border border-surface-3 bg-white px-5 py-5">
        <div className="h-4 w-64 animate-pulse rounded bg-surface-3" />
        <div className="mt-3 h-2 w-full animate-pulse rounded bg-surface-3" />
        <div className="mt-2 h-2 w-5/6 animate-pulse rounded bg-surface-3" />
      </div>
      <SupplierListSkeleton count={4} />
    </div>
  )
}

function RecommendationSkeleton() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-8 space-y-4">
      <div className="rounded-xl border border-surface-3 bg-white px-5 py-5">
        <div className="h-4 w-52 animate-pulse rounded bg-surface-3" />
        <div className="mt-3 h-2 w-full animate-pulse rounded bg-surface-3" />
        <div className="mt-2 h-2 w-2/3 animate-pulse rounded bg-surface-3" />
      </div>
      <SupplierListSkeleton count={3} />
    </div>
  )
}

export default function SmartLoader({ stage, loading }: SmartLoaderProps) {
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [nowTick, setNowTick] = useState(Date.now())

  useEffect(() => {
    if (loading) {
      setStartedAt((prev) => prev ?? Date.now())
      const interval = setInterval(() => setNowTick(Date.now()), 500)
      return () => clearInterval(interval)
    }
    setStartedAt(null)
    return undefined
  }, [loading])

  const elapsedMs = useMemo(() => {
    if (!loading || !startedAt) return 0
    return Math.max(0, nowTick - startedAt)
  }, [loading, nowTick, startedAt])

  if (!loading) return null

  if (elapsedMs < 10000) {
    return <StageAnimationRouter />
  }

  if (stage === 'discovering' || stage === 'verifying') {
    return <SupplierListSkeleton count={6} />
  }
  if (stage === 'comparing') {
    return <ComparisonSkeleton />
  }
  if (stage === 'recommending') {
    return <RecommendationSkeleton />
  }

  return <StageAnimationRouter />
}
