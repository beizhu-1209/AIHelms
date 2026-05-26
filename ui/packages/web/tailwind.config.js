/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      animation: {
        'blob': 'blob 20s infinite',
        'blob-reverse': 'blob-reverse 25s infinite',
        'blob-slow': 'blob 30s infinite',
      },
      keyframes: {
        blob: {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '25%': { transform: 'translate(30px, -50px) scale(1.1)' },
          '50%': { transform: 'translate(-20px, 20px) scale(0.9)' },
          '75%': { transform: 'translate(20px, 40px) scale(1.05)' },
        },
        'blob-reverse': {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '25%': { transform: 'translate(-30px, 40px) scale(0.95)' },
          '50%': { transform: 'translate(20px, -30px) scale(1.1)' },
          '75%': { transform: 'translate(-20px, -20px) scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
