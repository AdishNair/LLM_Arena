/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0c111f',
        mist: '#f4f6fb',
        pulse: '#ff6b35',
        tide: '#2a9d8f',
        navy: '#1d3557',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['IBM Plex Sans', 'sans-serif'],
      },
      boxShadow: {
        card: '0 16px 40px rgba(16, 24, 40, 0.08)',
      },
    },
  },
  plugins: [],
};
