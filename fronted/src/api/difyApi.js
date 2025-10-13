// Dify知识库API服务
const DIFY_BASE_URL = 'http://180.184.42.136/v1';
const DATASET_API_KEY = 'dataset-9narIk3OvvyO2rviVOhDk6cf';
const TARGET_DATASET_ID = 'a30efafb-f076-4c30-af65-57d1bd335a23'; // 国家政策知识库
const LOCAL_DATASET_ID = 'aba7c075-ed0f-4f55-9de2-55efb78e6a94'; // 地方政策知识库

// 通用请求配置
const createRequestConfig = () => ({
  headers: {
    'Authorization': `Bearer ${DATASET_API_KEY}`,
    'Content-Type': 'application/json',
  },
});

// 获取知识库列表
export const getDatasets = async () => {
  try {
    const response = await fetch(`${DIFY_BASE_URL}/datasets`, createRequestConfig());
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('获取知识库列表失败:', error);
    throw error;
  }
};

// 获取指定知识库的文档列表
export const getDatasetDocuments = async (datasetId = TARGET_DATASET_ID) => {
  try {
    const response = await fetch(
      `${DIFY_BASE_URL}/datasets/${datasetId}/documents`,
      createRequestConfig()
    );
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('获取文档列表失败:', error);
    throw error;
  }
};

// 获取知识库文档的所有分段详细信息
export const getDatasetDocumentSegments = async (datasetId, documentId) => {
  try {
    if (!datasetId || !documentId) {
      throw new Error('datasetId 和 documentId 为必填参数');
    }
    const response = await fetch(
      `${DIFY_BASE_URL}/datasets/${datasetId}/documents/${documentId}/segments?limit=100`,
      createRequestConfig(),
    );

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;

  } catch (error) {
    console.error('获取文档分段失败:', error);
    throw error;
  }
};

// 获取国家政策知识库信息和文档
// chunks的获取有limit和page的限制，目前限制为最多单页100条
export const getNationalPolicyData = async () => {
  try {
    // 获取知识库列表
    const datasetsResponse = await getDatasets();
    
    // 找到国家政策知识库
    const nationalPolicyDataset = datasetsResponse.data?.find(
      dataset => dataset.id === TARGET_DATASET_ID
    );
    
    if (!nationalPolicyDataset) {
      throw new Error('未找到国家政策知识库');
    }
    
    // 获取该知识库的文档列表
    const documentsResponse = await getDatasetDocuments(TARGET_DATASET_ID);
    const documents = documentsResponse.data || [];
    
    // 为每个文档获取分段信息
    const documentsWithSegments = await Promise.all(
      documents.map(async (doc) => {
        try {
          const segmentsResponse = await getDatasetDocumentSegments(TARGET_DATASET_ID, doc.id);
          return {
            ...doc,
            segments: segmentsResponse.data || []
          };
        } catch (error) {
          console.warn(`获取文档 ${doc.id} 的分段信息失败:`, error);
          return {
            ...doc,
            segments: []
          };
        }
      })
    );
    
    return {
      dataset: nationalPolicyDataset,
      documents: documentsWithSegments
    };
  } catch (error) {
    console.error('获取国家政策数据失败:', error);
    throw error;
  }
};

