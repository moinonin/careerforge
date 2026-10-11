import type { Config } from "tailwindcss";

// Tailwind CSS v4 — all design tokens live in src/app/globals.css via @theme.
// This file is kept minimal; content paths are auto-detected by Tailwind v4.
const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};
export default config;
