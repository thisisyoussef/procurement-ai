import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

import TamkinWorkspacePage from '@/features/tamkin/workspace/TamkinWorkspacePage'
import {
  resolveTamkinExperienceEnabled,
  TAMKIN_EXPERIENCE_COOKIE,
} from '@/lib/featureFlags'

interface WorkspaceRouteProps {
  params: Promise<{ projectId: string }>
}

export default async function WorkspacePage({ params }: WorkspaceRouteProps) {
  const cookieStore = await cookies()
  const isTamkinEnabled = resolveTamkinExperienceEnabled(
    cookieStore.get(TAMKIN_EXPERIENCE_COOKIE)?.value
  )

  if (!isTamkinEnabled) {
    redirect('/')
  }

  const { projectId } = await params
  return (
    <TamkinWorkspacePage
      projectId={projectId}
      experienceEnabled={isTamkinEnabled}
    />
  )
}
