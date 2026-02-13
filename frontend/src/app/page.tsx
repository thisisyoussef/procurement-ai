'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'

import { tamkinClient } from '@/lib/api/tamkinClient'
import { featureFlags } from '@/lib/featureFlags'

import './tamkin-landing.css'

type ConvoBlock =
  | { kind: 'message'; role: 'u' | 'a'; text: string }
  | { kind: 'status'; text: string }

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

  const [liveInput, setLiveInput] = useState('')
  const [isStartingIntake, setIsStartingIntake] = useState(false)
  const [intakeError, setIntakeError] = useState<string | null>(null)
  const [blocks, setBlocks] = useState<ConvoBlock[]>([])

  const [leadEmail, setLeadEmail] = useState('')
  const [leadNote, setLeadNote] = useState('')
  const [leadSubmitting, setLeadSubmitting] = useState(false)
  const [leadError, setLeadError] = useState<string | null>(null)
  const [leadSuccess, setLeadSuccess] = useState<string | null>(null)

  const [sessionId, setSessionId] = useState<string | null>(null)

  const convoRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!sessionId) {
      setSessionId(`sess_${Math.random().toString(36).slice(2)}`)
    }
  }, [sessionId])

  useEffect(() => {
    if (featureFlags.tamkinLandingBypass) {
      router.replace('/product')
    }
  }, [router])

  useEffect(() => {
    if (!convoRef.current) return
    convoRef.current.scrollTop = convoRef.current.scrollHeight
  }, [blocks])

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

  if (featureFlags.tamkinLandingBypass) return null

  const track = async (eventName: string, payload: Record<string, unknown> = {}) => {
    try {
      await tamkinClient.trackEvent({
        event_name: eventName,
        session_id: sessionId || undefined,
        path: '/',
        payload,
      })
    } catch {
      // Non-blocking telemetry.
    }
  }

  const startIntake = async () => {
    if (isStartingIntake) return

    const message =
      liveInput.trim() ||
      'Need 500 heavyweight hoodies with embroidery, target budget $15-20 per unit, shipping to Los Angeles in 6 weeks.'

    setIsStartingIntake(true)
    setIntakeError(null)
    setBlocks((prev) => [
      ...prev,
      { kind: 'message', role: 'u', text: message },
      {
        kind: 'message',
        role: 'a',
        text: 'Got it. I am starting your sourcing mission now and moving this into your product workspace.',
      },
      { kind: 'status', text: 'Starting mission and preparing your product workspace...' },
    ])

    await track('hero_intake_submit', { location: 'scene_chat' })

    try {
      const result = await tamkinClient.startIntake({
        message,
        source: 'landing_hero',
        session_id: sessionId || undefined,
      })
      router.push(result.redirect_path)
    } catch (err: any) {
      const detail = err?.message || 'Could not start your mission. Please try again.'
      setIntakeError(detail)
      setBlocks((prev) => [
        ...prev,
        {
          kind: 'message',
          role: 'a',
          text: `I could not start your mission right now: ${detail}`,
        },
      ])
      setIsStartingIntake(false)
    }
  }

  const submitLead = async (e: React.FormEvent) => {
    e.preventDefault()
    if (leadSubmitting) return

    setLeadSubmitting(true)
    setLeadError(null)
    setLeadSuccess(null)

    await track('early_access_submit_attempt', { has_note: Boolean(leadNote.trim()) })

    try {
      const result = await tamkinClient.submitLead({
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
        <a href="#" className="nav-word">tamkin</a>
        <div className="nav-links">
          <a href="#how">How It Works</a>
          <a href="#cases">Use Cases</a>
          <a href="#waitlist">Early Access</a>
          <Link
            href="/product"
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
        <div className="hero-arabic">تمكين</div>
        <h1 className="hero-headline">
          <span className="ln">Tell us what</span>
          <span className="ln">you need made.</span>
          <span className="ln">We <em>handle</em> the rest.</span>
        </h1>

        <div className="hero-foot">
          <div>
            <p>
              Tamkin finds manufacturers around the world, verifies them, gets real quotes, and manages everything - from first search to first order.
            </p>
            <div className="hero-ctas">
              <Link
                href="/product"
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
              Describe what you need in plain language. Tamkin searches global databases, verifies every match,
              reaches out for real quotes, and brings you options you can act on - in minutes.
            </p>
            <div className="scene-nums">
              <div className="sn"><div className="v">12K+</div><div className="l">Manufacturers</div></div>
              <div className="sn"><div className="v">47</div><div className="l">Countries</div></div>
              <div className="sn"><div className="v">~4m</div><div className="l">To first quote</div></div>
            </div>
          </div>

          <div className="convo rv" id="convo" ref={convoRef}>
            <div className="convo-input" id="inputWrap">
              <input
                id="liveInput"
                placeholder="Describe what you need - in your own words..."
                value={liveInput}
                onChange={(e) => setLiveInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') void startIntake()
                }}
                disabled={isStartingIntake}
              />
              <button className="convo-send" id="sendBtn" onClick={startIntake} aria-label="Start intake" disabled={isStartingIntake}>
                <svg viewBox="0 0 16 16" fill="none" aria-hidden>
                  <path d="M3 8h10M9 4l4 4-4 4" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>

            {blocks.map((block, idx) => {
              if (block.kind === 'message') {
                if (block.role === 'u') {
                  return (
                    <div key={`${block.kind}-${idx}`} className="m u">
                      <div className="m-bub">{block.text}</div>
                      <div className="m-av me">Y</div>
                    </div>
                  )
                }

                return (
                  <div key={`${block.kind}-${idx}`} className="m a">
                    <div className="m-av ag"><AgentAvatar /></div>
                    <div className="m-bub">{block.text}</div>
                  </div>
                )
              }

              return (
                <div key={`${block.kind}-${idx}`} className="status">
                  <div className="status-h"><span className="dot-pulse" /> Agent status</div>
                  <div className="status-line"><span className="ck">✓</span> {block.text}</div>
                </div>
              )
            })}

            {intakeError && (
              <div className="reco" role="alert">
                <strong>Could not start mission.</strong> {intakeError}
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="manifesto rv">
        <blockquote>
          The people who need sourcing tools the most have never heard the word <em>procurement</em>. We built Tamkin for them.
        </blockquote>
        <cite>The idea behind Tamkin</cite>
      </section>

      <section className="steps-section" id="steps">
        <div className="steps-header rv">
          <h2>Four steps.<br />Zero friction.</h2>
          <p>
            No sign-ups, no forms, no implementation. You talk to Tamkin like a person. It does the work of an entire sourcing team.
          </p>
        </div>

        <div className="step rv">
          <div className="step-n">01</div>
          <div>
            <h3>Describe what you need</h3>
            <p>
              "I need 500 custom hoodies with embroidered logos" is enough. Tamkin asks smart follow-ups to nail the details - fabric, colors, budget, timeline.
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
              Tamkin scans thousands of manufacturers globally, filters by your exact needs, and verifies every match with real business data - before you see a single result.
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
              No cold emails that go nowhere. Tamkin contacts the best matches, follows up, gets detailed pricing, and brings everything back to you - automatically.
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
              Compare verified manufacturers side by side with Tamkin&apos;s recommendation. Request samples or start your order - from the same conversation.
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
              <h2>Twenty hours of work.<br />Four minutes with Tamkin.</h2>
            </div>
            <p>
              The average small business spends 20+ hours on every sourcing project. Most of it is searching,
              emailing, waiting, and hoping. Tamkin replaces all of it.
            </p>
          </div>

          <div className="tl rv">
            <div className="tl-side">
              <div className="tl-label">Without Tamkin</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Hours Googling "custom hoodie manufacturer"</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Scrolling Alibaba hoping the reviews are real</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Cold emails that get ignored for weeks</div>
              <div className="tl-i"><span className="tl-ic">✕</span> No way to verify if a vendor is legitimate</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Comparing quotes across 14 email threads</div>
              <div className="tl-i"><span className="tl-ic">✕</span> Weeks before you get a single usable response</div>
            </div>

            <div className="tl-side">
              <div className="tl-label">With Tamkin</div>
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
              href="/product"
              className="btn-g"
              onClick={() => {
                void track('cta_start_sourcing_click', { location: 'final' })
              }}
            >
              Go to product now
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
        <div className="far">تمكين</div>
      </footer>
    </>
  )
}
