import React, { useState, useEffect } from 'react';
import { Card, List, Typography, Tag, Space, Input, Select, Spin, Empty, Button, message } from 'antd';
import { SearchOutlined, FileTextOutlined, CalendarOutlined, TagOutlined } from '@ant-design/icons';
import { getLocalPolicyData, transformLocalDifyDataToPolicyFormat } from '../api/weaviateApi';
import PolicyDetail from './PolicyDetail';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { Option } = Select;

const LocalPolicyLibrary = () => {
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [policies, setPolicies] = useState([]);
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState('list'); // 'list' | 'detail' | 'upload'
  const [selectedPolicy, setSelectedPolicy] = useState(null);
  const [uploadVisible, setUploadVisible] = useState(false);


  // 加载地方政策数据
  const loadLocalPolicyData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const { dataset, documents } = await getLocalPolicyData();
      console.log(dataset)
      const transformedPolicies = transformLocalDifyDataToPolicyFormat(dataset, documents);

      setPolicies(transformedPolicies);
      
      if (transformedPolicies.length === 0) {
        message.warning('暂无地方政策文件数据');
      }
    } catch (err) {
      console.error('加载地方政策数据失败:', err);
      setError(err.message || '加载数据失败');
      message.error('加载地方政策数据失败，请稍后重试');
      setPolicies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadLocalPolicyData();
  }, []);

  const filteredPolicies = policies.filter(policy => {
    const matchSearch = policy.title.toLowerCase().includes(searchText.toLowerCase()) ||
                       policy.summary.toLowerCase().includes(searchText.toLowerCase()) ||
                       policy.tags.some(tag => tag.toLowerCase().includes(searchText.toLowerCase()));
    const matchCategory = filterCategory === 'all' || policy.category === filterCategory;
    return matchSearch && matchCategory;
  });

  const categories = ['all', ...new Set(policies.map(p => p.category))];

  const handlePolicyClick = (policy) => {
    console.log('查看地方政策详情：', policy);
    setSelectedPolicy(policy);
    setCurrentView('detail');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setSelectedPolicy(null);
  };

  // 文件上传配置
  const uploadProps = {
    name: 'file',
    multiple: true,
    accept: '.pdf,.doc,.docx,.txt',
    beforeUpload: (file) => {
      const isValidType = file.type === 'application/pdf' || 
                         file.type === 'application/msword' || 
                         file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                         file.type === 'text/plain';
      if (!isValidType) {
        message.error('只能上传 PDF、Word 或 TXT 格式的文件！');
        return false;
      }
      const isLt10M = file.size / 1024 / 1024 < 10;
      if (!isLt10M) {
        message.error('文件大小不能超过 10MB！');
        return false;
      }
      return false; // 阻止自动上传，等待后端接口实现
    },
    onDrop(e) {
      console.log('拖拽上传文件', e.dataTransfer.files);
    },
    onChange(info) {
      const { status } = info.file;
      if (status === 'done') {
        message.success(`${info.file.name} 文件上传成功`);
        // TODO: 刷新政策列表
        loadLocalPolicyData();
      } else if (status === 'error') {
        message.error(`${info.file.name} 文件上传失败`);
      }
    },
  };

  // 如果当前视图是详情页面，显示PolicyDetail组件
  if (currentView === 'detail') {
    return (
      <PolicyDetail 
        policy={selectedPolicy} 
        onBack={handleBackToList}
      />
    );
  }

  if (currentView === 'upload') {
    const LocalPolicyUpload = React.lazy(() => import('./LocalPolicyUpload'));
    return (
      <React.Suspense fallback={<div className="text-center py-12">加载上传解析组件...</div>}>
        <LocalPolicyUpload onBack={handleBackToList} />
      </React.Suspense>
    );
  }

  // 否则显示地方政策列表
  return (
    <div className="space-y-6">
      {/* 搜索和筛选区域 */}
      <Card>
        <Space direction="vertical" size="middle" className="w-full">
          <div className="flex gap-4">
            <Search
              placeholder="搜索地方政策文件..."
              allowClear
              enterButton={<SearchOutlined />}
              size="large"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              className="flex-1"
            />
            <Select
              value={filterCategory}
              onChange={setFilterCategory}
              size="large"
              style={{ width: 200 }}
            >
              <Option value="all">全部分类</Option>
              {categories.slice(1).map(category => (
                <Option key={category} value={category}>{category}</Option>
              ))}
            </Select>
          </div>
          
          <div className="flex justify-between items-center">
            <Text type="secondary">
              共找到 {filteredPolicies.length} 个地方政策文件
            </Text>
            <Button type="primary" onClick={() => setCurrentView('upload')}>
              上传解析地方文件
            </Button>
          </div>
        </Space>
      </Card>

      {/* 政策列表 */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12">
            <Spin size="large" />
            <p className="mt-4 text-gray-500">正在加载地方政策文件...</p>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <Empty description={error} />
            <div className="mt-4">
              <Button type="primary" onClick={loadLocalPolicyData}>
                重新加载
              </Button>
            </div>
          </div>
        ) : filteredPolicies.length === 0 ? (
          <Empty description="暂无地方政策文件" />
        ) : (
          filteredPolicies.map(policy => (
            <Card
              key={policy.id}
              hoverable
              className="policy-card"
              onClick={() => handlePolicyClick(policy)}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Title level={4} className="mb-0">{policy.title}</Title>
                    <Tag color="orange">{policy.category}</Tag>
                    <Tag color="purple">地方政策</Tag>
                    <Tag color="green">已分块 {policy.chunks}</Tag>
                  </div>
                  
                  <Paragraph ellipsis={{ rows: 2 }} className="text-gray-600 mb-3">
                    {policy.summary}
                  </Paragraph>
                  
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    <Space>
                      <CalendarOutlined />
                      <Text type="secondary">{policy.date}</Text>
                    </Space>
                    <Space>
                      <TagOutlined />
                      {policy.tags.map(tag => (
                        <Tag key={tag} size="small">{tag}</Tag>
                      ))}
                    </Space>
                  </div>
                </div>
                
                <div className="text-right">
                  <div className="text-2xl font-bold text-orange-600">{policy.chunks}</div>
                  <div className="text-xs text-gray-500">分块数量</div>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default LocalPolicyLibrary;