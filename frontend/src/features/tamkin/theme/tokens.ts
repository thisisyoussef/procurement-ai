export const TAMKIN_THEME = {
  colors: {
    bg: '#081018',
    bgSoft: '#0f1822',
    card: '#131f2d',
    cardSoft: '#1a2a3d',
    text: '#f8f4ea',
    textMuted: '#b8c3d1',
    accent: '#d8ad6a',
    accentSoft: '#ffe7bf',
    success: '#5dd19a',
    warning: '#f8c66e',
    danger: '#ff8b8b',
    info: '#73b9ff',
  },
  shadows: {
    glow: '0 20px 80px rgba(7, 12, 19, 0.45)',
    card: '0 12px 28px rgba(0, 0, 0, 0.32)',
  },
  radii: {
    card: '20px',
    pill: '999px',
  },
} as const

export type TamkinTheme = typeof TAMKIN_THEME
