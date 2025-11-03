import { BASE_PREFIX, TARGET_DATASET_ID, LOCAL_DATASET_ID } from './config';
// 为保持对组件的兼容性，继续从本模块导出数据集常量
export { TARGET_DATASET_ID, LOCAL_DATASET_ID } from './config';

// 从文件名提取不带扩展的名称
const stripExt = (name = '') => name.replace(/\.[^/.]+$/, '');
const getExtTag = (name = '') => {
  const m = name.match(/\.([^.]+)$/);
  return m ? m[1].toUpperCase() : undefined;
};

// 拉取指定集合的文档列表
async function fetchDocuments(collectionName = TARGET_DATASET_ID) {
  const url = `${BASE_PREFIX}/rag/documents?collection_name=${encodeURIComponent(collectionName)}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`获取文档列表失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}

// 拉取指定文档的分段（chunks → segments 映射）
export async function getDatasetDocumentSegments(datasetId, documentId) {
  if (!documentId) throw new Error('documentId 为必填参数');
  const url = `${BASE_PREFIX}/rag/documents/${encodeURIComponent(documentId)}/chunks`;
  const resp = await fetch(url);
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`获取分段失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}

// 获取“国家政策”集合数据
export async function getNationalPolicyData() {
  const { dataset, documents } = await fetchDocuments(TARGET_DATASET_ID);
  return { dataset, documents };
}

// 获取“地方政策”集合数据
export async function getLocalPolicyData(fetchSegments = true) {
  const { dataset, documents } = await fetchDocuments(LOCAL_DATASET_ID);
  // 与原逻辑保持兼容：可选择不获取分段，返回空 segments 字段
  const docsWithSegments = (documents || []).map((doc) => ({ ...doc, segments: [] }));
  return { dataset, documents: docsWithSegments };
}

// 调用后端对比分析接口
export async function analyzePolicyComparison({ local_doc_id, national_doc_ids, limit = 2, collection_name }) {
  if (!local_doc_id) throw new Error('local_doc_id 为必填参数');
  if (!national_doc_ids || !Array.isArray(national_doc_ids) || national_doc_ids.length === 0) {
    throw new Error('national_doc_ids 为必填参数');
  }
  const url = `${BASE_PREFIX}/compare/analyze`;
  const payload = { local_doc_id, national_doc_ids, limit };
  if (collection_name) payload.collection_name = collection_name;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`政策对比分析失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}

// 将 SQLite 文档数据转换为组件所需格式
export const transformNationalPolicyData = (dataset, documents) => {
  return (documents || []).map((doc, index) => {
    const fileName = doc.source_filename || `政策文件 ${index + 1}`;
    const fileNameWithoutExt = stripExt(fileName);

    const getCategory = (name) => {
      const lowerName = name.toLowerCase();
      if (lowerName.includes('规划') || lowerName.includes('计划')) return '发展规划';
      if (lowerName.includes('经济') || lowerName.includes('产业')) return '产业政策';
      if (lowerName.includes('环境') || lowerName.includes('碳') || lowerName.includes('绿色')) return '环境政策';
      if (lowerName.includes('数字') || lowerName.includes('信息') || lowerName.includes('网络')) return '数字政策';
      if (lowerName.includes('环保') || lowerName.includes('环境')) return '环保政策';
      if (lowerName.includes('市场') || lowerName.includes('披露')) return '市场监管';
      if (lowerName.includes('金融') || lowerName.includes('银行')) return '金融政策';
      return '国家政策';
    };

    const generateTags = (name) => {
      const lowerName = name.toLowerCase();
      const tags = [];
      if (lowerName.includes('规划')) tags.push('规划');
      if (lowerName.includes('发展')) tags.push('发展');
      if (lowerName.includes('经济')) tags.push('经济');
      if (lowerName.includes('市场')) tags.push('市场');
      if (lowerName.includes('信息')) tags.push('信息');
      if (lowerName.includes('环保')) tags.push('环保');
      if (lowerName.includes('能源')) tags.push('能源');
      if (lowerName.includes('基本规则')) tags.push('基本规则');
      if (lowerName.includes('管理')) tags.push('管理');
      const extTag = getExtTag(fileName);
      if (extTag) tags.push(extTag);
      tags.push('政策文件');
      return [...new Set(tags)];
    };

    const chunkCount = (doc.parsing_payload && doc.parsing_payload.chunk_count) || 0;

    return {
      id: doc.id,
      title: fileNameWithoutExt,
      category: getCategory(fileNameWithoutExt),
      date: (doc.created_at ? new Date(doc.created_at).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]),
      status: doc.status || 'active',
      chunks: chunkCount,
      summary: `${fileNameWithoutExt}的相关政策文件，来自${dataset?.name || '政策知识库'}。共${chunkCount}个分段。`,
      tags: generateTags(fileNameWithoutExt),
      originalData: {
        document: doc,
        dataset: dataset,
        segments: doc.segments || [],
      },
    };
  });
};

