/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
      colors: {
        brand: { 50: "#eef4ff", 100: "#dbe6fe", 200: "#bfd3fe", 300: "#93b4fd", 400: "#6090fa", 500: "#3b6cf6", 600: "#2552eb", 700: "#1d3fd8", 800: "#1e36af", 900: "#1e3389" },
        ink: { 900: "#0f1b2d", 800: "#16253b", 700: "#1f3350" },
      },
      boxShadow: { card: "0 1px 2px rgba(16,24,40,.04), 0 1px 3px rgba(16,24,40,.06)" },
    },
  },
  plugins: [],
};
