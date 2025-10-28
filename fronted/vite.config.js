import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSourceLocator } from '@metagptx/vite-plugin-source-locator'


// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.DEV_PROXY_TARGET || 'http://127.0.0.1:10010'

  return {
    plugins: [viteSourceLocator({ prefix: 'mgx' }), react()],
    server: {
      proxy: {
        // 前端调用 /api/* 时，代理到后端 FastAPI 服务（可由 .env 配置）
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  }
})
