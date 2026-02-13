'use client'

import Link from 'next/link'
import { Suspense, useEffect, useState } from 'react'

import GoogleSignIn from '@/components/GoogleSignIn'
import { WorkspaceProvider } from '@/contexts/WorkspaceContext'
import WorkspaceShell from '@/components/workspace/WorkspaceShell'
import {
  AuthUser,
  clearAuthSession,
  fetchCurrentUser,
  getStoredAccessToken,
  getStoredAuthUser,
} from '@/lib/auth'

function ProductPageContent() {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null)
  const [authReady, setAuthReady] = useState(false)

  useEffect(() => {
    const initAuth = async () => {
      const token = getStoredAccessToken()
      if (!token) {
        setAuthReady(true)
        return
      }

      const cachedUser = getStoredAuthUser()
      if (cachedUser) setAuthUser(cachedUser)

      try {
        const me = await fetchCurrentUser()
        setAuthUser(me)
      } catch {
        clearAuthSession()
        setAuthUser(null)
      } finally {
        setAuthReady(true)
      }
    }
    initAuth()
  }, [])

  // ─── Loading ──────────────────────────────────────
  if (!authReady) {
    return <main className="min-h-screen bg-workspace-bg" />
  }

  // ─── Auth gate ────────────────────────────────────
  if (!authUser) {
    return (
      <main className="min-h-screen bg-workspace-bg flex items-center justify-center">
        <div className="glass-card p-8 max-w-sm w-full text-center space-y-5">
          <div className="w-10 h-10 rounded-xl bg-teal text-white mx-auto flex items-center justify-center font-heading font-bold text-lg">
            T
          </div>
          <h1 className="text-2xl font-heading text-workspace-text">
            Sign in to Tamkin
          </h1>
          <p className="text-sm text-workspace-muted">
            Continue to the procurement workspace with your Google account.
          </p>
          <div className="pt-1 flex justify-center dark-override">
            <GoogleSignIn onAuthenticated={setAuthUser} />
          </div>
          <Link
            href="/"
            className="inline-block text-xs text-workspace-muted hover:text-teal transition-colors"
          >
            ← Back to landing
          </Link>
        </div>
      </main>
    )
  }

  // ─── Authenticated workspace ──────────────────────
  const handleSignOut = () => setAuthUser(null)

  return (
    <WorkspaceProvider authUser={authUser} onSignOut={handleSignOut}>
      <WorkspaceShell />
    </WorkspaceProvider>
  )
}

export default function ProductPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-workspace-bg" />}>
      <ProductPageContent />
    </Suspense>
  )
}
