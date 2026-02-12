import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider, Layout, Menu, theme } from "antd";
import {
  BarChartOutlined,
  FileTextOutlined,
  ReadOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import NewsArchive from "./pages/NewsArchive";
import ArticleDetail from "./pages/ArticleDetail";
import Dashboard from "./pages/Dashboard";
import Summarize from "./pages/Summarize";
import Settings from "./pages/Settings";

const { Sider, Content, Header } = Layout;

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

const menuItems = [
  {
    key: "news",
    icon: <FileTextOutlined />,
    label: <Link to="/news">News Registry</Link>,
  },
  {
    key: "dashboard",
    icon: <BarChartOutlined />,
    label: <Link to="/dashboard">Analytics</Link>,
  },
  {
    key: "summarize",
    icon: <ReadOutlined />,
    label: <Link to="/summarize">Summarize</Link>,
  },
  {
    key: "settings",
    icon: <SettingOutlined />,
    label: <Link to="/settings">Settings</Link>,
  },
];

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider
        theme={{
          algorithm: theme.defaultAlgorithm,
          token: { colorPrimary: "#1677ff" },
        }}
      >
        <BrowserRouter>
          <Layout style={{ minHeight: "100vh" }}>
            <Sider breakpoint="lg" collapsedWidth="0">
              <div
                style={{
                  height: 64,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#fff",
                  fontWeight: 700,
                  fontSize: 14,
                  textAlign: "center",
                  lineHeight: 1.3,
                  padding: "0 8px",
                }}
              >
                ASEAN Trade Monitor
              </div>
              <Menu
                theme="dark"
                mode="inline"
                defaultSelectedKeys={["news"]}
                items={menuItems}
              />
            </Sider>
            <Layout>
              <Header
                style={{
                  padding: "0 24px",
                  background: "#fff",
                  fontSize: 18,
                  fontWeight: 600,
                }}
              >
                ASEAN Trade Monitor
              </Header>
              <Content style={{ margin: "24px", minHeight: 280 }}>
                <Routes>
                  <Route path="/" element={<NewsArchive />} />
                  <Route path="/news" element={<NewsArchive />} />
                  <Route path="/news/:id" element={<ArticleDetail />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/summarize" element={<Summarize />} />
                  <Route path="/settings" element={<Settings />} />
                </Routes>
              </Content>
            </Layout>
          </Layout>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
