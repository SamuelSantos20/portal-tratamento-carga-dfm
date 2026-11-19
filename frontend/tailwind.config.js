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
          950: '#071324',
          900: '#0B1E36',
          800: '#102A4C',
          700: '#183B66',
          600: '#214E85',
        },
        gold: {
          500: '#C5A059',
          400: '#D4B475',
          600: '#A6823C',
        }
      }
    },
  },
  plugins: [],
}
