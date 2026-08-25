import js from '@eslint/js';
import globals from 'globals';

export default [
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        lucide: 'readonly',
        mermaid: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
      'no-undef': 'error',
    },
  },
  {
    ignores: [
      'data/**',
      'dist/**',
      'coverage/**',
      'playwright-report/**',
      'test-results/**',
      '.venv/**',
      '.git/**',
    ],
  },
];
