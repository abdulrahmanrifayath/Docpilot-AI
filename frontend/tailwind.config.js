/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0B0F17',
          subtle: '#111827',
          card: '#161F30',
          hover: '#1F2B42',
        },
        brand: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          200: '#C7D2FE',
          300: '#A5B4FC',
          400: '#818CF8',
          500: '#6366F1', // Indigo primary
          600: '#4F46E5',
          700: '#4338CA',
          800: '#3730A3',
          900: '#312E81',
          accent: '#06B6D4', // Cyan accent
        },
        border: {
          subtle: '#1E293B',
          medium: '#334155',
          glow: '#6366F133',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 20px -5px rgba(99, 102, 241, 0.3)',
        'glow-cyan': '0 0 20px -5px rgba(6, 182, 212, 0.3)',
        'inner-light': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
