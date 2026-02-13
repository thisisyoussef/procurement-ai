export interface TermTranslation {
  customer: string
  industry: string
  context: string
}

export const TONE_TRANSLATION_TABLE: TermTranslation[] = [
  {
    customer: 'Find people who can make your product',
    industry: 'Supplier discovery',
    context: 'Landing hero and onboarding copy',
  },
  {
    customer: 'Check who is legit before you commit',
    industry: 'Supplier qualification',
    context: 'Trust and risk messaging',
  },
  {
    customer: 'Compare quotes side by side',
    industry: 'Bid analysis',
    context: 'Decision stage UI labels',
  },
  {
    customer: 'Manage every supplier relationship in one place',
    industry: 'Vendor management',
    context: 'Workspace framing copy',
  },
  {
    customer: 'Let the agent handle the busy work',
    industry: 'Workflow orchestration',
    context: 'Automation descriptions and tooltips',
  },
]
