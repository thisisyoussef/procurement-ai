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
        gold: {
          DEFAULT: '#d4af37',
          50: '#fdf8e8',
          100: '#faefc4',
          200: '#f5df8a',
          300: '#eecf50',
          400: '#d4af37',
          500: '#b8922c',
          600: '#967523',
          700: '#74591b',
          800: '#5c4617',
          900: '#4a3912',
        },
        workspace: {
          bg: '#0d1117',
          surface: '#161b22',
          border: '#30363d',
          hover: '#1c2128',
          muted: '#8b949e',
          text: '#e6edf3',
        },
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
