const TRUE_VALUES = new Set(['1', 'true', 'yes', 'on'])
const FALSE_VALUES = new Set(['0', 'false', 'no', 'off'])

export const TAMKIN_EXPERIENCE_COOKIE = 'tamkin_experience'

function normalize(value: string | null | undefined): string {
  return (value || '').trim().toLowerCase()
}

export function parseOptionalBool(value: string | null | undefined): boolean | null {
  const normalized = normalize(value)
  if (TRUE_VALUES.has(normalized)) return true
  if (FALSE_VALUES.has(normalized)) return false
  return null
}

export function getEnvTamkinExperienceDefault(): boolean {
  return (
    parseOptionalBool(process.env.NEXT_PUBLIC_TAMKIN_EXPERIENCE_ENABLED) ??
    parseOptionalBool(process.env.NEXT_PUBLIC_TAWRID_EXPERIENCE_ENABLED) ??
    false
  )
}

export function resolveTamkinExperienceEnabled(cookieValue?: string | null): boolean {
  return parseOptionalBool(cookieValue) ?? getEnvTamkinExperienceDefault()
}

export const isTamkinExperienceEnabled = getEnvTamkinExperienceDefault()

export function setTamkinExperienceCookie(enabled: boolean): void {
  if (typeof document === 'undefined') return
  document.cookie = [
    `${TAMKIN_EXPERIENCE_COOKIE}=${enabled ? '1' : '0'}`,
    'path=/',
    'max-age=31536000',
    'samesite=lax',
  ].join('; ')
}
