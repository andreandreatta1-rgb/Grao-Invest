import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        grao: {
          bg: "#0a0e1a",
          bg2: "#0f1628",
          card: "#141c30",
          card2: "#1a2340",
          green: "#00d4aa",
          green2: "#00ff9d",
          red: "#ff4d6a",
          gold: "#f5c842",
          blue: "#4f8ef7",
          text2: "#8a9bc0",
          text3: "#5a6a8a",
        },
      },
      boxShadow: {
        phone: "0 0 0 1px rgba(255,255,255,0.08), 0 30px 80px rgba(0,0,0,0.6), 0 0 120px rgba(0,212,170,0.08)",
        greenGlow: "0 0 20px rgba(0,212,170,0.2)",
        redGlow: "0 0 20px rgba(255,77,106,0.2)",
      },
      keyframes: {
        pulseStatus: {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.6", transform: "scale(0.85)" },
        },
        riseBar: {
          from: { transform: "scaleY(0)" },
          to: { transform: "scaleY(1)" },
        },
      },
      animation: {
        pulseStatus: "pulseStatus 1.5s infinite",
        riseBar: "riseBar 0.6s cubic-bezier(0.4,0,0.2,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