// 数据转换函数：将dify数据转换为前端组件需要的格式
export const transformDifyDataToPolicyFormat = (dataset, documents) => {
  return documents.map((doc, index) => {
    const uploadFile = doc.data_source_detail_dict?.upload_file;
    const fileName = uploadFile?.name || `政策文件 ${index + 1}`;
    const fileNameWithoutExt = fileName.replace(/\.[^/.]+$/, '');
    
    // 根据文件名智能推断分类
    const getCategory = (name) => {
      const lowerName = name.toLowerCase();
      if (lowerName.includes('规划') || lowerName.includes('计划')) return '发展规划';
      if (lowerName.includes('经济') || lowerName.includes('产业')) return '产业政策';
      if (lowerName.includes('环境') || lowerName.includes('碳') || lowerName.includes('绿色')) return '环境政策';
      if (lowerName.includes('数字') || lowerName.includes('信息') || lowerName.includes('网络')) return '数字政策';
      if (lowerName.includes('电力') || lowerName.includes('能源')) return '能源政策';
      if (lowerName.includes('市场') || lowerName.includes('披露')) return '市场监管';
      if (lowerName.includes('金融') || lowerName.includes('银行')) return '金融政策';
      return '国家政策';
    };
    
    // 根据文件名生成相关标签
    const generateTags = (name) => {
      const lowerName = name.toLowerCase();
      const tags = [];
      
      if (lowerName.includes('规划')) tags.push('规划');
      if (lowerName.includes('发展')) tags.push('发展');
      if (lowerName.includes('经济')) tags.push('经济');
      if (lowerName.includes('市场')) tags.push('市场');
      if (lowerName.includes('信息')) tags.push('信息');
      if (lowerName.includes('披露')) tags.push('披露');
      if (lowerName.includes('电力')) tags.push('电力');
      if (lowerName.includes('能源')) tags.push('能源');
      if (lowerName.includes('基本规则')) tags.push('基本规则');
      if (lowerName.includes('管理')) tags.push('管理');
      
      // 添加文件类型标签
      if (uploadFile?.extension) {
        tags.push(uploadFile.extension.toUpperCase());
      }
      
      tags.push('政策文件');
      return [...new Set(tags)]; // 去重
    };
    
    // 获取真实的分段数量
    const getRealChunksCount = (segments) => {
      if (!segments || !Array.isArray(segments)) return 0;
      // 只统计状态为 'completed' 且启用的分段
      return segments.filter(segment => 
        segment.status === 'completed' && segment.enabled
      ).length;
    };
    
    // 计算总字数（基于所有分段）
    const getTotalWordCount = (segments) => {
      if (!segments || !Array.isArray(segments)) return 0;
      return segments
        .filter(segment => segment.status === 'completed' && segment.enabled)
        .reduce((total, segment) => total + (segment.word_count || 0), 0);
    };
    
    const realChunks = getRealChunksCount(doc.segments);
    const totalWords = getTotalWordCount(doc.segments);
    
    return {
      id: doc.id,
      title: fileNameWithoutExt,
      category: getCategory(fileNameWithoutExt),
      date: uploadFile?.created_at 
        ? new Date(uploadFile.created_at * 1000).toISOString().split('T')[0]
        : new Date().toISOString().split('T')[0],
      status: 'active',
      chunks: realChunks, // 使用真实的分段数量
      summary: `${fileNameWithoutExt}的相关政策文件，来自${dataset.name}。共${realChunks}个分段，总计${totalWords}字。`,
      tags: generateTags(fileNameWithoutExt),
      // 保留原始数据以备后用
      originalData: {
        document: doc,
        uploadFile: uploadFile,
        dataset: dataset,
        segments: doc.segments // 保存分段信息
      }
    };
  });
};

// 获取地方政策知识库信息和文档（包含分段信息）
export const getLocalPolicyData = async (fetchSegments = true) => {
  try {
    // 获取知识库列表
    const datasetsResponse = await getDatasets();

    // 找到地方政策知识库
    const localPolicyDataset = datasetsResponse.data?.find(
      dataset => dataset.id === LOCAL_DATASET_ID
    );

    if (!localPolicyDataset) {
      throw new Error('未找到地方政策知识库');
    }

    // 获取该知识库的文档列表
    const documentsResponse = await getDatasetDocuments(LOCAL_DATASET_ID);
    const documents = documentsResponse.data || [];

    // 根据参数决定是否获取分段信息
    if (!fetchSegments) {
      console.warn('⚠️ 跳过分段信息获取（权限限制或手动禁用）');
      return {
        dataset: localPolicyDataset,
        documents: documents.map(doc => ({ ...doc, segments: [] }))
      };
    }

    // 为每个文档获取分段信息
    let segmentsFetchFailed = false;
    const documentsWithSegments = await Promise.all(
      documents.map(async (doc) => {
        try {
          const segmentsResponse = await getDatasetDocumentSegments(LOCAL_DATASET_ID, doc.id);
          return {
            ...doc,
            segments: segmentsResponse.data || []
          };
        } catch (error) {
          // 如果是404错误，说明权限不足
          if (error.message.includes('404') || error.message.includes('NOT FOUND')) {
            segmentsFetchFailed = true;
            console.error(`❌ 文档 ${doc.id} 分段获取失败(404): API Key 可能没有访问私有知识库分段的权限`);
          } else {
            console.warn(`获取文档 ${doc.id} 的分段信息失败:`, error);
          }
          return {
            ...doc,
            segments: []
          };
        }
      })
    );

    // 如果所有分段都获取失败，给出警告
    if (segmentsFetchFailed) {
      console.warn('⚠️ 地方政策知识库分段获取失败，可能的原因：');
      console.warn('调用URL错误或dataset url错误 ');
    }

    return {
      dataset: localPolicyDataset,
      documents: documentsWithSegments
    };
  } catch (error) {
    console.error('获取地方政策数据失败:', error);
    throw error;
  }
};

