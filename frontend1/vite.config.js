import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

export default defineConfig({
  plugins: [
    react(),
    nodePolyfills(), // Handles Node.js polyfills for browser environment
  ],
  define: {
    // Some libraries use the global object or process.env, even on the browser
    global: 'window',
    'process.env': {},
  },
  assetsInclude: ['**/*.owl'], // Ensures .owl files are treated as assets
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
  },
})
