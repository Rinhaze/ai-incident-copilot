import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
const api = process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000'
export default defineConfig({ plugins: [react()], server: { host: '127.0.0.1', proxy: { '/api': api, '/health': api } }, test: { environment: 'jsdom', globals: true, setupFiles: './src/test/setup.ts', exclude: ['e2e/**', 'node_modules/**'] } })
