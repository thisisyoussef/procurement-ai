import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        cream: '#FAFAF7',
        surface: '#FFFFFF',
        'surface-2': '#F3F2EF',
        'surface-3': '#EAE8E4',
        ink: {
          DEFAULT: '#111111',
          2: '#333333',
          3: '#777777',
          4: '#AAAAAA',
        },
        teal: {
          DEFAULT: '#00c9a7',
          50: '#ecfdf8',
          100: '#d1faf0',
          200: '#a7f3e2',
          300: '#6ee7cc',
          400: '#38d9b3',
          500: '#00c9a7',
          600: '#00a389',
          700: '#00826e',
          800: '#006758',
          900: '#005548',
        },
        warm: '#C9A96E',
        'search-bg': '#0A0A0A',
        'search-surface': '#141414',
      },
      fontFamily: {
        heading: ['"DM Serif Text"', 'Georgia', 'serif'],
        body: ['Manrope', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
export default config
