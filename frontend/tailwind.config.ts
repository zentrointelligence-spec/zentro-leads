import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: "#0F1B2D",
          blue: "#3B6FFF",
          "blue-dark": "#2855D8",
          "blue-light": "#EEF3FF",
          slate: "#64748B",
        },
        /** Flat aliases for `bg-brand-blue`, `text-brand-blue`, etc. */
        "brand-blue": "#3B6FFF",
        "brand-blue-dark": "#2855D8",
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
