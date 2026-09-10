import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(viteConfig, defineConfig({
  test: {
    environment: 'node',
    testTransformMode: {
      web: ['**/tests/ProviderManage.test.ts'],
    },
  },
}))
