'use client'

import Link from 'next/link'
import { Suspense, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import GoogleSignIn from '@/components/GoogleSignIn'
import OnboardingForm from '@/components/OnboardingForm'
import SourcingProfileCard from '@/components/dashboard/SourcingProfileCard'
import { dashboardClient } from '@/lib/api/dashboardClient'
import { m } from '@/lib/motion'
import { staggerContainer, cardEntrance, fadeUp, slideInLeft } from '@/lib/motion/variants'
import {
  AuthUser,
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
type ProjectStatusFilter =
  | 'active'
  | 'closed'
  | 'parsing'
  | 'clarifying'
  | 'steering'
  | 'discovering'
  | 'verifying'
  | 'comparing'
  | 'recommending'
  | 'outreaching'
  | 'complete'
  | 'failed'
  | 'canceled'

type StatusPreset = 'all' | 'active' | 'closed' | 'complete' | 'failed'

const ACTIVE_FILTER_STATUSES: ProjectStatusFilter[] = [
  'parsing',
  'clarifying',
  'steering',
  'discovering',
  'verifying',
  'comparing',
  'recommending',
  'outreaching',
]

const ALL_STATUS_FILTERS = new Set<ProjectStatusFilter>([
  'active',
  'closed',
  ...ACTIVE_FILTER_STATUSES,
  'complete',
  'failed',
  'canceled',
])

const STATUS_PRESETS: Array<{ key: StatusPreset; label: string; statuses: ProjectStatusFilter[] }> = [
  { key: 'all', label: 'All', statuses: [] },
  { key: 'active', label: 'Active', statuses: ['active'] },
  { key: 'closed', label: 'Closed', statuses: ['closed'] },
  { key: 'complete', label: 'Complete', statuses: ['complete'] },
  { key: 'failed', label: 'Failed', statuses: ['failed'] },
]

function normalizeStatusFilters(values: string[]): ProjectStatusFilter[] {
  const normalized: ProjectStatusFilter[] = []
  const seen = new Set<string>()
  for (const value of values) {
    const candidate = value.trim().toLowerCase() as ProjectStatusFilter
    if (!ALL_STATUS_FILTERS.has(candidate) || seen.has(candidate)) continue
    seen.add(candidate)
    normalized.push(candidate)
  }
  return normalized
}

function isSameStatusSet(left: ProjectStatusFilter[], right: ProjectStatusFilter[]): boolean {
  if (left.length !== right.length) return false
  return left.every((value) => right.includes(value))
}

function normalizeProjectQuery(value: string | null): string {
  return (value || '').trim()
}

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

function projectNarrative(project: DashboardProjectCard): string {
  if (project.stats.best_price) {
    return `Best quoted price so far: ${project.stats.best_price}`
  }
  if (project.stats.quotes_count > 0) {
    return `${project.stats.quotes_count} quotes collected so far`
  }
  if (project.status === 'complete') {
    return 'Completed. Ready to continue supplier conversations.'
  }
  return project.description
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
  const [selectedStatuses, setSelectedStatuses] = useState<ProjectStatusFilter[]>([])
  const [projectQuery, setProjectQuery] = useState('')

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

  useEffect(() => {
    setSelectedStatuses(normalizeStatusFilters(searchParams.getAll('status')))
  }, [searchParams])

  useEffect(() => {
    setProjectQuery(normalizeProjectQuery(searchParams.get('q')))
  }, [searchParams])

  const loadSummary = async () => {
    setSummaryLoading(true)
    setSummaryError(null)
    try {
      const data = await dashboardClient.getSummary(selectedStatuses, projectQuery)
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
  }, [authUser, selectedStatuses, projectQuery])

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

  const applyStatusPreset = (preset: StatusPreset) => {
    const nextStatuses = STATUS_PRESETS.find((item) => item.key === preset)?.statuses ?? []
    const params = new URLSearchParams(searchParams.toString())
    params.delete('status')
    for (const status of nextStatuses) params.append('status', status)
    const query = params.toString()
    router.replace(query ? `/dashboard?${query}` : '/dashboard', { scroll: false })
    trackTraceEvent('dashboard_status_filter_change', { preset, statuses: nextStatuses }, { path: '/dashboard' })
  }

  const applyProjectQuery = (nextQuery: string) => {
    const normalizedQuery = normalizeProjectQuery(nextQuery)
    const params = new URLSearchParams(searchParams.toString())
    if (normalizedQuery) params.set('q', normalizedQuery)
    else params.delete('q')
    const query = params.toString()
    router.replace(query ? `/dashboard?${query}` : '/dashboard', { scroll: false })
    trackTraceEvent('dashboard_project_filter_change', { query_length: normalizedQuery.length }, { path: '/dashboard' })
  }

  const activeStatusPreset: StatusPreset =
    STATUS_PRESETS.find((preset) => isSameStatusSet(selectedStatuses, preset.statuses))?.key ?? 'all'

  const goToNewProjectView = () => {
    trackTraceEvent('dashboard_new_project_view_open', {}, { path: '/dashboard' })
    router.push('/product?new=1')
  }

  const handleSearchSubmit = async () => {
    const trimmed = searchInput.trim()
    if (!trimmed || searchSubmitting) return

    setSearchSubmitting(true)
    setSearchError(null)
    trackTraceEvent('dashboard_search_submit', { description_length: trimmed.length }, { path: '/dashboard' })

    try {
      const data = await dashboardClient.startProject({
        title: trimmed.slice(0, 80),
        description: trimmed,
        source: 'dashboard_search',
      })
      trackTraceEvent('dashboard_search_started', { project_id: data.project_id }, { path: '/dashboard' })
      router.push(data.redirect_path || `/product?projectId=${data.project_id}`)
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err)
      if (detail === 'Not authenticated' || detail.startsWith('HTTP 401')) {
        clearAuthSession()
        setAuthUser(null)
        return
      }
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
          <h1 className="text-2xl font-heading text-ink">Sign in to Procurement AI</h1>
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
            {greeting?.body || 'Procurement AI is running your sourcing pipeline and outreach in the background.'}
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
            <m.div
              className="dash-att-cards"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {(summary?.attention || []).map((item) => (
                <m.button
                  type="button"
                  key={item.id}
                  variants={slideInLeft}
                  className="dash-att-card"
                  onClick={() => openProject(item.project_id, item.target_phase)}
                  whileHover={{ scale: 1.01 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className={`dash-att-dot ${item.priority === 'high' ? 'teal' : 'warm'}`} />
                  <div className="dash-att-info">
                    <div className="dash-att-title">{item.title}</div>
                    <div className="dash-att-sub">{item.subtitle}</div>
                  </div>
                  <div className="dash-att-action">{item.cta} →</div>
                </m.button>
              ))}
              {summary && summary.attention.length === 0 && (
                <div className="dash-empty">No actions needed right now.</div>
              )}
            </m.div>
          </div>
        )}

        {tab !== 'contacts' && (
          <div className="dash-projects">
            <div className="dash-section-label">Your projects</div>
            <div className="dash-proj-filter-bar" role="group" aria-label="Filter projects by status">
              {STATUS_PRESETS.map((preset) => (
                <button
                  type="button"
                  key={preset.key}
                  className={`dash-proj-filter ${activeStatusPreset === preset.key ? 'on' : ''}`}
                  onClick={() => applyStatusPreset(preset.key)}
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <div className="dash-search-bar" style={{ marginTop: 12 }}>
              <input
                className="dash-search-input"
                placeholder="Filter projects by title"
                value={projectQuery}
                onChange={(e) => setProjectQuery(e.target.value)}
                onBlur={() => applyProjectQuery(projectQuery)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') applyProjectQuery(projectQuery)
                  if (e.key === 'Escape') {
                    setProjectQuery('')
                    applyProjectQuery('')
                  }
                }}
              />
              <button
                type="button"
                className="dash-search-btn"
                onClick={() => applyProjectQuery(projectQuery)}
                disabled={normalizeProjectQuery(projectQuery) === normalizeProjectQuery(searchParams.get('q'))}
              >
                Apply
              </button>
            </div>
            <m.div
              className="dash-proj-grid"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {(summary?.projects || []).map((project) => (
                <m.button
                  type="button"
                  key={project.id}
                  variants={cardEntrance}
                  className="dash-proj-card"
                  onClick={() => openProject(project.id)}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className={`dash-proj-visual ${visualClass(project.visual_variant)}`}>
                    <div className="dash-proj-phase">{project.phase_label}</div>
                  </div>

                  <div className="dash-proj-body">
                    <div className="dash-proj-name">{project.name}</div>
                    <div className="dash-proj-desc">{projectNarrative(project)}</div>
                    <div className="dash-proj-outcome">{project.status_note}</div>

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
                    <div className="dash-proj-continue">Continue &rarr;</div>
                  </div>
                </m.button>
              ))}

              <m.button
                type="button"
                className="dash-proj-card empty"
                onClick={goToNewProjectView}
                variants={cardEntrance}
                whileHover={{ y: -3 }}
                whileTap={{ scale: 0.98 }}
              >
                <div className="dash-proj-empty-inner">
                  <div className="dash-proj-empty-icon">+</div>
                  <div className="dash-proj-empty-t">Start a new project</div>
                  <div className="dash-proj-empty-s">Tell Procurement AI what you need made and it handles the rest.</div>
                </div>
              </m.button>
            </m.div>
            {summary && summary.projects.length === 0 && (
              <div className="dash-empty">
                {projectQuery
                  ? 'No projects match this status and title filter yet.'
                  : 'No projects match this status filter yet.'}
              </div>
            )}
          </div>
        )}

        {tab !== 'contacts' && (
          <SourcingProfileCard authUser={authUser} projects={summary?.projects || []} />
        )}

        {tab !== 'contacts' && (
          <div className="dash-activity">
            <div className="dash-section-label">Recent activity</div>
            <m.div
              className="dash-acts"
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
            >
              {activityRows.map((event) => (
                <m.div className="dash-act-row" key={event.id} variants={cardEntrance}>
                  <div className="dash-act-time">{event.time_label}</div>
                  <div>
                    <div className="dash-act-title">{event.title}</div>
                    <div className="dash-act-desc">{event.description}</div>
                    {event.project_name ? <div className="dash-act-project">{event.project_name}</div> : null}
                  </div>
                </m.div>
              ))}
              {summary && activityRows.length === 0 && (
                <div className="dash-empty">No activity yet. Start a project to see updates.</div>
              )}
            </m.div>
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
