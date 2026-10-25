import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
      '/photos': 'http://127.0.0.1:5000',
      '/ml-images': 'http://127.0.0.1:5000',
    },
  },
})
