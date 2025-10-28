// 统一读取并导出前端可配置项（通过 Vite 环境变量）
// 注意：所有以 VITE_ 开头的变量均会被暴露到客户端，勿放敏感信息

const env = import.meta.env || {};

// 可选：后端完整 Origin（如 https://api.example.com），默认空字符串表示同源
export const API_BASE_URL = env.VITE_API_BASE_URL || '';
// 路径前缀（与后端路由 /api 对齐）
export const API_BASE_PREFIX = env.VITE_API_BASE_PREFIX || '/api';

// 拼接后的基础前缀，供 fetch 使用
export const BASE_PREFIX = `${API_BASE_URL}${API_BASE_PREFIX}`;

// 数据集标识（与后端集合名称一致）
export const TARGET_DATASET_ID = env.VITE_TARGET_DATASET_ID || 'national_policy_documents';
export const LOCAL_DATASET_ID = env.VITE_LOCAL_DATASET_ID || 'policy_documents';