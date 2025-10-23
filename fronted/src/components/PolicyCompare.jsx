import React, { useState, useMemo, useEffect, useRef } from 'react';
import { Card, Typography, Space, Button, Select, Switch, Row, Col, Empty, Tag, Divider } from 'antd';
import { DiffOutlined, SyncOutlined, FileTextOutlined } from '@ant-design/icons';
import { getNationalPolicyData, getLocalPolicyData, transformDifyDataToPolicyFormat, transformLocalDifyDataToPolicyFormat, analyzePolicyComparison } from '../api/weaivateApi';

const { Title, Text, Paragraph } = Typography;

// 政策文件对比分析（一对多）：左侧地方条款列表，右侧国家条款映射 + AI 分析
const PANEL_HEIGHT = 'calc(100vh - 260px)';

const PolicyCompare = () => {
  const [localDoc, setLocalDoc] = useState(null); // 单选地方政策文件
  const [nationalDocs, setNationalDocs] = useState([]); // 多选国家政策文件
  const [showOnlyDiff, setShowOnlyDiff] = useState(true); // 默认只显示存在差异的条款
  const [visibleCount, setVisibleCount] = useState(4); // 默认展示4条
  const [compareResults, setCompareResults] = useState([]); // 后端返回的对比结果（按地方条款粒度）
  const [selectedClauseId, setSelectedClauseId] = useState(null); // 当前选中的地方条款
  const [expandedKeys, setExpandedKeys] = useState([]); // 左侧折叠面板展开项
  const [loadingLists, setLoadingLists] = useState(false); // 列表加载状态
  const [generating, setGenerating] = useState(false); // 生成对比结果状态

  const [localOptions, setLocalOptions] = useState([]);
  const [nationalOptions, setNationalOptions] = useState([]);

  const rightPanelRef = useRef(null);

  // 真实数据获取：加载地方与国家政策文件列表
  const loadPolicyLists = async () => {
    try {
      setLoadingLists(true);
      const [localResp, nationalResp] = await Promise.all([
        getLocalPolicyData(false), // 只拉列表
        getNationalPolicyData(),
      ]);

      const localPolicies = transformLocalDifyDataToPolicyFormat(localResp.dataset, localResp.documents);
      const nationalPolicies = transformDifyDataToPolicyFormat(nationalResp.dataset, nationalResp.documents);

      setLocalOptions(localPolicies.map(p => ({ value: p.id, label: p.title })));
      setNationalOptions(nationalPolicies.map(p => ({ value: p.id, label: p.title })));
    } catch (error) {
      console.error('加载政策文件列表失败：', error);
    } finally {
      setLoadingLists(false);
    }
  };

  // 初始化加载一次
  useEffect(() => {
    loadPolicyLists();
  }, []);

  // 选择变化时，清空结果与选中条款
  useEffect(() => {
    setCompareResults([]);
    setSelectedClauseId(null);
    setVisibleCount(4);
  }, [localDoc, nationalDocs]);

  const filteredClauses = useMemo(() => {
    let list = compareResults;
    if (showOnlyDiff) list = list.filter(c => c.hasDiff);
    return list.slice(0, visibleCount);
  }, [compareResults, showOnlyDiff, visibleCount]);

  const selectedClause = useMemo(() => (
    compareResults.find(c => c.id === selectedClauseId)
  ), [compareResults, selectedClauseId]);

  const handleClauseClick = (clause) => {
    setSelectedClauseId(clause.id);
    // 右侧面板滚动置顶，模拟“跳转”效果
    if (rightPanelRef.current) {
      rightPanelRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  // 将后端返回的 clauses 映射为组件使用的结构
  const mapBackendToUIClauses = (clauses = []) => {
    return (clauses || []).map((c) => {
      const titleText = c.local_clause?.slice(0, 18) || c.id || '地方条款';
      const hasDiff = (c.diff_type || '').trim() !== '无差异';
      const diffSummary = c.diff_keywords || c.diff_type || '';
      const nationalClauses = (c.national_clauses || []).map((nc, idx) => ({
        title: nc.nation_name || `国家条款 ${idx + 1}`,
        excerpt: nc.clause || '',
      }));
      return {
        id: c.id,
        title: `地方条款 ${c.id}：${titleText}`,
        hasDiff,
        diffSummary,
        localExcerpt: c.local_clause || '',
        analysis: c.analysis || (hasDiff ? '' : '与国家条款一致'),
        nationalClauses,
      };
    });
  };

  const handleGenerate = async () => {
    if (!localDoc || nationalDocs.length === 0) return;
    try {
      setGenerating(true);
      const resp = await analyzePolicyComparison({
        local_doc_id: localDoc.value,
        national_doc_ids: nationalDocs.map(d => d.value),
        limit: 2,
        collection_name: undefined, // 使用后端默认国家集合
      });
      const results = mapBackendToUIClauses(resp.clauses || []);
      setCompareResults(results);
      const firstId = results[0]?.id || null;
      setSelectedClauseId(firstId);
      setExpandedKeys(firstId ? [firstId] : []);
      setVisibleCount(4);
    } catch (error) {
      console.error('生成对比结果失败：', error);
    } finally {
      setGenerating(false);
    }
  };

  const renderToolbar = () => (
    <Card>
      <Space direction="vertical" size="middle" className="w-full">
        <div className="flex items-center justify-between">
          <Space size="large" wrap>
            <Space>
              <Text type="secondary">选择地方政策：</Text>
              <Select
                placeholder="选择地方政策文件"
                style={{ width: 280 }}
                value={localDoc?.value}
                onChange={(v, option) => setLocalDoc(option)}
                allowClear
                loading={loadingLists}
                options={localOptions}
              />
            </Space>
            <Space>
              <Text type="secondary">选择国家对比政策（可多选）：</Text>
              <Select
                mode="multiple"
                placeholder="选择一个或多个国家政策文件"
                style={{ width: 420 }}
                value={nationalDocs.map(d => d.value)}
                onChange={(values, options) => setNationalDocs(options)}
                allowClear
                loading={loadingLists}
                options={nationalOptions}
              />
            </Space>
          </Space>
          <Space>
            <Button icon={<SyncOutlined />} onClick={() => { loadPolicyLists(); }} loading={loadingLists}>
              刷新列表
            </Button>
            <Button
              type="primary"
              icon={<DiffOutlined />}
              disabled={!localDoc || nationalDocs.length === 0}
              onClick={handleGenerate}
              loading={generating}
            >
              生成对比结果
            </Button>
          </Space>
        </div>
        <div className="flex items-center justify-between">
          <Space size="middle">
            <Space>
              <Text>只看差异</Text>
              <Switch checked={showOnlyDiff} onChange={setShowOnlyDiff} />
            </Space>
            <Tag color="blue">已选国家政策：{nationalDocs.length} 个</Tag>
          </Space>
        </div>
      </Space>
    </Card>
  );

  const renderLeftPanel = () => (
    <Card title="地方政策条款" style={{ height: PANEL_HEIGHT, overflowY: 'auto' }}>
      {!localDoc || nationalDocs.length === 0 ? (
        <Empty description="请选择地方政策与至少一个国家政策，并生成对比结果" />
      ) : (
        <>
          {/* <Divider orientation="left">对比条款列表</Divider> */}
          <div>
            {filteredClauses.length === 0 ? (
              <Empty description="暂无对比结果，点击上方生成按钮" />
            ) : null}
          </div>
          {/* 使用简单列表替代原折叠面板以展示映射后的标题与摘要 */}
          {filteredClauses.map((item) => (
            <Card key={item.id} className="mb-3" onClick={() => handleClauseClick(item)} hoverable>
              <Space>
                <Text strong>{item.title}</Text>
                {item.hasDiff ? <Tag color="red">存在差异</Tag> : <Tag>无差异</Tag>}
              </Space>
              <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                {item.diffSummary}
              </Paragraph>
            </Card>
          ))}
          {compareResults.length > filteredClauses.length && (
            <div className="flex justify-center mt-4">
              <Space>
                <Button onClick={() => setVisibleCount((prev) => prev + 6)}>展开更多</Button>
              </Space>
            </div>
          )}
        </>
      )}
    </Card>
  );

  const renderRightPanel = () => (
    <Card title="国家政策映射与AI分析" style={{ height: PANEL_HEIGHT, overflowY: 'auto' }}>
      {!selectedClause ? (
        <Empty description="点击左侧条款查看对应国家条款与分析" />
      ) : (
        <div ref={rightPanelRef}>
          {/* <Divider orientation="left">AI 分析</Divider> */}
          <Card type="inner" title={<Space><FileTextOutlined /><span>AI 分析结论</span></Space>} className="mb-4">
            <Paragraph style={{ marginBottom: 0 }}>
              {selectedClause.analysis}
            </Paragraph>
          </Card>

          {/* <Divider orientation="left">国家政策匹配条款</Divider> */}

          {(selectedClause.nationalClauses || []).map((nc, idx) => (
            <Card key={`${selectedClause.id}-${idx}`} type="inner" title={nc.title} className="mb-3">
              <Paragraph style={{ marginBottom: 0 }}>{nc.excerpt || '（暂无条款内容）'}</Paragraph>
            </Card>
          ))}

          {(selectedClause.nationalClauses || []).length === 0 && (
            <Paragraph type="secondary" style={{ marginBottom: 0 }}>
              未找到与该地方条款对应的国家条款
            </Paragraph>
          )}
        </div>
      )}
    </Card>
  );

  return (
    <div className="space-y-6">
      {renderToolbar()}
      <Row gutter={16}>
        <Col span={12}>{renderLeftPanel()}</Col>
        <Col span={12}>{renderRightPanel()}</Col>
      </Row>
    </div>
  );
};

export default PolicyCompare;