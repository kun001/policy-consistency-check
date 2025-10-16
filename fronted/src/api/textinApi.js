// 智谱 BigModel 文档解析 API 封装（替换 TextIn）
// 警告：在前端直接使用密钥存在泄露风险和 CORS 风险，生产环境建议通过服务端代理。

const ZHIPU_UPLOAD_URL = 'https://open.bigmodel.cn/api/paas/v4/files/parser/create?file';
const ZHIPU_RESULT_BASE = 'https://open.bigmodel.cn/api/paas/v4/files/parser/result';

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function detectFileType(fileBlob) {
  const mime = fileBlob?.type || '';
  if (mime === 'application/pdf') return 'PDF';
  if (mime === 'application/msword') return 'DOC';
  if (mime === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') return 'DOCX';
  if (mime.startsWith('image/')) return 'IMAGE';
  return 'PDF'; // 默认按 PDF 处理（与示例一致）
}

// 上传文件并获取解析任务ID
async function zhipuCreateTask(fileBlob, token, toolType = 'lite') {
  const form = new FormData();
  form.append('file', fileBlob, fileBlob.name);
  form.append('tool_type', toolType);
  form.append('file_type', detectFileType(fileBlob));

  const resp = await fetch(ZHIPU_UPLOAD_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: form,
  });

  const data = await resp.json().catch(async () => ({ message: await resp.text() }));
  if (!resp.ok) {
    throw new Error(`上传失败(${resp.status}): ${data?.message || resp.statusText}`);
  }
  if (!data?.task_id) {
    throw new Error(`未返回任务ID: ${JSON.stringify(data)}`);
  }
  return data.task_id;
}

// 根据任务ID获取解析结果
async function zhipuGetResult(taskId, token) {
  const url = `${ZHIPU_RESULT_BASE}/${taskId}/text`;
  const resp = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const data = await resp.json().catch(async () => ({ message: await resp.text() }));
  if (!resp.ok) {
    throw new Error(`结果获取失败(${resp.status}): ${data?.message || resp.statusText}`);
  }
  return data; // { status, message, content, task_id, parsing_result_url }
}

// 识别并解析文件为文本内容（带最多3次重试）
export async function recognizeDocument(fileBlob, options = {}, credentials, maxRetries = 3, retryIntervalMs = 2000) {
  if (!fileBlob) throw new Error('未提供文件');
  const token = credentials?.token;
  if (!token) throw new Error('缺少智谱 Authorization Token');

  // 1) 创建解析任务
  const taskId = await zhipuCreateTask(fileBlob, token, 'lite');

  // 2) 轮询获取结果（最多重试3次）
  let lastResult = null;
  for (let attempt = 0; attempt < Math.max(1, maxRetries); attempt++) {
    lastResult = await zhipuGetResult(taskId, token);
    if (lastResult?.status === 'succeeded') {
      return lastResult;
    }
    if (lastResult?.status === 'failed') {
      throw new Error(`解析失败: ${lastResult?.message || '未知错误'}`);
    }
    // 继续等待下一次重试（如状态为 processing/pending 等）
    if (attempt < maxRetries - 1) {
      await delay(retryIntervalMs);
    }
  }

  // 重试结束仍未成功
  throw new Error(`解析结果未就绪，已重试${maxRetries}次`);
}

// 提取文本内容（从智谱结果对象或JSON字符串）
export function extractMarkdown(response) {
  try {
    if (!response) return '';
    if (typeof response === 'string') {
      const json = JSON.parse(response);
      return json?.content || '';
    }
    // 对象
    return response?.content || '';
  } catch (e) {
    return '';
  }
}