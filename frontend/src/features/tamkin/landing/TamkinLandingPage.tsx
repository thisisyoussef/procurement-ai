'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  ArrowRight,
  Bot,
  Factory,
  Globe,
  ShieldCheck,
  Sparkles,
  Workflow,
} from 'lucide-react'

import ExperienceToggle from '@/features/tamkin/components/ExperienceToggle'
import { checkBackendHealth, createMission } from '@/lib/api/tamkinClient'
import { TAMKIN_CORE_LINE, TAMKIN_COPY } from '@/features/tamkin/copy/voice'

interface IntakeFormState {
  product: string
  quantity: string
  budget: string
  deadline: string
  destination: string
}

const INITIAL_FORM: IntakeFormState = {
  product: '',
  quantity: '',
  budget: '',
  deadline: '',
  destination: '',
}

const HERO_STATS = [
  { label: 'Search + Network in one flow', value: 'Hybrid sourcing' },
  { label: 'Operator review points', value: 'High-impact only' },
  { label: 'Mission control speed', value: 'Minutes, not months' },
]

const HOW_IT_WORKS = [
  {
    icon: Sparkles,
    title: 'Tell Tamkin what you need',
    copy: 'Start with plain language. “I need 500 hoodies made.” Tamkin turns that into a mission plan.',
  },
  {
    icon: Globe,
    title: 'Agent runs the search and vetting',
    copy: 'The agent pulls from web sources, directories, and supplier memory while checking quality signals.',
  },
  {
    icon: Workflow,
    title: 'Approve only what matters',
    copy: 'You only step in for shortlist lock-in, outbound send, and final supplier decisions.',
  },
]

interface TamkinLandingPageProps {
  experienceEnabled: boolean
}

