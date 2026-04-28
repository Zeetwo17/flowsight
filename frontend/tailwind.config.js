/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        ink2: "#1e293b",
        accent: "#3282fa",
        normal: "#46c878",
        stressed: "#f0b43c",
        critical: "#dc3c3c"
      }
    }
  },
  plugins: []
};
