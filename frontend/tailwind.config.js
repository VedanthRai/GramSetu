/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f7f4ee", card: "#fffdf9", ink: { DEFAULT: "#1b2a41", soft: "#4a5568", faint: "#8a94a6" },
        saffron: { DEFAULT: "#d9771f", light: "#fbe9d7", dark: "#a95712" },
        verified: { DEFAULT: "#2f7d4f", light: "#e3f2e8" }, danger: { DEFAULT: "#b42318", light: "#fdecea" },
        line: "#e4ddd0",
      },
      fontFamily: {
        sans: ["'Noto Sans'", "'Noto Sans Devanagari'", "'Noto Sans Kannada'", "'Noto Sans Tamil'", "system-ui", "sans-serif"],
        display: ["'Fraunces'", "Georgia", "serif"],
      },
    },
  },
  plugins: [],
};
