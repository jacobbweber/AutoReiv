import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/unit/frontend/**/*.test.js'],
    setupFiles: ['./tests/unit/frontend/vitest.setup.js'],
    globals: true
  }
});
