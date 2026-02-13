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

  const handleSignOut = () => setAuthUser(null)

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
