# Procurement AI — Frontend Technical Reference

> **The UI That Makes AI Procurement Feel Like Having a Smart Colleague**
> Last updated: February 14, 2026

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Technology Stack](#2-technology-stack)
3. [Directory Structure](#3-directory-structure)
4. [Application Architecture](#4-application-architecture)
5. [Routing & Page Structure](#5-routing--page-structure)
6. [Visual Design System](#6-visual-design-system)
7. [Animation System](#7-animation-system)
8. [State Management — WorkspaceContext](#8-state-management--workspacecontext)
9. [Type System — pipeline.ts](#9-type-system--pipelinets)
10. [Phase System — How Stages Become Tabs](#10-phase-system--how-stages-become-tabs)
11. [Polling Engine — Real-Time Status Updates](#11-polling-engine--real-time-status-updates)
12. [Chat System — useChat Hook](#12-chat-system--usechat-hook)
13. [Component Tree — Full Hierarchy](#13-component-tree--full-hierarchy)
14. [Landing Page — First Impression](#14-landing-page--first-impression)
15. [Dashboard Page — Project Memory](#15-dashboard-page--project-memory)
16. [Workspace Shell — The Main Arena](#16-workspace-shell--the-main-arena)
17. [Phase Tab Bar — Navigation & Identity](#17-phase-tab-bar--navigation--identity)
18. [Center Stage — Phase Router](#18-center-stage--phase-router)
19. [Brief Phase — Play-by-Play](#19-brief-phase--play-by-play)
20. [Search Phase — Play-by-Play](#20-search-phase--play-by-play)
21. [Compare Phase — Play-by-Play](#21-compare-phase--play-by-play)
22. [Outreach Phase — Play-by-Play](#22-outreach-phase--play-by-play)
23. [Samples & Order Phases — Placeholders](#23-samples--order-phases--placeholders)
24. [Live Progress Feed — The Narrative Engine](#24-live-progress-feed--the-narrative-engine)
25. [Checkpoint Banner — Human-in-the-Loop](#25-checkpoint-banner--human-in-the-loop)
26. [Stage Transition Toast — Moment Markers](#26-stage-transition-toast--moment-markers)
27. [Error Recovery Card — Contextual Recovery](#27-error-recovery-card--contextual-recovery)
28. [Input Bar — Conversational Steering](#28-input-bar--conversational-steering)
29. [Supplier Profile View — Deep Dive](#29-supplier-profile-view--deep-dive)
30. [Verdict View — Recommendation First](#30-verdict-view--recommendation-first)
31. [Stage Animations — Visual Storytelling](#31-stage-animations--visual-storytelling)
32. [Auth System](#32-auth-system)
33. [API Client Layer](#33-api-client-layer)
34. [Feature Flags](#34-feature-flags)
35. [Telemetry & Tracing](#35-telemetry--tracing)
36. [End-to-End User Journey — Complete Walkthrough](#36-end-to-end-user-journey--complete-walkthrough)
37. [Data Flow Diagrams](#37-data-flow-diagrams)
38. [Key Design Decisions & Trade-offs](#38-key-design-decisions--trade-offs)

---

## 1. Design Philosophy

Procurement AI's frontend is built on a single insight: procurement is boring, but watching an AI work for you is mesmerizing. The interface is designed to make the user feel like they've just delegated a complex task to a brilliant colleague who narrates their work as they go.

### Core Principles

**Agent-first, not dashboard-first.** Traditional procurement tools show empty tables and wait for the user to fill them. Procurement AI shows a conversational agent that asks smart questions and then goes to work. The first thing a user sees is a greeting, not a form.

**Narrative over data.** Instead of dumping raw search results into a spreadsheet, the UI tells a story: "I searched 6 databases and found 34 potential suppliers. After checking their websites and reviews, 18 looked credible. I compared them on price, quality, and reliability. Here are my top 3 picks and why." Every data point exists within a narrative frame.

**Progressive disclosure.** The user starts with the verdict (top 3 picks + why) and drills down only if curious. The full comparison table, individual verification reports, and raw search results are all accessible but never forced on the user. This respects the user's time while maintaining transparency.

**Human-in-the-loop at key moments.** The AI runs autonomously but pauses at decision points (checkpoints) to ask the user: "I found 34 suppliers. Before I verify all of them, do you want me to focus on any particular region?" These checkpoints have auto-continue timers so the pipeline doesn't stall, but the user can pause and steer at any time.

**Phase-based mental model.** The 5-agent backend pipeline maps to 6 user-facing phases (brief → search → compare → outreach → samples → order) displayed as tabs. This gives users a persistent sense of where they are in the process and what's coming next, without exposing the complexity of the underlying agent orchestration.

---

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Framework | Next.js | 15.1 | App Router, SSR, API rewrites |
| UI Library | React | 19 | Component model, hooks, Suspense |
| Styling | Tailwind CSS | 3.4 | Utility-first CSS, custom design tokens |
| Animation | Motion (Framer Motion) | 12.34 | Declarative animations, layout transitions |
| Scroll Animation | GSAP + ScrollTrigger | 3.14 | Landing page scroll-driven animations |
| Interactive Graphics | Rive | 4.27 | Stage animations (globe, particles) |
| Icons | Lucide React | 0.469 | Consistent icon set |
| Language | TypeScript | 5.7 | Full type safety, strict mode |
| Build | PostCSS + Autoprefixer | — | CSS processing pipeline |

### Build Configuration

The Next.js config (`next.config.ts`) sets `output: 'standalone'` for containerized deployment and rewrites all `/api/*` requests to the FastAPI backend:

```
Next.js :3000  →  /api/:path*  →  proxy  →  FastAPI :8000/api/:path*
```

This means the frontend never calls the backend directly — all API traffic goes through Next.js rewrites, which simplifies CORS and deployment behind a single domain.

---

## 3. Directory Structure

```
frontend/src/
├── app/                          # Next.js App Router pages
│   ├── layout.tsx                # Root layout (fonts, providers)
│   ├── page.tsx                  # Landing page (/)
│   ├── globals.css               # Global styles + animations
│   ├── procurement-landing.css        # Landing-specific styles
│   ├── dashboard/
│   │   ├── page.tsx              # Dashboard (/dashboard)
│   │   └── dashboard.css
│   └── product/
│       └── page.tsx              # Workspace (/product)
│
├── components/
│   ├── ChatPanel.tsx             # Legacy chat panel
│   ├── ClarifyingQuestions.tsx    # Clarifying Q&A UI
│   ├── ComparisonView.tsx        # Legacy comparison table
│   ├── GoogleSignIn.tsx          # OAuth sign-in button
│   ├── LogViewer.tsx             # Raw event log viewer
│   ├── OnboardingForm.tsx        # User onboarding form
│   ├── OutreachPanel.tsx         # Outreach email UI
│   ├── PipelineProgress.tsx      # Legacy progress bar
│   ├── RecommendationView.tsx    # Legacy recommendation display
│   ├── RequirementsCard.tsx      # Parsed requirements card
│   ├── RouteTrace.tsx            # Debug route tracer
│   ├── SearchForm.tsx            # Legacy search form
│   ├── StarRating.tsx            # Star rating display
│   ├── SupplierResults.tsx       # Legacy supplier list
│   │
│   ├── animation/                # Stage-specific animations
│   │   ├── AnimatedCounter.tsx
│   │   ├── StageAnimationRouter.tsx
│   │   ├── globe/                # Discovery globe animation
│   │   │   ├── GlobeSVG.tsx
│   │   │   ├── regionCoordinates.ts
│   │   │   ├── useGlobeTimeline.ts
│   │   │   └── worldMapDots.ts
│   │   ├── shared/               # Shared animation components
│   │   │   ├── EventTickerOverlay.tsx
│   │   │   ├── ProgressRing.tsx
│   │   │   └── useStageProgress.ts
│   │   └── stages/               # Per-stage animation components
│   │       ├── ComparingAnimation.tsx
│   │       ├── DiscoveryGlobe.tsx
│   │       ├── ParsingAnimation.tsx
│   │       ├── RecommendingAnimation.tsx
│   │       └── VerificationAnimation.tsx
│   │
│   └── workspace/                # V2 workspace components
│       ├── AgentGreeting.tsx      # Welcome screen
│       ├── CenterStage.tsx        # Phase router
│       ├── CheckpointBanner.tsx   # Human-in-the-loop prompts
│       ├── ErrorRecoveryCard.tsx  # Contextual error recovery
│       ├── InputBar.tsx           # Chat-like input
│       ├── LeftRail.tsx           # Side navigation
│       ├── LiveProgressFeed.tsx   # Stage progress narrative
│       ├── PhaseTabBar.tsx        # Tab navigation
│       ├── ProactiveAlerts.tsx    # Alert notifications
│       ├── StageTransitionToast.tsx
│       ├── SupplierCard.tsx       # Supplier list item
│       ├── WorkspaceShell.tsx     # Main layout container
│       ├── compare/
│       │   ├── FunnelSummary.tsx  # "34 found → 3 recommended"
│       │   └── VerdictView.tsx    # Recommendation-first view
│       ├── phases/
│       │   ├── BriefPhase.tsx
│       │   ├── SearchPhase.tsx
│       │   ├── ComparePhase.tsx
│       │   ├── OutreachPhase.tsx
│       │   ├── SamplesPhase.tsx
│       │   └── OrderPhase.tsx
│       └── supplier-profile/
│           ├── SupplierProfileView.tsx
│           ├── ProfileHero.tsx
│           ├── ProfilePortfolio.tsx
│           ├── ProfileAssessment.tsx
│           ├── ProfileCapabilities.tsx
│           ├── ProfileCommunicationLog.tsx
│           ├── ProfileCompanyDetails.tsx
│           ├── ProfileQuote.tsx
│           └── ProfileVerification.tsx
│
├── contexts/
│   └── WorkspaceContext.tsx       # Central state management (~900 lines)
│
├── hooks/
│   ├── useChat.ts                # Chat messaging with SSE streaming
│   ├── useOutreach.ts            # Outreach actions
│   └── usePipelinePolling.ts     # Legacy polling hook
│
├── types/
│   ├── pipeline.ts               # Pipeline status, phases, decisions
│   └── supplierProfile.ts        # Supplier profile interfaces
│
└── lib/
    ├── auth.ts                   # Auth tokens, session, fetch helpers
    ├── featureFlags.ts           # Feature flag definitions
    ├── telemetry.ts              # Event tracking, tracing
    ├── api/
    │   ├── procurementClient.ts       # Typed API client (intake, leads, events)
    │   └── dashboardClient.ts    # Dashboard data client
    ├── contracts/
    │   ├── procurement.ts             # API request/response types
    │   └── dashboard.ts          # Dashboard API types
    └── motion/
        ├── index.ts              # Re-exports (m, AnimatePresence, primitives)
        ├── config.ts             # Timing, easing, spring constants
        ├── variants.ts           # Reusable animation variants
        ├── primitives.tsx        # Ready-made motion components
        ├── LazyMotionProvider.tsx # Performance-optimized motion provider
        ├── useReducedMotion.ts   # Accessibility: prefers-reduced-motion
        └── useScrollTimeline.ts  # Scroll-driven animation hook
```

---

## 4. Application Architecture

The frontend follows a layered architecture where each layer has a clear responsibility:

```
┌─────────────────────────────────────────────────────┐
│                   Pages (App Router)                  │
│  layout.tsx → page.tsx / dashboard / product          │
├─────────────────────────────────────────────────────┤
│                  Context Providers                     │
│  WorkspaceProvider (state machine + polling + API)    │
├─────────────────────────────────────────────────────┤
│                  Shell Components                      │
│  WorkspaceShell → PhaseTabBar + CenterStage          │
├─────────────────────────────────────────────────────┤
│                  Phase Components                      │
│  BriefPhase / SearchPhase / ComparePhase / ...       │
├─────────────────────────────────────────────────────┤
│                  Shared Components                     │
│  LiveProgressFeed / CheckpointBanner / InputBar      │
├─────────────────────────────────────────────────────┤
│                  Hooks & Libraries                     │
│  useChat / auth / procurementClient / motion / telemetry  │
└─────────────────────────────────────────────────────┘
```

**Pages** are thin wrappers — they set up providers and render shells. **Context Providers** own the state and API communication. **Shell Components** handle layout and navigation. **Phase Components** render the content for each stage of the procurement journey. **Shared Components** appear across phases (progress feed, checkpoints, input bar). **Hooks & Libraries** provide reusable logic and infrastructure.

The key architectural choice is that **WorkspaceContext is the single source of truth**. Every component reads from it. There is no prop-drilling of pipeline status, project IDs, or phase information. This makes the component tree clean but means the context file is large (~900 lines) — a deliberate trade-off for simplicity.

---

## 5. Routing & Page Structure

Procurement AI has three pages, each at a different URL:

| Route | Page | Purpose |
|-------|------|---------|
| `/` | `app/page.tsx` | Landing page — marketing, demo, waitlist |
| `/dashboard` | `app/dashboard/page.tsx` | Project list, onboarding, account |
| `/product` | `app/product/page.tsx` | Main workspace — where work happens |

### URL-Driven State

The workspace page (`/product`) uses URL search parameters to drive state, enabling browser back/forward navigation and shareable links:

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `projectId` | Active project | `?projectId=abc123` |
| `phase` | Active tab | `?phase=compare` |
| `supplierIndex` | Supplier profile overlay | `?supplierIndex=3` |
| `supplierName` | Supplier profile by name | `?supplierName=FooBar` |

When a user navigates to `/product?projectId=abc123`, the WorkspaceContext reads the URL, fetches that project's status, and starts polling. When the pipeline advances from "discovering" to "verifying", the context updates the `?phase=` parameter to keep the URL in sync. This means every state the user can be in has a unique URL — critical for browser history and sharing.

### Root Layout

The root `layout.tsx` loads two Google Fonts and wraps everything in the motion provider:

- **DM Serif Text** (CSS variable `--font-heading`) — elegant serif used for headings, scores, and the hero
- **Manrope** (CSS variable `--font-body`) — clean geometric sans-serif for all body text

The `LazyMotionProvider` wraps the entire app in Framer Motion's `LazyMotion` with the `domAnimation` feature set, which loads animation code on-demand rather than upfront. This reduces the initial bundle by ~15KB.

---

## 6. Visual Design System

### Color Palette

Procurement AI uses a warm, premium palette that signals trustworthiness without corporate coldness:

| Token | Hex | Usage |
|-------|-----|-------|
| `cream` | `#FAFAF7` | Page background — warm off-white |
| `surface` | `#FFFFFF` | Card backgrounds |
| `surface-2` | `#F3F2EF` | Secondary surfaces, hover states |
| `surface-3` | `#EAE8E4` | Borders, dividers |
| `ink` | `#111111` | Primary text |
| `ink-2` | `#333333` | Secondary text |
| `ink-3` | `#777777` | Tertiary text, labels |
| `ink-4` | `#AAAAAA` | Muted text, timestamps |
| `teal` | `#00C9A7` | Primary action color, scores, CTA buttons |
| `warm` | `#C9A96E` | Caveats, warnings, secondary accent |

The teal-on-cream palette was chosen to feel different from typical B2B SaaS (which skews blue/grey). The warm tones create a sense of reliability and expertise — like a procurement consultant's office, not a spreadsheet.

### Typography Scale

The type scale uses precise pixel values rather than `rem` for fine control:

| Size | Usage |
|------|-------|
| `text-[9px]` | Uppercase tracking labels ("CAVEATS") |
| `text-[10px]` | Section headers, uppercase labels |
| `text-[11px]` | Secondary info, descriptions, metadata |
| `text-[12px]` | Body text in cards, buttons, explanations |
| `text-[13px]` | Primary text, names, titles |
| `text-[14px]` | Executive summary, important prose |
| `text-2xl` | Section headings ("My Recommendation") |

### Card System

All cards use a shared `.card` utility class defined in `globals.css`:

```css
.card {
  background: #FFFFFF;
  border: 1px solid #EAE8E4;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
```

Cards with left accent borders indicate semantic meaning:
- `border-l-teal` — AI recommendation or executive summary
- `border-l-warm` — caveats or warnings
- `border-l-red-400` — errors or failures

### Global Animations

Three CSS keyframe animations are used across the app:

- `breathe` — slow pulsing scale (4s cycle) for ambient elements
- `pulse` — opacity fade (2s cycle) for status indicators
- `fin` — fade-in-up (0.5s) for entrance effects

These CSS animations are used for simple, always-running effects. Complex coordinated animations use the Framer Motion system instead.

---

## 7. Animation System

Procurement AI uses a layered animation system with a shared configuration that ensures visual consistency:

### Timing Constants (`lib/motion/config.ts`)

```
Easing:
  EASE_OUT_EXPO  = [0.16, 1, 0.3, 1]  — the signature "snap then glide" curve

Springs:
  SPRING_SNAPPY  = stiffness: 300, damping: 30   — tabs, toggles
  SPRING_GENTLE  = stiffness: 180, damping: 24   — panels, overlays
  SPRING_BOUNCY  = stiffness: 400, damping: 20   — playful micro-interactions

Durations:
  instant:   0.15s   — state changes (hover, press)
  fast:      0.25s   — exit animations, dismissals
  normal:    0.40s   — standard entrances
  slow:      0.65s   — hero animations, first impressions
  cinematic: 0.90s   — landing page scroll reveals

Stagger intervals:
  fast:   0.04s   — list items in rapid sequence
  normal: 0.08s   — card grids, supplier lists
  slow:   0.12s   — landing page sections
```

The `EASE_OUT_EXPO` curve is the foundation of Procurement AI's motion personality. It starts fast (the element snaps into place) then decelerates gradually (the element glides to rest). This creates a sense of precision and responsiveness — the interface feels like it's anticipating the user's next move.

### Reusable Variants (`lib/motion/variants.ts`)

All animations are defined as Framer Motion `Variants` objects that can be applied to any `m.div`:

| Variant | Motion | Use Case |
|---------|--------|----------|
| `fadeUp` | opacity 0→1, y 28→0 | Hero text, section entrances |
| `fadeIn` | opacity 0→1 | Subtle reveals, overlays |
| `scaleIn` | opacity 0→1, scale 0.92→1 | Cards, modals |
| `slideInLeft` | opacity 0→1, x -24→0 | Side panel items |
| `slideInRight` | opacity 0→1, x 24→0 | Notification slides |
| `cardEntrance` | opacity 0→1, y 16→0, scale 0.97→1 | Supplier cards, ranked picks |
| `staggerContainer` | stagger children 0.08s | Parent wrapper for lists |
| `expandCollapse` | height 0→auto, opacity 0→1 | Collapsible sections, logs |
| `phaseTransition` | opacity+y enter/exit | Phase switching in CenterStage |

### Motion Primitives (`lib/motion/primitives.tsx`)

Pre-built components for common patterns:

- `FadeUp` / `FadeIn` / `ScaleReveal` — wrapper divs with entrance animations
- `SlideInLeft` / `SlideInRight` — directional slides
- `StaggerList` / `StaggerItem` — parent-child stagger pair
- `PresenceGroup` — AnimatePresence wrapper

### Accessibility

The `useReducedMotion` hook reads the user's `prefers-reduced-motion` system preference. When enabled, all durations are reduced to zero and transforms are disabled, ensuring the interface remains usable for users with vestibular disorders.

---

## 8. State Management — WorkspaceContext

The `WorkspaceContext` (~900 lines) is the brain of the workspace. It uses React's `useReducer` pattern for predictable state updates.

### State Shape

```typescript
interface WorkspaceState {
  projectId: string | null         // Active project
  projectList: WorkspaceProjectSummary[]  // User's projects
  projectListLoading: boolean
  status: PipelineStatus | null    // Full pipeline status from backend
  loading: boolean                 // Submission in progress
  polling: boolean                 // Polling active
  activePhase: Phase               // Currently displayed tab
  highestReachedPhase: Phase       // Furthest phase reached
  userOverridePhase: boolean       // User manually switched tabs
  backendOk: boolean | null        // Backend health check
  errorMessage: string | null      // Error to display
}
```

### Action Types

```typescript
type WorkspaceAction =
  | 'RESET_ACTIVE_PROJECT'     // Clear project, back to greeting
  | 'SELECT_PROJECT'           // Load a specific project
  | 'SET_PROJECT_LIST_LOADING' // Toggle project list loading
  | 'SET_PROJECT_LIST'         // Update project list
  | 'SET_BACKEND_OK'           // Backend health result
  | 'SET_ERROR'                // Set/clear error message
  | 'SET_LOADING'              // Toggle loading state
  | 'SET_POLLING'              // Toggle polling state
  | 'SET_STATUS'               // New pipeline status arrived
  | 'SET_ACTIVE_PHASE'         // Switch active tab (user or auto)
```

### The Critical Reducer — SET_STATUS

The most important action is `SET_STATUS`, which fires every 1.2 seconds during polling. The reducer does several things atomically:

1. **Updates `status`** with the new `PipelineStatus` from the backend.
2. **Computes `activePhase`** by calling `stageToPhase(status.current_stage)`. If the user has manually overridden the phase (clicked a different tab), the override is respected.
3. **Advances `highestReachedPhase`** if the new phase is further along than the previous highest. This controls which tabs are clickable.
4. **Clears `errorMessage`** when a previously failed status moves to a non-error state.

This means a single status poll can trigger a tab switch, unlock new tabs, and clear an error — all in one render cycle. The reducer pattern ensures these are atomic.

### Key Context Methods

**`handleSearch(description: string)`** — The entry point. Creates a new project via `POST /api/v1/projects` with the user's natural language description, then starts polling. This is called from `AgentGreeting` or the `InputBar`.

**`cancelCurrentProject()`** — Sends `POST /api/v1/projects/{id}/cancel` and stops polling.

**`restartCurrentProject(opts?)`** — Sends `POST /api/v1/projects/{id}/restart` with optional `fromStage` (restart from a specific pipeline stage) and `additionalContext` (extra instructions for the agent).

**`setDecisionPreference(lane)`** — Sends `POST /api/v1/projects/{id}/decision-preference` with the user's preferred recommendation lane (best_overall, best_low_risk, best_speed_to_order).

**`handleClarifyingAnswered()`** — Resumes polling after the user answers clarifying questions. The checkpoint submission itself is handled by `CheckpointBanner`.

**`refreshStatus()`** — Force-fetches the latest status outside the normal poll cycle.

### URL Synchronization

The context watches `searchParams` for changes and synchronizes:

- On mount: reads `?projectId=` and `?phase=` from URL, loads project
- On status change: updates `?phase=` to match the auto-computed active phase
- On user tab click: updates `?phase=` to the selected tab
- On new project: sets `?projectId=` in URL
- On supplier profile: sets `?supplierIndex=` or `?supplierName=`

This bidirectional sync means the URL is always a truthful representation of the UI state.

---

## 9. Type System — pipeline.ts

The `pipeline.ts` file defines all the TypeScript interfaces that mirror the backend's Pydantic models. This is the contract between frontend and backend.

### PipelineStatus — The Central Data Object

Every 1.2 seconds, the frontend receives a `PipelineStatus` from `GET /api/v1/projects/{id}/status`. This single object contains everything the UI needs:

```typescript
interface PipelineStatus {
  project_id: string
  status: string                        // 'running' | 'complete' | 'failed' | 'canceled' | 'clarifying' | 'steering'
  current_stage: string                 // 'parsing' | 'discovering' | 'verifying' | 'comparing' | 'recommending' | 'outreaching'
  error: string | null
  parsed_requirements: ParsedRequirements | null
  discovery_results: any                // Raw discovery data
  verification_results: any             // Verification reports
  comparison_result: any                // Comparison matrix
  recommendation: RecommendationResult | null
  progress_events?: ProgressEvent[]     // Activity log
  clarifying_questions?: ClarifyingQuestion[] | null
  decision_preference?: DecisionLane | null
  buyer_context?: Record<string, unknown> | null
  active_checkpoint?: CheckpointEvent | null
  proactive_alerts?: ProactiveAlert[]
}
```

Each field progressively fills in as the pipeline advances: `parsed_requirements` appears after parsing, `discovery_results` after searching, and so on. The phase components check for the presence of these fields to decide what to render.

### ParsedRequirements

The structured output of the parsing agent:

```typescript
interface ParsedRequirements {
  product_type?: string           // "heavyweight hoodies"
  material?: string | null        // "cotton fleece"
  dimensions?: string | null
  quantity?: number | null        // 500
  customization?: string | null   // "custom embroidery"
  delivery_location?: string | null
  deadline?: string | null
  certifications_needed?: string[]
  budget_range?: string | null
  missing_fields?: string[]       // Fields the agent couldn't infer
  search_queries?: string[]       // Generated search queries
  risk_tolerance?: string | null
  priority_tradeoff?: string | null
  clarifying_questions?: ClarifyingQuestion[]
}
```

### SupplierRecommendation

Each recommended supplier:

```typescript
interface SupplierRecommendation {
  rank: number                           // 1, 2, 3
  supplier_name: string                  // "Suzhou Textiles Co."
  supplier_index: number                 // Index into suppliers array
  overall_score: number                  // 0-100
  confidence: string                     // "high" | "medium" | "low"
  reasoning: string                      // Full reasoning paragraph
  best_for: string                       // "Best for quality at scale"
  lane?: DecisionLane | null             // Which decision lane
  why_trust?: string[]                   // Trust evidence bullets
  uncertainty_notes?: string[]           // What's unknown
  verify_before_po?: string[]            // Pre-order checks
  needs_manual_verification?: boolean
}
```

### CheckpointEvent

When the pipeline pauses for human input:

```typescript
interface CheckpointEvent {
  checkpoint_type: CheckpointType       // 'confirm_requirements' | 'review_suppliers' | ...
  summary: string                       // Human-readable description
  next_stage_preview: string            // What happens after approval
  context_questions: ContextQuestion[]  // Questions to answer
  adjustable_parameters: Record<string, unknown>
  auto_continue_seconds: number         // Countdown before auto-proceed
  requires_explicit_approval: boolean   // Must user actively approve?
  timestamp: number
}
```

---

## 10. Phase System — How Stages Become Tabs

The backend pipeline has **stages** (parsing, discovering, verifying, comparing, recommending, outreaching). The frontend groups these into **phases** — the tabs the user sees:

```
Backend Stages          →    Frontend Phases
──────────────────────────────────────────────
parsing                 →    brief
clarifying              →    brief
steering                →    brief
discovering             →    search
verifying               →    search
comparing               →    compare
recommending            →    compare
outreaching             →    outreach
complete                →    outreach
```

This mapping lives in `stageToPhase()` in `pipeline.ts`. The insight is that users don't care about the difference between "discovering" and "verifying" — both are part of the "search" phase from their perspective. Similarly, "comparing" and "recommending" are both "compare".

### Phase Accessibility

Not all tabs are clickable at all times. `isPhaseAccessible()` controls this:

- **brief** — always accessible
- **search** — accessible once the pipeline has reached the search stage
- **compare** — accessible once the pipeline has reached the compare stage
- **outreach** — accessible once recommendations exist
- **samples** / **order** — always accessible (placeholder phases)

### Phase Completion

`isPhaseComplete()` determines whether a tab gets a completion checkmark:

- **brief** is complete when `parsed_requirements` exists and the stage has moved past parsing/clarifying
- **search** is complete when both `discovery_results` and `verification_results` exist and the stage is past verifying
- **compare** is complete when `recommendation` exists and status is complete

---

## 11. Polling Engine — Real-Time Status Updates

The workspace uses a 1200ms polling interval to keep the UI synchronized with the backend pipeline. This is the heartbeat of the application.

### Poll Lifecycle

```
User submits description
  → handleSearch() creates project
  → dispatch SET_POLLING = true
  → setInterval fires every 1200ms
  → GET /api/v1/projects/{id}/status
  → dispatch SET_STATUS with new PipelineStatus
  → Reducer computes new activePhase, highestReachedPhase
  → Components re-render with new data
  → Repeat until terminal status or clarifying pause
```

### When Polling Stops

The `shouldContinuePolling()` function determines when to stop:

```typescript
function shouldContinuePolling(status: PipelineStatus): boolean {
  if (TERMINAL_STATUSES.has(status.status)) return false  // complete, failed, canceled
  if (status.status === 'clarifying') return false         // Waiting for user answers
  return true                                              // Keep polling (including 'steering')
}
```

Note that `steering` status (checkpoints) does NOT stop polling. This is because checkpoints have auto-continue timers — the backend may resolve the checkpoint on its own after N seconds, so the frontend needs to keep polling to catch the transition.

### Backend Health Check

On mount, the context pings `GET /api/health` to check if the backend is reachable. If it fails, `backendOk` is set to `false`, and CenterStage shows a warning banner with instructions to start the server.

---

## 12. Chat System — useChat Hook

The `useChat` hook provides an in-workspace conversational interface for steering the pipeline. Users can ask questions or give instructions while the pipeline is running.

### SSE Streaming Protocol

The chat endpoint (`POST /api/v1/projects/{id}/chat`) returns a Server-Sent Events stream:

```
data: {"type": "token", "content": "I've "}
data: {"type": "token", "content": "updated "}
data: {"type": "token", "content": "your search..."}
data: {"type": "done", "action": {"action_type": "restart_search"}}
data: {"type": "action_result", "result": "Search restarted with new criteria"}
```

The hook accumulates tokens into `streamingText` for real-time display, then moves the complete response to `messages` when "done" arrives. If the response includes an action (like restarting the search), the hook displays the action status and calls `onResultsUpdated` so the workspace can refresh.

### Chat Message Types

```
token         — Partial response text (accumulates during streaming)
done          — Final response, optionally with an action
action_result — Backend action completed (e.g., "Search restarted")
error         — Error message from the backend
```

---

## 13. Component Tree — Full Hierarchy

```
RootLayout (layout.tsx)
  ├── <head> (DM Serif Text + Manrope fonts)
  ├── LazyMotionProvider (Framer Motion)
  ├── RouteTrace (debug tracing)
  └── <children>
      │
      ├── Landing Page (page.tsx, route: /)
      │   ├── Hero section
      │   ├── Demo conversation player
      │   ├── Four-step scroll animation
      │   ├── Before/After comparison
      │   ├── Use cases grid
      │   └── Early access form
      │
      ├── Dashboard (dashboard/page.tsx, route: /dashboard)
      │   ├── GoogleSignIn (if not authenticated)
      │   ├── OnboardingForm (if onboarding incomplete)
      │   └── DashboardPageContent
      │       ├── Project list
      │       └── Activity feed
      │
      └── Workspace (product/page.tsx, route: /product)
          └── WorkspaceProvider (context)
              └── WorkspaceShell
                  ├── PhaseTabBar
                  │   ├── Phase tabs (brief, search, compare, outreach, samples, order)
                  │   ├── Status indicator (pulsing dot)
                  │   └── User avatar + dropdown menu
                  │
                  └── <main> (scrollable area)
                      ├── CenterStage
                      │   ├── StageTransitionToast (floating)
                      │   ├── Backend offline warning (if applicable)
                      │   │
                      │   ├── [if supplier profile requested]
                      │   │   └── SupplierProfileView
                      │   │       ├── ProfileHero
                      │   │       ├── ProfileQuote
                      │   │       ├── ProfileAssessment
                      │   │       ├── ProfileVerification
                      │   │       ├── ProfileCompanyDetails
                      │   │       ├── ProfileCapabilities
                      │   │       ├── ProfilePortfolio
                      │   │       └── ProfileCommunicationLog
                      │   │
                      │   └── [normal phase view]
                      │       ├── CheckpointBanner
                      │       ├── LiveProgressFeed
                      │       └── AnimatePresence
                      │           └── [Active Phase Component]
                      │               ├── BriefPhase
                      │               │   ├── AgentGreeting (no project)
                      │               │   ├── StageAnimationRouter (parsing)
                      │               │   ├── ClarifyingQuestionsInline (clarifying)
                      │               │   └── RequirementsCard (parsed)
                      │               ├── SearchPhase
                      │               │   ├── Filters (search, sort, country)
                      │               │   └── SupplierCard list (staggered)
                      │               ├── ComparePhase
                      │               │   ├── VerdictView (default)
                      │               │   │   ├── Executive summary
                      │               │   │   ├── Ranked picks (top 3)
                      │               │   │   ├── Decision confidence
                      │               │   │   ├── FunnelSummary
                      │               │   │   └── Caveats
                      │               │   └── Full comparison table (drill-down)
                      │               ├── OutreachPhase
                      │               ├── SamplesPhase (placeholder)
                      │               └── OrderPhase (placeholder)
                      │
                      └── InputBar
                          ├── Phase-contextual quick actions
                          ├── Chat history overlay
                          └── Textarea + send button
```

---

## 14. Landing Page — First Impression

**File:** `app/page.tsx`

The landing page is a long-scroll marketing page with interactive demo elements. It uses GSAP ScrollTrigger for scroll-driven animations and IntersectionObserver for lazy demo playback.

### Sections

1. **Hero** — "Tell us what you need made" headline with navigation links
2. **See It In Action** — 5 interactive demo scenarios showing realistic agent conversations. Each demo shows a user query and simulates the agent's response with typing animations.
3. **Four Steps** — Scroll-animated illustration of the Brief → Search → Compare → Outreach flow. Each step fades in as the user scrolls past it.
4. **Before & After** — Side-by-side comparison of manual procurement vs. Procurement AI-automated procurement
5. **Use Cases** — Icon grid showing different product categories (apparel, food packaging, electronics, etc.)
6. **Early Access** — Email signup form that submits to `procurementClient.submitLead()`

### Demo Scenarios

The landing page includes 5 pre-written demo conversations:

- Custom enamel pins for a streetwear brand
- Organic cotton tote bags for an eco-marketplace
- Biodegradable food packaging
- Hand-poured soy candles
- Custom screen-printed t-shirts

Each demo simulates the agent's search process with realistic supplier results, comparison scores, and recommendation reasoning.

---

## 15. Dashboard Page — Project Memory

**File:** `app/dashboard/page.tsx`

The dashboard shows the user's project history and account state.

### States

1. **Not authenticated** — Shows `GoogleSignIn` component
2. **Authenticated, onboarding incomplete** — Shows `OnboardingForm` (company name, industry, typical procurement volume)
3. **Authenticated, onboarded** — Shows project list with status indicators and the option to start a new project

---

## 16. Workspace Shell — The Main Arena

**File:** `components/workspace/WorkspaceShell.tsx`

The shell is a simple layout container:

```
┌──────────────────────────────────────┐
│         PhaseTabBar (top)            │
├──────────────────────────────────────┤
│                                      │
│                                      │
│         CenterStage (main)           │
│         (scrollable)                 │
│                                      │
│                                      │
├──────────────────────────────────────┤
│         InputBar (bottom)            │
└──────────────────────────────────────┘
```

The main area has `overflow-y-auto` for scrolling. The tab bar and input bar are fixed-position relative to the shell.

---

## 17. Phase Tab Bar — Navigation & Identity

**File:** `components/workspace/PhaseTabBar.tsx`

The tab bar serves three purposes: navigation, progress indication, and identity.

### Tab Layout

Six tabs in order: Brief, Search, Compare, Outreach, Samples, Order.

Each tab shows:
- The phase name
- A completion checkmark if the phase is done
- Disabled styling if the phase isn't accessible yet
- The active tab gets an animated underline (spring animation)

### Status Indicator

Next to the project name, a small dot indicates the pipeline status:
- **Teal pulsing dot** — pipeline is running
- **Green solid dot** — pipeline is complete
- **Red solid dot** — pipeline failed

### User Menu

The right side shows the user's avatar (or initials) with a dropdown menu containing:
- Dashboard link
- Sign out button

---

## 18. Center Stage — Phase Router

**File:** `components/workspace/CenterStage.tsx`

CenterStage is the content router that determines what to show based on the current state:

```typescript
const PHASE_COMPONENTS: Record<string, React.ComponentType> = {
  brief: BriefPhase,
  search: SearchPhase,
  outreach: OutreachPhase,
  compare: ComparePhase,
  samples: SamplesPhase,
  order: OrderPhase,
}
```

### Rendering Logic

1. **Always render** `StageTransitionToast` (floating, position-fixed)
2. **If backend is offline**, show a warning banner with startup instructions
3. **If supplier profile requested** (URL has `?supplierIndex=` or `?supplierName=`), render `SupplierProfileView` as a full overlay
4. **Otherwise**, render the normal phase view:
   - `CheckpointBanner` (shows if there's an active checkpoint)
   - `LiveProgressFeed` (shows if pipeline is running)
   - `AnimatePresence` wrapping the active phase component with `phaseTransition` variant

The `AnimatePresence mode="wait"` ensures the exiting phase fades out before the entering phase fades in. The `key={activePhase}` triggers the animation on phase switches.

---

## 19. Brief Phase — Play-by-Play

**File:** `components/workspace/phases/BriefPhase.tsx`

The Brief phase has four distinct states, rendered sequentially:

### State 1: No Project (Empty State)

When the user first arrives or starts a new project, they see the `AgentGreeting` component:

**AgentGreeting** (`components/workspace/AgentGreeting.tsx`) creates a conversational first impression:

- A greeting message in an agent-styled bubble: "Hi! I'm Procurement AI, your sourcing assistant."
- A large textarea where the user describes what they need
- Four suggestion chips for quick-start ideas (enamel pins, tote bags, food packaging, candles)
- A "What happens next" section showing the 4-step process (Parse → Search → Verify → Recommend)
- For returning users: personalized greeting with their name and last category

The greeting uses staggered entrance animations — the message appears first, then the textarea slides up, then the suggestion chips fade in one by one.

### State 2: Parsing (Loading)

Once the user submits, the `StageAnimationRouter` takes over and shows a parsing animation — a visual representation of the AI reading and understanding the brief. A progress ring indicates movement.

### State 3: Clarifying Questions

If the parsing agent determines it needs more information (e.g., the user said "hoodies" but didn't specify quantity), the status changes to `clarifying` and an inline Q&A component appears. Each question includes:
- The question text
- Why the agent is asking (contextual justification)
- Suggestion chips for common answers
- An "impact if skipped" note
- A text input for custom answers

### State 4: Requirements Parsed

Once parsing is complete, the phase shows a `RequirementsCard` — a structured summary of the parsed requirements (product type, material, quantity, certifications, etc.) with:
- A "Restart with changes" button to re-run parsing with additional context
- Visual indicators for which fields were inferred vs. explicitly stated

---

## 20. Search Phase — Play-by-Play

**File:** `components/workspace/phases/SearchPhase.tsx`

The Search phase displays supplier results as they're discovered and verified.

### During Discovery/Verification

While the backend is in `discovering` or `verifying` stage:
- The `LiveProgressFeed` at the top shows the 5-stage progress bar with "Searching across multiple databases" narrative
- Supplier cards appear progressively as they're discovered
- Each `SupplierCard` shows: name, country, categories, Google rating, relevance score

### After Search Complete

Once verification is done:
- Full list of verified suppliers with rich cards
- **Search filter** — text search across supplier names
- **Sort controls** — relevance (default), rating, verification score, name
- **Country filter** — dropdown populated from discovered supplier countries
- **Intermediary toggle** — show/hide intermediaries vs. direct manufacturers
- **Load more** — pagination for large result sets
- Staggered card entrance animation when the list first appears

### Supplier Card

Each `SupplierCard` shows:
- Supplier name (clickable → opens SupplierProfileView)
- Country and city
- Product categories
- Google rating + review count (using `StarRating` component)
- Certifications (if any)
- Relevance and verification score bars
- Description snippet

---

## 21. Compare Phase — Play-by-Play

**File:** `components/workspace/phases/ComparePhase.tsx`

The Compare phase uses a "verdict first" approach — the user sees the recommendation before the detailed comparison.

### Default View: VerdictView

**File:** `components/workspace/compare/VerdictView.tsx`

The VerdictView is the primary display and shows:

1. **Executive Summary** — A prose paragraph from the recommendation agent explaining its overall assessment: "After analyzing 18 verified suppliers, I recommend Suzhou Textiles as your best option. They scored highest on quality and reliability with competitive pricing..."

2. **Ranked Picks** — A compact list of the top 3 recommendations, each showing:
   - Rank badge (teal for #1, grey for others)
   - Supplier thumbnail or initials
   - Supplier name (clickable → profile)
   - "Best for" tag (e.g., "Best for quality at scale")
   - Overall score out of 100

3. **Decision Confidence** — Visible by default (no toggle needed):
   - "Why trust this pick" — evidence bullets
   - "Key uncertainties" — what's unknown
   - "Verify before placing order" — pre-order checks

4. **Actions**:
   - Primary CTA: "Approve & send outreach" — triggers the outreach pipeline
   - Secondary: "See full comparison →" — switches to detailed view

5. **Funnel Summary** (`compare/FunnelSummary.tsx`) — A one-liner showing the agent's work: "34 found → 22 unique → 18 verified → 8 compared → 3 recommended". This is the "magic communicator" — it shows the user how much work the AI did on their behalf.

6. **Caveats** — Amber-bordered card listing any limitations or assumptions in the recommendation

### Full Comparison View

Clicking "See full comparison" switches to the full comparison table with:
- All scored suppliers in a sortable table
- Score breakdowns across dimensions
- Decision lane labels (best overall, best low-risk, best speed)
- A "← Back to recommendation" button at the top

---

## 22. Outreach Phase — Play-by-Play

**File:** `components/workspace/phases/OutreachPhase.tsx`

The Outreach phase handles the post-recommendation workflow:

- Draft RFQ (Request for Quote) emails for approved suppliers
- Preview and edit email content before sending
- Track sent/pending/replied status for each supplier
- Handle follow-up scheduling for non-responsive suppliers

---

## 23. Samples & Order Phases — Placeholders

**Files:** `phases/SamplesPhase.tsx`, `phases/OrderPhase.tsx`

These phases are currently placeholders showing "Coming soon" messaging. They're always accessible in the tab bar to communicate the full procurement lifecycle, even though the functionality isn't built yet.

The Samples phase will handle sample request tracking, quality evaluation checklists, and sample comparison. The Order phase will handle purchase order generation, terms negotiation, and shipment tracking.

---

## 24. Live Progress Feed — The Narrative Engine

**File:** `components/workspace/LiveProgressFeed.tsx`

The LiveProgressFeed is the component that makes the AI's work visible and understandable. It transforms raw pipeline events into a narrative the user can follow.

### 5-Stage Progress Bar

A horizontal bar divided into 5 segments:

```
┌─────┬─────┬─────┬─────┬─────┐
│Brief│Search│Verify│Compare│Recommend│
└─────┴─────┴─────┴─────┴─────┘
```

Each segment has three states:
- **Completed** — solid teal fill
- **Active** — animated teal fill (grows from 30% to 80% over 20 seconds, creating a sense of progress even without exact percentages)
- **Pending** — grey fill

### Stage Narratives

Instead of technical stage names, the feed shows first-person narratives:

| Stage | Narrative |
|-------|-----------|
| parsing | "Reading your request and building a sourcing plan" |
| discovering | "Searching across multiple databases for matching suppliers" |
| verifying | "Checking each supplier's credibility and contact info" |
| comparing | "Scoring suppliers on price, quality, delivery, and more" |
| recommending | "Preparing a clear shortlist with reasoning for each pick" |
| steering | "Waiting for your input on a decision point" |
| clarifying | "I have some questions to make sure I find the right suppliers" |

### Narrative Events

The feed detects `narrative_update` and `stage_summary` substeps in the progress events array. These are agent-generated human-readable summaries (e.g., "Found 12 suppliers in China matching 'embroidered hoodies'") that appear as the latest activity.

### Collapsible Activity Log

Below the narrative, a collapsible section shows the raw activity log — every `ProgressEvent` from the pipeline. This is collapsed by default with a toggle reading "Show activity log (N)". Advanced users can expand it to see every API call, search query, and verification step.

### Decision Milestones

When the `procurementFocusCircleSearchV1` feature flag is enabled, the feed also shows decision milestones — notable moments like "Checkpoint: Confirm requirements" that mark significant pipeline transitions.

---

## 25. Checkpoint Banner — Human-in-the-Loop

**File:** `components/workspace/CheckpointBanner.tsx`

The CheckpointBanner appears when the pipeline pauses at a decision point (a `CheckpointEvent` in the status).

### Anatomy

```
┌──────────────────────────────────────────────┐
│ [Teal left border]                           │
│                                              │
│  Checkpoint: Confirm requirements            │
│                                              │
│  "I've parsed your brief. Before I start     │
│   searching, does this look right?"          │
│                                              │
│  Next up: I'll search supplier databases     │
│                                              │
│  ┌─────────────────────────────────────┐     │
│  │ Question 1: Preferred regions?      │     │
│  │ [▾ Select or type answer          ] │     │
│  │                                     │     │
│  │ Question 2: Quality priority (1-10)?│     │
│  │ [______________________________   ] │     │
│  └─────────────────────────────────────┘     │
│                                              │
│  [Approve & continue]    Auto-continuing     │
│                           in 28s [Pause]     │
└──────────────────────────────────────────────┘
```

### Auto-Continue Timer

Each checkpoint has an `auto_continue_seconds` value (typically 30-60 seconds). The banner shows a countdown. If the user doesn't interact, the checkpoint automatically resolves with default values. The user can:
- **Pause** the timer to take more time
- **Resume** the timer
- **Submit early** with their answers

### Question Types

The banner renders different input controls based on the `ContextQuestion` structure:
- **Options provided** → dropdown select
- **No options** → free text input
- **Default value** → pre-filled, user can change

### Submission

When the user clicks "Approve & continue" (or the timer expires), the banner submits to `POST /api/v1/projects/{id}/checkpoint` with the answers. The WorkspaceContext then calls `handleClarifyingAnswered()` to resume polling.

---

## 26. Stage Transition Toast — Moment Markers

**File:** `components/workspace/StageTransitionToast.tsx`

A floating pill at the top center of the viewport that announces pipeline stage transitions.

### Behavior

1. Watches `status.current_stage` for changes
2. Skips the first stage (initial load — no toast)
3. On change: shows a teal pill with the transition message for 3 seconds, then auto-dismisses

### Messages

```
parsing     → "Understanding your brief..."
discovering → "Brief understood. Starting supplier search..."
verifying   → "Found suppliers. Now checking their credibility..."
comparing   → "Verification complete. Building your comparison..."
recommending→ "Comparison ready. Preparing my recommendation..."
complete    → "All done. Here are my picks."
outreaching → "Sending outreach on your behalf..."
```

### Animation

The toast uses `AnimatePresence` with a vertical slide + fade:
- Enter: opacity 0→1, y -20→0 (slides down from top)
- Exit: opacity 1→0, y 0→-20 (slides back up)
- Duration: 0.3s with `EASE_OUT_EXPO`

---

## 27. Error Recovery Card — Contextual Recovery

**File:** `components/workspace/ErrorRecoveryCard.tsx`

Instead of generic "Something went wrong" messages, this component analyzes the error string and pipeline stage to provide contextual recovery guidance.

### Error Detection

The component pattern-matches on the error string:

| Error Pattern | Title | Guidance |
|---------------|-------|----------|
| `rate_limit` | "Search temporarily throttled" | "Usually resolves in a minute" |
| `no_suppliers_found` | "No suppliers matched your criteria" | "Try broadening requirements" + Edit brief button |
| `timeout` | "Search took too long" | "Database took longer than expected" |
| `api` / `llm` / `anthropic` | "AI processing error" | "AI model encountered an issue" |
| Stage = discovering | "Search encountered an issue" | "Something went wrong finding suppliers" + Edit brief |
| Stage = verifying | "Verification hit a snag" | "Trouble verifying some suppliers" |
| Fallback | "Something went wrong" | Shows the raw error message |

### Actions

Each error card offers:
- **Retry button** — with a contextual label ("Retry now", "Broaden search and retry", "Try again")
- **Edit brief button** — shown when the error suggests the input needs changing (no suppliers found, discovery failures)
- **Loading state** — retry button shows "Retrying…" and disables during the retry

---

## 28. Input Bar — Conversational Steering

**File:** `components/workspace/InputBar.tsx`

The InputBar sits at the bottom of the workspace and provides a chat-like interface for steering the pipeline.

### Phase-Contextual Quick Actions

The input bar shows different suggestion chips depending on the active phase:

| Phase | Quick Actions |
|-------|---------------|
| brief | "Help me describe my product better", "What info helps you search?" |
| search | "Focus on direct manufacturers", "Add more suppliers from Europe", "Why were some filtered out?" |
| compare | "Why this ranking?", "Prioritize speed over cost", "Show budget breakdown" |
| outreach | "Draft a follow-up for non-responders", "Change tone to more casual" |
| samples | "What should I look for in samples?", "Evaluate quality vs. spec" |
| order | "Negotiate better terms", "What should my PO include?" |

### Chat History

The input bar includes a slide-up panel that shows the full chat history:
- User messages (right-aligned)
- Assistant responses (left-aligned)
- Streaming text indicator (typing dots) during active streaming
- Action status messages ("Running: restart_search...")

### Input Behavior

- **Enter** sends the message
- **Shift+Enter** adds a newline
- Disabled state when no project is active
- File attachment button (currently disabled, shows "Coming soon" tooltip)

---

## 29. Supplier Profile View — Deep Dive

**File:** `components/workspace/supplier-profile/SupplierProfileView.tsx`

When a user clicks a supplier name anywhere in the UI, the CenterStage renders `SupplierProfileView` as a full overlay (replacing the normal phase view).

### Loading

The component fetches from `GET /api/v1/projects/{projectId}/supplier/{index}/profile` or by name. A skeleton loader displays while waiting.

### Profile Sections

Each section is a separate component for maintainability:

1. **ProfileHero** — Supplier name, rating, key stats (MOQ, lead time, price range), location badge, logo/image

2. **ProfileQuote** — Detailed pricing breakdown (if available): unit price, MOQ tiers, sample cost, shipping estimates, payment terms

3. **ProfileAssessment** — The AI's assessment of this supplier:
   - Rank and overall score
   - Confidence level (high/medium/low)
   - Strengths and weaknesses (bullet lists)
   - "Best for" tag
   - Decision lane assignment

4. **ProfileVerification** — What the verification agent found:
   - Website analysis results
   - Google reviews summary
   - Business registration check
   - Contact enrichment results
   - Risk level indicator

5. **ProfileCompanyDetails** — Contact info, company address, year established, categories, certifications

6. **ProfileCapabilities** — Production capabilities, capacity, machinery, quality standards

7. **ProfilePortfolio** — Product images (if found during discovery)

8. **ProfileCommunicationLog** — History of outreach emails sent and received

### Navigation

A back button at the top returns to the previous phase view. The URL parameter (`?supplierIndex=` or `?supplierName=`) is cleared on navigation.

---

## 30. Verdict View — Recommendation First

**File:** `components/workspace/compare/VerdictView.tsx`

The VerdictView is the crown jewel of the UI — it's where all the agent work comes together into a single, clear recommendation.

### Design Intent

Traditional procurement tools show a comparison table and leave the user to figure out which supplier is best. Procurement AI inverts this: it shows the recommendation first ("Here are my top 3 picks and why") and only shows the full data if the user wants it.

### Information Hierarchy

1. **Executive Summary** (prose paragraph with teal left border)
2. **Top 3 Picks** (compact list with rank badges and scores)
3. **Trust Evidence** (why trust, uncertainties, verify-before-PO)
4. **Actions** (approve outreach, or drill into full comparison)
5. **Funnel Summary** (quantified agent work: "34 found → 3 recommended")
6. **Caveats** (amber card with limitations)

### FunnelSummary Component

**File:** `components/workspace/compare/FunnelSummary.tsx`

A single-line visual showing the research funnel:

```
34 found  →  22 unique  →  18 verified  →  8 compared  →  3 recommended
```

Each number comes from the respective pipeline stage results. Steps with null or zero counts are omitted. This is the single most effective element for communicating the agent's value — "I looked at 34 options so you don't have to."

---

## 31. Stage Animations — Visual Storytelling

**Directory:** `components/animation/`

Each pipeline stage has a custom full-screen animation that plays while the stage is active. These replace empty loading states with engaging visuals.

### StageAnimationRouter

Routes to the correct animation based on `current_stage`:

| Stage | Animation | Description |
|-------|-----------|-------------|
| parsing | `ParsingAnimation` | Text analysis visualization |
| discovering | `DiscoveryGlobe` | Animated globe with search points |
| verifying | `VerificationAnimation` | Checkmark verification flow |
| comparing | `ComparingAnimation` | Side-by-side score comparison |
| recommending | `RecommendingAnimation` | Final ranking reveal |

### Discovery Globe

The most elaborate animation. An SVG globe (`GlobeSVG.tsx`) with world map dots (`worldMapDots.ts`) and animated search points that light up as the agent searches different regions. Uses:
- `regionCoordinates.ts` — maps region names to SVG coordinates
- `useGlobeTimeline.ts` — GSAP timeline for search point animations

### Shared Components

- `ProgressRing` — SVG circular progress indicator
- `EventTickerOverlay` — Real-time event text scrolling across the animation
- `useStageProgress` — Hook that estimates progress percentage from events

---

## 32. Auth System

**File:** `lib/auth.ts`

The auth system uses token-based authentication stored in `localStorage`:

### Storage

```
localStorage:
  procurement_access_token → Bearer token string
  procurement_auth_user    → JSON-serialized AuthUser object
```

### AuthUser

```typescript
interface AuthUser {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
  plan?: string | null
  onboarding_completed?: boolean
  company_name?: string | null
  job_title?: string | null
  phone?: string | null
  company_website?: string | null
  business_address?: string | null
  company_description?: string | null
}
```

### Auth Utilities

- `getStoredAccessToken()` — retrieves the token
- `buildAuthHeaders()` — returns `{ Authorization: 'Bearer <token>' }` headers
- `authFetch(url, init)` — wrapper around `fetch()` that automatically injects auth headers. Every API call in the app goes through this function.
- `fetchCurrentUser()` — calls `GET /api/v1/auth/me` to verify the token and get the latest user profile

The `GoogleSignIn` component handles the OAuth flow and stores the resulting token and user data.

---

## 33. API Client Layer

### procurementClient (`lib/api/procurementClient.ts`)

A typed API client for non-polling operations:

```typescript
procurementClient.startIntake(body)    → POST /api/v1/intake/start
procurementClient.submitLead(body)     → POST /api/v1/leads
procurementClient.trackEvent(body)     → POST /api/v1/events
```

### dashboardClient (`lib/api/dashboardClient.ts`)

Handles dashboard-specific API calls (project list, activity feed, user stats).

### API Contracts

The `lib/contracts/` directory defines TypeScript interfaces for all API request/response shapes. These mirror the backend's Pydantic models and ensure type safety across the boundary.

---

## 34. Feature Flags

**File:** `lib/featureFlags.ts`

Three feature flags control progressive rollout:

| Flag | Default | Purpose |
|------|---------|---------|
| `procurementLandingBypass` | false | Skip landing page, go directly to workspace |
| `procurementClientTracing` | true | Enable telemetry event tracking |
| `procurementFocusCircleSearchV1` | false | Enable V1 focused search UX (decision milestones, enhanced progress) |

Flags are read from `NEXT_PUBLIC_*` environment variables at build time. The `parseBool()` helper handles various truthy values ("1", "true", "yes", "on").

---

## 35. Telemetry & Tracing

**File:** `lib/telemetry.ts`

The telemetry system tracks user interactions for debugging and analytics:

### Session Tracing

`getTraceSessionId()` generates a unique session ID (stored in `sessionStorage`) that persists across page navigations within a single browser session.

### Event Tracking

`trackTraceEvent(name, payload, context)` sends events with:
- Event name (e.g., "project_created", "phase_switched", "supplier_clicked")
- Payload (contextual data, truncated to prevent large payloads)
- ISO timestamp
- Session ID for correlation

### Console Tracing

`traceConsole()` provides timestamped console logging for development debugging. The `RouteTrace` component logs route changes when `procurementClientTracing` is enabled.

---

## 36. End-to-End User Journey — Complete Walkthrough

Here's what happens, step by step, when a user goes from landing to recommendation:

### 1. Landing (page.tsx)

The user arrives at `/`. They see the hero, scroll through the demo, and click "Get Started" → navigates to `/dashboard`.

### 2. Sign In (dashboard/page.tsx)

If not authenticated, `GoogleSignIn` handles OAuth. On success, the token and user data are stored in localStorage, and the dashboard renders.

### 3. Onboarding (dashboard/page.tsx)

If `onboarding_completed` is false, the `OnboardingForm` collects company details. On submit, the user data is updated and the full dashboard appears.

### 4. Start New Project (dashboard → /product)

User clicks "New Project" → navigates to `/product` with no `?projectId=`. WorkspaceContext has `projectId: null`.

### 5. AgentGreeting (BriefPhase → AgentGreeting)

With no project, BriefPhase renders `AgentGreeting`. The user sees "Hi! I'm Procurement AI..." and types their description. They click send.

### 6. Project Creation (WorkspaceContext → handleSearch)

`handleSearch()` fires:
1. `dispatch SET_LOADING = true`
2. `POST /api/v1/projects` with `{ description: "500 heavyweight hoodies..." }`
3. Backend returns `{ project_id: "proj_abc123" }`
4. `dispatch SELECT_PROJECT projectId = "proj_abc123"`
5. URL updates to `?projectId=proj_abc123&phase=brief`
6. Polling starts (1200ms interval)

### 7. Parsing Stage (BriefPhase → StageAnimationRouter)

First poll returns `{ status: "running", current_stage: "parsing" }`. BriefPhase shows the parsing animation. `StageTransitionToast` is suppressed (first stage).

### 8. Clarifying Questions (optional)

If the parsing agent needs more info, poll returns `{ status: "clarifying", clarifying_questions: [...] }`. Polling pauses. BriefPhase shows inline Q&A. User answers and submits → `POST /api/v1/projects/{id}/checkpoint` → polling resumes.

### 9. Discovery Stage

Poll returns `{ current_stage: "discovering" }`. `StageTransitionToast` shows "Brief understood. Starting supplier search...". `stageToPhase("discovering")` returns "search". Reducer advances `activePhase` to "search" and unlocks the search tab. `LiveProgressFeed` shows the 5-stage bar with "Search" segment filling. The `DiscoveryGlobe` animation plays. SearchPhase begins populating as suppliers are found.

### 10. Verification Stage

Poll returns `{ current_stage: "verifying" }`. Toast: "Found suppliers. Now checking their credibility..." Progress bar advances to the "Verify" segment. SearchPhase continues to update as verification scores come in.

### 11. Checkpoint (optional)

If the pipeline pauses for a checkpoint, poll returns `{ active_checkpoint: { checkpoint_type: "review_suppliers", ... } }`. `CheckpointBanner` appears above the phase content. Auto-continue timer starts. User can review, answer questions, or let the timer expire.

### 12. Comparison Stage

Poll returns `{ current_stage: "comparing" }`. Toast: "Verification complete. Building your comparison..." Phase auto-switches to "compare". `ComparePhase` shows the `ComparingAnimation` while results are computed.

### 13. Recommendation Stage

Poll returns `{ current_stage: "recommending" }`. The recommendation agent is preparing the final picks.

### 14. Complete

Poll returns `{ status: "complete", recommendation: { ... } }`. Toast: "All done. Here are my picks." Polling stops. `ComparePhase` renders `VerdictView` with:
- Executive summary
- Top 3 ranked suppliers
- Trust evidence and uncertainties
- "Approve & send outreach" CTA
- Funnel summary: "34 found → 22 unique → 18 verified → 8 compared → 3 recommended"
- Caveats

### 15. User Reviews & Acts

The user reads the recommendation. They can:
- **Click a supplier name** → SupplierProfileView loads with deep details
- **Click "See full comparison"** → Full comparison table appears
- **Click "Approve & send outreach"** → Outreach pipeline begins, phase switches to outreach
- **Use the InputBar** to ask questions: "Why did you rank Suzhou first?"

---

## 37. Data Flow Diagrams

### Polling Data Flow

```
┌───────────┐ 1200ms  ┌──────────────────────┐
│  setInterval ├──────→│ GET /projects/{id}/   │
│  (polling)  │        │ status               │
└───────────┘        └──────────┬───────────┘
                                │ PipelineStatus
                                ▼
                     ┌────────────────────────┐
                     │  WorkspaceContext       │
                     │  dispatch SET_STATUS    │
                     │                        │
                     │  Compute:              │
                     │  - activePhase         │
                     │  - highestReachedPhase │
                     │  - errorMessage        │
                     └──────────┬─────────────┘
                                │ React re-render
                    ┌───────────┼───────────────┐
                    ▼           ▼               ▼
              PhaseTabBar  CenterStage   LiveProgressFeed
              (tab state)  (phase view)  (progress bar)
```

### Chat Data Flow

```
┌──────────┐  text   ┌──────────┐  POST   ┌──────────────┐
│ InputBar  ├───────→│ useChat   ├───────→│ /chat (SSE)   │
└──────────┘        └────┬─────┘        └──────┬─────────┘
                         │                      │ SSE stream
                         │ streamingText        │
                         ▼                      │ tokens
                    ┌──────────┐               │
                    │ Chat     │◄──────────────┘
                    │ History  │
                    │ Panel    │  action_result
                    └──────────┘  ──────────→ refreshStatus()
```

### Checkpoint Flow

```
┌──────────────┐  active_checkpoint  ┌──────────────────┐
│ Poll status   ├──────────────────→│ CheckpointBanner  │
└──────────────┘                    │                    │
                                    │ Shows questions    │
                                    │ Starts timer       │
                                    └────────┬───────────┘
                                             │ submit
                                             ▼
                                    ┌────────────────────┐
                                    │ POST /checkpoint    │
                                    │ with answers        │
                                    └────────┬───────────┘
                                             │
                                             ▼
                                    ┌────────────────────┐
                                    │ Resume polling      │
                                    │ Pipeline continues  │
                                    └────────────────────┘
```

---

## 38. Key Design Decisions & Trade-offs

### Single Context vs. Multiple Stores

**Decision:** One large WorkspaceContext (~900 lines) instead of separate contexts for project, status, phase, etc.

**Why:** Simplicity. Every component that needs workspace state imports `useWorkspace()`. There's no need to compose providers or think about which context has which data. The trade-off is that the context file is large and all consumers re-render on any state change — but since there are typically fewer than 30 components mounted at once, this hasn't caused performance issues.

### Polling vs. WebSocket/SSE

**Decision:** HTTP polling at 1200ms intervals instead of WebSocket or SSE for status updates.

**Why:** Simplicity and resilience. Polling works through any proxy or CDN. It recovers automatically from network interruptions (the next poll just works). WebSocket would require connection management, reconnection logic, and server-side state tracking. The 1.2s interval provides near-real-time updates without overwhelming the backend. The trade-off is slightly higher latency and bandwidth usage, but for a pipeline that runs for 1-5 minutes, this is negligible.

### URL-Driven State

**Decision:** Project ID and active phase live in URL search parameters.

**Why:** Browser back/forward navigation works naturally. Users can bookmark or share a link to a specific project in a specific phase. The URL is always a truthful snapshot of the UI state. The trade-off is slightly more complex state synchronization (bidirectional sync between URL and context).

### Phase Tabs vs. Single Scroll

**Decision:** Horizontal tab navigation with discrete phase views instead of one long scrollable page.

**Why:** The procurement pipeline has clear stages with different information density. Tabs give users a mental model of progress ("I'm in the Compare phase now") and let them navigate freely between phases. A single long scroll would make it hard to find specific information and would render all phases simultaneously, increasing memory usage.

### Verdict-First vs. Table-First

**Decision:** ComparePhase defaults to VerdictView (recommendation) instead of a comparison table.

**Why:** 90% of users want to know "what should I pick?" not "show me every data point." The verdict view answers that question immediately with executive summary, top 3 picks, and trust evidence. The 10% who want the full data can click through to the comparison table. This mirrors how a procurement consultant would present findings — lead with the recommendation, have the backup data available.

### Auto-Continue Checkpoints

**Decision:** Checkpoints have countdown timers that auto-continue with defaults.

**Why:** The pipeline should never stall indefinitely waiting for human input. If the user steps away, the pipeline continues with sensible defaults (the agent's own judgment). The user can always revisit and adjust later. The pause button gives users who want to carefully review the option to do so.

### CSS Animations vs. Framer Motion

**Decision:** Simple repeating effects (pulsing dots, breathing) use CSS `@keyframes`. Complex coordinated animations use Framer Motion variants.

**Why:** CSS animations are cheaper (no JavaScript tick) and don't need React state. Framer Motion is needed when animations coordinate with React state changes (enter/exit transitions, stagger sequences, gesture-driven animations). The motion library provides both — CSS for the simple stuff, Framer for the complex stuff.

---

*This document is the comprehensive technical reference for Procurement AI's frontend. It covers every component, every flow, and every design decision. If you're building on this codebase, start here.*
