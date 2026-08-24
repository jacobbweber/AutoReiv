import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30000,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  use: {
    baseURL: process.env.AUTOREIV_BASE_URL || 'http://127.0.0.1:8765',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: process.env.AUTOREIV_NO_SERVER ? undefined : {
    command: 'python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8765',
    url: 'http://127.0.0.1:8765/health',
    reuseExistingServer: true,
    timeout: 15000,
  },
});
