/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "-apple-system", "Segoe UI", "sans-serif"],
        display: ["Iowan Old Style", "Palatino Linotype", "Book Antiqua", "Georgia", "serif"],
        mono: ["SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      screens: {
        xs: "420px",
      },
    },
  },
  plugins: [],
};
