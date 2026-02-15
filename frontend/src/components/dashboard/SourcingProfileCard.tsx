'use client'

import type { AuthUser } from '@/lib/auth'
import type { DashboardProjectCard } from '@/lib/contracts/dashboard'

interface SourcingProfileCardProps {
  authUser: AuthUser
  projects: DashboardProjectCard[]
}

function deriveCategories(projects: DashboardProjectCard[]): string[] {
  const categories = new Set<string>()
  for (const project of projects) {
    const name = (project.name || '').trim()
    if (!name) continue
    const category = name.split(' ').slice(0, 2).join(' ')
    if (category) categories.add(category)
    if (categories.size >= 5) break
  }
  return Array.from(categories)
}

export default function SourcingProfileCard({ authUser, projects }: SourcingProfileCardProps) {
  const categories = deriveCategories(projects)

  return (
    <div className="dash-card-panel">
      <div className="dash-section-label">Your sourcing profile</div>
      <div className="dash-card-content">
        <p className="dash-card-line">
          Categories: {categories.length > 0 ? categories.join(' · ') : 'Building from your next projects'}
        </p>
        <p className="dash-card-line">
          Company: {authUser.company_name || 'Not set'}
        </p>
        <p className="dash-card-line">
          Ship from: {authUser.business_address || 'Add business address in profile'}
        </p>
        <p className="dash-card-line">
          Built from {projects.length} sourcing project{projects.length === 1 ? '' : 's'}
        </p>
      </div>
    </div>
  )
}
