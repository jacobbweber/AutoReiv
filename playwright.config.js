import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  outputDir: './test-results',
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],
  use: {
    baseURL: process.env.AUTOREIV_BASE_URL || 'http://127.0.0.1:8765',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  // CARD-467: scripts/smoke_server.py force-pins data dir / DB / wiki / backups under
  // scratch/smoke_data (wiped each start) and refuses to start on live AppData.
  // Never reuse a server already on :8765 - the guard cannot vet a server it did not start.
  webServer: process.env.AUTOREIV_NO_SERVER ? undefined : {
    command: 'python scripts/smoke_server.py --host 127.0.0.1 --port 8765',
    url: 'http://127.0.0.1:8765/health',
    reuseExistingServer: false,
    timeout: 30000,
    env: {
      AUTOREIV_DATA_DIR: './scratch/smoke_data',
      AUTOREIV_DB_PATH: './scratch/smoke_data/database/autoreiv.db',
      AUTOREIV_WIKI_PATH: './scratch/smoke_data/wiki',
    },
  },
});
