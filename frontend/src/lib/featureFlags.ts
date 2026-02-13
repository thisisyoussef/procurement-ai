const truthy = new Set(['1', 'true', 'yes', 'on'])

function parseBool(value: string | undefined, fallback = false): boolean {
  if (value == null) return fallback
  return truthy.has(value.trim().toLowerCase())
}

export const featureFlags = {
  tamkinLandingBypass: parseBool(process.env.NEXT_PUBLIC_TAMKIN_LANDING_BYPASS, false),
  tamkinClientTracing: parseBool(process.env.NEXT_PUBLIC_TAMKIN_CLIENT_TRACING, true),
}
