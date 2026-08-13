/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#12213A',
          800: '#1E293B',
          700: '#334155',
        },
        slatebg: {
          50: '#F7F8FA',
          100: '#F1F5F9',
        },
        risk: {
          low: '#64748B',
          lowBg: '#F1F5F9',
          moderate: '#D97706',
          moderateBg: '#FEF3C7',
          high: '#B91C1C',
          highBg: '#FEE2E2',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'IBM Plex Mono', 'monospace'],
        display: ['IBM Plex Sans', 'Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
