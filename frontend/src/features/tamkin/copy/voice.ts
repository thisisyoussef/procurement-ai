import { TONE_TRANSLATION_TABLE } from './translationTable'

export const TAMKIN_CORE_LINE = 'Find the right people to make your stuff. Manage them like a pro.'

export const TAMKIN_COPY_RULES = [
  'Lead with outcomes, not features.',
  'Start with the operator reality, then show the next best step.',
  'Use plain words first, then translate to industry terms only when needed.',
  'Stay specific. Avoid hype and generic claims.',
  'Keep microcopy action-first and concise.',
]

export const TAMKIN_VOICE_MARKERS = {
  do: [
    'Talk like an experienced operator helping another operator.',
    'Use clear verbs: find, compare, approve, send, track.',
    'Show progress and next action in every state.',
  ],
  avoid: [
    'Avoid “revolutionary,” “synergy,” and inflated enterprise phrasing.',
    'Avoid long, abstract explanations without user action.',
    'Avoid jargon without translation.',
  ],
}

export const TAMKIN_COPY = {
  navTagline: 'Sourcing operations for growing businesses',
  heroEyebrow: 'Built for SMB operators',
  heroTitle: 'Stop guessing who can make your product.',
  heroSubtitle:
    'Tamkin helps you find, vet, and manage suppliers in one place, while your agent handles the busy work in the background.',
  primaryCta: 'Start sourcing chat',
  secondaryCta: 'See mission flow',
  trustLine: 'Designed for teams that need answers quickly, not six months from now.',
  intakeTitle: 'Start with your sourcing mission',
  intakeSubtitle: 'Give us the essentials. Tamkin takes it from there.',
  workspaceTitle: 'Mission workspace',
  workspaceSubtitle: 'Your agent is running the process. You step in only for key approvals.',
  timelineTitle: 'Agent timeline',
  approvalsTitle: 'Approvals',
  savedMissionsTitle: 'Saved missions',
}

export function translateIndustryTerm(industryTerm: string): string {
  const normalized = industryTerm.trim().toLowerCase()
  const match = TONE_TRANSLATION_TABLE.find((entry) => entry.industry.toLowerCase() === normalized)
  return match ? match.customer : industryTerm
}
