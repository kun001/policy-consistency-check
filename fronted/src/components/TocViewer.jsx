import React from 'react';
import { Tree, Tag, Space } from 'antd';

// 将后端返回的 toc 树转换为 AntD Tree 数据
function makeTreeData(toc, fileName) {
  if (!toc || !Array.isArray(toc.children)) return [];

  const toNode = (n) => {
    const titleParts = [];
    if (n.type === 'chapter' || n.type === 'section' || n.type === 'article') {
      if (n.label) titleParts.push(n.label);
    }
    if (n.type === 'article' && n.text) {
      // 只展示 label，详细内容在右侧详情展示
    }

    const title = titleParts.length ? titleParts.join(' ') : (n.type === 'document' ? (fileName || '文档') : n.id);
    const children = Array.isArray(n.children) ? n.children.map(toNode) : undefined;

    return {
      key: n.id || `${n.type}-${n.index || Math.random()}`,
      title,
      children,
      dataRef: n,
    };
  };

  return toc.children.map(toNode);
}

const TocViewer = ({ toc, fileName, onSelectArticle }) => {
  const treeData = makeTreeData(toc, fileName);

  const handleSelect = (_keys, info) => {
    const node = info.node?.dataRef;
    if (node && node.type === 'article') {
      const text = node.text || '';
      onSelectArticle?.(node, text);
    }
  };

  return (
    <Tree
      treeData={treeData}
      onSelect={handleSelect}
      defaultExpandAll
      showLine
    />
  );
};

export default TocViewer;