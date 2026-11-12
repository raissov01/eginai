import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Әзірлеу кезінде /api сұраныстары FastAPI-ға (8000) жіберіледі
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
