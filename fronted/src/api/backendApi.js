// Python 后端 API 封装
// 使用 Vite 代理至 http://localhost:10010，避免跨域

const BASE_PREFIX = '/api';

// 提取文档分段（结构化 TOC）
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