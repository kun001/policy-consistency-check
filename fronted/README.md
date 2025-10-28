# React + Vite Template

A modern React template for web applications and games, featuring React 18, Vite, TailwindCSS, and Material UI.

## Project Structure

```
├── src/
│   ├── App.jsx          # Main application component
│   ├── main.jsx         # Application entry point
│   └── index.css        # Global styles (Tailwind)
├── public/              # Static assets
├── index.html           # HTML template
├── vite.config.js       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
├── postcss.config.js    # PostCSS configuration
└── eslint.config.js     # ESLint configuration
```

## Development Guidelines

- Modify `index.html` and `src/App.jsx` as needed
- Create new folders or files in `src/` directory as needed
- Style components using TailwindCSS utility classes
- Avoid modifying `src/main.jsx` and `src/index.css`
- Only modify `vite.config.js` if absolutely necessary

## Available Scripts
- `pnpm install` - Install dependencies
- `pnpm run dev` - Start development server
- `pnpm run lint` - Lint source files

## Tech Stack

- React
- Vite
- TailwindCSS
- ESLint
- Javascript

## 环境变量与配置

- 前端通过 `.env` 文件进行配置，示例见 `.env.example`。
- 客户端可读取的变量必须以 `VITE_` 前缀开头，切勿在前端环境变量中放置任何敏感信息（如 API Key）。

可用变量说明：

- `VITE_API_BASE_URL`：后端地址的 Origin（如 `https://api.example.com`）。为空表示同源部署。
- `VITE_API_BASE_PREFIX`：后端路由前缀（默认 `/api`）。
- `VITE_TARGET_DATASET_ID`：国家政策集合名（默认 `national_policy_documents`）。
- `VITE_LOCAL_DATASET_ID`：地方政策集合名（默认 `policy_documents`）。
- `DEV_PROXY_TARGET`：开发环境代理目标（仅在本地开发有效，默认 `http://127.0.0.1:10010`）。

使用方法：

1. 复制 `.env.example` 为 `.env.development`，根据需要填写上述变量。
2. 本地开发运行 `pnpm run dev`，Vite 会读取 `.env.development` 并代理 `/api` 到后端。
3. 生产部署时设置 `VITE_API_BASE_URL` 与 `VITE_API_BASE_PREFIX`，前端将使用 `${VITE_API_BASE_URL}${VITE_API_BASE_PREFIX}` 作为接口前缀。

注意：`.gitignore` 已忽略 `.env*` 文件，请勿将真实环境配置提交到 GitHub。
