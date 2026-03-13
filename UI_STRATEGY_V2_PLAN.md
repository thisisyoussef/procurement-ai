# Procurement AI UI Strategy V2 — Communicating the Magic

> Companion plan to `AGENT_STRATEGY_V2_PLAN.md`. Focuses on the frontend experience:
> making the AI agent visible, the process trustworthy, and the results actionable.

---

## Table of Contents

1. [Diagnosis: Why the Current UI Feels Confusing](#1-diagnosis)
2. [Design Principles for V2](#2-design-principles)
3. [Phase 1 — Conversational First Impression](#3-phase-1)
4. [Phase 2 — Live Agent Narrative](#4-phase-2)
5. [Phase 3 — Checkpoint & Steering UI](#5-phase-3)
6. [Phase 4 — Results That Tell a Story](#6-phase-4)
7. [Phase 5 — Dashboard & Project Memory](#7-phase-5)
8. [Phase 6 — Polish & Delight](#8-phase-6)
9. [Component Inventory & File Map](#9-component-map)
10. [Implementation Timeline](#10-timeline)

---

<a id="1-diagnosis"></a>
## 1. Diagnosis: Why the Current UI Feels Confusing

### 1.1 The Core Problem

The UI currently treats the AI agent like a backend process and the user like a passive viewer. The "magic" — an AI that thinks, researches, cross-references, and makes judgments — is hidden behind a progress dot and a few status labels like "Searching suppliers" or "Verifying supplier fit."

A user watching the current UI sees:
- A loading animation
- Then suddenly, a wall of supplier cards

They don't see the *thinking*. They don't see the agent reject 47 intermediaries, discover a factory that the user didn't know existed, or notice that two suppliers are actually the same entity. That's where the magic lives, and none of it reaches the user.

### 1.2 Specific UX Issues

| Area | Problem | Impact |
|------|---------|--------|
| **First interaction** | Textarea + "Start sourcing" button feels like a search bar, not a conversation with an expert | Sets wrong mental model — users expect Google, not a sourcing agent |
| **Progress feed** | `LiveProgressFeed` shows one-line labels ("Searching suppliers") with timestamps | No sense of what the agent is *actually doing* or *why* |
| **Phase transitions** | Auto-advance silently moves tabs; user doesn't know why they're now on "Search" | Feels like things happen *to* you, not *for* you |
| **Search results** | Flat list of `SupplierCard` components with filter/sort controls | Looks like a directory listing, not a curated recommendation |
| **Compare phase** | 880 lines of dense JSX with outreach shortlist, editorial cards, AI recommendation, decision confidence panels, cost rows, caveats — all on one scroll | Information overload; users don't know where to focus |
| **Recommendation cards** | Decision Confidence panel is collapsed by default behind "Expand details" | The most valuable information (why trust, uncertainties, verify-before-PO) is hidden |
| **Outreach phase** | Status badges (Queued, Awaiting reply, Responded) in small text | No clear call-to-action; user doesn't know what to do next |
| **Clarifying questions** | Appears as a form card inside BriefPhase; `why_this_question` hidden behind feature flag | Feels like a chore, not a collaboration |
| **InputBar** | Quick actions are generic ("Why this ranking?") and chat panel slides up from bottom | Disconnected from the phase the user is actually viewing |
| **Empty states** | Samples & Order show placeholder text | User doesn't know what's coming or when |
| **Error states** | Generic red card with error string | No recovery guidance, no "here's what happened and what to do" |
| **No buyer context** | The UI never asks *about the user* — shipping location, budget constraints, quality priorities | Agent works blind; results feel generic |
| **No agent personality** | Stage labels are functional ("Verifying supplier fit") not human | Doesn't feel like working with a knowledgeable sourcing partner |

### 1.3 What "Communicating the Magic" Means

The goal is not more animations or visual flair. It's **narrative transparency**:

- The user should *read* what the agent is thinking, not just see a spinner
- Every result should come with a *judgment*, not just data
- The user should feel they can *steer* the process, not just watch it
- The UI should make the user feel *smarter*, not overwhelmed

---

<a id="2-design-principles"></a>
## 2. Design Principles for V2

### P1: Conversation First, Dashboard Second
The primary interaction model is a conversation with an expert sourcing agent, not a form submission. The first screen should feel like sitting down with a consultant who asks good questions.

### P2: Show the Thinking, Not Just the Results
Every stage of the pipeline should surface the agent's reasoning in real-time. Not as raw logs, but as a readable narrative: "I found 23 factories in Guangdong, but only 4 have verified export licenses for your category."

### P3: Progressive Disclosure by Confidence
Don't dump everything at once. Surface the verdict first (this is the best option, here's why), then let users drill into supporting evidence. The current UI does the opposite — shows raw data first and hides the judgment.

### P4: Steer Without Blocking
Checkpoints should appear inline and auto-continue after a timeout. The user can steer if they want, but the agent keeps working by default. Never make the user feel like they're holding up the process.

### P5: Remember and Personalize
The UI should reflect the user's history: "Last time you sourced packaging, you prioritized speed over cost. Want to use the same priority?" The agent gets smarter, and the UI shows it.

### P6: One Clear Action Per View
Every screen should have exactly one primary action the user can take. If there are multiple, the UI must visually prioritize one. The Compare phase currently has three competing sections with no hierarchy.

---

<a id="3-phase-1"></a>
## 3. Phase 1 — Conversational First Impression

### 3.1 Problem

Current `BriefPhase` empty state:
```
┌──────────────────────────────────────┐
│    What do you need made?            │
│                                      │
│    [         textarea          ]     │
│              [Start sourcing]        │
│                                      │
│    chip  chip  chip  chip            │
└──────────────────────────────────────┘
```

This looks like a search engine. Users type "custom enamel pins" and expect instant results. When they get a 2-minute pipeline, they're confused.

### 3.2 Solution: Agent Greeting + Guided Intake

Replace the textarea with a conversational interface that sets the right expectation:

```
┌──────────────────────────────────────────────────┐
│                                                  │
│   ┌─────────────────────────────────────────┐    │
│   │ 👋 I'm your sourcing agent. Tell me     │    │
│   │ what you need and I'll find the best     │    │
│   │ suppliers, verify them, and give you a   │    │
│   │ clear recommendation.                    │    │
│   │                                          │    │
│   │ This usually takes 2-3 minutes. I'll     │    │
│   │ show you what I'm finding along the way. │    │
│   └─────────────────────────────────────────┘    │
│                                                  │
│   ┌─────────────────────────────────────────┐    │
│   │ Describe what you need manufactured...  │    │
│   │                                         │    │
│   │                              [Send →]   │    │
│   └─────────────────────────────────────────┘    │
│                                                  │
│   Try: "500 custom enamel pins for my brand"     │
│        "Organic cotton totes, need samples first"│
│        "Biodegradable food packaging, small run"  │
│                                                  │
│   ┌ What happens next ──────────────────────┐    │
│   │ ① I'll parse your requirements          │    │
│   │ ② Search multiple supplier databases     │    │
│   │ ③ Verify each match for credibility      │    │
│   │ ④ Compare and rank the best options      │    │
│   └─────────────────────────────────────────┘    │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 3.3 Component Changes

**File: `frontend/src/components/workspace/phases/BriefPhase.tsx`**

Replace the empty state (lines 58-131) with a new `AgentGreeting` component:

```tsx
// NEW FILE: frontend/src/components/workspace/AgentGreeting.tsx

interface AgentGreetingProps {
  onSubmit: (text: string) => void
  loading: boolean
  errorMessage: string | null
  userName?: string        // From authUser
  hasHistory?: boolean     // Has previous projects
  lastCategory?: string   // From sourcing profile
}

export default function AgentGreeting({
  onSubmit, loading, errorMessage, userName, hasHistory, lastCategory
}: AgentGreetingProps) {
  const [input, setInput] = useState('')

  // Personalized greeting based on history
  const greeting = hasHistory
    ? `Welcome back${userName ? `, ${userName.split(' ')[0]}` : ''}. What are we sourcing today?`
    : `I'm your sourcing agent. Tell me what you need — I'll find suppliers, verify them, and recommend the best path forward.`

  const subtitle = hasHistory && lastCategory
    ? `Last time you sourced ${lastCategory}. Starting a new category, or continuing?`
    : `This usually takes 2-3 minutes. I'll show you what I'm finding along the way.`

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
      {/* Agent message bubble */}
      <div className="max-w-xl w-full mb-6">
        <div className="bg-surface-2/50 rounded-2xl rounded-tl-sm px-5 py-4">
          <p className="text-[14px] text-ink leading-relaxed">{greeting}</p>
          <p className="text-[12px] text-ink-3 mt-2">{subtitle}</p>
        </div>
      </div>

      {/* Input card */}
      <div className="w-full max-w-xl">
        <div className="card p-1.5">
          <textarea ... />
          <div className="flex justify-end px-2 pb-2">
            <button ...>Start sourcing</button>
          </div>
        </div>

        {/* Suggestion chips - phrased as full sentences */}
        <div className="flex flex-wrap gap-2 mt-4 justify-center">
          {SUGGESTIONS.map(...)}
        </div>
      </div>

      {/* What happens next - subtle process preview */}
      <div className="max-w-xl w-full mt-8">
        <ProcessPreview />
      </div>
    </div>
  )
}
```

**New sub-component: `ProcessPreview`**

A minimal 4-step visual that sets expectations. NOT a feature list — a promise:

```tsx
function ProcessPreview() {
  const steps = [
    { label: 'Parse your requirements', detail: 'I extract specs, constraints, and priorities' },
    { label: 'Search multiple databases', detail: 'Direct manufacturers, marketplaces, regional specialists' },
    { label: 'Verify each match', detail: 'Check websites, reviews, certifications, business registration' },
    { label: 'Rank and recommend', detail: 'Side-by-side comparison with clear reasoning' },
  ]

  return (
    <div className="border border-surface-3 rounded-xl px-5 py-4">
      <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-ink-4 mb-3">
        What happens next
      </p>
      <div className="space-y-2.5">
        {steps.map((step, i) => (
          <div key={i} className="flex items-start gap-3">
            <span className="w-5 h-5 rounded-full bg-surface-2 flex items-center justify-center
                           text-[10px] font-bold text-ink-4 shrink-0 mt-0.5">
              {i + 1}
            </span>
            <div>
              <p className="text-[12px] text-ink-2 font-medium">{step.label}</p>
              <p className="text-[10px] text-ink-4">{step.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
```

### 3.4 Returning User Variant

If `authUser.onboarding_completed` and the user has previous projects, show a compact variant:

```
┌──────────────────────────────────────────────┐
│  Welcome back, Youssef. What are we          │
│  sourcing today?                             │
│                                              │
│  Last time you sourced packaging.            │
│  Starting a new category, or continuing?     │
│                                              │
│  [         textarea          ]               │
│                              [Send →]        │
│                                              │
│  Recent: Packaging · Enamel Pins · Textiles  │
└──────────────────────────────────────────────┘
```

The "Recent" row shows past categories from the user's `sourcing_profile`, letting them quickly restart a familiar search with context.

---

<a id="4-phase-2"></a>
## 4. Phase 2 — Live Agent Narrative

### 4.1 Problem

The current `LiveProgressFeed` is a small card at the top of the page showing:
- A label like "Searching suppliers"
- A one-line detail like "Searching across web and supplier memory for matches"
- A timestamp

This is a *log*, not a *narrative*. The user can't tell what's happening, how far along things are, or whether the results are good.

### 4.2 Solution: Agent Narration Panel

Replace the progress feed with a persistent narration panel that shows the agent's thinking in real-time, formatted as readable prose.

```
┌── Agent Activity ──────────────────────────────────┐
│                                                    │
│  ◉ Searching for manufacturers                     │
│  ━━━━━━━━━━━━━━━━━━━━━━━░░░░░ Step 2 of 5          │
│                                                    │
│  Found 34 potential matches across 3 regions.      │
│  Filtered out 12 trading companies — focusing on   │
│  direct manufacturers with verified export         │
│  licenses.                                         │
│                                                    │
│  Currently checking: Shenzhen Pin Factory Co.      │
│  ─────────────────────────────────────────────────  │
│  Earlier:                                          │
│  · Parsed your brief — identified "enamel pins,    │
│    custom design, 500 units, no deadline pressure"  │
│  · Asked 2 clarifying questions to narrow the       │
│    search (plating type, packaging needs)           │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 4.3 Component Design

**File: `frontend/src/components/workspace/AgentNarrationPanel.tsx`** (NEW)

```tsx
interface AgentNarrationPanelProps {
  // All sourced from status polling
  currentStage: string
  progressEvents: ProgressEvent[]
  narrativeBriefing?: string    // NEW from agent_state.py
  discoveryBriefing?: string    // NEW from agent_state.py
  supplierCount?: number
  filteredCount?: number
  activeCheckpoint?: CheckpointEvent | null
}

export default function AgentNarrationPanel(props: AgentNarrationPanelProps) {
  // Derive narrative text from events + briefings
  // Show stage progress bar (1-5 scale based on pipeline position)
  // Current activity line (what the agent is doing RIGHT NOW)
  // Narrative summary (2-3 sentences about what happened so far)
  // Earlier events (collapsed, expandable)
}
```

**Key behavioral changes from current `LiveProgressFeed`:**

1. **Stage progress indicator**: A 5-segment bar showing pipeline progress (Parse → Discover → Verify → Compare → Recommend), not just a pulsing dot
2. **Narrative text**: Instead of "Searching suppliers", show "Found 34 potential matches across 3 regions. Filtered out 12 trading companies — focusing on direct manufacturers."
3. **Currently checking**: Show the specific supplier name being processed, so the user sees motion
4. **Earlier events**: Collapsed section with past stage summaries, so the user can review what happened

**Data source**: The `narrative_briefing` and `discovery_briefing` fields added to `PipelineState` in the agent strategy plan. These are LLM-generated summaries of what each stage found, written in second person ("I found...", "I filtered...").

### 4.4 Narrative Text Generation

Each agent stage should emit a human-readable narrative event alongside its structured data. This is a **backend change** coordinated with the agent strategy plan:

```python
# In each agent's run function, emit a narrative progress event:
await emit_progress(state, {
    "stage": "discovering",
    "substep": "narrative_update",
    "detail": f"Found {len(raw_results)} potential suppliers. "
              f"Filtered to {len(filtered)} after removing trading companies "
              f"and duplicates. Strongest cluster: {top_region}.",
    "narrative": True,  # Flag for frontend to display prominently
})
```

The frontend filters for `narrative: True` events and displays them as the main body text, while non-narrative events go to the "Earlier" section.

### 4.5 Stage-Specific Narratives

| Stage | Example Narrative |
|-------|-------------------|
| Parsing | "Got it — you need custom enamel pins, 500 units, soft enamel with butterfly clutch backs. No hard deadline, which gives us more supplier options." |
| Discovery | "Found 34 potential suppliers across China, Thailand, and Turkey. 22 are direct manufacturers. Strongest cluster is in Shenzhen with 8 verified factories." |
| Verification | "Verified 18 of 22 manufacturers. 4 had outdated websites or no verifiable business registration. Top scorer: Shenzhen Pin Factory (87/100)." |
| Comparison | "Compared the top 8 on price, quality indicators, lead time, and shipping logistics. Clear winner on value: Shenzhen Pin Factory at $0.42/unit landed." |
| Recommendation | "My top pick is Shenzhen Pin Factory — best combination of price, verified quality, and fast sampling. Second option (Thailand Pin Co) is 20% more but offers in-house design support." |

These narratives replace the current `fallbackMessage()` function in `LiveProgressFeed.tsx` (lines 35-59).

---

<a id="5-phase-3"></a>
## 5. Phase 3 — Checkpoint & Steering UI

### 5.1 Problem

The current pipeline is fully autonomous — the user submits a brief and waits. The only interaction point is the clarifying questions form, which feels like a required step rather than a collaboration.

With the checkpoint system from the agent strategy plan, we need UI to:
1. Display checkpoint questions inline without blocking the pipeline
2. Let the user adjust weights, confidence thresholds, or search parameters
3. Auto-continue after a timeout so the pipeline doesn't stall

### 5.2 Solution: Inline Checkpoint Cards

Checkpoints appear as cards within the `AgentNarrationPanel`, not as separate pages or modals. They have a countdown timer and auto-dismiss.

```
┌── Agent Activity ──────────────────────────────────┐
│                                                    │
│  ◉ Checkpoint: Review discovered suppliers         │
│                                                    │
│  I found 22 manufacturers. Before I start          │
│  verifying them, anything you want to adjust?      │
│                                                    │
│  ┌─────────────────────────────────────────────┐   │
│  │ Priority weighting                    ▼     │   │
│  │                                             │   │
│  │  Price      ━━━━━━━━━━━━━━━━━━░░  70%      │   │
│  │  Quality    ━━━━━━━━━━━━━━━░░░░░  60%      │   │
│  │  Speed      ━━━━━━━━░░░░░░░░░░░  40%      │   │
│  │  Proximity  ━━━━━━░░░░░░░░░░░░░  30%      │   │
│  │                                             │   │
│  │  [ Looks good, continue ]   Adjust →        │   │
│  │                                             │   │
│  │  Auto-continuing in 25s...                  │   │
│  └─────────────────────────────────────────────┘   │
│                                                    │
└────────────────────────────────────────────────────┘
```

### 5.3 Component Design

**File: `frontend/src/components/workspace/CheckpointCard.tsx`** (NEW)

```tsx
interface CheckpointCardProps {
  checkpoint: CheckpointEvent   // From agent_state.py
  onRespond: (response: CheckpointResponse) => void
  autoContineSeconds?: number   // Default: 30
}

export default function CheckpointCard({
  checkpoint, onRespond, autoContinueSeconds = 30
}: CheckpointCardProps) {
  const [secondsLeft, setSecondsLeft] = useState(autoContinueSeconds)
  const [expanded, setExpanded] = useState(false)
  const [userValues, setUserValues] = useState<Record<string, any>>({})

  // Countdown timer
  useEffect(() => {
    if (secondsLeft <= 0) {
      onRespond({ checkpoint_id: checkpoint.id, action: 'auto_continue' })
      return
    }
    const timer = setTimeout(() => setSecondsLeft(s => s - 1), 1000)
    return () => clearTimeout(timer)
  }, [secondsLeft])

  // Reset timer on user interaction
  const handleUserInteraction = () => setSecondsLeft(autoContinueSeconds)

  return (
    <div className="card border-l-[3px] border-l-teal p-5 my-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <p className="text-[10px] font-semibold tracking-[1.5px] uppercase text-teal">
            Checkpoint
          </p>
          <p className="text-[13px] text-ink font-medium mt-1">
            {checkpoint.title}
          </p>
        </div>
        <span className="text-[10px] text-ink-4">
          Auto-continuing in {secondsLeft}s
        </span>
      </div>

      <p className="text-[12px] text-ink-3 mb-4">
        {checkpoint.description}
      </p>

      {/* Contextual questions from checkpoint */}
      {checkpoint.questions?.map(q => (
        <CheckpointQuestion
          key={q.field}
          question={q}
          value={userValues[q.field]}
          onChange={(val) => {
            handleUserInteraction()
            setUserValues(prev => ({ ...prev, [q.field]: val }))
          }}
        />
      ))}

      {/* Weight sliders (for ADJUST_WEIGHTS type) */}
      {checkpoint.type === 'ADJUST_WEIGHTS' && (
        <WeightSliders
          weights={checkpoint.current_weights}
          onChange={(weights) => {
            handleUserInteraction()
            setUserValues(prev => ({ ...prev, weights }))
          }}
        />
      )}

      <div className="flex items-center gap-3 mt-4">
        <button
          onClick={() => onRespond({
            checkpoint_id: checkpoint.id,
            action: 'continue',
            values: userValues,
          })}
          className="px-4 py-2 bg-teal text-white rounded-lg text-[12px]
                     font-medium hover:bg-teal-600 transition-colors"
        >
          {Object.keys(userValues).length > 0 ? 'Apply & continue' : 'Looks good, continue'}
        </button>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[11px] text-ink-4 hover:text-ink-3 transition-colors"
        >
          {expanded ? 'Less options' : 'More options'}
        </button>
      </div>
    </div>
  )
}
```

### 5.4 Checkpoint Types and Their UI

| Checkpoint Type | When | UI Component |
|----------------|------|-------------|
| `CONFIRM_REQUIREMENTS` | After parsing | Show parsed brief summary + "Is this right?" with edit fields |
| `REVIEW_SUPPLIERS` | After discovery | Show supplier count by region + quality breakdown + "Focus on any region?" |
| `SET_CONFIDENCE_GATE` | Before comparison | Slider: "Minimum quality threshold" (default 60/100) |
| `ADJUST_WEIGHTS` | Before recommendation | 4 weight sliders: Price / Quality / Speed / Proximity |
| `OUTREACH_PREFERENCES` | Before outreach | Communication style (formal/casual), preferred contact method, budget to share |

### 5.5 Buyer Context Gathering

Instead of a form, gather buyer context progressively through checkpoint questions. The `BuyerContext` fields from the agent strategy plan map to natural checkpoint moments:

| BuyerContext Field | Gathered At | Question |
|-------------------|-------------|----------|
| `shipping_destination` | CONFIRM_REQUIREMENTS | "Where do you need this shipped?" |
| `budget_range` | CONFIRM_REQUIREMENTS | "What's your target budget per unit?" |
| `timeline` | CONFIRM_REQUIREMENTS | "When do you need the first order delivered?" |
| `quality_priority` | ADJUST_WEIGHTS | "How important is quality vs. price?" (slider) |
| `preferred_regions` | REVIEW_SUPPLIERS | "Any preferred manufacturing regions?" |
| `communication_language` | OUTREACH_PREFERENCES | "What language should outreach be in?" |

**This replaces the need for an upfront onboarding form.** Context is gathered *in the moment it's relevant*, not as a chore before the user even knows what they need.

### 5.6 API Integration

New endpoints needed (coordinate with backend):

```
POST /api/v1/projects/{id}/checkpoint/respond
  Body: { checkpoint_id, action, values }
  Returns: { ok: true, next_stage: "verifying" }

GET /api/v1/projects/{id}/status
  Returns (expanded): {
    ...existing fields,
    active_checkpoint: CheckpointEvent | null,
    checkpoint_responses: CheckpointResponse[],
    buyer_context: BuyerContext,
  }
```

The polling loop in `WorkspaceContext` already stops on `clarifying` status. Add `steering` as another pause state:

```tsx
// In WorkspaceContext.tsx, update shouldStopPolling:
const PAUSE_STATUSES = new Set(['clarifying', 'steering'])
const TERMINAL_STATUSES = new Set(['complete', 'failed', 'canceled'])

// Don't fully stop polling on 'steering' — just slow it to 3s
// so we can detect when the checkpoint resolves
```

---

<a id="6-phase-4"></a>
## 6. Phase 4 — Results That Tell a Story

### 6.1 Problem: The Compare Phase Is a Data Dump

The current `ComparePhase.tsx` (880 lines) renders three major sections in a single scroll:

1. **Outreach shortlist** — checkbox grid of 8 suppliers
2. **Supplier comparison** — 4 editorial cards with score bars
3. **AI Recommendation** — decision lanes, executive summary, ranked picks, decision confidence, caveats

This is *everything at once*. A user seeing this for the first time doesn't know:
- What do these scores mean?
- Why should I trust the recommendation?
- What am I supposed to *do*?

### 6.2 Solution: Split Into Verdict → Evidence → Action

Restructure Compare into three distinct views with clear hierarchy:

#### View A: The Verdict (Default View)

What the user sees first — the agent's recommendation in plain language.

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  My Recommendation                                   │
│  ──────────────────                                  │
│                                                      │
│  "Shenzhen Pin Factory is your best option. They     │
│   offer the lowest landed cost ($0.42/unit), have a  │
│   verified 5-year export history, and can ship       │
│   samples within 7 days. The main risk is their      │
│   minimum order is 300 units — just under your 500   │
│   target, so no issue there."                        │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  #1  Shenzhen Pin Factory     $0.42  ★★★★½    │  │
│  │      Best overall · 7-day samples · Low risk   │  │
│  ├────────────────────────────────────────────────┤  │
│  │  #2  Thailand Pin Co          $0.51  ★★★★     │  │
│  │      Best for design support · 12-day samples  │  │
│  ├────────────────────────────────────────────────┤  │
│  │  #3  Istanbul Pins Ltd        $0.48  ★★★½     │  │
│  │      Fastest shipping to EU · Smaller MOQ      │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  [Approve & send outreach]    See full comparison →  │
│                                                      │
│  ┌─ What I considered ──────────────────────────┐    │
│  │ 34 found → 22 manufacturers → 18 verified →  │    │
│  │ 8 compared → 3 recommended                   │    │
│  └──────────────────────────────────────────────┘    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

#### View B: Full Comparison (Drill-Down)

Accessible via "See full comparison →". Shows the editorial cards, score bars, strengths/weaknesses — all the detail currently in ComparePhase, but reached by choice, not by default.

#### View C: Outreach Approval (Action Step)

After clicking "Approve & send outreach", show a focused confirmation:

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  Ready to reach out to 3 suppliers               │
│                                                  │
│  Here's what I'll send on your behalf:           │
│                                                  │
│  "Hi [Supplier], I'm looking for a quote on      │
│   500 custom enamel pins with soft enamel and     │
│   butterfly clutch backs. Could you share your    │
│   unit pricing, MOQ, sample lead time, and        │
│   shipping cost to [user's location]?"            │
│                                                  │
│  ☑ Shenzhen Pin Factory                          │
│  ☑ Thailand Pin Co                               │
│  ☑ Istanbul Pins Ltd                             │
│                                                  │
│  [Confirm & send]         [Edit message]         │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 6.3 Component Restructure

**Current:** `ComparePhase.tsx` (1 file, 880 lines)

**Proposed:**
```
frontend/src/components/workspace/phases/
├── ComparePhase.tsx            (router — renders VerdictView by default)
├── compare/
│   ├── VerdictView.tsx         (recommendation summary + compact ranked list)
│   ├── FullComparisonView.tsx  (editorial cards, score bars, detailed analysis)
│   ├── OutreachApproval.tsx    (confirmation step with message preview)
│   ├── RecommendationCard.tsx  (extracted from ComparePhase — one ranked pick)
│   ├── SupplierScoreCard.tsx   (extracted — editorial card with scores)
│   ├── DecisionConfidence.tsx  (extracted — trust panel, now visible by default)
│   └── FunnelSummary.tsx       (NEW — "34 found → 22 manufacturers → 3 recommended")
```

### 6.4 The Funnel Summary

A new component that communicates the *work* the agent did:

```tsx
// NEW FILE: frontend/src/components/workspace/compare/FunnelSummary.tsx

interface FunnelSummaryProps {
  totalRaw: number
  deduplicated: number
  verified: number
  compared: number
  recommended: number
}

export default function FunnelSummary(props: FunnelSummaryProps) {
  const steps = [
    { label: 'Found', count: props.totalRaw },
    { label: 'Unique', count: props.deduplicated },
    { label: 'Verified', count: props.verified },
    { label: 'Compared', count: props.compared },
    { label: 'Recommended', count: props.recommended },
  ]

  return (
    <div className="flex items-center gap-1 text-[11px]">
      {steps.map((step, i) => (
        <Fragment key={step.label}>
          <span className="text-ink-3">
            <span className="font-medium text-ink-2">{step.count}</span> {step.label.toLowerCase()}
          </span>
          {i < steps.length - 1 && (
            <span className="text-ink-4 mx-1">→</span>
          )}
        </Fragment>
      ))}
    </div>
  )
}
```

This single line — "34 found → 22 unique → 18 verified → 8 compared → 3 recommended" — communicates more about the agent's value than the entire current progress feed.

### 6.5 Decision Confidence: Visible by Default

The current Decision Confidence panel is collapsed behind "Expand details". This is the most valuable part of the recommendation — it tells users *why to trust* the agent's judgment and *what's uncertain*.

**Change:** Show the first item of each section (why_trust, uncertainty_notes, verify_before_po) by default. No collapse toggle. Full list shown on click.

```tsx
// In RecommendationCard.tsx:
// Instead of:
//   expandedTrustPanels[supplier_index] ? rec.why_trust : rec.why_trust.slice(0, 1)
// Always show:
//   rec.why_trust.slice(0, 2) with "+ N more" link

<div className="mt-3 space-y-2 bg-surface-2/30 rounded-lg px-4 py-3">
  <TrustSection title="Why trust" items={rec.why_trust} />
  <TrustSection title="Key uncertainties" items={rec.uncertainty_notes} />
  <TrustSection title="Verify before placing order" items={rec.verify_before_po} />
</div>
```

### 6.6 Search Phase: From Directory to Curated List

The current `SearchPhase` shows a flat list with filter/sort — it looks like a supplier directory. For V2:

**Change 1: Add a discovery briefing at the top**

Before the supplier list, show the agent's summary of what it found:

```tsx
{status?.discovery_results?.discovery_briefing && (
  <div className="card border-l-[3px] border-l-teal px-5 py-4 mb-6">
    <p className="text-[13px] text-ink-2 leading-relaxed">
      {status.discovery_results.discovery_briefing}
    </p>
  </div>
)}
```

Example: "I searched 5 databases and found 34 potential suppliers. 22 are direct manufacturers (the rest are trading companies I filtered out). The strongest cluster is in Shenzhen (8 factories), followed by Bangkok (4) and Istanbul (3)."

**Change 2: Group suppliers by discovery team**

If multi-team discovery is enabled, show suppliers grouped by which team found them:

```
Direct Manufacturers (12)
├── Shenzhen Pin Factory · 87/100 · $0.42/unit
├── Guangzhou Metal Arts · 82/100 · $0.45/unit
└── + 10 more

Regional Specialists (6)
├── Istanbul Pins Ltd · 79/100 · $0.48/unit
└── + 5 more

Market Intelligence Finds (4)
├── Thailand Pin Co · 81/100 · $0.51/unit
└── + 3 more
```

**Change 3: Highlight cross-referenced suppliers**

Suppliers found by multiple teams get a badge: "Found by 3 teams" — this communicates reliability.

---

<a id="7-phase-5"></a>
## 7. Phase 5 — Dashboard & Project Memory

### 7.1 Dashboard Improvements

The current dashboard is functional but doesn't communicate the agent's personality. Improvements:

**A. Project cards show narrative, not just status**

Current:
```
┌─────────────────────────┐
│ Custom Enamel Pins       │
│ Status: complete         │
│ 18 suppliers · 3 picks   │
└─────────────────────────┘
```

Proposed:
```
┌─────────────────────────────────────────────┐
│ Custom Enamel Pins                          │
│                                             │
│ Best option: Shenzhen Pin Factory           │
│ $0.42/unit landed · 7-day samples           │
│                                             │
│ 34 found → 3 recommended                   │
│ Outreach: 2 responded, 1 awaiting          │
│                                ─ 3 days ago │
└─────────────────────────────────────────────┘
```

The card shows the *outcome*, not just the process state. The user can see at a glance which project got the best results.

**B. "Continue conversation" entry point**

Each project card should have a subtle "Continue →" link that takes the user back to the workspace with full context. The agent should resume with awareness: "Welcome back. When we left off, you had 2 supplier responses. Want me to follow up with the third?"

**C. Sourcing profile section**

New section on the dashboard showing the user's learned preferences:

```
┌─ Your Sourcing Profile ────────────────────────┐
│                                                │
│ Categories: Packaging, Enamel Pins, Textiles   │
│ Preferred regions: China, Turkey               │
│ Priority: Price > Quality > Speed              │
│ Typical MOQ: 200-1000 units                    │
│ Ship to: San Francisco, CA                     │
│                                                │
│ Built from 4 sourcing projects    [Edit]       │
└────────────────────────────────────────────────┘
```

### 7.2 Project Memory in New Searches

When starting a new project, if the user has a sourcing profile, show a subtle banner:

```
┌─────────────────────────────────────────────────────┐
│ ℹ Using your sourcing profile: ships to SF, prefers │
│   price over speed. [Adjust for this project]       │
└─────────────────────────────────────────────────────┘
```

This communicates that the agent *remembers* and gets smarter over time.

---

<a id="8-phase-6"></a>
## 8. Phase 6 — Polish & Delight

### 8.1 Transition Announcements

When the pipeline moves to a new stage, show a brief toast-style announcement:

```tsx
// NEW: frontend/src/components/workspace/StageTransitionToast.tsx

function StageTransitionToast({ from, to }: { from: string; to: string }) {
  const messages: Record<string, string> = {
    'parsing→discovering': 'Brief understood. Starting supplier search...',
    'discovering→verifying': 'Found suppliers. Now checking their credibility...',
    'verifying→comparing': 'Verification complete. Building your comparison...',
    'comparing→recommending': 'Comparison ready. Preparing my recommendation...',
    'recommending→complete': 'All done. Here are my picks.',
  }

  const key = `${from}→${to}`
  const message = messages[key] || `Moving to ${to}...`

  return (
    <m.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="fixed top-4 left-1/2 -translate-x-1/2 z-50
                 bg-ink text-white text-[12px] px-4 py-2.5 rounded-full shadow-lg"
    >
      {message}
    </m.div>
  )
}
```

### 8.2 Empty States That Educate

Replace "Coming soon" placeholders with informative previews:

**Samples Phase:**
```
┌──────────────────────────────────────────────┐
│                                              │
│  📦 Sample Management                        │
│                                              │
│  Once suppliers respond, you'll be able to:  │
│  · Request and track samples                 │
│  · Compare sample quality side by side       │
│  · Share feedback directly with suppliers    │
│                                              │
│  Currently: 2 suppliers have responded to    │
│  your outreach. Waiting on 1 more.           │
│                                              │
└──────────────────────────────────────────────┘
```

**Order Phase:**
```
┌──────────────────────────────────────────────┐
│                                              │
│  📋 Order Management                         │
│                                              │
│  After selecting a supplier, this is where   │
│  you'll manage:                              │
│  · Purchase order creation and tracking      │
│  · Payment milestone management              │
│  · Production updates and delivery tracking  │
│                                              │
│  You're at the outreach stage — this         │
│  unlocks after you pick a supplier.          │
│                                              │
└──────────────────────────────────────────────┘
```

### 8.3 Error States With Recovery

Replace the current generic error card:

```tsx
// Current:
<div className="card border-l-[3px] border-l-red-400 px-5 py-4">
  <p>Pipeline Error</p>
  <p>{status.error}</p>
</div>
```

With contextual error recovery:

```tsx
// NEW: frontend/src/components/workspace/ErrorRecoveryCard.tsx

function ErrorRecoveryCard({ error, stage, projectId, onRetry }: Props) {
  const recovery = getRecoveryGuidance(error, stage)

  return (
    <div className="card border-l-[3px] border-l-red-400 px-5 py-4">
      <p className="text-[13px] font-semibold text-ink-2">{recovery.title}</p>
      <p className="text-[12px] text-ink-3 mt-1">{recovery.explanation}</p>
      <div className="mt-3 flex items-center gap-3">
        <button onClick={onRetry} className="...">
          {recovery.retryLabel}
        </button>
        {recovery.alternativeAction && (
          <button onClick={recovery.alternativeAction.handler} className="...">
            {recovery.alternativeAction.label}
          </button>
        )}
      </div>
    </div>
  )
}

function getRecoveryGuidance(error: string, stage: string) {
  if (error.includes('rate_limit')) {
    return {
      title: 'Search temporarily throttled',
      explanation: 'I hit a rate limit on one of the supplier databases. This usually resolves in a minute.',
      retryLabel: 'Retry now',
    }
  }
  if (error.includes('no_suppliers_found')) {
    return {
      title: 'No suppliers matched your criteria',
      explanation: 'This usually means the product description is too specific or the category is niche.',
      retryLabel: 'Broaden search and retry',
      alternativeAction: {
        label: 'Edit brief',
        handler: () => { /* navigate to brief phase */ },
      },
    }
  }
  // ... more error patterns
}
```

### 8.4 InputBar Contextual Actions

Replace the static quick actions with phase-contextual ones:

```tsx
const PHASE_ACTIONS: Record<Phase, string[]> = {
  brief: ['Help me describe my product better', 'What info helps you find better suppliers?'],
  search: ['Focus on direct manufacturers only', 'Add more suppliers from Europe', 'Why did you filter these out?'],
  compare: ['Why this ranking?', 'Prioritize speed over price', 'Show me budget options'],
  outreach: ['Draft a follow-up for non-responders', 'Change my message tone to more formal'],
  samples: ['What should I look for in samples?'],
  order: ['Help me negotiate better terms'],
}
```

### 8.5 Skeleton Loading States

Replace the `StageAnimationRouter` (globe, checkmarks, etc.) with a hybrid approach:

1. **Keep the animations** for the first 10 seconds (they set a premium feel)
2. **After 10 seconds**, transition to a skeleton of the expected content

```tsx
function SmartLoader({ stage, elapsedMs }: { stage: string; elapsedMs: number }) {
  if (elapsedMs < 10000) {
    return <StageAnimationRouter />
  }

  // After 10s, show skeleton of what's coming
  switch (stage) {
    case 'discovering':
      return <SupplierListSkeleton count={6} />
    case 'comparing':
      return <ComparisonSkeleton />
    case 'recommending':
      return <RecommendationSkeleton />
    default:
      return <StageAnimationRouter />
  }
}
```

### 8.6 Micro-Interactions

Small details that communicate quality:

- **Score bars animate on scroll** (already implemented via `whileInView` — keep this)
- **Supplier card hover**: subtle shadow + lift (currently flat)
- **Recommendation rank number**: pulse once when first visible
- **Outreach status change**: brief green flash when a supplier responds
- **Checkpoint timer**: smooth countdown ring animation
- **Funnel numbers**: count up from 0 when first visible

---

<a id="9-component-map"></a>
## 9. Component Inventory & File Map

### 9.1 New Components to Create

| Component | File Path | Purpose |
|-----------|-----------|---------|
| `AgentGreeting` | `components/workspace/AgentGreeting.tsx` | Conversational first impression for new projects |
| `ProcessPreview` | `components/workspace/ProcessPreview.tsx` | 4-step visual promise of what happens next |
| `AgentNarrationPanel` | `components/workspace/AgentNarrationPanel.tsx` | Replaces `LiveProgressFeed` with narrative + stage progress |
| `CheckpointCard` | `components/workspace/CheckpointCard.tsx` | Inline checkpoint with countdown auto-continue |
| `CheckpointQuestion` | `components/workspace/CheckpointQuestion.tsx` | Individual question renderer for checkpoints |
| `WeightSliders` | `components/workspace/WeightSliders.tsx` | Priority weight adjustment UI |
| `VerdictView` | `components/workspace/compare/VerdictView.tsx` | Recommendation summary — default Compare view |
| `FullComparisonView` | `components/workspace/compare/FullComparisonView.tsx` | Detailed editorial cards — drill-down from Verdict |
| `OutreachApproval` | `components/workspace/compare/OutreachApproval.tsx` | Focused outreach confirmation with message preview |
| `RecommendationCard` | `components/workspace/compare/RecommendationCard.tsx` | Extracted single recommendation pick |
| `SupplierScoreCard` | `components/workspace/compare/SupplierScoreCard.tsx` | Extracted editorial comparison card |
| `DecisionConfidence` | `components/workspace/compare/DecisionConfidence.tsx` | Trust panel (visible by default now) |
| `FunnelSummary` | `components/workspace/compare/FunnelSummary.tsx` | "34 found → 3 recommended" progress line |
| `StageTransitionToast` | `components/workspace/StageTransitionToast.tsx` | Brief announcement on stage change |
| `ErrorRecoveryCard` | `components/workspace/ErrorRecoveryCard.tsx` | Contextual error display with recovery actions |
| `SourcingProfileCard` | `components/dashboard/SourcingProfileCard.tsx` | Learned preferences display on dashboard |
| `SmartLoader` | `components/workspace/SmartLoader.tsx` | Animation → skeleton transition after 10s |

### 9.2 Components to Modify

| Component | File Path | Changes |
|-----------|-----------|---------|
| `BriefPhase` | `phases/BriefPhase.tsx` | Replace empty state with `AgentGreeting`; integrate `CheckpointCard` for `CONFIRM_REQUIREMENTS` |
| `SearchPhase` | `phases/SearchPhase.tsx` | Add discovery briefing card at top; group by discovery team; cross-reference badges |
| `ComparePhase` | `phases/ComparePhase.tsx` | Split into router for VerdictView/FullComparisonView/OutreachApproval |
| `OutreachPhase` | `phases/OutreachPhase.tsx` | Add response notification highlights; clearer status hierarchy |
| `SamplesPhase` | `phases/SamplesPhase.tsx` | Replace "coming soon" with informative preview |
| `OrderPhase` | `phases/OrderPhase.tsx` | Replace "coming soon" with informative preview |
| `CenterStage` | `workspace/CenterStage.tsx` | Add `StageTransitionToast`; replace `LiveProgressFeed` with `AgentNarrationPanel` |
| `WorkspaceContext` | `contexts/WorkspaceContext.tsx` | Add `steering` pause state; add `buyer_context` to state; add checkpoint response handler |
| `PhaseTabBar` | `workspace/PhaseTabBar.tsx` | Add stage progress indicator; highlight active stage within tab |
| `InputBar` | `workspace/InputBar.tsx` | Phase-contextual quick actions |
| `Dashboard` | `app/dashboard/page.tsx` | Add narrative to project cards; add sourcing profile section |

### 9.3 Components to Remove / Deprecate

| Component | Reason |
|-----------|--------|
| `LiveProgressFeed` | Replaced by `AgentNarrationPanel` |
| `ClarifyingQuestionsInline` (in BriefPhase) | Replaced by `CheckpointCard` with `CONFIRM_REQUIREMENTS` type |

---

<a id="10-timeline"></a>
## 10. Implementation Timeline

### Week 1: Foundation

**Goal:** Ship the conversational first impression and agent narration.

| Day | Task | Files |
|-----|------|-------|
| 1-2 | Create `AgentGreeting` + `ProcessPreview` components | `AgentGreeting.tsx`, `ProcessPreview.tsx` |
| 2-3 | Replace `BriefPhase` empty state with `AgentGreeting` | `BriefPhase.tsx` |
| 3-4 | Create `AgentNarrationPanel` to replace `LiveProgressFeed` | `AgentNarrationPanel.tsx` |
| 4-5 | Wire narrative events from backend to narration panel | `WorkspaceContext.tsx`, `CenterStage.tsx` |
| 5 | Add `StageTransitionToast` | `StageTransitionToast.tsx`, `CenterStage.tsx` |

**Backend coordination:** Agents need to emit `narrative: true` progress events (see Section 4.4). Can be mocked on frontend initially.

### Week 2: Results Restructure

**Goal:** Split Compare phase into Verdict → Evidence → Action flow.

| Day | Task | Files |
|-----|------|-------|
| 1 | Extract `RecommendationCard`, `SupplierScoreCard`, `DecisionConfidence` from `ComparePhase.tsx` | `compare/` directory |
| 2 | Create `VerdictView` — recommendation-first default | `compare/VerdictView.tsx` |
| 3 | Create `FullComparisonView` — detailed drill-down | `compare/FullComparisonView.tsx` |
| 3 | Create `FunnelSummary` component | `compare/FunnelSummary.tsx` |
| 4 | Create `OutreachApproval` — focused confirmation | `compare/OutreachApproval.tsx` |
| 5 | Refactor `ComparePhase.tsx` as router between views | `ComparePhase.tsx` |

### Week 3: Checkpoint System

**Goal:** Ship inline checkpoint UI with auto-continue.

| Day | Task | Files |
|-----|------|-------|
| 1-2 | Create `CheckpointCard`, `CheckpointQuestion`, `WeightSliders` | `CheckpointCard.tsx` etc. |
| 3 | Integrate checkpoints into `AgentNarrationPanel` | `AgentNarrationPanel.tsx` |
| 4 | Add `steering` state handling to `WorkspaceContext` | `WorkspaceContext.tsx` |
| 5 | Add checkpoint response API call | `WorkspaceContext.tsx` or new hook |

**Backend coordination:** Requires checkpoint API endpoints from Phase 3 of the agent strategy plan.

### Week 4: Dashboard, Polish & Errors

**Goal:** Improve dashboard, add contextual errors, and polish transitions.

| Day | Task | Files |
|-----|------|-------|
| 1 | Update dashboard project cards with narrative summaries | `dashboard/page.tsx` |
| 2 | Create `SourcingProfileCard` for dashboard | `dashboard/SourcingProfileCard.tsx` |
| 3 | Create `ErrorRecoveryCard` with contextual recovery | `ErrorRecoveryCard.tsx` |
| 3 | Update `SamplesPhase` and `OrderPhase` empty states | `SamplesPhase.tsx`, `OrderPhase.tsx` |
| 4 | Add phase-contextual quick actions to `InputBar` | `InputBar.tsx` |
| 4 | Add `SmartLoader` (animation → skeleton transition) | `SmartLoader.tsx` |
| 5 | Search phase: discovery briefing + team grouping | `SearchPhase.tsx` |

### Week 5: Integration & QA

| Day | Task |
|-----|------|
| 1-2 | End-to-end integration testing with backend checkpoint system |
| 3 | Accessibility pass (ARIA labels, keyboard nav, contrast) |
| 4 | Performance audit (bundle size, lazy loading, skeleton states) |
| 5 | User testing with 3-5 target users; collect feedback |

---

## Summary of Impact

| Metric | Current | After V2 |
|--------|---------|----------|
| First-impression clarity | "What does this do?" | "This is an AI sourcing agent that will find and vet suppliers for me" |
| Pipeline transparency | Pulsing dot + stage label | Real-time narrative of what the agent is doing and finding |
| Time to first useful information | ~2 min (wait for full pipeline) | ~15 sec (parsing narrative appears immediately) |
| User steering ability | None (wait for results) | Checkpoints at each stage with auto-continue |
| Result comprehension | Dense 880-line scroll | Verdict first, evidence on demand |
| Agent personality | Generic status labels | Conversational narrative in first person |
| Returning user experience | Same as new user | Personalized greeting + sourcing profile |
| Error recovery | Red card with error string | Contextual explanation + recovery action |

The fundamental shift is from **"here's what the system is doing"** to **"here's what I'm finding for you and why."**
