import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // reactHooks' "recommended" flat config bundles the newer React
      // Compiler analysis rules, including this one, which flags calling a
      // state setter (directly or via a function that does) synchronously
      // inside a useEffect body — in practice this is the app's chosen,
      // consistent architecture for "fetch data when this page/section
      // mounts" across nearly every page (Admin, Analytics, Billing,
      // Dashboard, Login, Onboarding, Settings, Tasks, etc — ~15 call
      // sites). Migrating all of that to an alternative pattern (fetching
      // in event handlers, or adopting a data-fetching library) would be a
      // real, separate architectural project, not a lint cleanup, and it's
      // not something to rewrite blind without the ability to click
      // through the app and verify data still loads correctly everywhere.
      // Kept visible as a warning rather than silenced, so new code is
      // still nudged toward the stricter pattern.
      'react-hooks/set-state-in-effect': 'warn',
      // Flags calling any impure function (Date.now(), Math.random(), etc.)
      // synchronously during render — the two real cases here are both
      // Date.now() used as a "roughly now" filter cutoff / display
      // fallback. There's no meaningful way to useMemo a wall-clock read
      // (memoization is dependency-based, not time-based); doing this
      // "properly" would mean introducing a real ticking clock
      // (useState + setInterval) purely to satisfy the compiler for a
      // value where a few milliseconds of staleness has zero observable
      // effect. Not worth that complexity for this use case.
      'react-hooks/purity': 'warn',
      // AuthContext.jsx (useAuth) and toast.jsx (showToast,
      // registerToastHandler) each co-locate a small non-component helper
      // with the component/context they belong to — a standard, idiomatic
      // React pattern. Splitting them into separate files purely to
      // satisfy Vite Fast Refresh isn't worth the added indirection for
      // files this small.
      'react-refresh/only-export-components': ['warn', {
        allowConstantExport: true,
        allowExportNames: ['useAuth', 'registerToastHandler', 'showToast'],
      }],
    },
  },
  {
    // Test files run under Node (via vitest), not the browser — `global`
    // is a real, valid reference there, just not part of the browser
    // globals set used everywhere else.
    files: ['**/*.test.{js,jsx}', 'src/test/**/*.js'],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
    },
  },
])
