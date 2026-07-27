/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Approximate corporate blue/gold, not verified against real RBC
        // brand guidelines — swap for exact values if/when available.
        brand: {
          blue: "#0033A0",
          "blue-dark": "#00205B",
          gold: "#FFC72C",
        },
      },
      keyframes: {
        fadeIn: { "0%": { opacity: 0 }, "100%": { opacity: 1 } },
      },
    },
  },
  plugins: [],
};
