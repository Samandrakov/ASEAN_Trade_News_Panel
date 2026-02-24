import { lazy, Suspense } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Button, ConfigProvider, Layout, Menu, Spin, theme } from "antd";
import {
  BarChartOutlined,
  FileTextOutlined,
  LogoutOutlined,
  ReadOutlined,
  CloudDownloadOutlined,
} from "@ant-design/icons";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { AuthProvider, RequireAuth, useAuth } from "./auth/AuthContext";

const Login = lazy(() => import("./pages/Login"));
const NewsArchive = lazy(() => import("./pages/NewsArchive"));
const ArticleDetail = lazy(() => import("./pages/ArticleDetail"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Summarize = lazy(() => import("./pages/Summarize"));
const Settings = lazy(() => import("./pages/Settings"));
const MapEditor = lazy(() => import("./pages/MapEditor"));
const ScraperDetail = lazy(() => import("./pages/ScraperDetail"));

const { Sider, Content, Header } = Layout;

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5000,
      gcTime: 60000,
    },
  },
});

const menuItems = [
  {
    key: "news",
    icon: <FileTextOutlined />,
    label: <Link to="/news">Реестр новостей</Link>,
  },
  {
    key: "dashboard",
    icon: <BarChartOutlined />,
    label: <Link to="/dashboard">Аналитика</Link>,
  },
  {
    key: "summarize",
    icon: <ReadOutlined />,
    label: <Link to="/summarize">Суммаризация</Link>,
  },
  {
    key: "settings",
    icon: <CloudDownloadOutlined />,
    label: <Link to="/settings">Сборщики</Link>,
  },
];

const PageLoader = (
  <div style={{ display: "flex", justifyContent: "center", paddingTop: 100 }}>
    <Spin size="large" />
  </div>
);

function AppLayout() {
  const { logout, username } = useAuth();

  return (
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
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span>ASEAN Trade Monitor</span>
          <span style={{ fontSize: 14, fontWeight: 400 }}>
            {username && (
              <Button
                type="text"
                icon={<LogoutOutlined />}
                onClick={logout}
                style={{ color: "#666" }}
              >
                Выйти ({username})
              </Button>
            )}
          </span>
        </Header>
        <Content style={{ margin: "24px", minHeight: 280 }}>
          <Suspense fallback={PageLoader}>
            <Routes>
              <Route path="/" element={<NewsArchive />} />
              <Route path="/news" element={<NewsArchive />} />
              <Route path="/news/:id" element={<ArticleDetail />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/summarize" element={<Summarize />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/settings/maps/new" element={<MapEditor />} />
              <Route path="/settings/maps/:mapId" element={<MapEditor />} />
              <Route
                path="/settings/maps/:mapId/detail"
                element={<ScraperDetail />}
              />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
    </Layout>
  );
}

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
          <AuthProvider>
            <Suspense fallback={PageLoader}>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                  path="/*"
                  element={
                    <RequireAuth>
                      <AppLayout />
                    </RequireAuth>
                  }
                />
              </Routes>
            </Suspense>
          </AuthProvider>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;
