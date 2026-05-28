import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontWeight: {
        "500": "500",
        "600": "600",
        "700": "700",
        "800": "800",
      },
      colors: {
        background: "var(--bg-base)",
        foreground: "var(--text-primary)",
        accent: {
          from: "var(--accent-from)",
          to:   "var(--accent-to)",
        },
      },
      animation: {
        "gradient-shift": "gradient-shift 3s ease infinite",
        "pulse-glow":     "pulse-glow 2s ease-in-out infinite",
        "fade-in-up":     "fade-in-up 0.4s ease both",
        "fade-in":        "fade-in 0.3s ease both",
        "slide-in-left":  "slide-in-left 0.35s ease both",
        "spin-slow":      "spin-slow 3s linear infinite",
      },
    },
  },
  plugins: [],
};
export default config;
