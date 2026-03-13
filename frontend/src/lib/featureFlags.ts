const truthy = new Set(['1', 'true', 'yes', 'on'])

function parseBool(value: string | undefined, fallback = false): boolean {
  if (value == null) return fallback
  return truthy.has(value.trim().toLowerCase())
}

export const featureFlags = {
  procurementLandingBypass: parseBool(process.env.NEXT_PUBLIC_PROCUREMENT_LANDING_BYPASS, false),
  procurementClientTracing: parseBool(process.env.NEXT_PUBLIC_PROCUREMENT_CLIENT_TRACING, true),
  procurementFocusCircleSearchV1: parseBool(process.env.NEXT_PUBLIC_PROCUREMENT_FOCUS_CIRCLE_V1, false),
  // Keep enabled for testing; set NEXT_PUBLIC_PROCUREMENT_DEBUG_CONSOLE_FEED=false to disable.
  procurementDebugConsoleFeed: parseBool(process.env.NEXT_PUBLIC_PROCUREMENT_DEBUG_CONSOLE_FEED, true),
}
