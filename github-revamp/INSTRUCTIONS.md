# GitHub Profile Revamp — How to Apply Everything

## Prerequisites

1. **Git authenticated with GitHub** (SSH key or HTTPS personal access token)
   ```bash
   # Test: this should NOT ask for a password
   git ls-remote https://github.com/thisisyoussef/thisisyoussef.git
   ```

2. **GitHub CLI (`gh`) installed and authenticated** (for repo descriptions)
   ```bash
   # Install
   brew install gh          # macOS
   # or: https://cli.github.com

   # Authenticate
   gh auth login
   ```

## Step 1: Push READMEs (git)

This clones each repo, replaces the README, commits, and pushes. Covers **all 35+ repos**.

```bash
cd github-revamp
chmod +x update_repos.sh update_descriptions.sh
bash update_repos.sh
```

**What it updates:**
- Profile README (thisisyoussef/thisisyoussef)
- 8 showcase repos (detailed READMEs with Mermaid architecture diagrams)
- 2 Instad ecosystem repos (with cross-links)
- 5 mid-tier project repos
- 7 Flutter bootcamp repos
- 13 smaller projects and coursework repos

**Note:** If procurement-ai isn't on GitHub yet, create the repo first:
```bash
gh repo create thisisyoussef/procurement-ai --public --description "AI procurement agent for small businesses"
# Then push your code + the README from readmes/procurement-ai_README.md
```

## Step 2: Update Descriptions & Topics (gh CLI)

Updates the one-liner descriptions and topic tags for ALL your repos (even the ones without new READMEs).

```bash
bash update_descriptions.sh
```

## Step 3: Pin Your Best Repos (manual — 30 seconds)

Go to https://github.com/thisisyoussef → click **"Customize your pins"**

Pin these 6 in this order:

1. **event-scribe-ai-assist** — Production community platform with AI. The "in production" signal alone puts this above 90% of portfolio projects. Shows: React, TypeScript, Supabase, OpenAI, full-stack ownership.

2. **procurement-ai** — Multi-agent AI system. Shows you understand agent orchestration, not just "I called an API." Shows: Python, FastAPI, LangGraph, Claude, systems design.

3. **PLCProgrammingLanguage** — Full compiler from scratch. Very few engineers build compilers. Top companies (Google, Meta, etc.) love seeing this. Shows: deep CS fundamentals, Java, compiler theory.

4. **exquizite** — Full-stack platform with document intelligence. Has async job queues, document parsing, real-time WebSockets — this is NOT a todo app. Shows: Node.js, Express, MongoDB, Redis, Bull, Socket.io.

5. **stevo_flutter** — Mobile app with AI + real-time features. Shows your Flutter depth goes beyond tutorials. Shows: Flutter, Dart, OpenAI, Socket.io, Redis.

6. **instad** — 3-app ecosystem with shared core library. Shows you think in systems and can architect multi-app platforms. Shows: Flutter, Firebase, Google Maps, architectural maturity.

**Why this order:** Production → AI/Agents → CS Depth → Backend → Mobile → Architecture. A recruiter scanning left-to-right sees range and depth in 10 seconds.

## Step 4: Update Profile Settings (manual — 1 minute)

Go to https://github.com/settings/profile

| Field | Update to |
|-------|----------|
| **Name** | Youssef Ahmed |
| **Bio** | Software engineer — full-stack, mobile (Flutter), AI agents. I build things people use. |
| **Company** | *(your current company, or leave blank)* |
| **Location** | *(your current city)* |
| **Website** | linkedin.com/in/youssefia |
| **Hireable** | ✅ Check this box |

## What Changed & Why

| Before | After | Why it matters |
|--------|-------|---------------|
| Bio says "New Grad" | Professional one-liner | You graduated 3 years ago |
| Profile README lists 2 random projects | Curated table of 6 best projects with "why it's interesting" column | Recruiters scan in 10 seconds |
| Most repos have zero description | Every repo has a description + topic tags | Discoverability, professionalism |
| PLC Compiler: zero documentation | Full README with compilation pipeline Mermaid diagram | One of your most impressive projects was invisible |
| Exquizite: zero documentation | README showing job queues, doc processing, real-time | Looked like "another todo app" before |
| MemoryManager: zero documentation | README showing sbrk(), best-fit/worst-fit, Valgrind testing | Systems programming cred was hidden |
| No architecture diagrams | Mermaid diagrams in 8 project READMEs | Renders natively on GitHub, shows systems thinking |
| No pinned repos strategy | 6 pins: production → AI → compilers → backend → mobile → architecture | Story of range and depth |
| 35+ repos with no README | Every repo has a README | No dead ends when recruiters click around |

## Complete File Inventory

```
github-revamp/
├── PROFILE_README.md                           # Profile README
├── readmes/
│   ├── event-scribe-ai-assist_README.md        # ★ Showcase (Mermaid diagram)
│   ├── procurement-ai_README.md                # ★ Showcase (Mermaid diagram)
│   ├── PLCProgrammingLanguage_README.md        # ★ Showcase (Mermaid diagram)
│   ├── exquizite_README.md                     # ★ Showcase (Mermaid diagram)
│   ├── stevo_flutter_README.md                 # ★ Showcase (Mermaid diagram)
│   ├── instad_README.md                        # ★ Showcase (Mermaid diagram)
│   ├── sawa_README.md                          # ★ Showcase (Mermaid diagram)
│   ├── MemoryManager_README.md                 # ★ Showcase (Mermaid diagram)
│   ├── pocketpay_README.md                     # ★ Showcase (Mermaid diagram)
│   ├── instad_user_README.md                   # Ecosystem
│   ├── instad_venue_README.md                  # Ecosystem
│   ├── kafka-tutorial_README.md                # Mid-tier
│   ├── jaeger-tracing_README.md                # Mid-tier
│   ├── aqius_README.md                         # Mid-tier
│   ├── job_search_README.md                    # Mid-tier
│   ├── localization_task_README.md             # Mid-tier
│   ├── bitcoin-flutter-final_README.md         # Bootcamp
│   ├── Clima-Flutter_README.md                 # Bootcamp
│   ├── flash-chat_README.md                    # Bootcamp
│   ├── magic-8-ball-flutter_README.md          # Bootcamp
│   ├── bmi-calculator-flutter_README.md        # Bootcamp
│   ├── dicee-flutter_README.md                 # Bootcamp
│   ├── xylophone-flutter_README.md             # Bootcamp
│   ├── NutrientHelper_README.md                # Coursework
│   ├── NutritionListProject_README.md          # Coursework
│   ├── Pakudex_README.md                       # Coursework
│   ├── SciCalculator_README.md                 # Coursework
│   ├── LinkedList_README.md                    # Coursework
│   ├── task-manager_README.md                  # Small project
│   ├── notes-app_README.md                     # Small project
│   ├── weather_website_README.md               # Small project
│   ├── InstaBugTask_README.md                  # Assessment
│   ├── todoapp_README.md                       # Small project
│   ├── tamas_README.md                         # Small project
│   ├── qintarapp_README.md                     # Small project
│   └── iOS-101-Prework_README.md               # Course
├── update_repos.sh                             # Push all READMEs
├── update_descriptions.sh                      # Update all descriptions + topics
└── INSTRUCTIONS.md                             # This file
```
