# 政策一致性检查（Policy Consistency Check）

一个用于“政策文件解析、入库与一致性对比”的全栈示例项目。前端支持上传/浏览/对比，本地或生产后端提供解析与向量检索服务，结合 Weaviate 与外部解析服务完成端到端流程。

- 前端：React + Vite + Ant Design + Tailwind
- 后端：FastAPI（Python），Weaviate 客户端，SQLite 持久化，智谱文档解析，SiliconFlow 向量化

## 功能概览

- 上传并解析政策文件：一次性完成解析、切分、向量化与持久化（`/api/rag/ingest-and-index`）
- 政策文件库：国家与地方政策列表、详情、分段数据查看
- 一致性对比：地方政策条款与国家政策条款的差异分析（`/api/compare/analyze`）
- RAG 检索：基于 Weaviate 的混合/向量搜索（`/api/rag/search`、`/api/weaviate/search`）

## 目录结构

```
policy-consistency-check/
├── fronted/                # 前端（React + Vite）
│   ├── src/                # 页面与 API 封装
│   ├── .env.example        # 前端环境变量示例（VITE_ 前缀）
│   └── vite.config.js      # 本地开发代理到 Python 后端
└── py-backend/             # 后端（FastAPI）
    ├── api/                # 外部服务与 Weaviate 封装
    ├── router/             # FastAPI 路由（rag、weaviate、compare 等）
    ├── src/                # 业务模块（settings、weaviateEngine 等）
    ├── .env.example        # 后端环境变量示例
    └── app.py              # 应用入口（uvicorn 启动）
```

## 快速开始

### 1) 启动后端（Python / FastAPI）

- 创建并激活虚拟环境后安装依赖（示例）：

```bash
pip install fastapi uvicorn weaviate-client requests python-dotenv pydantic tqdm
```

- 配置环境变量：复制 `py-backend/.env.example` 为 `py-backend/.env.development`，填写至少以下项：
  - `SILICONFLOW_API_TOKEN`：向量化所需 Token
  - `WEAVIATE_API_KEY`：Weaviate 访问密钥
  - `ZHIPU_API_TOKEN`：智谱文档解析 Token
  - 如需修改 Weaviate 连接或服务端口，按需覆盖对应变量

- 启动：

```bash
python py-backend/app.py
# 或者：uvicorn app:app --host 0.0.0.0 --port 10010
```

后端默认监听 `APP_HOST=0.0.0.0`，`APP_PORT=10010`（可在 `.env` 中修改）。

### 2) 启动前端（React + Vite）

```bash
cd fronted
pnpm install
cp .env.example .env.development  # 按需填写变量
pnpm run dev
```

- 本地开发代理：`/api/*` 将被代理到后端（`DEV_PROXY_TARGET`，默认 `http://127.0.0.1:10010`）。
- 生产部署：设置 `VITE_API_BASE_URL`（后端域名）与 `VITE_API_BASE_PREFIX`（通常 `/api`）。

## 环境变量与配置

### 前端（Vite）

- `VITE_API_BASE_URL`：后端地址 Origin（留空表示同源）
- `VITE_API_BASE_PREFIX`：后端路由前缀（默认 `/api`）
- `VITE_TARGET_DATASET_ID`：国家政策集合名（默认 `national_policy_documents`）
- `VITE_LOCAL_DATASET_ID`：地方政策集合名（默认 `policy_documents`）
- `DEV_PROXY_TARGET`：开发代理目标（默认 `http://127.0.0.1:10010`）

> 注意：所有以 `VITE_` 前缀的变量会被构建到客户端，请勿放置敏感信息。

### 后端（FastAPI）

- 服务：`APP_HOST`、`APP_PORT`
- 集合：`DEFAULT_COLLECTION_NAME`（默认 `policy_documents`）
- SiliconFlow：`SILICONFLOW_API_TOKEN`
- Weaviate：
  - `WEAVIATE_HTTP_HOST`、`WEAVIATE_HTTP_PORT`、`WEAVIATE_HTTP_SECURE`
  - `WEAVIATE_GRPC_HOST`、`WEAVIATE_GRPC_PORT`、`WEAVIATE_GRPC_SECURE`
  - `WEAVIATE_API_KEY`
- 智谱 BigModel：`ZHIPU_API_TOKEN`、`ZHIPU_UPLOAD_URL`、`ZHIPU_RESULT_BASE`
- 存储根目录（可选）：`STORAGE_ROOT`（默认 `<project>/storage`）

> 后端通过 `src/settings.py` 统一读取环境变量，`app.py` 在启动时加载 `.env`。

## 主要 API（摘要）

- 解析与入库
  - `POST /api/rag/ingest-and-index`：上传文件 → 解析 → 切分 → 向量化 → 持久化
  - `GET  /api/rag/documents?collection_name=...`：列出集合中文档
  - `GET  /api/rag/documents/{doc_id}/chunks`：列出分段（供前端详情页）
  - `GET  /api/rag/documents/{doc_id}/parsed`：获取解析产物（正文、目录、计数、关键词）
- 一致性对比
  - `POST /api/compare/analyze`：输入地方文档与多个国家文档 ID，返回条款级对比结果
- Weaviate 检索
  - `POST /api/weaviate/search`：混合/向量搜索（支持 filters 与条件组合）

## 数据存储与向量库

- 持久化目录结构（默认 `storage/`）：
  - `storage/docs/<collection_id>/<doc_id>/raw/` 原始文件
  - `storage/docs/<collection_id>/<doc_id>/parsed/` 解析产物（`content.txt`、`toc.json`、`segments.json`、`keywords.json`）
- 数据库（SQLite）：`collections`、`documents`、`chunks` 等表，记录文档元信息与向量化状态。
- 向量库：Weaviate，封装于 `src/weaviate/weaviateEngine.py` 与 `api/weaivateApi.py`。

## 测试（后端）

- 示例测试位于 `py-backend/tests/`，部分测试依赖真实 Token 与可用的 Weaviate 服务。
- 运行示例：

```bash
python py-backend/tests/test_embedding_pipeline.py
python py-backend/tests/test_weaviate_engine.py
```

> 请在本地 `.env.development` 中配置必需的 Token 与连接参数，避免将真实凭证提交到仓库。

## 开发与部署建议

- 保持 `.env*` 文件与 `storage/` 目录在版本控制中忽略（仓库已配置 `.gitignore`）。
- 前端的所有敏感信息必须由后端读取与持有（不要放入 `VITE_` 变量）。
- 生产环境建议：
  - 为后端部署反向代理与 TLS，限制接口暴露范围
  - 将 SQLite 迁移到托管数据库（如 Postgres/MySQL）并加上更细的索引策略
  - 将 `storage/` 迁移到对象存储（OSS/S3），通过配置项设置基路径

## 许可

本项目仅作为演示用示例代码，未附带许可证文件。若需明确许可证，请在仓库中添加相应的 LICENSE 文件。