export default function TamkinLandingPage({ experienceEnabled }: TamkinLandingPageProps) {
  const router = useRouter()
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null)
  const [showIntake, setShowIntake] = useState(false)
  const [form, setForm] = useState<IntakeFormState>(INITIAL_FORM)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const runHealthCheck = async () => {
      const ok = await checkBackendHealth()
      setBackendOnline(ok)
    }

    void runHealthCheck()
    const interval = setInterval(runHealthCheck, 10000)
    return () => clearInterval(interval)
  }, [])

  const missionPreview = useMemo(() => {
    const segments = [
      form.product ? `Need: ${form.product}` : null,
      form.quantity ? `Quantity: ${form.quantity}` : null,
      form.budget ? `Budget: ${form.budget}` : null,
      form.deadline ? `Timeline: ${form.deadline}` : null,
      form.destination ? `Deliver to: ${form.destination}` : null,
    ].filter(Boolean)

    return segments.length > 0
      ? `${segments.join(' | ')}. Please find the right suppliers, compare quotes, and keep me updated with key approvals only.`
      : 'Tell Tamkin your product, quantity, budget, timeline, and destination to start a mission.'
  }, [form])

  const handleCreateMission = async () => {
    if (!form.product.trim()) {
      setError('Start with what you need made or sourced.')
      return
    }

    setError(null)
    setIsCreating(true)

    const title = form.product.trim().slice(0, 80)
    const descriptionLines = [
      `I need help sourcing: ${form.product.trim()}.`,
      form.quantity.trim() ? `Target quantity: ${form.quantity.trim()}.` : null,
      form.budget.trim() ? `Budget: ${form.budget.trim()}.` : null,
      form.deadline.trim() ? `Required timeline: ${form.deadline.trim()}.` : null,
      form.destination.trim() ? `Delivery destination: ${form.destination.trim()}.` : null,
      'Please find strong options, vet suppliers, and ask me only for high-impact approvals.',
    ].filter(Boolean)

    try {
      const created = await createMission({
        title,
        productDescription: descriptionLines.join(' '),
      })
      router.push(`/workspace/${created.project_id}`)
    } catch (err: any) {
      setError(err?.message || 'Could not start mission right now.')
      setIsCreating(false)
    }
  }

  return (
    <main className="tamkin-shell min-h-screen overflow-x-clip">
      <ExperienceToggle enabled={experienceEnabled} />
      <div className="tamkin-bg-orbs" aria-hidden />

      <header className="sticky top-0 z-40 border-b border-white/10 bg-[rgba(8,16,24,0.82)] backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-[1240px] items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="tamkin-gold-ring flex h-10 w-10 items-center justify-center rounded-xl bg-[#132235] shadow-[0_10px_30px_rgba(0,0,0,0.35)]">
              <Factory className="h-5 w-5 text-[#f5d9ab]" />
            </div>
            <div>
              <p className="tamkin-display text-xl font-semibold tracking-wide text-[#fff4dc]">Tamkin</p>
              <p className="text-xs text-[#9eb0c4]">تمكين</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs text-[#dbe4ef] md:inline-flex">
              {TAMKIN_COPY.navTagline}
            </span>
            <span
              className={`rounded-full px-3 py-1 text-xs font-medium ${
                backendOnline === false
                  ? 'border border-red-300/50 bg-red-500/20 text-red-100'
                  : 'border border-emerald-300/40 bg-emerald-500/20 text-emerald-100'
              }`}
            >
              {backendOnline === false ? 'API offline' : 'API connected'}
            </span>
          </div>
        </div>
      </header>

      <section className="relative mx-auto grid w-full max-w-[1240px] gap-10 px-6 pb-20 pt-16 lg:grid-cols-[1.15fr_0.85fr]">
        <div>
          <p className="mb-4 inline-flex rounded-full border border-[#f3cb8b66] bg-[#f3cb8b1f] px-4 py-1 text-xs uppercase tracking-[0.2em] text-[#f5d9ab]">
            {TAMKIN_COPY.heroEyebrow}
          </p>
          <h1 className="tamkin-display text-5xl leading-[1.02] text-[#fff4dc] md:text-6xl">
            {TAMKIN_COPY.heroTitle}
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-[#cad6e3]">
            {TAMKIN_COPY.heroSubtitle}
          </p>
          <p className="mt-4 max-w-2xl text-base text-[#f3cb8b]">{TAMKIN_CORE_LINE}</p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <button
              onClick={() => setShowIntake(true)}
              className="tamkin-cta inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-semibold"
            >
              {TAMKIN_COPY.primaryCta}
              <ArrowRight className="h-4 w-4" />
            </button>
            <a
              href="#mission-preview"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-5 py-3 text-sm text-[#e2eaf4] transition hover:bg-white/10"
            >
              {TAMKIN_COPY.secondaryCta}
            </a>
          </div>

          <p className="mt-4 text-sm text-[#95a8be]">{TAMKIN_COPY.trustLine}</p>

          <div className="mt-8 grid gap-3 md:grid-cols-3">
            {HERO_STATS.map((item) => (
              <article
                key={item.label}
                className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 shadow-[0_18px_40px_rgba(0,0,0,0.2)]"
              >
                <p className="text-xl font-semibold text-[#f9f2e5]">{item.value}</p>
                <p className="mt-1 text-xs text-[#96a9be]">{item.label}</p>
              </article>
            ))}
          </div>
        </div>

        <div id="mission-preview" className="relative">
          <div className="tamkin-panel h-full rounded-[28px] border border-white/10 bg-[linear-gradient(160deg,#131f2dcc,#0d1622e8)] p-6 shadow-[0_35px_90px_rgba(0,0,0,0.42)]">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm font-medium text-[#e8eff7]">Mission control preview</p>
              <span className="rounded-full border border-[#f3cb8b59] bg-[#f3cb8b26] px-3 py-1 text-xs text-[#f5d9ab]">
                Cinematic mode
              </span>
            </div>

            <div className="space-y-3">
              <div className="rounded-2xl border border-white/10 bg-[#0e1824] p-4">
                <p className="text-xs uppercase tracking-[0.16em] text-[#8ea3bb]">Mission input</p>
                <p className="mt-2 text-sm leading-relaxed text-[#ecf2f9]">{missionPreview}</p>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-emerald-300/20 bg-emerald-500/10 p-4">
                  <p className="text-xs text-emerald-100">Agent action</p>
                  <p className="mt-2 text-sm text-emerald-50">Searching global + local supplier signals</p>
                </div>
                <div className="rounded-2xl border border-amber-300/30 bg-amber-500/10 p-4">
                  <p className="text-xs text-amber-100">Approval gate</p>
                  <p className="mt-2 text-sm text-amber-50">Approve shortlist before outreach is sent</p>
                </div>
              </div>
            </div>

            <div className="mt-6 border-t border-white/10 pt-4 text-sm text-[#b6c3d2]">
              Inbox + timeline stay live while the agent runs tasks in the background.
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto grid w-full max-w-[1240px] gap-8 px-6 pb-16 md:grid-cols-3">
        {HOW_IT_WORKS.map((item) => (
          <article
            key={item.title}
            className="rounded-2xl border border-white/10 bg-white/[0.03] p-6 transition hover:border-[#f3cb8b66] hover:bg-white/[0.055]"
          >
            <item.icon className="h-5 w-5 text-[#f5d9ab]" />
            <h3 className="mt-4 text-lg font-semibold text-[#f7ede0]">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-[#afbed0]">{item.copy}</p>
          </article>
        ))}
      </section>

      <section className="mx-auto w-full max-w-[1240px] px-6 pb-20">
        <div className="grid gap-6 rounded-[28px] border border-white/10 bg-[linear-gradient(145deg,#0f1824,#111f30)] p-8 md:grid-cols-[1.1fr_0.9fr]">
          <div>
            <h2 className="tamkin-display text-4xl text-[#fff2db]">A sourcing operator in your pocket</h2>
            <p className="mt-3 max-w-xl text-base leading-relaxed text-[#bcc9d8]">
              Stop juggling spreadsheets, random links, and unverified contacts. Tamkin keeps your supplier search,
              approvals, and relationship history in one operational thread.
            </p>

            <div className="mt-6 space-y-3">
              <p className="flex items-center gap-3 text-sm text-[#d2deea]"><ShieldCheck className="h-4 w-4 text-[#7dd8a4]" /> Verified signal-first recommendations</p>
              <p className="flex items-center gap-3 text-sm text-[#d2deea]"><Bot className="h-4 w-4 text-[#73b9ff]" /> Agent-powered execution with human checkpoints</p>
              <p className="flex items-center gap-3 text-sm text-[#d2deea]"><Factory className="h-4 w-4 text-[#f4cc8f]" /> Built for real products, real suppliers, and real deadlines</p>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/20 p-5">
            <p className="text-xs uppercase tracking-[0.18em] text-[#97a9bf]">Before vs after</p>
            <div className="mt-4 space-y-3 text-sm">
              <div className="rounded-xl border border-red-300/30 bg-red-500/10 p-3 text-red-50">
                Before: Google tabs, unclear suppliers, and manual follow-up chaos.
              </div>
              <div className="rounded-xl border border-emerald-300/30 bg-emerald-500/10 p-3 text-emerald-50">
                After: one mission thread, ranked options, and approvals only where your decision matters.
              </div>
            </div>
          </div>
        </div>
      </section>

      {showIntake && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#04080ecc] p-4 backdrop-blur-sm">
          <div className="w-full max-w-2xl rounded-[28px] border border-white/15 bg-[linear-gradient(170deg,#121d2b,#0d1520)] p-6 shadow-[0_38px_110px_rgba(0,0,0,0.48)]">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="tamkin-display text-3xl text-[#fff2db]">{TAMKIN_COPY.intakeTitle}</h2>
                <p className="mt-1 text-sm text-[#b8c8d9]">{TAMKIN_COPY.intakeSubtitle}</p>
              </div>
              <button
                onClick={() => {
                  if (isCreating) return
                  setShowIntake(false)
                  setError(null)
                }}
                className="rounded-full border border-white/20 px-3 py-1.5 text-xs text-[#d3deeb] hover:bg-white/10"
              >
                Close
              </button>
            </div>

            <div className="grid gap-3 sm:grid-cols-2">
              <label className="space-y-1 sm:col-span-2">
                <span className="text-xs text-[#96a9be]">What do you need made or sourced?</span>
                <input
                  value={form.product}
                  onChange={(event) => setForm((prev) => ({ ...prev, product: event.target.value }))}
                  placeholder="Example: 500 heavyweight hoodies with custom labels"
                  className="w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-[#eff4fb] placeholder:text-[#7e95ad] focus:border-[#f3cb8b88] focus:outline-none"
                />
              </label>

              <label className="space-y-1">
                <span className="text-xs text-[#96a9be]">Quantity</span>
                <input
                  value={form.quantity}
                  onChange={(event) => setForm((prev) => ({ ...prev, quantity: event.target.value }))}
                  placeholder="500 units"
                  className="w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-[#eff4fb] placeholder:text-[#7e95ad] focus:border-[#f3cb8b88] focus:outline-none"
                />
              </label>

              <label className="space-y-1">
                <span className="text-xs text-[#96a9be]">Budget</span>
                <input
                  value={form.budget}
                  onChange={(event) => setForm((prev) => ({ ...prev, budget: event.target.value }))}
                  placeholder="$4-8 per unit"
                  className="w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-[#eff4fb] placeholder:text-[#7e95ad] focus:border-[#f3cb8b88] focus:outline-none"
                />
              </label>

              <label className="space-y-1">
                <span className="text-xs text-[#96a9be]">Deadline</span>
                <input
                  value={form.deadline}
                  onChange={(event) => setForm((prev) => ({ ...prev, deadline: event.target.value }))}
                  placeholder="Need samples in 2 weeks"
                  className="w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-[#eff4fb] placeholder:text-[#7e95ad] focus:border-[#f3cb8b88] focus:outline-none"
                />
              </label>

              <label className="space-y-1">
                <span className="text-xs text-[#96a9be]">Destination</span>
                <input
                  value={form.destination}
                  onChange={(event) => setForm((prev) => ({ ...prev, destination: event.target.value }))}
                  placeholder="Austin, Texas"
                  className="w-full rounded-xl border border-white/15 bg-white/5 px-3 py-2 text-sm text-[#eff4fb] placeholder:text-[#7e95ad] focus:border-[#f3cb8b88] focus:outline-none"
                />
              </label>
            </div>

            {error && <p className="mt-3 text-sm text-[#ffb1b1]">{error}</p>}

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <p className="text-xs text-[#8ea4bd]">Tamkin will ask follow-up questions only if needed.</p>
              <button
                onClick={handleCreateMission}
                disabled={isCreating}
                className="tamkin-cta inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isCreating ? 'Starting mission...' : 'Start sourcing chat'}
                <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  )
}
