'use client'

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '')

export const AUTH_TOKEN_KEY = 'tamkin_access_token'
export const AUTH_USER_KEY = 'tamkin_auth_user'

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  avatar_url: string | null
  plan?: string | null
}

export function getStoredAccessToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem(AUTH_TOKEN_KEY)
}

export function getStoredAuthUser(): AuthUser | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem(AUTH_USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as AuthUser
  } catch {
    return null
  }
}

export function setAuthSession(accessToken: string, user: AuthUser): void {
  if (typeof window === 'undefined') return
  localStorage.setItem(AUTH_TOKEN_KEY, accessToken)
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user))
}

export function clearAuthSession(): void {
  if (typeof window === 'undefined') return
  localStorage.removeItem(AUTH_TOKEN_KEY)
  localStorage.removeItem(AUTH_USER_KEY)
}

export function withAccessTokenQuery(url: string): string {
  const token = getStoredAccessToken()
  if (!token) return url
  const delimiter = url.includes('?') ? '&' : '?'
  return `${url}${delimiter}access_token=${encodeURIComponent(token)}`
}

export function buildAuthHeaders(headers?: HeadersInit): Headers {
  const merged = new Headers(headers || {})
  const token = getStoredAccessToken()
  if (token) {
    merged.set('Authorization', `Bearer ${token}`)
  }
  return merged
}

export async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: buildAuthHeaders(init?.headers),
  })
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const res = await authFetch(`${API_BASE}/api/v1/auth/me`)
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
  return (await res.json()) as AuthUser
}
