import type {
  ChatHistoryMessage,
  MissionSummary,
  OutreachPlanResponse,
  OutreachTimelineResponse,
  PipelineStatusResponse,
  StreamEvent,
} from '@/lib/contracts/tamkin'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')
const SAVED_MISSIONS_KEY = 'tamkin.savedMissions.v1'
const APPROVALS_KEY_PREFIX = 'tamkin.approvals.v1.'

type FetchOptions = RequestInit & { path: string }

async function fetchJson<T>({ path, ...init }: FetchOptions): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || JSON.stringify(data)
    } catch {
      detail = `${detail} ${response.statusText}`
    }
    throw new Error(detail)
  }

  return response.json() as Promise<T>
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(3000) })
    return response.ok
  } catch {
    return false
  }
}

export async function createMission(input: {
  title: string
  productDescription: string
}): Promise<{ project_id: string; status: string }> {
  return fetchJson({
    path: '/api/v1/projects',
    method: 'POST',
    body: JSON.stringify({
      title: input.title,
      product_description: input.productDescription,
    }),
  })
}

export async function getMissionStatus(projectId: string): Promise<PipelineStatusResponse> {
  return fetchJson({ path: `/api/v1/projects/${projectId}/status` })
}

export async function submitClarifyingAnswers(projectId: string, answers: Record<string, string>): Promise<void> {
  await fetchJson({
    path: `/api/v1/projects/${projectId}/answer`,
    method: 'POST',
    body: JSON.stringify({ answers }),
  })
}

export async function skipClarifyingQuestions(projectId: string): Promise<void> {
  await fetchJson({
    path: `/api/v1/projects/${projectId}/skip-questions`,
    method: 'POST',
  })
}

export async function getChatHistory(projectId: string): Promise<ChatHistoryMessage[]> {
  return fetchJson({ path: `/api/v1/projects/${projectId}/chat/history` })
}

export async function getOutreachPlan(projectId: string): Promise<OutreachPlanResponse> {
  return fetchJson({ path: `/api/v1/projects/${projectId}/outreach/plan` })
}

export async function getOutreachTimeline(projectId: string): Promise<OutreachTimelineResponse> {
  return fetchJson({ path: `/api/v1/projects/${projectId}/outreach/timeline` })
}

export async function streamMissionChat(
  projectId: string,
  message: string,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/v1/projects/${projectId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })

  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const data = await response.json()
      detail = data.detail || JSON.stringify(data)
    } catch {
      detail = `${detail} ${response.statusText}`
    }
    throw new Error(detail)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('No streaming body received')
  }

  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''

    for (const chunk of chunks) {
      const lines = chunk.split('\n')
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6).trim()
        if (!payload) continue

        try {
          const event = JSON.parse(payload) as StreamEvent
          onEvent(event)
        } catch {
          // ignore malformed payloads and keep stream alive
        }
      }
    }
  }
}

function loadJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function saveJson<T>(key: string, value: T): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Ignore storage errors in private mode / quota limits.
  }
}

export function listSavedMissions(): MissionSummary[] {
  return loadJson<MissionSummary[]>(SAVED_MISSIONS_KEY, [])
}

export function upsertSavedMission(mission: MissionSummary): MissionSummary[] {
  const current = listSavedMissions()
  const filtered = current.filter((item) => item.id !== mission.id)
  const next = [mission, ...filtered].slice(0, 24)
  saveJson(SAVED_MISSIONS_KEY, next)
  return next
}

export function loadApprovalStates(projectId: string): Record<string, 'approved' | 'rejected'> {
  return loadJson<Record<string, 'approved' | 'rejected'>>(`${APPROVALS_KEY_PREFIX}${projectId}`, {})
}

export function saveApprovalStates(
  projectId: string,
  states: Record<string, 'approved' | 'rejected'>
): void {
  saveJson(`${APPROVALS_KEY_PREFIX}${projectId}`, states)
}
