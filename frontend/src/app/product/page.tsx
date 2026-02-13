'use client'

import Link from 'next/link'
import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import GoogleSignIn from '@/components/GoogleSignIn'
import { WorkspaceProvider } from '@/contexts/WorkspaceContext'
import WorkspaceShell from '@/components/workspace/WorkspaceShell'
import { trackTraceEvent } from '@/lib/telemetry'
import {
  AuthUser,
  clearAuthSession,
  fetchCurrentUser,
  getStoredAccessToken,
  getStoredAuthUser,
} from '@/lib/auth'

function ProductPageContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredAccessToken()
      if (!token) {
        trackTraceEvent('auth_required_for_product', { path: '/product' })
        setAuthReady(true)
        return
      }

      const cachedUser = getStoredAuthUser()
      if (cachedUser) setAuthUser(cachedUser)

      try {
        const me = await fetchCurrentUser()
        setAuthUser(me)
        trackTraceEvent('auth_session_restored', { user_id: me.id }, { path: '/product' })
      } catch {
        clearAuthSession()
        setAuthUser(null)
        trackTraceEvent('auth_session_invalidated', {}, { path: '/product', level: 'warn' })
      } finally {
        setAuthReady(true)
      }
    }
    initAuth()
  }, [])

  useEffect(() => {
    if (!authReady || !authUser) return
    const projectId = searchParams.get('projectId')?.trim()
    if (!projectId) {
      trackTraceEvent('product_redirect_to_dashboard', {}, { path: '/product' })
      router.replace('/dashboard')
    }
  }, [authReady, authUser, router, searchParams])

  if (!authReady) {
    return <main className="min-h-screen bg-cream" />
  }

  if (!authUser) {
    return (
      <main className="min-h-screen bg-cream flex items-center justify-center">
        <div className="card p-8 max-w-sm w-full text-center space-y-5">
          <div className="w-10 h-10 rounded-xl bg-teal text-white mx-auto flex items-center justify-center font-body font-extrabold text-lg">
            T
          </div>
          <h1 className="text-2xl font-heading text-ink">
            Sign in to Tamkin
          </h1>
          <p className="text-sm text-ink-3">
            Continue to the procurement workspace with your Google account.
          </p>
          <div className="pt-1 flex justify-center">
            <GoogleSignIn onAuthenticated={setAuthUser} />
          </div>
          <Link
            href="/"
            className="inline-block text-xs text-ink-4 hover:text-teal transition-colors"
          >
            Back to landing
          </Link>
        </div>
      </main>
    )
  }

  const selectedProjectId = searchParams.get('projectId')?.trim()
  if (!selectedProjectId) {
    return <main className="min-h-screen bg-cream" />
  }

  const handleSignOut = () => {
    trackTraceEvent('auth_sign_out', { user_id: authUser.id }, { path: '/product' })
    setAuthUser(null)
  }

  return (
    <WorkspaceProvider authUser={authUser} onSignOut={handleSignOut}>
      <WorkspaceShell />
    </WorkspaceProvider>
  )
}

export default function ProductPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-cream" />}>
      <ProductPageContent />
    </Suspense>
  )
}