// 数据转换函数：将地方政策dify数据转换为前端组件需要的格式
export const transformLocalDifyDataToPolicyFormat = (dataset, documents) => {
  return documents.map((doc, index) => {
    const uploadFile = doc.data_source_detail_dict?.upload_file;
    const fileName = uploadFile?.name || `地方政策文件 ${index + 1}`;
    const fileNameWithoutExt = fileName.replace(/\.[^/.]+$/, '');
    
    // 根据文件名智能推断地方政策分类
    const getLocalCategory = (name) => {
      const lowerName = name.toLowerCase();
      if (lowerName.includes('北京') || lowerName.includes('上海') || lowerName.includes('广东') || lowerName.includes('深圳')) return '一线城市政策';
      return '地方政策';
    };
    
    // 根据文件名生成地方政策相关标签
    const generateLocalTags = (name) => {
      const lowerName = name.toLowerCase();
      const tags = [];
      
      // 地区标签
      if (lowerName.includes('北京')) tags.push('北京市');
      if (lowerName.includes('上海')) tags.push('上海市');
      if (lowerName.includes('广东')) tags.push('广东省');
      if (lowerName.includes('深圳')) tags.push('深圳市');
      if (lowerName.includes('杭州')) tags.push('杭州市');
      if (lowerName.includes('成都')) tags.push('成都市');
      
      // 政策类型标签
      if (lowerName.includes('条例')) tags.push('条例');
      if (lowerName.includes('规划')) tags.push('规划');
      if (lowerName.includes('方案')) tags.push('方案');
      if (lowerName.includes('办法')) tags.push('办法');
      if (lowerName.includes('意见')) tags.push('意见');
      if (lowerName.includes('通知')) tags.push('通知');
      
      // 领域标签
      if (lowerName.includes('数字经济')) tags.push('数字经济');
      if (lowerName.includes('人工智能')) tags.push('人工智能');
      if (lowerName.includes('数据')) tags.push('数据要素');
      if (lowerName.includes('产业')) tags.push('产业发展');
      
      // 添加文件类型标签
      if (uploadFile?.extension) {
        tags.push(uploadFile.extension.toUpperCase());
      }
      
      tags.push('地方政策');
      return [...new Set(tags)]; // 去重
    };
    
    // 获取真实的分段数量
    const getRealChunksCount = (segments) => {
      if (!segments || !Array.isArray(segments)) return 0;
      return segments.filter(segment => 
        segment.status === 'completed' && segment.enabled
      ).length;
    };
    
    // 计算总字数（基于所有分段）
    const getTotalWordCount = (segments) => {
      if (!segments || !Array.isArray(segments)) return 0;
      return segments
        .filter(segment => segment.status === 'completed' && segment.enabled)
        .reduce((total, segment) => total + (segment.word_count || 0), 0);
    };
    
    const realChunks = getRealChunksCount(doc.segments);
    const totalWords = getTotalWordCount(doc.segments);
    
    return {
      id: doc.id,
      title: fileNameWithoutExt,
      category: getLocalCategory(fileNameWithoutExt),
      date: uploadFile?.created_at 
        ? new Date(uploadFile.created_at * 1000).toISOString().split('T')[0]
        : new Date().toISOString().split('T')[0],
      status: 'active',
      chunks: realChunks, // 使用真实的分段数量
      summary: `${fileNameWithoutExt}的相关地方政策文件，来自${dataset.name}。共${realChunks}个分段，总计${totalWords}字。`,
      tags: generateLocalTags(fileNameWithoutExt),
      source: 'local',
      // 保留原始数据以备后用
      originalData: {
        document: doc,
        uploadFile: uploadFile,
        dataset: dataset,
        segments: doc.segments // 保存分段信息
      }
    };
  });
};

// 导出常量
export { TARGET_DATASET_ID, LOCAL_DATASET_ID, DIFY_BASE_URL };