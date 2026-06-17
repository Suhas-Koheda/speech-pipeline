import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy /segments/* → serve from the parent speech-pipeline directory
    // so audio files like ../segments/TEDx Talks/... become /segments/TEDx Talks/...
    proxy: {
      '/segments': {
        target: 'http://localhost:8080',
        changeOrigin: false,
      },
    },
  },
})
