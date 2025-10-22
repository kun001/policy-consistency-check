import React, { useState, useEffect } from 'react';
import { Card, List, Typography, Tag, Space, Input, Select, Spin, Empty, Button, message } from 'antd';
import { SearchOutlined, FileTextOutlined, CalendarOutlined, TagOutlined } from '@ant-design/icons';
import { getNationalPolicyData, transformDifyDataToPolicyFormat } from '../api/weaviateApi';
import PolicyDetail from './PolicyDetail';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;
const { Option } = Select;

const PolicyLibrary = () => {
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [policies, setPolicies] = useState([]);
  const [error, setError] = useState(null);
  const [currentView, setCurrentView] = useState('list'); // 'list' or 'detail'
  const [selectedPolicy, setSelectedPolicy] = useState(null);

  // 获取国家政策文件知识库中的文件
  const loadPolicyData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const { dataset, documents } = await getNationalPolicyData();
      const transformedPolicies = transformDifyDataToPolicyFormat(dataset, documents);
      
      setPolicies(transformedPolicies);
      
      if (transformedPolicies.length === 0) {
        message.warning('暂无政策文件数据');
      }
    } catch (err) {
      console.error('加载政策数据失败:', err);
      setError(err.message || '加载数据失败');
      message.error('加载政策数据失败，请稍后重试');
      setPolicies([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicyData();
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
    console.log('查看政策详情：', policy);
    setSelectedPolicy(policy);
    setCurrentView('detail');
  };

  const handleBackToList = () => {
    setCurrentView('list');
    setSelectedPolicy(null);
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

  // 新增：上传解析视图
  if (currentView === 'upload') {
    const NationalPolicyUpload = React.lazy(() => import('./NationalPolicyUpload'));
    return (
      <React.Suspense fallback={<div className="text-center py-12">加载上传解析组件...</div>}>
        <NationalPolicyUpload onBack={handleBackToList} />
      </React.Suspense>
    );
  }

  // 否则显示政策列表
  return (
    <div className="space-y-6">
      {/* 搜索和筛选区域 */}
      <Card>
        <Space direction="vertical" size="middle" className="w-full">
          <div className="flex gap-4">
            <Search
              placeholder="搜索政策文件..."
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
              共找到 {filteredPolicies.length} 个政策文件
            </Text>
            <Button type="primary" onClick={() => setCurrentView('upload')}>
              上传解析国家文件
            </Button>
          </div>
        </Space>
      </Card>

      {/* 政策列表 */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12">
            <Spin size="large" />
            <p className="mt-4 text-gray-500">正在加载政策文件...</p>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <Empty description={error} />
            <div className="mt-4">
              <Button type="primary" onClick={loadPolicyData}>
                重新加载
              </Button>
            </div>
          </div>
        ) : filteredPolicies.length === 0 ? (
          <Empty description="暂无政策文件" />
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
                    <Tag color="blue">{policy.category}</Tag>
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
                  <div className="text-2xl font-bold text-blue-600">{policy.chunks}</div>
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

export default PolicyLibrary;