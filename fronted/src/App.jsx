import React, { useState } from 'react';
import { Layout, Menu, Typography } from 'antd';
import { DatabaseOutlined, MenuFoldOutlined, MenuUnfoldOutlined, FileOutlined } from '@ant-design/icons';
import PolicyLibrary from './components/PolicyLibrary';
import LocalPolicyLibrary from './components/LocalPolicyLibrary';
import './App.css';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

function App() {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('1');

  const menuItems = [
    {
      key: '1',
      icon: <DatabaseOutlined />,
      label: '国家政策文件库',
    },
    {
      key: '2',
      icon: <FileOutlined />,
      label: '地方政策文件库',
    },
  ];

  const renderContent = () => {
    switch (selectedKey) {
      case '1':
        return <PolicyLibrary />;
      case '2':
        return <LocalPolicyLibrary />;
      default:
        return <PolicyLibrary />;
    }
  };

  return (
    <Layout className="min-h-screen">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className="bg-white shadow-lg"
        style={{
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 100,
        }}
      >
        <div className="p-4 border-b border-gray-200">
           <div className="flex items-center justify-between">
             <div className="flex items-center">
               {/* <DatabaseOutlined className="text-blue-600 text-xl" /> */}
               {!collapsed && (
                 <Title level={4} className="ml-2 mb-0 text-gray-700">
                   政策管理
                 </Title>
               )}
             </div>
             {React.createElement(collapsed ? MenuUnfoldOutlined : MenuFoldOutlined, {
               className: 'text-lg cursor-pointer hover:text-blue-600 transition-colors',
               onClick: () => setCollapsed(!collapsed),
             })}
           </div>
         </div>
        <Menu
          theme="light"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onSelect={({ key }) => setSelectedKey(key)}
          className="border-r-0"
        />
      </Sider>

      <Layout style={{ marginLeft: collapsed ? 80 : 200, transition: 'margin-left 0.2s' }}>
        <Header className="bg-white shadow-sm px-6 flex items-center">
           <Title level={3} className="mb-0 text-gray-700">
             {selectedKey === '1' ? '国家政策文件库' : '地方政策文件库'}
           </Title>
         </Header>

        <Content className="p-6 bg-gray-50" style={{ minHeight: 'calc(100vh - 64px)' }}>
          {renderContent()}
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;