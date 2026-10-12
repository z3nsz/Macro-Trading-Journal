import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // The browser calls /api/... on the Vite dev server (port 5173).
    // Vite forwards those requests to FastAPI (port 8000), so the browser
    // sees one origin and CORS never becomes an issue during development.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
