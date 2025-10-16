import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSourceLocator } from '@metagptx/vite-plugin-source-locator'


// https://vitejs.dev/config/
export default defineConfig({
  plugins: [viteSourceLocator({
    prefix: 'mgx'
  }), react()],
  server: {
    proxy: {
      // 前端调用 /api/* 时，代理到后端 FastAPI 服务
      '/api': {
        target: 'http://127.0.0.1:10010',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
