/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // Preflight OFF: keep the hand-built HUD design untouched — Tailwind only
  // ADDS utilities (used for the responsive layout), it does not reset anything.
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        hudbg: '#04070d',
        hudcyan: '#1fe5ff',
        hudgold: '#ff9d2f',
      },
    },
  },
  plugins: [],
};
