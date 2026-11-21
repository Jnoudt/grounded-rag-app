/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#102a43",
        audit: "#0f766e",
        amber: "#d97706",
        parchment: "#f4f1ea"
      }
    }
  },
  plugins: []
};
