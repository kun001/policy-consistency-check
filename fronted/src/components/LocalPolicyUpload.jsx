import React, { useState } from 'react';
import { Card, Typography, Space, Button, Upload, message, Divider, Tag } from 'antd';
import { ArrowLeftOutlined, UploadOutlined, FileMarkdownOutlined, FileTextOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import { recognizeDocument, extractMarkdown } from '../api/textinApi';
import { extractSegments } from '../api/backendApi';
import TocViewer from './TocViewer';

const { Title, Paragraph, Text } = Typography;

// 智谱 BigModel 解析所需 Token（示例）
const defaultCredentials = {
  token: 'f3c226a18383452c8d5958519619e4bf.h35ddv1JmcoLarYe',
};

// 智谱接口不需要额外的可选解析参数

const LocalPolicyUpload = ({ onBack }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [markdown, setMarkdown] = useState('');
  const [markdownCollapsed, setMarkdownCollapsed] = useState(true);
  // 智谱解析无需 options 参数
  const [structured, setStructured] = useState(null); // 后端结构化响应
  const [selectedArticle, setSelectedArticle] = useState('');

  const PREVIEW_LINES = 8;
  const getCollapsedMarkdown = (text) => {
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
      setMarkdown('');
      setStructured(null);
      setSelectedArticle('');

      const resObj = await recognizeDocument(file, {}, defaultCredentials);
      setResponseText(JSON.stringify(resObj, null, 2));
      const md = extractMarkdown(resObj);
      setMarkdown(md);
      if (!md) {
        message.info('解析成功，但未返回 content 字段');
      } else {
        message.success('解析成功，已生成文档内容');
      }

      // 紧接着执行结构化提取
      const seg = await extractSegments(file, false);
      setStructured(seg);
      message.success('结构化提取成功');
    } catch (err) {
      console.error(err);
      message.error(`解析或结构化提取失败：${err.message || '未知错误'}`);
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
              解析文件
            </Button>
            {markdown && (
              <Button icon={<FileMarkdownOutlined />} onClick={() => downloadText(markdown, 'result.md')}>
                下载 Markdown
              </Button>
            )}
            {responseText && (
              <Button icon={<FileTextOutlined />} onClick={() => downloadText(responseText, 'textin.json')}>
                下载原始响应
              </Button>
            )}
            {structured && (
              <Button icon={<FileTextOutlined />} onClick={() => downloadText(JSON.stringify(structured, null, 2), 'structured.json')}>
                下载结构化JSON
              </Button>
            )}
          </Space>
        </div>

        <Title level={3}>上传并解析地方政策文件</Title>
        <Paragraph type="secondary">
          支持 PDF/图片等格式，解析为 Markdown 与结构化 JSON。
        </Paragraph>

        <Upload.Dragger beforeUpload={beforeUpload} maxCount={1} accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff">
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此处</p>
          <p className="ant-upload-hint">单次上传一个文件，最大 50MB</p>
        </Upload.Dragger>

        {/* 智谱接口不再需要额外的请求参数配置 */}
      </Card>

      {markdown && (() => {
        const { truncated, isTruncated } = getCollapsedMarkdown(markdown);
        const displayText = markdownCollapsed ? truncated + (isTruncated ? '\n…' : '') : markdown;
        return (
          <Card
            title="Markdown 预览"
            extra={
              <Button type="link" onClick={() => setMarkdownCollapsed(!markdownCollapsed)} icon={markdownCollapsed ? <DownOutlined /> : <UpOutlined />}>
                {markdownCollapsed ? '展开' : '收起'}
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

      {/* {responseText && (
        <Card title="完整 JSON 响应">
          <pre style={{ whiteSpace: 'pre-wrap' }}>{responseText}</pre>
        </Card>
      )} */}
    </div>
  );
};

export default LocalPolicyUpload;