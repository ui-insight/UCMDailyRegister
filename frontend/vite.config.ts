/// <reference types="vitest/config" />
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  // Deployed environments assert the viewer's role by having nginx inject the
  // trusted auth headers (see frontend/nginx.conf). Mirror that locally by
  // setting DEV_TRUSTED_ROLE / DEV_TRUSTED_SECRET in frontend/.env.local plus
  // the matching TRUSTED_ROLE_HEADER_SECRET in backend/.env; leave them unset
  // for public-only behavior.
  const env = loadEnv(mode, process.cwd(), 'DEV_TRUSTED')
  return {
    plugins: [react(), tailwindcss()],
    test: {
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      globals: true,
      css: true,
    },
    server: {
      proxy: {
        '/api': {
          target: 'http://localhost:8001',
          ...(env.DEV_TRUSTED_ROLE
            ? {
                headers: {
                  'X-Trusted-User-Role': env.DEV_TRUSTED_ROLE,
                  'X-Trusted-Auth-Secret': env.DEV_TRUSTED_SECRET ?? '',
                },
              }
            : {}),
        },
      },
    },
  }
})
