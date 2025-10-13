import axios from 'axios';

// TextIn 文档解析 API 封装
// 警告：在前端直接使用密钥存在泄露风险和 CORS 风险，生产环境建议通过服务端代理。

const TEXTIN_BASE_URL = 'https://api.textin.com/ai/service/v1/pdf_to_markdown';

// 将默认参数与用户输入参数合并
const defaultOptions = {
  table_flavor: 'md',
  get_image: 'objects',
  paratext_mode: 'none',
  markdown_details: 0,
  crop_dewarp: 0,
  remove_watermark: 1,
  apply_chart: 1,
};

// 识别并解析文件为 Markdown/JSON
export async function recognizeDocument(fileBlob, options = {}, credentials) {
  if (!fileBlob) throw new Error('未提供文件');

  const { appId, secretCode } = credentials || {};
  if (!appId || !secretCode) throw new Error('缺少 TextIn 授权信息');

  const mergedOptions = { ...defaultOptions, ...options };

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(mergedOptions)) {
    if (value !== undefined && value !== null) {
      params.append(key, value.toString());
    }
  }

  const url = `${TEXTIN_BASE_URL}${params.toString() ? '?' + params.toString() : ''}`;

  const arrayBuffer = await fileBlob.arrayBuffer();

  const response = await axios({
    method: 'post',
    url,
    data: arrayBuffer,
    headers: {
      'x-ti-app-id': appId,
      'x-ti-secret-code': secretCode,
      'Content-Type': 'application/octet-stream',
    },
    responseType: 'text',
  });

  return response.data; // 返回字符串形式的 JSON
}

// 从响应字符串中提取 markdown（若存在）
export function extractMarkdown(responseText) {
  try {
    const json = JSON.parse(responseText);
    return json?.result?.markdown || '';
  } catch (e) {
    return '';
  }
}