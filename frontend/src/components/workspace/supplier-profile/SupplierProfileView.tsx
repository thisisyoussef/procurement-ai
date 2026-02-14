'use client'

import { useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'
import { authFetch } from '@/lib/auth'
import { useWorkspace } from '@/contexts/WorkspaceContext'
import type { SupplierProfileResponse } from '@/types/supplierProfile'
import ProfileHero from './ProfileHero'
import ProfilePortfolio from './ProfilePortfolio'
import ProfileAssessment from './ProfileAssessment'
import ProfileQuote from './ProfileQuote'
import ProfileCapabilities from './ProfileCapabilities'
import ProfileVerification from './ProfileVerification'
import ProfileCompanyDetails from './ProfileCompanyDetails'
import ProfileCommunicationLog from './ProfileCommunicationLog'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface Props {
  supplierIndex?: number
  supplierName?: string
}

export default function SupplierProfileView({ supplierIndex, supplierName }: Props) {
  const { projectId, status } = useWorkspace()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [profile, setProfile] = useState<SupplierProfileResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!projectId) return
    if (supplierIndex == null && !supplierName) return
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        let url: string
        if (supplierIndex != null) {
          url = `${API_BASE}/api/v1/projects/${projectId}/supplier/${supplierIndex}/profile`
        } else {
          url = `${API_BASE}/api/v1/projects/${projectId}/supplier/by-name/profile?name=${encodeURIComponent(supplierName!)}`
        }
        const res = await authFetch(url)
        if (!res.ok) {
          throw new Error(res.status === 404 ? 'Supplier not found' : `HTTP ${res.status}`)
        }
        const data = await res.json()
        if (!cancelled) setProfile(data)
      } catch (err: any) {
        if (!cancelled) setError(err.message || 'Failed to load supplier profile')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [projectId, supplierIndex, supplierName])

  function goBack() {
    const params = new URLSearchParams(searchParams.toString())
    params.delete('supplierIndex')
    params.delete('supplierName')
    router.push(`/product?${params.toString()}`)
  }

  // Derive project title for breadcrumb
  const projectTitle = status?.parsed_requirements?.product_type || 'Project'

  if (loading) {
    return (
      <div className="max-w-[960px] mx-auto px-6 py-12">
        <button onClick={goBack} className="flex items-center gap-2 text-[12px] font-medium text-ink-3 hover:text-ink mb-8 transition-colors">
          <ArrowLeft size={16} />
          Back to {projectTitle}
        </button>
        <div className="space-y-8 animate-pulse">
          {/* Hero skeleton */}
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-surface-2" />
            <div className="space-y-2">
              <div className="h-8 w-64 rounded bg-surface-2" />
              <div className="h-4 w-40 rounded bg-surface-2" />
            </div>
          </div>
          <div className="flex gap-10">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="space-y-1">
                <div className="h-7 w-16 rounded bg-surface-2" />
                <div className="h-3 w-20 rounded bg-surface-2" />
              </div>
            ))}
          </div>
          {/* Section skeletons */}
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="space-y-3">
              <div className="h-3 w-24 rounded bg-surface-2" />
              <div className="h-40 rounded-2xl bg-surface-2" />
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="max-w-[960px] mx-auto px-6 py-12">
        <button onClick={goBack} className="flex items-center gap-2 text-[12px] font-medium text-ink-3 hover:text-ink mb-8 transition-colors">
          <ArrowLeft size={16} />
          Back to {projectTitle}
        </button>
        <div className="card px-6 py-10 text-center">
          <p className="text-[14px] font-medium text-ink-2 mb-1">Could not load supplier profile</p>
          <p className="text-[12px] text-ink-4">{error || 'Unknown error'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-[960px] mx-auto px-6 pb-24">
      {/* Back nav */}
      <button onClick={goBack} className="flex items-center gap-2 text-[12px] font-medium text-ink-3 hover:text-ink mt-6 mb-2 transition-colors">
        <ArrowLeft size={16} />
        {projectTitle}
      </button>

      {/* Hero */}
      <ProfileHero profile={profile} />

      {/* Portfolio */}
      {profile.images.length > 0 && (
        <Section label="Their work" delay={2}>
          <ProfilePortfolio images={profile.images} name={profile.name} />
        </Section>
      )}

      {/* Agent's Assessment */}
      {profile.assessment && (
        <Section label="Agent's assessment" delay={3}>
          <ProfileAssessment assessment={profile.assessment} />
        </Section>
      )}

      {/* Quote */}
      {profile.quote && (
        <Section label="Your quote" delay={4}>
          <ProfileQuote quote={profile.quote} name={profile.name} />
        </Section>
      )}

      {/* Capabilities */}
      <Section label="Capabilities" delay={5}>
        <ProfileCapabilities company={profile.company} description={profile.description} />
      </Section>

      {/* Verification */}
      {profile.verification && (
        <Section label="Verification" delay={6}>
          <ProfileVerification
            verification={profile.verification}
            company={profile.company}
            heroStats={profile.hero_stats}
          />
        </Section>
      )}

      {/* Company Details */}
      <Section label="Company details" delay={7}>
        <ProfileCompanyDetails company={profile.company} quote={profile.quote} />
      </Section>

      {/* Communication Log */}
      {profile.communication_log.length > 0 && (
        <Section label="Communication log" delay={8}>
          <ProfileCommunicationLog messages={profile.communication_log} />
        </Section>
      )}
    </div>
  )
}

function Section({ label, delay, children }: { label: string; delay: number; children: React.ReactNode }) {
  return (
    <div className={`mb-12 animate-fin`} style={{ animationDelay: `${delay * 0.05}s` }}>
      <div className="text-[9.5px] font-bold text-ink-4 tracking-[2px] uppercase mb-5">
        {label}
      </div>
      {children}
    </div>
  )
}
