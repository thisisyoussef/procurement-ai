'use client'

import { useState } from 'react'

import { AuthUser, authFetch, setAuthSession, getStoredAccessToken } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

interface OnboardingFormProps {
  authUser: AuthUser
  onComplete: (updatedUser: AuthUser) => void
}

export default function OnboardingForm({ authUser, onComplete }: OnboardingFormProps) {
  const [companyName, setCompanyName] = useState(authUser.company_name || '')
  const [jobTitle, setJobTitle] = useState(authUser.job_title || '')
  const [phone, setPhone] = useState(authUser.phone || '')
  const [companyWebsite, setCompanyWebsite] = useState(authUser.company_website || '')
  const [businessAddress, setBusinessAddress] = useState(authUser.business_address || '')
  const [companyDescription, setCompanyDescription] = useState(authUser.company_description || '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = companyName.trim().length > 0 && jobTitle.trim().length > 0 && !submitting

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!canSubmit) return

    setSubmitting(true)
    setError(null)
    trackTraceEvent('onboarding_profile_submit', { user_id: authUser.id })

    try {
      const res = await authFetch(`${API_BASE}/api/v1/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: companyName.trim(),
          job_title: jobTitle.trim(),
          phone: phone.trim() || null,
          company_website: companyWebsite.trim() || null,
          business_address: businessAddress.trim() || null,
          company_description: companyDescription.trim() || null,
        }),
      })

      if (!res.ok) {
        const payload = await res.json().catch(() => ({}))
        throw new Error(payload?.detail || `HTTP ${res.status}`)
      }

      const updatedUser = (await res.json()) as AuthUser
      const token = getStoredAccessToken()
      if (token) setAuthSession(token, updatedUser)

      trackTraceEvent('onboarding_profile_complete', { user_id: authUser.id })
      onComplete(updatedUser)
    } catch (err: any) {
      setError(err?.message || 'Something went wrong')
      trackTraceEvent('onboarding_profile_error', {
        user_id: authUser.id,
        detail: err?.message || 'unknown',
      }, { level: 'warn' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="min-h-screen bg-cream flex items-center justify-center px-4">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-10 h-10 rounded-xl bg-teal text-white mx-auto flex items-center justify-center font-body font-extrabold text-lg mb-4">
            T
          </div>
          <h1 className="font-heading text-3xl text-ink mb-2">
            Set up your business profile
          </h1>
          <p className="text-[14px] text-ink-3">
            This info will be used in supplier outreach emails so they know who they&apos;re talking to.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="card p-6 space-y-5">
          {/* Company Name */}
          <div>
            <label htmlFor="companyName" className="block text-[12px] font-semibold text-ink-2 mb-1.5">
              Company name <span className="text-teal">*</span>
            </label>
            <input
              id="companyName"
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Acme Co."
              required
              className="w-full border border-surface-3 rounded-lg px-3 py-2.5 text-[13px] text-ink
                         placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
            />
          </div>

          {/* Job Title */}
          <div>
            <label htmlFor="jobTitle" className="block text-[12px] font-semibold text-ink-2 mb-1.5">
              Your role / title <span className="text-teal">*</span>
            </label>
            <input
              id="jobTitle"
              type="text"
              value={jobTitle}
              onChange={(e) => setJobTitle(e.target.value)}
              placeholder="Founder, Head of Operations, etc."
              required
              className="w-full border border-surface-3 rounded-lg px-3 py-2.5 text-[13px] text-ink
                         placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
            />
          </div>

          {/* Two-column: Phone + Website */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="phone" className="block text-[12px] font-semibold text-ink-2 mb-1.5">
                Phone
              </label>
              <input
                id="phone"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+1 (555) 123-4567"
                className="w-full border border-surface-3 rounded-lg px-3 py-2.5 text-[13px] text-ink
                           placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
              />
            </div>
            <div>
              <label htmlFor="companyWebsite" className="block text-[12px] font-semibold text-ink-2 mb-1.5">
                Website
              </label>
              <input
                id="companyWebsite"
                type="url"
                value={companyWebsite}
                onChange={(e) => setCompanyWebsite(e.target.value)}
                placeholder="https://yourcompany.com"
                className="w-full border border-surface-3 rounded-lg px-3 py-2.5 text-[13px] text-ink
                           placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
              />
            </div>
          </div>

          {/* Business Address */}
          <div>
            <label htmlFor="businessAddress" className="block text-[12px] font-semibold text-ink-2 mb-1.5">
              Business address / location
            </label>
            <input
              id="businessAddress"
              type="text"
              value={businessAddress}
              onChange={(e) => setBusinessAddress(e.target.value)}
              placeholder="City, State, Country"
              className="w-full border border-surface-3 rounded-lg px-3 py-2.5 text-[13px] text-ink
                         placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
            />
          </div>

          {/* Company Description */}
          <div>
            <label htmlFor="companyDescription" className="block text-[12px] font-semibold text-ink-2 mb-1.5">
              About your business
            </label>
            <textarea
              id="companyDescription"
              value={companyDescription}
              onChange={(e) => setCompanyDescription(e.target.value)}
              placeholder="A short description of what your company does. This helps suppliers understand who they're working with."
              rows={3}
              className="w-full resize-none border border-surface-3 rounded-lg px-3 py-2.5 text-[13px] text-ink
                         placeholder:text-ink-4 focus:ring-1 focus:ring-teal/30 focus:border-teal/50 focus:outline-none bg-cream/50"
            />
            <p className="text-[10px] text-ink-4 mt-1">
              Optional — used in the opening of outreach emails.
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="border-l-[3px] border-l-red-400 bg-red-50 px-4 py-3 rounded-r-lg">
              <p className="text-[12px] text-red-700">{error}</p>
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={!canSubmit}
            className="w-full px-5 py-3 bg-teal text-white rounded-lg text-[14px] font-medium
                       hover:bg-teal-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? 'Saving...' : 'Continue to workspace'}
          </button>
        </form>
      </div>
    </main>
  )
}
