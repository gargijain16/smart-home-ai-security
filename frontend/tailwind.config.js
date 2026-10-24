/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: { sans: ['Manrope', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'Roboto', 'sans-serif'] },
      colors: {
        ink: { 950: '#060a14', 900: '#0a1020', 800: '#0f172a', 700: '#162036', 600: '#1f2b45' },
        cyan: { 400: '#22d3ee', 500: '#06b6d4' },
      },
    },
  },
  plugins: [],
}
