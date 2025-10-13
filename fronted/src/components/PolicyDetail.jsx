// PolicyDetail 组件
import React, { useState, useEffect } from 'react';
import { Card, Typography, Tag, Space, Input, Button, Spin, Empty, message, Divider, Statistic, Row, Col, Tooltip } from 'antd';
import { ArrowLeftOutlined, SearchOutlined, FileTextOutlined, ClockCircleOutlined, NumberOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { getDatasetDocumentSegments, LOCAL_DATASET_ID, TARGET_DATASET_ID } from '../api/difyApi';

const { Title, Text, Paragraph } = Typography;
const { Search } = Input;

const PolicyDetail = ({ policy, onBack }) => {
  const [loading, setLoading] = useState(false);
  const [segments, setSegments] = useState([]);
  const [searchText, setSearchText] = useState('');
  const [error, setError] = useState(null);

  // 加载政策文档的分段数据（支持轻量复用）
  const loadSegments = async (force = false) => {
    if (!policy?.id) {
      setError('无效的政策文档ID');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const datasetIdForDoc =
        policy?.originalData?.document?.dataset_id ||
        policy?.originalData?.dataset?.id ||
        (policy?.source === 'local' ? LOCAL_DATASET_ID : TARGET_DATASET_ID);

      // 轻量复用：优先使用列表中的分段（非强制刷新时）
      const cachedSegments = Array.isArray(policy?.originalData?.segments) ? policy.originalData.segments : [];
      if (!force && cachedSegments.length > 0) {
        const sortedCached = [...cachedSegments].sort((a, b) => a.position - b.position);
        setSegments(sortedCached);
        setLoading(false);
        return;
      }

      const response = await getDatasetDocumentSegments(datasetIdForDoc, policy.id);
      const segmentsData = response.data || [];

      // 按位置排序
      const sortedSegments = segmentsData.sort((a, b) => a.position - b.position);
      setSegments(sortedSegments);

      if (sortedSegments.length === 0) {
        message.warning('该文档暂无分段数据');
      }
    } catch (err) {
      console.error('加载分段数据失败:', err);
      setError(err.message || '加载分段数据失败');
      message.error('加载分段数据失败，请稍后重试');
      setSegments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // 进入详情或切换文档时，尝试轻量复用；若无缓存则拉取
    loadSegments(false);
  }, [policy?.id]);

  // 筛选分段
  const filteredSegments = segments.filter(segment => {
    if (!searchText) return true;
    return segment.content.toLowerCase().includes(searchText.toLowerCase());
  });

  // 计算统计信息
  const stats = {
    totalSegments: segments.length,
    completedSegments: segments.filter(s => s.status === 'completed').length,
    totalWords: segments.reduce((sum, s) => sum + (s.word_count || 0), 0),
    totalTokens: segments.reduce((sum, s) => sum + (s.tokens || 0), 0)
  };

  // 格式化时间
  const formatTime = (timestamp) => {
    if (!timestamp) return '未知';
    return new Date(timestamp * 1000).toLocaleString('zh-CN');
  };

  // 获取状态标签颜色
  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'green';
      case 'processing': return 'blue';
      case 'error': return 'red';
      default: return 'default';
    }
  };

  // 获取状态文本
  const getStatusText = (status) => {
    switch (status) {
      case 'completed': return '已完成';
      case 'processing': return '处理中';
      case 'error': return '错误';
      default: return '未知';
    }
  };

  if (!policy) {
    return (
      <div className="text-center py-12">
        <Empty description="未选择政策文档" />
        <Button type="primary" onClick={onBack} className="mt-4">
          返回列表
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* 头部信息 */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={onBack}
            type="text"
            size="large"
          >
            返回列表
          </Button>
          <Space>
            <Button type="primary" icon={<FileTextOutlined />}>
              导出分段
            </Button>
          </Space>
        </div>
        
        <div className="mb-6">
          <Title level={2} className="mb-2">{policy.title}</Title>
          <Space size="middle" wrap>
            <Tag color="blue" className="text-sm px-3 py-1">{policy.category}</Tag>
            <Tag color="green" className="text-sm px-3 py-1">共 {stats.totalSegments} 个分段</Tag>
            <Text type="secondary">
              <ClockCircleOutlined className="mr-1" />
              {policy.date}
            </Text>
          </Space>
        </div>

        {/* 统计信息 */}
        <Row gutter={16} className="mb-6">
          <Col span={6}>
            <Statistic 
              title="总分段数" 
              value={stats.totalSegments} 
              prefix={<NumberOutlined />}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="已完成" 
              value={stats.completedSegments} 
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="总字数" 
              value={stats.totalWords}
              suffix="字"
            />
          </Col>
          <Col span={6}>
            <Statistic 
              title="总Token数" 
              value={stats.totalTokens}
              suffix="tokens"
            />
          </Col>
        </Row>

        {/* 搜索框 */}
        <Search
          placeholder="搜索分段内容..."
          allowClear
          enterButton={<SearchOutlined />}
          size="large"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          className="mb-4"
        />
        
        <Text type="secondary">
          显示 {filteredSegments.length} / {segments.length} 个分段
        </Text>
      </Card>

      {/* 分段列表 */}
      <div className="space-y-4">
        {loading ? (
          <div className="text-center py-12">
            <Spin size="large" />
            <p className="mt-4 text-gray-500">正在加载分段数据...</p>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <Empty description={error} />
            <div className="mt-4">
              <Button type="primary" onClick={loadSegments}>
                重新加载
              </Button>
            </div>
          </div>
        ) : filteredSegments.length === 0 ? (
          <Empty description={searchText ? "未找到匹配的分段" : "暂无分段数据"} />
        ) : (
          filteredSegments.map((segment, index) => (
            <Card
              key={segment.id}
              className="segment-card"
              size="small"
            >
              <div className="flex justify-between items-start mb-3">
                <div className="flex items-center gap-2">
                  <Tag color="blue">第 {segment.position} 段</Tag>
                  <Tag color={getStatusColor(segment.status)}>
                    {getStatusText(segment.status)}
                  </Tag>
                  {!segment.enabled && (
                    <Tag color="red">已禁用</Tag>
                  )}
                </div>
                <div className="text-right text-sm text-gray-500">
                  <div>{segment.word_count || 0} 字</div>
                  <div>{segment.tokens || 0} tokens</div>
                </div>
              </div>
              
              <Paragraph className="text-gray-800 leading-relaxed mb-3">
                {segment.content}
              </Paragraph>
              
              <Divider className="my-3" />
              
              <div className="flex justify-between items-center text-xs text-gray-500">
                <Space size="large">
                  <span>创建时间: {formatTime(segment.created_at)}</span>
                  <span>更新时间: {formatTime(segment.updated_at)}</span>
                  {segment.hit_count > 0 && (
                    <span>命中次数: {segment.hit_count}</span>
                  )}
                </Space>
                <Tooltip title={`分段ID: ${segment.id}`}>
                  <Text code className="cursor-pointer">
                    {segment.id.substring(0, 8)}...
                  </Text>
                </Tooltip>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};

export default PolicyDetail;