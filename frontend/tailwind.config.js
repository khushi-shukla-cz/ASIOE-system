/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        cream: '#FAFAF7',
        sage: {
          50: '#f0f4f0',
          100: '#E8F0E8',
          200: '#C8DCC8',
          400: '#7AAD7A',
          600: '#4A8A4A',
          800: '#2D602D',
        },
        slate: {
          50: '#F8F9FB',
          100: '#EFF1F5',
          200: '#D8DCE8',
          400: '#8892A8',
          600: '#4A5568',
          800: '#1A2235',
          900: '#0F1724',
        },
        amber: {
          50: '#FFF8EE',
          100: '#FFF0D4',
          200: '#FFD990',
          400: '#F5A623',
          600: '#D4860A',
        },
        rose: {
          50: '#FFF1F2',
          100: '#FFE0E2',
          200: '#FFC0C5',
          400: '#F87171',
          600: '#DC2626',
        },
        sky: {
          50: '#F0F8FF',
          100: '#E0F0FF',
          200: '#BAE0FF',
          400: '#38A0F5',
          600: '#0077CC',
        },
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      boxShadow: {
        card: '0 2px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
        'card-hover': '0 8px 32px rgba(0,0,0,0.10), 0 2px 8px rgba(0,0,0,0.06)',
        glow: '0 0 30px rgba(74,138,74,0.15)',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-delayed': 'float 6s ease-in-out 2s infinite',
        'pulse-soft': 'pulse-soft 3s ease-in-out infinite',
        'fade-up': 'fade-up 0.5s ease-out',
        'slide-in': 'slide-in 0.4s ease-out',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '0.7' },
          '50%': { opacity: '1' },
        },
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in': {
          '0%': { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
      },
    },
  },
  plugins: [],
}
