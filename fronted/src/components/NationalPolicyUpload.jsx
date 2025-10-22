import React, { useState } from 'react';
import { Card, Typography, Space, Button, Upload, message, Tag } from 'antd';
import { ArrowLeftOutlined, UploadOutlined, FileTextOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import { ingestAndIndex, getParsedDocument } from '../api/backendApi';
import TocViewer from './TocViewer';

const { Title, Paragraph, Text } = Typography;

const NationalPolicyUpload = ({ onBack }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [contentPreview, setContentPreview] = useState('');
  const [contentCollapsed, setContentCollapsed] = useState(true);
  const [structured, setStructured] = useState(null); // 后端结构化响应（toc/counts/file）
  const [selectedArticle, setSelectedArticle] = useState('');

  const COLLECTION_NAME = 'national_policy_documents';
  const PREVIEW_LINES = 8;

  const getCollapsedText = (text) => {
    const lines = String(text || '').split('\n');
    const isTruncated = lines.length > PREVIEW_LINES;
    const truncated = lines.slice(0, PREVIEW_LINES).join('\n');
    return { truncated, isTruncated };
  };

  const beforeUpload = (f) => {
    setFile(f);
    return false; // 阻止自动上传
  };

  const handleParse = async () => {
    if (!file) {
      message.warning('请先选择文件');
      return;
    }

    try {
      setLoading(true);
      setResponseText('');
      setContentPreview('');
      setStructured(null);
      setSelectedArticle('');

      // 一次性上传并完成解析+切分+向量化+持久化（国家政策集合）
      const ingest = await ingestAndIndex(file, { collection_name: COLLECTION_NAME, batch_size: 8, max_retries: 2 });
      setResponseText(JSON.stringify(ingest, null, 2));
      message.success('上传并索引完成');

      // 拉取解析产物（正文、目录树、计数）
      const parsed = await getParsedDocument(ingest.doc_id);
      setStructured({ toc: parsed.toc, counts: parsed.counts, file: parsed.file });
      setContentPreview(parsed.content || '');
      message.success('解析产物获取成功');
    } catch (err) {
      console.error(err);
      message.error(`上传或解析失败：${err.message || '未知错误'}`);
    } finally {
      setLoading(false);
    }
  };

  const downloadText = (text, filename) => {
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between mb-4">
          <Button icon={<ArrowLeftOutlined />} onClick={onBack} type="text" size="large">
            返回列表
          </Button>
          <Space>
            <Button type="primary" icon={<UploadOutlined />} onClick={handleParse} loading={loading} disabled={!file}>
              上传并解析
            </Button>
            {responseText && (
              <Button icon={<FileTextOutlined />} onClick={() => downloadText(responseText, 'ingest-response.json')}>
                下载后端响应
              </Button>
            )}
            {structured && (
              <Button icon={<FileTextOutlined />} onClick={() => downloadText(JSON.stringify(structured, null, 2), 'parsed.json')}>
                下载解析产物
              </Button>
            )}
          </Space>
        </div>

        <Title level={3}>上传并解析国家政策文件</Title>
        <Paragraph type="secondary">
          支持 PDF/图片等格式，解析为正文与结构化 JSON（后端一次完成）。
        </Paragraph>

        <Upload.Dragger beforeUpload={beforeUpload} maxCount={1} accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff,.docx,.txt,.md">
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此处</p>
          <p className="ant-upload-hint">单次上传一个文件，最大 50MB</p>
        </Upload.Dragger>
      </Card>

      {contentPreview && (() => {
        const { truncated, isTruncated } = getCollapsedText(contentPreview);
        const displayText = contentCollapsed ? truncated + (isTruncated ? '\n…' : '') : contentPreview;
        return (
          <Card
            title="正文预览"
            extra={
              <Button type="link" onClick={() => setContentCollapsed(!contentCollapsed)} icon={contentCollapsed ? <DownOutlined /> : <UpOutlined />}>
                {contentCollapsed ? '展开' : '收起'}
              </Button>
            }
          >
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{displayText}</pre>
          </Card>
        );
      })()}

      {structured && (
        <Card title="结构化目录预览">
          <Space size="large" className="mb-4">
            <span>章节 <Tag color="blue">{structured.counts?.chapters ?? 0}</Tag></span>
            <span>节 <Tag color="green">{structured.counts?.sections ?? 0}</Tag></span>
            <span>条款 <Tag color="purple">{structured.counts?.articles ?? 0}</Tag></span>
          </Space>
          <TocViewer
            toc={structured.toc}
            fileName={structured.file?.name}
            onSelectArticle={(_node, text) => setSelectedArticle(text)}
          />
        </Card>
      )}

      {structured && (
        <Card title="条款详情">
          {selectedArticle ? (
            <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{selectedArticle}</pre>
          ) : (
            <div className="text-gray-500">点击目录中的条款以查看详细内容</div>
          )}
        </Card>
      )}
    </div>
  );
};

export default NationalPolicyUpload;