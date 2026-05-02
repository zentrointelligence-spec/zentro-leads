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
        primary: {
          DEFAULT: "var(--color-brand)",
          dark: "#c2410c",
          light: "var(--color-brand-light)",
        },
        hot: {
          DEFAULT: "var(--color-hot)",
          light: "var(--color-hot-bg)",
        },
        warm: {
          DEFAULT: "var(--color-warm)",
          light: "var(--color-warm-bg)",
        },
        potential: {
          DEFAULT: "var(--color-potential)",
          light: "var(--color-potential-bg)",
        },
        cold: {
          DEFAULT: "var(--color-cold)",
          light: "var(--color-cold-bg)",
        },
        success: {
          DEFAULT: "var(--color-success)",
          light: "var(--color-success-bg)",
        },
        background: {
          primary: "var(--bg-primary)",
          secondary: "var(--bg-secondary)",
          tertiary: "var(--bg-tertiary)",
          card: "var(--bg-card)",
          hover: "var(--bg-hover)",
          input: "var(--bg-input)",
        },
        card: {
          DEFAULT: "var(--bg-card)",
          border: "var(--border-primary)",
        },
        foreground: {
          primary: "var(--text-primary)",
          secondary: "var(--text-secondary)",
          muted: "var(--text-tertiary)",
          disabled: "var(--text-disabled)",
        },
        border: {
          DEFAULT: "var(--border-primary)",
          strong: "var(--border-secondary)",
        },
        sidebar: {
          DEFAULT: "var(--sidebar-bg)",
          border: "var(--sidebar-border)",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      fontSize: {
        "2xs": ["10px", { lineHeight: "14px" }],
        xs: ["12px", { lineHeight: "16px" }],
        sm: ["13px", { lineHeight: "18px" }],
        base: ["14px", { lineHeight: "20px" }],
        lg: ["16px", { lineHeight: "24px" }],
        xl: ["18px", { lineHeight: "28px" }],
        "2xl": ["20px", { lineHeight: "30px" }],
        "3xl": ["24px", { lineHeight: "32px" }],
        "4xl": ["30px", { lineHeight: "38px" }],
        "5xl": ["36px", { lineHeight: "44px" }],
      },
      spacing: {
        sidebar: "260px",
        topbar: "64px",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
        xl: "18px",
        "2xl": "24px",
        full: "999px",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
      },
      transitionDuration: {
        fast: "150ms",
        base: "250ms",
        slow: "350ms",
      },
      animation: {
        "fade-in-up": "fade-in-up 0.4s cubic-bezier(0.22, 1, 0.36, 1) both",
      },
    },
  },
  plugins: [],
};

export default config;
