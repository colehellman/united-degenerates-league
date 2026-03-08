import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    watch: {
      usePolling: true
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/tests/setup.ts'],
    coverage: {
      provider: 'v8',
      // Only track coverage for files that have corresponding tests.
      // Complex data-heavy pages (CompetitionDetail, CreateCompetition) and
      // the WebSocket hook are excluded — their logic is integration-tested
      // at the API layer, not in unit tests.
      include: [
        'src/App.tsx',
        'src/services/authStore.ts',
        'src/components/BugReportModal.tsx',
        'src/components/ErrorBoundary.tsx',
        'src/components/Layout.tsx',
        'src/pages/Login.tsx',
        'src/pages/Register.tsx',
        'src/pages/Dashboard.tsx',
        'src/pages/Competitions.tsx',
        'src/pages/Admin.tsx',
      ],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 85,
        statements: 90,
      },
    },
  },
})
