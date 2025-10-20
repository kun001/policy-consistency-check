// Python 后端 API 封装
// 使用 Vite 代理至 http://localhost:10010，避免跨域

const BASE_PREFIX = '/api';

// 提交文档，后端一次性完成解析、切分、向量化与持久化
export async function ingestAndIndex(fileBlob, options = {}) {
  if (!fileBlob) throw new Error('未提供文件');
  const form = new FormData();
  form.append('file', fileBlob, fileBlob.name);
  if (options.collection_name) form.append('collection_name', options.collection_name);
  if (options.batch_size) form.append('batch_size', String(options.batch_size));
  if (options.max_retries) form.append('max_retries', String(options.max_retries));
  if (options.client_params) form.append('client_params', JSON.stringify(options.client_params));

  const resp = await fetch(`${BASE_PREFIX}/rag/ingest-and-index`, {
    method: 'POST',
    body: form,
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`上传并索引失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}

// 获取指定文档的解析产物（content/toc/counts/keywords）
export async function getParsedDocument(docId) {
  if (!docId) throw new Error('docId 为必填参数');
  const resp = await fetch(`${BASE_PREFIX}/rag/documents/${encodeURIComponent(docId)}/parsed`, {
    method: 'GET',
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`获取解析产物失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}

// 兼容旧的段落结构提取接口（仅保留以防其他页面使用）
export async function extractSegments(fileBlob, save = false) {
  if (!fileBlob) throw new Error('未提供文件');
  const form = new FormData();
  form.append('file', fileBlob, fileBlob.name);
  form.append('save', save ? 'true' : 'false');
  const resp = await fetch(`${BASE_PREFIX}/extract-segments`, {
    method: 'POST',
    body: form,
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`结构化提取失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}