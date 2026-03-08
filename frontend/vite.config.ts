import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true,
    },
  },
  test: {
    globals: true,         // exposes vi, describe, it, expect without imports
    environment: 'jsdom',  // DOM APIs required by React Testing Library
    setupFiles: ['./src/tests/setup.ts'], // registers @testing-library/jest-dom matchers
  },
})
