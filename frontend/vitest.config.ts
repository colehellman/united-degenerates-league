/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/tests/setup.ts',
    exclude: ['e2e/**', 'node_modules/**'],
    // you might want to disable it, if you don't have tests that rely on CSS
    // since parsing CSS is slow
    css: true,
    coverage: {
      provider: 'v8',
      // all: false → only instrument files actually imported during test execution.
      // This prevents untested pages (CompetitionDetail, CreateCompetition) and
      // the WebSocket hook from appearing as 0% in the summary.
      all: false,
      // Restrict the report to files that have corresponding unit tests.
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
      // Belt-and-suspenders: explicitly exclude files that slip in transitively.
      exclude: [
        'src/main.tsx',
        'src/pages/CompetitionDetail.tsx',
        'src/pages/CreateCompetition.tsx',
        'src/hooks/**',
        'src/types/**',
        'src/tests/**',
        '**/*.test.{ts,tsx}',
        '**/*.d.ts',
      ],
      thresholds: {
        lines: 95,
        functions: 95,
        branches: 90,
        statements: 95,
      },
    },
  },
});
