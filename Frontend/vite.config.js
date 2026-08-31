import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(),],

  // Vitest reads this same config, so tests resolve modules exactly as the app does.
  test: {
    // Node has no `document`; jsdom supplies one.
    environment: 'jsdom',
    // describe/it/expect without importing them in every file.
    globals: true,
    setupFiles: './src/test-setup.js',
    // The default 'forks' pool never starts its worker on Windows, and threads
    // are lighter anyway - plenty for a suite this size.
    pool: 'threads',
    // Processing Tailwind in tests buys nothing and costs time.
    css: false,
  },
})
