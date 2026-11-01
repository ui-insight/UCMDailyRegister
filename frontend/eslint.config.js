import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

// Complexity ratchet: new code stays at 20 or below. Each file listed here is
// capped at its current worst score, so it can't get worse. Lower a cap as the
// file is refactored, and delete the entry once it reaches the default.
const MAX_COMPLEXITY = 20
const COMPLEXITY_CAPS = {
  'src/pages/EditPage.tsx': 75,
  'src/pages/BuilderPage.tsx': 44,
  'src/components/submission/SchedulePrefs.tsx': 38,
  'src/components/submission/SubmissionForm.tsx': 38,
  'src/components/editor/SubmissionMeta.tsx': 34,
  'src/components/editor/AIEditControls.tsx': 25,
}

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    rules: {
      // These compiler-oriented rules were introduced by newer react-hooks plugin releases.
      // Keep the existing lint baseline while upgrading the frontend toolchain.
      'react-hooks/immutability': 'off',
      'react-hooks/set-state-in-effect': 'off',
      complexity: ['error', MAX_COMPLEXITY],
    },
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
  },
  ...Object.entries(COMPLEXITY_CAPS).map(([file, cap]) => ({
    files: [file],
    rules: { complexity: ['error', cap] },
  })),
])
