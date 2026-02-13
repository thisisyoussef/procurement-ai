import { cookies } from 'next/headers'

import LegacyHome from '@/features/legacy/LegacyHome'
import TamkinLandingPage from '@/features/tamkin/landing/TamkinLandingPage'
import {
  resolveTamkinExperienceEnabled,
  TAMKIN_EXPERIENCE_COOKIE,
} from '@/lib/featureFlags'

export default async function HomePage() {
  const cookieStore = await cookies()
  const isTamkinEnabled = resolveTamkinExperienceEnabled(
    cookieStore.get(TAMKIN_EXPERIENCE_COOKIE)?.value
  )

  if (!isTamkinEnabled) {
    return <LegacyHome experienceEnabled={isTamkinEnabled} />
  }

  return <TamkinLandingPage experienceEnabled={isTamkinEnabled} />
}