// 地方政策的转换
export const transformLocalPolicyData = (dataset, documents) => {
  return (documents || []).map((doc, index) => {
    const fileName = doc.source_filename || `地方政策文件 ${index + 1}`;
    const fileNameWithoutExt = stripExt(fileName);

    const getLocalCategory = (name) => {
      const lowerName = name.toLowerCase();
      if (lowerName.includes('北京') || lowerName.includes('上海') || lowerName.includes('广东') || lowerName.includes('深圳')) return '一线城市政策';
      return '地方政策';
    };

    const generateLocalTags = (name) => {
      const lowerName = name.toLowerCase();
      const tags = [];
      if (lowerName.includes('北京')) tags.push('北京市');
      if (lowerName.includes('上海')) tags.push('上海市');
      if (lowerName.includes('广东')) tags.push('广东省');
      if (lowerName.includes('深圳')) tags.push('深圳市');
      if (lowerName.includes('杭州')) tags.push('杭州市');
      if (lowerName.includes('成都')) tags.push('成都市');
      if (lowerName.includes('条例')) tags.push('条例');
      if (lowerName.includes('规划')) tags.push('规划');
      if (lowerName.includes('方案')) tags.push('方案');
      if (lowerName.includes('办法')) tags.push('办法');
      if (lowerName.includes('意见')) tags.push('意见');
      if (lowerName.includes('通知')) tags.push('通知');
      if (lowerName.includes('数字经济')) tags.push('数字经济');
      if (lowerName.includes('人工智能')) tags.push('人工智能');
      if (lowerName.includes('数据')) tags.push('数据要素');
      if (lowerName.includes('产业')) tags.push('产业发展');
      const extTag = getExtTag(fileName);
      if (extTag) tags.push(extTag);
      tags.push('地方政策');
      return [...new Set(tags)];
    };

    const chunkCount = (doc.parsing_payload && doc.parsing_payload.chunk_count) || 0;

    return {
      id: doc.id,
      title: fileNameWithoutExt,
      category: getLocalCategory(fileNameWithoutExt),
      date: (doc.created_at ? new Date(doc.created_at).toISOString().split('T')[0] : new Date().toISOString().split('T')[0]),
      status: doc.status || 'active',
      chunks: chunkCount,
      summary: `${fileNameWithoutExt}的相关地方政策文件，来自${dataset?.name || '地方政策知识库'}。共${chunkCount}个分段。`,
      tags: generateLocalTags(fileNameWithoutExt),
      source: 'local',
      originalData: {
        document: doc,
        dataset: dataset,
        segments: doc.segments || [],
      },
    };
  });
};

// 可选：RAG 检索接口
export async function ragSearch({
  query,
  collection_name = TARGET_DATASET_ID,
  siliconflow_api_token,
  weaviate_api_key,
  client_params,
  limit = 10,
  filter_conditions,
  filters,
} = {}) {
  const url = `${BASE_PREFIX}/rag/search`;
  const payload = {
    query,
    collection_name,
    siliconflow_api_token,
    weaviate_api_key,
    client_params,
    limit,
    filter_conditions,
    filters,
  };
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => '');
    throw new Error(`RAG 检索失败(${resp.status}): ${text || resp.statusText}`);
  }
  return resp.json();
}