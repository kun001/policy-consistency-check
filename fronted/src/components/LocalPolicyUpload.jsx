import React, { useState } from 'react';
import { Card, Typography, Space, Button, Upload, message, Input, Divider } from 'antd';
import { ArrowLeftOutlined, UploadOutlined, FileMarkdownOutlined, FileTextOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import { recognizeDocument, extractMarkdown } from '../api/textinApi';

const { Title, Paragraph, Text } = Typography;

const defaultCredentials = {
  appId: '69bad75362e19a06c1cbbcc85cb41db0',
  secretCode: '560544972179686676b68a8e67efc0f2',
};

const defaultOptions = {
  table_flavor: 'md',
  get_image: 'objects',
  paratext_mode: 'none',
  markdown_details: 0,
  crop_dewarp: 0,
  remove_watermark: 1,
  apply_chart: 1,
};

const LocalPolicyUpload = ({ onBack }) => {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [markdown, setMarkdown] = useState('');
  const [markdownCollapsed, setMarkdownCollapsed] = useState(true);
  const [options, setOptions] = useState(defaultOptions);

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

      const resText = await recognizeDocument(file, options, defaultCredentials);
      setResponseText(resText);
      const md = extractMarkdown(resText);
      setMarkdown(md);
      if (!md) {
        message.info('解析成功，但未返回 markdown 字段');
      } else {
        message.success('解析成功，已生成 Markdown');
      }
    } catch (err) {
      console.error(err);
      message.error(`解析失败：${err.message || '未知错误'}`);
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
              <Button icon={<FileTextOutlined />} onClick={() => downloadText(responseText, 'result.json')}>
                下载原始响应
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

        <Divider />

        <Title level={4}>请求参数（可选）</Title>
        <Space direction="vertical" className="w-full">
          <div className="flex gap-4">
            <div className="flex-1">
              <Text>table_flavor</Text>
              <Input value={options.table_flavor} onChange={(e) => setOptions({ ...options, table_flavor: e.target.value })} />
            </div>
            <div className="flex-1">
              <Text>get_image</Text>
              <Input value={options.get_image} onChange={(e) => setOptions({ ...options, get_image: e.target.value })} />
            </div>
            <div className="flex-1">
              <Text>paratext_mode</Text>
              <Input value={options.paratext_mode} onChange={(e) => setOptions({ ...options, paratext_mode: e.target.value })} />
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <Text>markdown_details</Text>
              <Input type="number" value={options.markdown_details} onChange={(e) => setOptions({ ...options, markdown_details: Number(e.target.value) })} />
            </div>
            <div className="flex-1">
              <Text>crop_dewarp</Text>
              <Input type="number" value={options.crop_dewarp} onChange={(e) => setOptions({ ...options, crop_dewarp: Number(e.target.value) })} />
            </div>
            <div className="flex-1">
              <Text>remove_watermark</Text>
              <Input type="number" value={options.remove_watermark} onChange={(e) => setOptions({ ...options, remove_watermark: Number(e.target.value) })} />
            </div>
            <div className="flex-1">
              <Text>apply_chart</Text>
              <Input type="number" value={options.apply_chart} onChange={(e) => setOptions({ ...options, apply_chart: Number(e.target.value) })} />
            </div>
          </div>
        </Space>
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

      {/* {responseText && (
        <Card title="完整 JSON 响应">
          <pre style={{ whiteSpace: 'pre-wrap' }}>{responseText}</pre>
        </Card>
      )} */}
    </div>
  );
};

export default LocalPolicyUpload;