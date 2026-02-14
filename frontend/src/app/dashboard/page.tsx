'use client'

import Link from 'next/link'
import { Suspense, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import GoogleSignIn from '@/components/GoogleSignIn'
import OnboardingForm from '@/components/OnboardingForm'
import { dashboardClient } from '@/lib/api/dashboardClient'
import {
  AuthUser,
  authFetch,
  clearAuthSession,
  fetchCurrentUser,
  getStoredAccessToken,
  getStoredAuthUser,
} from '@/lib/auth'
import type {
  DashboardActivityItem,
  DashboardContactsResponse,
  DashboardProjectCard,
  DashboardSummaryResponse,
} from '@/lib/contracts/dashboard'
import { trackTraceEvent } from '@/lib/telemetry'

import './dashboard.css'

type TabKey = 'home' | 'projects' | 'contacts'

function statusClass(project: DashboardProjectCard): string {
  if (project.status === 'complete') return 'complete'
  if (project.status === 'clarifying') return 'waiting'
  if (project.status === 'failed' || project.status === 'canceled') return 'waiting'
  return 'active'
}

function visualClass(variant: number): string {
  if (variant === 2) return 'dash-proj-vis-2'
  if (variant === 3) return 'dash-proj-vis-3'
  return 'dash-proj-vis-1'
}

function DashboardPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
  const [authReady, setAuthReady] = useState(false)

  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryError, setSummaryError] = useState<string | null>(null)

  const [contacts, setContacts] = useState<DashboardContactsResponse | null>(null)
  const [contactsLoading, setContactsLoading] = useState(false)
  const [contactsError, setContactsError] = useState<string | null>(null)

  const [tab, setTab] = useState<TabKey>('home')

  const [searchInput, setSearchInput] = useState('')
  const [searchSubmitting, setSearchSubmitting] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)

  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredAccessToken()
      if (!token) {
        setAuthReady(true)
        return
      }

      const cached = getStoredAuthUser()
      if (cached) setAuthUser(cached)

      try {
        const me = await fetchCurrentUser()
        setAuthUser(me)
        trackTraceEvent('dashboard_auth_session_restored', { user_id: me.id }, { path: '/dashboard' })
      } catch {
        clearAuthSession()
        setAuthUser(null)
        trackTraceEvent('dashboard_auth_session_invalid', {}, { path: '/dashboard', level: 'warn' })
      } finally {
        setAuthReady(true)
      }
    }

    void initAuth()
  }, [])

  useEffect(() => {
    const tabParam = (searchParams.get('tab') || '').toLowerCase()
    if (tabParam === 'projects' || tabParam === 'contacts' || tabParam === 'home') {
      setTab(tabParam as TabKey)
      return
    }
    setTab('home')
  }, [searchParams])

  const loadSummary = async () => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      const data = await dashboardClient.getSummary()
      setSummary(data)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setSummaryError(detail)
    } finally {
      setSummaryLoading(false)
    }
  }

  const loadContacts = async () => {
    setContactsLoading(true)
    setContactsError(null)
    try {
      const data = await dashboardClient.getContacts(100)
      setContacts(data)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      setContactsError(detail)
    } finally {
      setContactsLoading(false)
    }
  }

  useEffect(() => {
    if (!authUser) return
    void loadSummary()
    const interval = setInterval(() => {
      void loadSummary()
    }, 25000)
    return () => clearInterval(interval)
  }, [authUser])

  useEffect(() => {
    if (!authUser || tab !== 'contacts') return
    void loadContacts()
  }, [authUser, tab])

  const greeting = summary?.greeting

  const openProject = (projectId: string, phase?: string | null) => {
    const params = new URLSearchParams({ projectId })
    if (phase) params.set('phase', phase)
    trackTraceEvent('dashboard_project_open', { project_id: projectId, phase }, { path: '/dashboard' })
    router.push(`/product?${params.toString()}`)
  }

  const switchTab = (nextTab: TabKey) => {
    const params = new URLSearchParams(searchParams.toString())
    if (nextTab === 'home') params.delete('tab')
    else params.set('tab', nextTab)
    const query = params.toString()
    router.replace(query ? `/dashboard?${query}` : '/dashboard', { scroll: false })
    trackTraceEvent('dashboard_tab_change', { tab: nextTab }, { path: '/dashboard' })
  }

  const goToNewProjectView = () => {
    trackTraceEvent('dashboard_new_project_view_open', {}, { path: '/dashboard' })
    router.push('/product?new=1')
  }

  const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

  const handleSearchSubmit = async () => {
    const trimmed = searchInput.trim()
    if (!trimmed || searchSubmitting) return

    setSearchSubmitting(true)
    setSearchError(null)
    trackTraceEvent('dashboard_search_submit', { description_length: trimmed.length }, { path: '/dashboard' })

    try {
      const res = await authFetch(`${API_BASE}/api/v1/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: trimmed.slice(0, 80),
          product_description: trimmed,
        }),
      })

      if (res.status === 401) {
        clearAuthSession()
        setAuthUser(null)
        return
      }

      if (!res.ok) {
        let detail = `HTTP ${res.status}`
        try {
          const payload = (await res.json()) as { detail?: string }
          detail = payload.detail || detail
        } catch { /* keep */ }
        throw new Error(detail)
      }

      const data = (await res.json()) as { project_id: string }
      trackTraceEvent('dashboard_search_started', { project_id: data.project_id }, { path: '/dashboard' })
      router.push(`/product?projectId=${data.project_id}`)
    } catch (err: any) {
      const detail = err?.message || 'Could not start project. Try again.'
      setSearchError(detail)
      setSearchSubmitting(false)
    }
  }

  const firstLetter = useMemo(
    () => (authUser?.full_name?.[0] || authUser?.email?.[0] || 'Y').toUpperCase(),
    [authUser]
  )

  if (!authReady) return <main className="min-h-screen bg-cream" />

  if (!authUser) {
    return (
      <main className="min-h-screen bg-cream flex items-center justify-center">
        <div className="card p-8 max-w-sm w-full text-center space-y-5">
          <div className="w-10 h-10 rounded-xl bg-teal text-white mx-auto flex items-center justify-center font-body font-extrabold text-lg">
            T
          </div>
          <h1 className="text-2xl font-heading text-ink">Sign in to Tamkin</h1>
          <p className="text-sm text-ink-3">Open your dashboard and track all sourcing projects in one place.</p>
          <div className="pt-1 flex justify-center">
            <GoogleSignIn onAuthenticated={setAuthUser} />
          </div>
          <Link href="/" className="inline-block text-xs text-ink-4 hover:text-teal transition-colors">
            Back to landing
          </Link>
        </div>
      </main>
    )
  }

  // Onboarding gate — collect business profile before showing dashboard
  if (!authUser.onboarding_completed) {
    return (
      <OnboardingForm
        authUser={authUser}
        onComplete={(updatedUser) => {
          trackTraceEvent('onboarding_gate_passed', { user_id: updatedUser.id }, { path: '/dashboard' })
          setAuthUser(updatedUser)
        }}
      />
    )
  }

  const handleSignOut = () => {
    trackTraceEvent('dashboard_sign_out', { user_id: authUser.id }, { path: '/dashboard' })
    clearAuthSession()
    setAuthUser(null)
  }

  const activityRows: DashboardActivityItem[] = summary?.recent_activity || []

  return (
    <div className="dash-page">
      <nav className="dash-nav">
        <div className="dash-nav-left">
          <div className="dash-logo">tam<em>kin</em></div>
          <div className="dash-nav-links">
            <button type="button" className={`dash-nav-link ${tab === 'home' ? 'on' : ''}`} onClick={() => switchTab('home')}>Home</button>
            <button type="button" className={`dash-nav-link ${tab === 'projects' ? 'on' : ''}`} onClick={() => switchTab('projects')}>Projects</button>
            <button type="button" className={`dash-nav-link ${tab === 'contacts' ? 'on' : ''}`} onClick={() => switchTab('contacts')}>Contacts</button>
          </div>
        </div>

        <div className="dash-nav-right">
          <button type="button" className="dash-new-btn" onClick={goToNewProjectView}>New project</button>
          <button type="button" className="dash-av" onClick={handleSignOut} title="Sign out">{firstLetter}</button>
        </div>
      </nav>

      <main className="dash-main">
        <div className="dash-greeting">
          <div className="dash-greeting-time">{greeting?.time_label || 'Today'}</div>
          <h1 className="dash-greeting-title">
            {greeting?.headline || `Good day, ${greeting?.user_first_name || authUser.full_name || 'there'}`}
            <em>.</em>
          </h1>
          <p className="dash-greeting-body">
            {greeting?.body || 'Tamkin is running your sourcing pipeline and outreach in the background.'}
          </p>
        </div>

        {/* Search bar */}
        {tab !== 'contacts' && (
          <div className="dash-search-wrap">
            <div className="dash-search-bar">
              <input
                className="dash-search-input"
                placeholder="What do you need made?"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void handleSearchSubmit()
                }}
                disabled={searchSubmitting}
              />
              <button
                className="dash-search-btn"
                onClick={handleSearchSubmit}
                disabled={searchSubmitting || !searchInput.trim()}
              >
                {searchSubmitting ? (
                  <span className="dash-search-spinner" />
                ) : (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
                    <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                )}
              </button>
            </div>
            {searchError && <div className="dash-error" style={{ marginTop: 8 }}>{searchError}</div>}
          </div>
        )}

        {summaryError && <div className="dash-error">Dashboard error: {summaryError}</div>}
        {summaryLoading && !summary && <div className="dash-empty">Loading dashboard...</div>}

        {tab !== 'contacts' && (
          <div className="dash-attention">
            <div className="dash-section-label">Needs your attention</div>
            <div className="dash-att-cards">
              {(summary?.attention || []).map((item) => (
                <button
                  type="button"
                  key={item.id}
                  className="dash-att-card"
                  onClick={() => openProject(item.project_id, item.target_phase)}
                >
                  <div className={`dash-att-dot ${item.priority === 'high' ? 'teal' : 'warm'}`} />
                  <div className="dash-att-info">
                    <div className="dash-att-title">{item.title}</div>
                    <div className="dash-att-sub">{item.subtitle}</div>
                  </div>
                  <div className="dash-att-action">{item.cta} →</div>
                </button>
              ))}
              {summary && summary.attention.length === 0 && (
                <div className="dash-empty">No actions needed right now.</div>
              )}
            </div>
          </div>
        )}

        {tab !== 'contacts' && (
          <div className="dash-projects">
            <div className="dash-section-label">Your projects</div>
            <div className="dash-proj-grid">
              {(summary?.projects || []).map((project) => (
                <button
                  type="button"
                  key={project.id}
                  className="dash-proj-card"
                  onClick={() => openProject(project.id)}
                >
                  <div className={`dash-proj-visual ${visualClass(project.visual_variant)}`}>
                    <div className="dash-proj-phase">{project.phase_label}</div>
                  </div>

                  <div className="dash-proj-body">
                    <div className="dash-proj-name">{project.name}</div>
                    <div className="dash-proj-desc">{project.description}</div>

                    <div className="dash-proj-progress">
                      {Array.from({ length: project.progress_total }).map((_, idx) => {
                        const step = idx + 1
                        const cls =
                          step < project.progress_step ? 'done' : step === project.progress_step ? 'current' : ''
                        return <div key={`${project.id}:pip:${step}`} className={`dash-proj-pip ${cls}`} />
                      })}
                    </div>

                    <div className="dash-proj-stats">
                      <div className="dash-proj-stat"><strong>{project.stats.quotes_count}</strong> quotes</div>
                      {project.stats.best_price ? (
                        <div className="dash-proj-stat"><strong>{project.stats.best_price}</strong> best price</div>
                      ) : null}
                      {project.stats.samples_sent > 0 ? (
                        <div className="dash-proj-stat"><strong>{project.stats.samples_sent}</strong> samples sent</div>
                      ) : null}
                    </div>

                    <div className={`dash-proj-status ${statusClass(project)}`}>{project.status_note}</div>
                  </div>
                </button>
              ))}

              <button type="button" className="dash-proj-card empty" onClick={goToNewProjectView}>
                <div className="dash-proj-empty-inner">
                  <div className="dash-proj-empty-icon">+</div>
                  <div className="dash-proj-empty-t">Start a new project</div>
                  <div className="dash-proj-empty-s">Tell Tamkin what you need made and it handles the rest.</div>
                </div>
              </button>
            </div>
          </div>
        )}

        {tab !== 'contacts' && (
          <div className="dash-activity">
            <div className="dash-section-label">Recent activity</div>
            <div className="dash-acts">
              {activityRows.map((event) => (
                <div className="dash-act-row" key={event.id}>
                  <div className="dash-act-time">{event.time_label}</div>
                  <div>
                    <div className="dash-act-title">{event.title}</div>
                    <div className="dash-act-desc">{event.description}</div>
                    {event.project_name ? <div className="dash-act-project">{event.project_name}</div> : null}
                  </div>
                </div>
              ))}
              {summary && activityRows.length === 0 && (
                <div className="dash-empty">No activity yet. Start a project to see updates.</div>
              )}
            </div>
          </div>
        )}

        {tab === 'contacts' && (
          <div>
            <div className="dash-section-label">Supplier contacts</div>
            {contactsError && <div className="dash-error">Contacts error: {contactsError}</div>}
            {contactsLoading && !contacts && <div className="dash-empty">Loading contacts...</div>}
            {contacts && (
              <div className="dash-contacts-list">
                <div className="dash-contact-row head">
                  <div>Supplier</div>
                  <div>Location</div>
                  <div>Interactions</div>
                  <div>Last activity</div>
                </div>
                {contacts.suppliers.map((supplier) => {
                  const canLink = !!supplier.last_project_id
                  const handleClick = canLink
                    ? () => {
                        const params = new URLSearchParams({
                          projectId: supplier.last_project_id!,
                          supplierName: supplier.name,
                        })
                        router.push(`/product?${params.toString()}`)
                      }
                    : undefined

                  return (
                    <div
                      className={`dash-contact-row${canLink ? ' cursor-pointer hover:bg-black/[.02] transition-colors' : ''}`}
                      key={supplier.supplier_id}
                      onClick={handleClick}
                    >
                      <div>
                        <div className={`dash-contact-name${canLink ? ' hover:text-teal transition-colors' : ''}`}>{supplier.name}</div>
                        <div>{supplier.email || supplier.website || 'No contact listed'}</div>
                      </div>
                      <div>{[supplier.city, supplier.country].filter(Boolean).join(', ') || 'Unknown'}</div>
                      <div>{supplier.interaction_count} across {supplier.project_count} projects</div>
                      <div>{supplier.last_interaction_at ? new Date(supplier.last_interaction_at * 1000).toLocaleDateString() : 'N/A'}</div>
                    </div>
                  )
                })}
                {contacts.count === 0 && <div className="dash-contact-row"><div>No supplier contacts yet.</div></div>}
              </div>
            )}
          </div>
        )}
      </main>

    </div>
  )
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-cream" />}>
      <DashboardPageContent />
    </Suspense>
  )
}
