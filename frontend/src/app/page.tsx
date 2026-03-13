'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'

import { procurementClient } from '@/lib/api/procurementClient'
import { featureFlags } from '@/lib/featureFlags'
import { trackTraceEvent } from '@/lib/telemetry'
import { m, AnimatePresence } from '@/lib/motion'
import { fadeUp, staggerContainer, cardEntrance } from '@/lib/motion/variants'
import { useScrollTimeline } from '@/lib/motion/useScrollTimeline'

import './procurement-landing.css'

type ConvoBlock =
  | { kind: 'message'; role: 'u' | 'a'; text: string }
  | { kind: 'status'; text: string }

interface DemoScenario {
  userMessage: string
  steps: ConvoBlock[]
}

const DEMO_SCENARIOS: DemoScenario[] = [
  {
    userMessage: 'Need 500 heavyweight hoodies with embroidery, budget $15-20/unit, ship to LA in 6 weeks.',
    steps: [
      { kind: 'message', role: 'a', text: 'Got it — heavyweight cut-and-sew hoodies, 500 units, embroidered, $15-20 range, Los Angeles delivery in 6 weeks.' },
      { kind: 'status', text: 'Parsing requirements...' },
      { kind: 'status', text: 'Searching 12,400+ manufacturers across 47 countries' },
      { kind: 'message', role: 'a', text: 'Found 23 verified manufacturers matching your specs. Top 3 are in Portugal, Pakistan, and China — all with 4.5+ ratings and MOQs under 300.' },
      { kind: 'status', text: 'Verifying business registration and reviews' },
      { kind: 'message', role: 'a', text: 'Verification complete. Reaching out to your top matches for real quotes now.' },
    ],
  },
  {
    userMessage: 'I\'m launching a skincare line — need recyclable packaging: mailer boxes, tissue paper, stickers. About 5,000 units.',
    steps: [
      { kind: 'message', role: 'a', text: 'Skincare packaging set — mailer boxes, tissue paper, and stickers, all recyclable, 5,000 units. Let me find the best options.' },
      { kind: 'status', text: 'Parsing requirements...' },
      { kind: 'status', text: 'Scanning packaging manufacturers globally' },
      { kind: 'message', role: 'a', text: 'Found 18 eco-certified packaging suppliers. Best matches are in the US, UK, and India with competitive pricing for your volume.' },
      { kind: 'status', text: 'Verifying sustainability certifications' },
      { kind: 'message', role: 'a', text: 'Top 5 verified — all FSC certified with recyclable materials. Sending quote requests now.' },
    ],
  },
  {
    userMessage: 'We need 200 canvas tote bags with our nonprofit logo for a fundraiser. Trying to stay under $5 each.',
    steps: [
      { kind: 'message', role: 'a', text: 'Canvas tote bags, 200 units, single logo print, under $5/unit for a nonprofit fundraiser. I\'ll find you the best deal.' },
      { kind: 'status', text: 'Parsing requirements...' },
      { kind: 'status', text: 'Searching promotional product suppliers' },
      { kind: 'message', role: 'a', text: 'Found 14 suppliers that can hit your price point. 3 domestic options can deliver in 2 weeks with screen printing included.' },
      { kind: 'status', text: 'Comparing quotes and lead times' },
      { kind: 'message', role: 'a', text: 'Best match: $3.80/unit with free shipping for nonprofits, 10-day turnaround. Want me to get a sample?' },
    ],
  },
  {
    userMessage: 'Need a certified stamping supplier for an automotive mounting bracket — 10,000 units/month, must be IATF 16949.',
    steps: [
      { kind: 'message', role: 'a', text: 'Automotive stamping — mounting brackets, 10K/month production volume, IATF 16949 certification required. Searching now.' },
      { kind: 'status', text: 'Parsing requirements...' },
      { kind: 'status', text: 'Filtering for IATF 16949 certified facilities' },
      { kind: 'message', role: 'a', text: 'Found 9 IATF-certified stamping facilities. Top matches in Mexico, China, and Germany with capacity for 10K+/month.' },
      { kind: 'status', text: 'Verifying certifications and production capacity' },
      { kind: 'message', role: 'a', text: 'All 9 verified — certifications confirmed, references checked. Ready to compare pricing and lead times side by side.' },
    ],
  },
  {
    userMessage: 'Custom enamel pins for my streetwear brand — 1,000 units, soft enamel, 3 colorways, butterfly clutch backing.',
    steps: [
      { kind: 'message', role: 'a', text: 'Soft enamel pins, 1,000 units across 3 colorways, butterfly clutch. Classic choice for merch drops. Searching now.' },
      { kind: 'status', text: 'Parsing requirements...' },
      { kind: 'status', text: 'Searching enamel pin manufacturers worldwide' },
      { kind: 'message', role: 'a', text: 'Found 31 manufacturers. Best pricing at this MOQ comes from suppliers in Dongguan and Shenzhen — as low as $0.35/unit.' },
      { kind: 'status', text: 'Verifying quality samples and reviews' },
      { kind: 'message', role: 'a', text: 'Top 4 verified with 500+ positive reviews each. Quote requests sent — expect responses within 24 hours.' },
    ],
  },
]

