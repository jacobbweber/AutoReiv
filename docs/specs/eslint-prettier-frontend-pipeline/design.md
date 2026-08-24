# Technical Design: ESLint & Prettier Static Analysis Pipeline for Frontend

> **Spec Status**: In Review  
> **Card Reference**: [CARD-034](file:///.github/cards/CARD-034-eslint-and-prettier-static-analysis-pipeline-for-frontend.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/eslint-prettier-frontend-pipeline/requirements.md)

---

## 1. Architectural Configuration Strategy

### Toolchain Stack
- **ESLint 9+ Flat Config**: `eslint.config.js` exporting standard JS recommended rules with `globals.browser` for `src/web/static/` and `globals.node` for tests and config files.
- **Prettier**: `.prettierrc` defining formatting rules.
- **Unified Pipeline**:
  ```mermaid
  flowchart LR
      Preflight["npm run preflight"] --> Ruff["1. Ruff (Python)"]
      Preflight --> Pytest["2. Pytest (Python)"]
      Preflight --> ESLint["3. ESLint (Frontend)"]
      Preflight --> Vitest["4. Vitest (Unit)"]
      Preflight --> Playwright["5. Playwright (Smoke)"]
      Preflight --> RTM["6. RTM Matrix Verify"]
  ```

---

## 2. Configuration Contracts

### `eslint.config.js`
```javascript
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
    ignores: ['data/**', 'dist/**', 'coverage/**', 'playwright-report/**', 'test-results/**'],
  },
];
```

### `.prettierrc`
```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 120
}
```
