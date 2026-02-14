// Matches existing --ease: cubic-bezier(0.16, 1, 0.3, 1) from globals.css
export const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const

export const SPRING_SNAPPY = { type: 'spring' as const, stiffness: 300, damping: 30 }
export const SPRING_GENTLE = { type: 'spring' as const, stiffness: 180, damping: 24 }
export const SPRING_BOUNCY = { type: 'spring' as const, stiffness: 400, damping: 20, mass: 0.8 }

export const DURATION = {
  instant: 0.15,
  fast: 0.25,
  normal: 0.4,
  slow: 0.65,
  cinematic: 0.9,
} as const

export const STAGGER = {
  fast: 0.04,
  normal: 0.08,
  slow: 0.12,
} as const