function AgentAvatar() {
  return (
    <svg viewBox="0 0 28 28" fill="none" aria-hidden>
      <path d="M14 3L24 8.5V19.5L14 25L4 19.5V8.5L14 3Z" stroke="white" strokeWidth="1.5" fill="none" />
      <path d="M14 10L19 12.75V18.25L14 21L9 18.25V12.75L14 10Z" fill="white" opacity="0.9" />
    </svg>
  )
}

function CaseIconOne() {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden>
      <path d="M20 4L8 10v6c0 2 1 3.5 3 4l9 4 9-4c2-.5 3-2 3-4v-6L20 4z" stroke="var(--ink)" strokeWidth="1.2" fill="none" />
      <path d="M14 18v8M26 18v8M14 26c0 2 2.7 4 6 4s6-2 6-4" stroke="var(--ink)" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      <circle cx="20" cy="14" r="2" fill="var(--accent)" opacity="0.6" />
    </svg>
  )
}

function CaseIconTwo() {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden>
      <rect x="8" y="12" width="24" height="18" rx="2" stroke="var(--ink)" strokeWidth="1.2" fill="none" />
      <path d="M8 18h24" stroke="var(--ink)" strokeWidth="1.2" />
      <path d="M14 12V8h12v4" stroke="var(--ink)" strokeWidth="1.2" fill="none" strokeLinecap="round" />
      <circle cx="20" cy="24" r="2.5" fill="var(--accent)" opacity="0.6" />
    </svg>
  )
}

function CaseIconThree() {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden>
      <path d="M20 6l-2 6h-6l5 3.5-2 6.5 5-4 5 4-2-6.5 5-3.5h-6L20 6z" stroke="var(--ink)" strokeWidth="1.2" fill="none" strokeLinejoin="round" />
      <path d="M12 28c0 0 2 6 8 6s8-6 8-6" stroke="var(--ink)" strokeWidth="1.2" fill="none" strokeLinecap="round" />
    </svg>
  )
}

function CaseIconFour() {
  return (
    <svg viewBox="0 0 40 40" fill="none" aria-hidden>
      <circle cx="20" cy="20" r="12" stroke="var(--ink)" strokeWidth="1.2" fill="none" />
      <circle cx="20" cy="20" r="4" stroke="var(--ink)" strokeWidth="1.2" fill="none" />
      <path d="M20 8v4M20 28v4M32 20h-4M12 20H8" stroke="var(--ink)" strokeWidth="1.2" strokeLinecap="round" />
      <circle cx="20" cy="20" r="1.5" fill="var(--accent)" opacity="0.6" />
    </svg>
  )
}

