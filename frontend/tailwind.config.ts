import type { Config } from "tailwindcss";
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1220",
        panel: "#111a2e",
        brand: { DEFAULT: "#2563eb", soft: "#1e293b" },
      },
    },
  },
  plugins: [],
};
export default config;
