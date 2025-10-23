import React, { useState, useMemo, useEffect, useRef } from 'react';
import { Card, Typography, Space, Button, Select, Switch, Row, Col, Empty, Tag, Divider, Collapse } from 'antd';
import { DiffOutlined, SyncOutlined, FileTextOutlined } from '@ant-design/icons';
import { getNationalPolicyData, getLocalPolicyData, transformDifyDataToPolicyFormat, transformLocalDifyDataToPolicyFormat } from '../api/weaivateApi';

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

  // 占位：模拟后端的对比结果结构
  const generateMockCompareResults = (loc, nats) => {
    if (!loc || !nats.length) return [];
    const mkNat = (docId, idx) => ({
      docId,
      clauseId: `${docId}-C${idx}`,
      title: `国家条款 ${idx}`,
      excerpt: `国家条款${idx}原文`,
    });
    return [
      {
        id: 'L-001',
        title: '地方条款 1：交易结算与保证金',
        hasDiff: true,
        diffSummary: '保证金比例与结算周期存在差异（示例）',
        localExcerpt: '地方规定：保证金比例为5%，结算周期为月度……',
        matchedNational: nats.map(n => mkNat(n.value, 1)),
        analysis: 'AI分析：地方政策在结算周期上更为严格，可能导致现金流压力增大；建议在条款对齐时考虑过渡期与豁免条件。',
      },
      {
        id: 'L-002',
        title: '地方条款 2：信息披露与报备',
        hasDiff: true,
        diffSummary: '披露频次与范围不同（示例）',
        localExcerpt: '地方规定：每季度披露，并报备至地方交易中心……',
        matchedNational: nats.map(n => mkNat(n.value, 2)),
        analysis: 'AI分析：国家要求的披露范围更广，但频次较低；地方要求更频繁。建议统一为季度披露并增加关键指标报备。',
      },
      {
        id: 'L-003',
        title: '地方条款 3：信用评估与黑名单',
        hasDiff: false,
        diffSummary: '与国家条款一致（示例）',
        localExcerpt: '地方规定：按国家统一信用规则执行业务评估……',
        matchedNational: nats.map(n => mkNat(n.value, 3)),
        analysis: 'AI分析：该条款与国家要求一致，无需调整。',
      },
      {
        id: 'L-004',
        title: '地方条款 4：履约保障与保险',
        hasDiff: true,
        diffSummary: '保险类型和触发条件不同（示例）',
        localExcerpt: '地方规定：支持保函与保险两种形式，触发条件为违约风险评估……',
        matchedNational: nats.map(n => mkNat(n.value, 4)),
        analysis: 'AI分析：国家政策对触发条件更严格；建议明确风控阈值并设置豁免条款，降低企业负担。',
      },
      {
        id: 'L-005',
        title: '地方条款 5：交易申报与变更',
        hasDiff: true,
        diffSummary: '申报时限与变更流程不同（示例）',
        localExcerpt: '地方规定：申报需提前10个工作日，变更需审批……',
        matchedNational: nats.map(n => mkNat(n.value, 5)),
        analysis: 'AI分析：建议统一申报提前期至7-10个工作日，并优化变更流程为分级授权审批。',
      },
      {
        id: 'L-006',
        title: '地方条款 1：交易结算与保证金',
        hasDiff: true,
        diffSummary: '保证金比例与结算周期存在差异（示例）',
        localExcerpt: '地方规定：保证金比例为5%，结算周期为月度……',
        matchedNational: nats.map(n => mkNat(n.value, 1)),
        analysis: 'AI分析：地方政策在结算周期上更为严格，可能导致现金流压力增大；建议在条款对齐时考虑过渡期与豁免条件。',
      },
      {
        id: 'L-007',
        title: '地方条款 2：信息披露与报备',
        hasDiff: true,
        diffSummary: '披露频次与范围不同（示例）',
        localExcerpt: '地方规定：每季度披露，并报备至地方交易中心……',
        matchedNational: nats.map(n => mkNat(n.value, 2)),
        analysis: 'AI分析：国家要求的披露范围更广，但频次较低；地方要求更频繁。建议统一为季度披露并增加关键指标报备。',
      },
      {
        id: 'L-008',
        title: '地方条款 3：信用评估与黑名单',
        hasDiff: false,
        diffSummary: '与国家条款一致（示例）',
        localExcerpt: '地方规定：按国家统一信用规则执行业务评估……',
        matchedNational: nats.map(n => mkNat(n.value, 3)),
        analysis: 'AI分析：该条款与国家要求一致，无需调整。',
      },
      {
        id: 'L-009',
        title: '地方条款 4：履约保障与保险',
        hasDiff: true,
        diffSummary: '保险类型和触发条件不同（示例）',
        localExcerpt: '地方规定：支持保函与保险两种形式，触发条件为违约风险评估……',
        matchedNational: nats.map(n => mkNat(n.value, 4)),
        analysis: 'AI分析：国家政策对触发条件更严格；建议明确风控阈值并设置豁免条款，降低企业负担。',
      },
      {
        id: 'L-010',
        title: '地方条款 5：交易申报与变更',
        hasDiff: true,
        diffSummary: '申报时限与变更流程不同（示例）',
        localExcerpt: '地方规定：申报需提前10个工作日，变更需审批……',
        matchedNational: nats.map(n => mkNat(n.value, 5)),
        analysis: 'AI分析：建议统一申报提前期至7-10个工作日，并优化变更流程为分级授权审批。',
      },
    ];
  };

  const handleGenerate = () => {
    const results = generateMockCompareResults(localDoc, nationalDocs).map(c => ({
      ...c,
      localFullText: c.localExcerpt ? `${c.localExcerpt}（示例扩展正文，实际接入后替换为全文）` : '（示例：暂无全文，后端接入后显示）',
    }));
    setCompareResults(results);
    const firstId = results[0]?.id || null;
    setSelectedClauseId(firstId);
    setExpandedKeys(firstId ? [firstId] : []);
    setVisibleCount(4);
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
          <Collapse
            activeKey={expandedKeys}
            onChange={(keys) => {
              const arr = Array.isArray(keys) ? keys : [keys];
              setExpandedKeys(arr);
              const last = arr[arr.length - 1] || null;
              if (last) setSelectedClauseId(last);
              if (rightPanelRef.current) {
                rightPanelRef.current.scrollTo({ top: 0, behavior: 'smooth' });
              }
            }}
          >
            {filteredClauses.map((item) => (
              <Collapse.Panel
                header={(
                  <Space>
                    <Text strong>{item.title}</Text>
                    {item.hasDiff ? <Tag color="red">存在差异</Tag> : <Tag>无差异</Tag>}
                  </Space>
                )}
                key={item.id}
                extra={<Text type="secondary">{item.diffSummary}</Text>}
              >
                <Paragraph style={{ marginBottom: 0 }}>
                  {item.localFullText || item.localExcerpt}
                </Paragraph>
              </Collapse.Panel>
            ))}
          </Collapse>
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
        <Empty description="点击左侧存在差异的地方条款查看对应国家条款与分析" />
      ) : (
        <div ref={rightPanelRef}>
          <Divider orientation="left">AI 分析</Divider>
          <Card type="inner" title={<Space><FileTextOutlined /><span>AI 分析结论</span></Space>} className="mb-4">
            <Paragraph style={{ marginBottom: 0 }}>
              {selectedClause.analysis}
            </Paragraph>
          </Card>

          <Divider orientation="left">国家政策匹配条款</Divider>

          {nationalDocs.map(nDoc => {
            const match = (selectedClause.matchedNational || []).find(m => m.docId === nDoc.value);
            return (
              <Card
                key={nDoc.value}
                type="inner"
                title={`${nDoc.label}`}
                className="mb-3"
              >
                {match ? (
                  <>
                    <Title level={5} style={{ marginTop: 0 }}>{match.title}</Title>
                    <Paragraph style={{ marginBottom: 0 }}>{match.excerpt}</Paragraph>
                  </>
                ) : (
                  <Paragraph type="secondary" style={{ marginBottom: 0 }}>
                    未找到与该地方条款对应的国家条款（占位）
                  </Paragraph>
                )}
              </Card>
            );
          })}
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