export default function HomePage() {
  const router = useRouter()

  const [blocks, setBlocks] = useState<ConvoBlock[]>([])
  const [demoTyping, setDemoTyping] = useState(false)

  const [leadEmail, setLeadEmail] = useState('')
  const [leadNote, setLeadNote] = useState('')
  const [leadSubmitting, setLeadSubmitting] = useState(false)
  const [leadError, setLeadError] = useState<string | null>(null)
  const [leadSuccess, setLeadSuccess] = useState<string | null>(null)

  const convoRef = useRef<HTMLDivElement | null>(null)
  const demoStartedRef = useRef(false)

  useEffect(() => {
    if (featureFlags.procurementLandingBypass) {
      trackTraceEvent('landing_bypass_redirect', { to: '/product' })
      router.replace('/product')
    }
  }, [router])

  useEffect(() => {
    if (!convoRef.current) return
    convoRef.current.scrollTop = convoRef.current.scrollHeight
  }, [blocks])

  // Auto-play a random demo scenario when the convo section scrolls into view
  useEffect(() => {
    if (demoStartedRef.current) return

    const convoEl = document.getElementById('convo')
    if (!convoEl) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !demoStartedRef.current) {
            demoStartedRef.current = true
            observer.disconnect()
            void runDemo()
          }
        })
      },
      { threshold: 0.3 }
    )

    observer.observe(convoEl)
    return () => observer.disconnect()
  }, [])

  const runDemo = async () => {
    const scenario = DEMO_SCENARIOS[Math.floor(Math.random() * DEMO_SCENARIOS.length)]

    // Show user message
    setBlocks([{ kind: 'message', role: 'u', text: scenario.userMessage }])

    // Drip in each step with realistic delays
    for (let i = 0; i < scenario.steps.length; i++) {
      const step = scenario.steps[i]
      const delay = step.kind === 'status' ? 800 : 1200
      setDemoTyping(true)
      await new Promise((resolve) => setTimeout(resolve, delay))
      setDemoTyping(false)
      setBlocks((prev) => [...prev, step])
    }
  }

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('v')
        })
      },
      { threshold: 0.1, rootMargin: '0px 0px -20px 0px' }
    )

    document.querySelectorAll('.rv').forEach((node) => observer.observe(node))
    return () => observer.disconnect()
  }, [])

  // GSAP ScrollTrigger for the "Four steps" section
  useScrollTimeline((gsap, ScrollTrigger) => {
    const steps = document.querySelectorAll('.step')
    const stepsHeader = document.querySelector('.steps-header')

    // Stagger each step's entrance as user scrolls
    if (stepsHeader) {
      gsap.fromTo(
        stepsHeader,
        { opacity: 0, y: 40 },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          ease: 'power3.out',
          scrollTrigger: {
            trigger: stepsHeader,
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
        }
      )
    }

    steps.forEach((step, i) => {
      gsap.fromTo(
        step,
        { opacity: 0, y: 50, scale: 0.97 },
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.7,
          ease: 'power3.out',
          delay: i * 0.1,
          scrollTrigger: {
            trigger: step,
            start: 'top 80%',
            toggleActions: 'play none none none',
          },
        }
      )

      // Animate the step number
      const stepNum = step.querySelector('.step-n')
      if (stepNum) {
        gsap.fromTo(
          stepNum,
          { opacity: 0, scale: 0.5 },
          {
            opacity: 1,
            scale: 1,
            duration: 0.5,
            ease: 'back.out(2)',
            scrollTrigger: {
              trigger: step,
              start: 'top 80%',
              toggleActions: 'play none none none',
            },
          }
        )
      }
    })

    // Manifesto parallax-style entrance
    const manifesto = document.querySelector('.manifesto')
    if (manifesto) {
      gsap.fromTo(
        manifesto,
        { opacity: 0, y: 60 },
        {
          opacity: 1,
          y: 0,
          duration: 1,
          ease: 'power2.out',
          scrollTrigger: {
            trigger: manifesto,
            start: 'top 85%',
            toggleActions: 'play none none none',
          },
        }
      )
    }

    return () => {
      ScrollTrigger.getAll().forEach((t) => t.kill())
    }
  })

  if (featureFlags.procurementLandingBypass) return null

  const track = async (eventName: string, payload: Record<string, unknown> = {}) => {
    trackTraceEvent(eventName, payload, { path: '/' })
  }

  const submitLead = async (e: React.FormEvent) => {
    e.preventDefault()
    if (leadSubmitting) return

    setLeadSubmitting(true)
    setLeadError(null)
    setLeadSuccess(null)

    await track('early_access_submit_attempt', { has_note: Boolean(leadNote.trim()) })

    try {
      const result = await procurementClient.submitLead({
        email: leadEmail,
        sourcing_note: leadNote.trim() || undefined,
        source: 'landing_early_access',
      })

      if (result.deduped) {
        setLeadSuccess('You are already on the list. We updated your latest sourcing note.')
      } else {
        setLeadSuccess('You are in. We will contact you with early access updates.')
      }

      setLeadEmail('')
      setLeadNote('')
      await track('early_access_submit_success', { deduped: result.deduped })
    } catch (err: any) {
      const detail = err?.message || 'Could not save your request.'
      setLeadError(detail)
      await track('early_access_submit_error', { detail })
    } finally {
      setLeadSubmitting(false)
    }
  }

  return (
    <>
      <nav className="nav">
        <a href="#" className="nav-word">procurement ai</a>
        <div className="nav-links">
          <a href="#how">How It Works</a>
          <a href="#cases">Use Cases</a>
          <a href="#waitlist">Early Access</a>
          <Link
            href="/dashboard"
            className="nav-cta"
            onClick={() => {
              void track('cta_start_sourcing_click', { location: 'nav' })
            }}
          >
            Start now
          </Link>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-mark">PROCUREMENT AI</div>

        {/* ── Hero decorations ── */}
        <svg className="deco deco-hex" width="120" height="120" viewBox="0 0 120 120" fill="none" aria-hidden>
          <path d="M60 10L105 35V85L60 110L15 85V35L60 10Z" stroke="var(--accent)" strokeWidth="0.7" opacity="0.12" />
          <path d="M60 28L90 45V79L60 96L30 79V45L60 28Z" stroke="var(--accent)" strokeWidth="0.5" opacity="0.08" />
        </svg>
        <svg className="deco deco-circle" width="80" height="80" viewBox="0 0 80 80" fill="none" aria-hidden>
          <circle cx="40" cy="40" r="36" stroke="var(--accent)" strokeWidth="0.7" opacity="0.1" />
          <circle cx="40" cy="40" r="20" stroke="var(--accent)" strokeWidth="0.5" opacity="0.06" strokeDasharray="4 6" />
        </svg>
        <svg className="deco deco-diamond" width="60" height="60" viewBox="0 0 60 60" fill="none" aria-hidden>
          <rect x="30" y="4" width="36" height="36" rx="2" transform="rotate(45 30 4)" stroke="var(--accent)" strokeWidth="0.7" opacity="0.1" />
        </svg>
        <svg className="deco deco-dots" width="100" height="100" viewBox="0 0 100 100" fill="none" aria-hidden>
          {[0,1,2,3,4].map(r => [0,1,2,3,4].map(c => (
            <circle key={`${r}-${c}`} cx={10 + c * 20} cy={10 + r * 20} r="1.2" fill="var(--accent)" opacity="0.1" />
          )))}
        </svg>

        <h1 className="hero-headline">
          <span className="ln">Tell us what</span>
          <span className="ln">you need made.</span>
          <span className="ln">We <em>handle</em> the rest.</span>
        </h1>

        <div className="hero-foot">
          <div>
            <p>
              Procurement AI finds manufacturers around the world, verifies them, gets real quotes, and manages everything - from first search to first order.
            </p>
            <div className="hero-ctas">
              <Link
                href="/dashboard"
                className="btn-d"
                onClick={() => {
                  void track('cta_start_sourcing_click', { location: 'hero' })
                }}
              >
                Start sourcing now
                <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
              <a href="#waitlist" className="btn-g">Get Early Access</a>
            </div>
          </div>

          <div className="scroll-cue">
            <span>Scroll</span>
            <div className="scroll-bar" />
          </div>
        </div>
      </section>

      <section className="scene" id="how">
        <div className="scene-layout">
          <div className="scene-text rv">
            <div className="scene-tag">See it in action</div>
            <h2>Like having the world&apos;s best sourcing agent on call.</h2>
            <p>
              Describe what you need in plain language. Procurement AI searches global databases, verifies every match,
              reaches out for real quotes, and brings you options you can act on - in minutes.
            </p>
            <div className="scene-nums">
              <div className="sn"><div className="v">12K+</div><div className="l">Manufacturers</div></div>
              <div className="sn"><div className="v">47</div><div className="l">Countries</div></div>
              <div className="sn"><div className="v">~4m</div><div className="l">To first quote</div></div>
            </div>
          </div>

          <div className="convo rv" id="convo" ref={convoRef}>
            {blocks.length === 0 && (
              <div className="convo-placeholder">
                <div className="convo-placeholder-icon">
                  <AgentAvatar />
                </div>
                <p>Watch Procurement AI work...</p>
              </div>
            )}

            {blocks.map((block, idx) => {
              if (block.kind === 'message') {
                if (block.role === 'u') {
                  return (
                    <m.div
                      key={`${block.kind}-${idx}`}
                      className="m u"
                      initial={{ opacity: 0, y: 12, scale: 0.96 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                    >
                      <div className="m-bub">{block.text}</div>
                    </m.div>
                  )
                }

                return (
                  <m.div
                    key={`${block.kind}-${idx}`}
                    className="m a"
                    initial={{ opacity: 0, y: 12, scale: 0.96 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <div className="m-av ag"><AgentAvatar /></div>
                    <div className="m-bub">{block.text}</div>
                  </m.div>
                )
              }

              return (
                <m.div
                  key={`${block.kind}-${idx}`}
                  className="status"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                >
                  <div className="status-h"><span className="dot-pulse" /> Agent status</div>
                  <div className="status-line"><span className="ck">&#10003;</span> {block.text}</div>
                </m.div>
              )
            })}

            {demoTyping && (
              <div className="m a">
                <div className="m-av ag"><AgentAvatar /></div>
                <div className="m-bub typing-indicator">
                  <span /><span /><span />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Wave divider ── */}
      <div className="deco-wave-wrap" aria-hidden>
        <svg className="deco-wave" viewBox="0 0 1440 60" preserveAspectRatio="none" fill="none">
          <path d="M0 30C240 60 480 0 720 30C960 60 1200 0 1440 30" stroke="var(--accent)" strokeWidth="1" opacity="0.12" />
          <path d="M0 40C240 10 480 50 720 20C960 50 1200 10 1440 40" stroke="var(--accent)" strokeWidth="0.6" opacity="0.07" />
        </svg>
      </div>

      <section className="manifesto rv">
        <blockquote>
          The people who need sourcing tools the most have never heard the word <em>procurement</em>. We built Procurement AI for them.
        </blockquote>
        <cite>The idea behind Procurement AI</cite>
      </section>

      <section className="steps-section" id="steps">
        {/* ── Steps corner decoration ── */}
        <svg className="deco deco-steps-corner" width="140" height="140" viewBox="0 0 140 140" fill="none" aria-hidden>
          <path d="M0 140L140 0" stroke="var(--accent)" strokeWidth="0.5" opacity="0.08" />
          <path d="M0 100L100 0" stroke="var(--accent)" strokeWidth="0.5" opacity="0.06" />
          <path d="M0 60L60 0" stroke="var(--accent)" strokeWidth="0.5" opacity="0.04" />
          <circle cx="70" cy="70" r="3" fill="var(--accent)" opacity="0.12" />
        </svg>
        <div className="steps-header rv">
          <h2>Four steps.<br />Zero friction.</h2>
          <p>
            No sign-ups, no forms, no implementation. You talk to Procurement AI like a person. It does the work of an entire sourcing team.
          </p>
        </div>

        <div className="step rv">
          <div className="step-n">01</div>
          <div>
            <h3>Describe what you need</h3>
            <p>
              "I need 500 custom hoodies with embroidered logos" is enough. Procurement AI asks smart follow-ups to nail the details - fabric, colors, budget, timeline.
            </p>
          </div>
          <div className="step-details">
            <div className="sd">Natural language - no forms, no industry jargon</div>
            <div className="sd">Upload reference images, sketches, or tech packs</div>
            <div className="sd">Clarifies what matters before it starts searching</div>
          </div>
        </div>

        <div className="step rv">
          <div className="step-n">02</div>
          <div>
            <h3>We search the world</h3>
            <p>
              Procurement AI scans thousands of manufacturers globally, filters by your exact needs, and verifies every match with real business data - before you see a single result.
            </p>
          </div>
          <div className="step-details">
            <div className="sd">Searches across 47 countries in seconds</div>
            <div className="sd">Verifies business registration, reviews, and history</div>
            <div className="sd">Filters for your specs, budget, and minimum order</div>
          </div>
        </div>

        <div className="step rv">
          <div className="step-n">03</div>
          <div>
            <h3>We reach out and get quotes</h3>
            <p>
              No cold emails that go nowhere. Procurement AI contacts the best matches, follows up, gets detailed pricing, and brings everything back to you - automatically.
            </p>
          </div>
          <div className="step-details">
            <div className="sd">Automated outreach that actually gets responses</div>
            <div className="sd">Follows up so you never have to chase</div>
            <div className="sd">Returns real quotes with pricing, MOQ, and lead times</div>
          </div>
        </div>

        <div className="step rv">
          <div className="step-n">04</div>
          <div>
            <h3>You pick. We go.</h3>
            <p>
              Compare verified manufacturers side by side with Procurement AI&apos;s recommendation. Request samples or start your order - from the same conversation.
            </p>
          </div>
          <div className="step-details">
            <div className="sd">Side-by-side comparison with a clear recommendation</div>
            <div className="sd">One tap to request samples</div>
            <div className="sd">Full order lifecycle managed in one place</div>
          </div>
        </div>
      </section>

      <section className="dark">
        <div className="dark-inner">
          <div className="dark-header rv">
            <div>
              <div className="scene-tag" style={{ color: 'var(--accent)' }}>Before &amp; After</div>
              <h2>Twenty hours of work.<br />Four minutes with Procurement AI.</h2>
            </div>
            <p>
              The average small business spends 20+ hours on every sourcing project. Most of it is searching,
              emailing, waiting, and hoping. Procurement AI replaces all of it.
            </p>
          </div>

          <div className="tl rv">
            <div className="tl-side">
              <div className="tl-label">Without Procurement AI</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Hours Googling "custom hoodie manufacturer"</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Scrolling Alibaba hoping the reviews are real</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Cold emails that get ignored for weeks</div>
              <div className="tl-i"><span className="tl-ic">✕</span> No way to verify if a vendor is legitimate</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Comparing quotes across 14 email threads</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Weeks before you get a single usable response</div>
            </div>

            <div className="tl-side">
              <div className="tl-label">With Procurement AI</div>
              <div className="tl-i"><span className="tl-ic">✓</span> Searches 12,000+ manufacturers instantly</div>
              <div className="tl-i"><span className="tl-ic">✓</span> Every match verified with real business data</div>
              <div className="tl-i"><span className="tl-ic">✓</span> Reaches out and follows up automatically</div>
              <div className="tl-i"><span className="tl-ic">✓</span> Registration, reviews, and track record checked</div>
              <div className="tl-i"><span className="tl-ic">✓</span> Side-by-side comparison in one view</div>
              <div className="tl-i"><span className="tl-ic">✓</span> First real quotes in under five minutes</div>
            </div>
          </div>
        </div>
      </section>

      <section className="cases" id="cases">
        <div className="cases-head rv">
          <h2>If you need<br />something made,<br />just ask.</h2>
          <p>From 200 tote bags for a fundraiser to 10,000 automotive parts per month.</p>
        </div>

        <div className="cg">
          <div className="cx rv">
            <div className="cx-icon"><CaseIconOne /></div>
            <div className="cx-t">Apparel &amp; Merch</div>
            <div className="cx-d">Hoodies, tees, hats, full clothing lines. From your first sample run to your biggest drop yet - anywhere in the world.</div>
            <div className="cx-p">We&apos;re launching a streetwear brand and need someone who can do heavyweight cut-and-sew hoodies with embroidery. About 500 to start.</div>
          </div>

          <div className="cx rv">
            <div className="cx-icon"><CaseIconTwo /></div>
            <div className="cx-t">Product &amp; Packaging</div>
            <div className="cx-d">Custom boxes, labels, bags, bottles. Everything between your product and your customer&apos;s hands.</div>
            <div className="cx-p">I&apos;m launching a skincare line and need beautiful recyclable packaging - mailer boxes, tissue paper, stickers. Around 5,000 units to start.</div>
          </div>

          <div className="cx rv">
            <div className="cx-icon"><CaseIconThree /></div>
            <div className="cx-t">Nonprofits &amp; Community</div>
            <div className="cx-d">Event supplies, branded materials, fundraiser merch. Make every dollar count with vetted vendors and real quotes.</div>
            <div className="cx-p">We&apos;re hosting a community fundraiser and need nice canvas tote bags with our logo - maybe 200? Trying to stay under $5 each if possible.</div>
          </div>

          <div className="cx rv">
            <div className="cx-icon"><CaseIconFour /></div>
            <div className="cx-t">Manufacturing &amp; Auto</div>
            <div className="cx-d">Custom parts, precision machining, stamping, molding. Certified suppliers for production-volume manufacturing.</div>
            <div className="cx-p">We need a certified stamping supplier for an automotive mounting bracket - about 10,000 units a month, needs to be IATF 16949.</div>
          </div>
        </div>
      </section>

      <section className="final" id="waitlist">
        {/* ── Final section radial decoration ── */}
        <svg className="deco deco-radial" width="300" height="300" viewBox="0 0 300 300" fill="none" aria-hidden>
          <circle cx="150" cy="150" r="140" stroke="var(--accent)" strokeWidth="0.5" opacity="0.06" />
          <circle cx="150" cy="150" r="100" stroke="var(--accent)" strokeWidth="0.5" opacity="0.05" />
          <circle cx="150" cy="150" r="60" stroke="var(--accent)" strokeWidth="0.5" opacity="0.04" />
          <line x1="150" y1="10" x2="150" y2="290" stroke="var(--accent)" strokeWidth="0.3" opacity="0.04" />
          <line x1="10" y1="150" x2="290" y2="150" stroke="var(--accent)" strokeWidth="0.3" opacity="0.04" />
        </svg>

        <div className="rv">
          <div className="scene-tag" style={{ textAlign: 'center' }}>Early Access</div>
          <h2>Stop searching.<br />Start <em>finding</em>.</h2>
          <p>Join the waitlist. Tell us what you&apos;re sourcing - we&apos;ll show you what&apos;s possible.</p>

          <form onSubmit={submitLead}>
            <div className="ff">
              <input
                type="email"
                className="fi"
                placeholder="your@email.com"
                value={leadEmail}
                onChange={(e) => setLeadEmail(e.target.value)}
                required
                disabled={leadSubmitting}
              />
              <button className="fb" type="submit" disabled={leadSubmitting}>
                {leadSubmitting ? 'Saving...' : 'Get Early Access'}
              </button>
            </div>
            <input
              type="text"
              className="fi"
              style={{ marginTop: 10, width: '100%', maxWidth: 440, marginLeft: 'auto', marginRight: 'auto', display: 'block' }}
              placeholder="What are you sourcing? (optional)"
              value={leadNote}
              onChange={(e) => setLeadNote(e.target.value)}
              disabled={leadSubmitting}
            />
          </form>

          <div className="hero-ctas" style={{ justifyContent: 'center' }}>
            <Link
              href="/dashboard"
              className="btn-g"
              onClick={() => {
                void track('cta_start_sourcing_click', { location: 'final' })
              }}
            >
              Open dashboard now
            </Link>
          </div>

          {leadError && <div className="fn" style={{ color: '#B91C1C' }}>{leadError}</div>}
          {leadSuccess && <div className="fn" style={{ color: '#065F46' }}>{leadSuccess}</div>}
          {!leadError && !leadSuccess && <div className="fn">Free to try - No credit card - First 100 get priority</div>}
        </div>
      </section>

      <footer className="foot">
        <div className="fw">tam<em>kin</em></div>
        <div className="fl">
          <a href="#">About</a>
          <a href="#">Blog</a>
          <a href="#">Twitter</a>
          <a href="#">LinkedIn</a>
        </div>
        <div className="far">PROCUREMENT AI</div>
      </footer>
    </>
  )
}
