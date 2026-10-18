import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on the home network so the phone can open the dev server.
    host: true,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
