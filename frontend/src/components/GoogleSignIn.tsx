'use client'

import { useEffect, useRef, useState } from 'react'

import { AuthUser, setAuthSession } from '@/lib/auth'
import { trackTraceEvent } from '@/lib/telemetry'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''

declare global {
  interface Window {
    google?: any
  }
}

interface GoogleSignInProps {
  onAuthenticated: (user: AuthUser) => void
}

function loadGoogleScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined') {
      resolve()
      return
    }
    if (window.google?.accounts?.id) {
      resolve()
      return
    }

    const existing = document.getElementById('google-identity-script') as HTMLScriptElement | null
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error('Failed to load Google script')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.id = 'google-identity-script'
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Google script'))
    document.head.appendChild(script)
  })
}

export default function GoogleSignIn({ onAuthenticated }: GoogleSignInProps) {
  const buttonRef = useRef<HTMLDivElement | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    let cancelled = false

    const setup = async () => {
      if (!GOOGLE_CLIENT_ID) {
        setError('Google sign-in is not configured in frontend env')
        trackTraceEvent('google_signin_not_configured', {}, { level: 'warn' })
        return
      }

      try {
        await loadGoogleScript()
        if (cancelled || !buttonRef.current || !window.google?.accounts?.id) return

        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: async (response: { credential?: string }) => {
            if (!response?.credential) return
            setIsLoading(true)
            setError(null)
            trackTraceEvent('google_signin_token_received')
            try {
              const authRes = await fetch(`${API_BASE}/api/v1/auth/google`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id_token: response.credential }),
              })
              const payload = await authRes.json().catch(() => ({}))
              if (!authRes.ok) {
                throw new Error(payload?.detail || `HTTP ${authRes.status}`)
              }

              setAuthSession(payload.access_token, payload.user)
              onAuthenticated(payload.user as AuthUser)
              trackTraceEvent('google_signin_success', {
                user_id: payload?.user?.id,
                email: payload?.user?.email,
              })
            } catch (err: any) {
              setError(err?.message || 'Failed to sign in with Google')
              trackTraceEvent(
                'google_signin_error',
                { detail: err?.message || 'unknown' },
                { level: 'warn' }
              )
            } finally {
              setIsLoading(false)
            }
          },
        })

        buttonRef.current.innerHTML = ''
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'pill',
          width: 280,
        })
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.message || 'Failed to initialize Google sign-in')
          trackTraceEvent(
            'google_signin_init_error',
            { detail: err?.message || 'unknown' },
            { level: 'warn' }
          )
        }
      }
    }

    setup()
    return () => {
      cancelled = true
    }
  }, [onAuthenticated])

  return (
    <div className="space-y-3">
      <div ref={buttonRef} />
      {isLoading && <p className="text-xs text-slate-500">Signing you in...</p>}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
