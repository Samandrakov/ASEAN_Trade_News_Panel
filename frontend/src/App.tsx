import { lazy, Suspense, useState } from "react";
import { QueryClient, QueryClientProvider, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  ConfigProvider,
  Drawer,
  Form,
  Input,
  Layout,
  List,
  Menu,
  Modal,
  Select,
  Space,
  Spin,
  Switch,
  Tag,
  Tooltip,
  Typography,
  theme,
  message,
} from "antd";
import {
  BarChartOutlined,
  BellOutlined,
  BookOutlined,
  CloudDownloadOutlined,
  DeleteOutlined,
  FileTextOutlined,
  LogoutOutlined,
  PlusOutlined,
  ReadOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import { BrowserRouter, Link, Route, Routes } from "react-router-dom";
import { AuthProvider, RequireAuth, useAuth } from "./auth/AuthContext";
import ErrorBoundary from "./components/ErrorBoundary";
import { COUNTRY_CODES } from "./constants";
import {
  fetchAlerts,
  fetchAlertMatches,
  fetchUnreadCount,
  createAlert,
  updateAlert,
  deleteAlert,
  markAllRead,
} from "./api/alerts";

const Login = lazy(() => import("./pages/Login"));
const NewsArchive = lazy(() => import("./pages/NewsArchive"));
const ArticleDetail = lazy(() => import("./pages/ArticleDetail"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Summarize = lazy(() => import("./pages/Summarize"));
const Settings = lazy(() => import("./pages/Settings"));
const MapEditor = lazy(() => import("./pages/MapEditor"));
const ScraperDetail = lazy(() => import("./pages/ScraperDetail"));
const Bookmarks = lazy(() => import("./pages/Bookmarks"));
const Users = lazy(() => import("./pages/Users"));

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

const PageLoader = (
  <div style={{ display: "flex", justifyContent: "center", paddingTop: 100 }}>
    <Spin size="large" />
  </div>
);

// COUNTRY_CODES imported from ./constants

function AlertsDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient();
  const [msg, ctxHolder] = message.useMessage();
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: alerts = [] } = useQuery({ queryKey: ["alerts"], queryFn: fetchAlerts });
  const { data: matches = [] } = useQuery({
    queryKey: ["alert-matches"],
    queryFn: () => fetchAlertMatches({ limit: 30 }),
    enabled: open,
    refetchInterval: open ? 30000 : false,
  });

  const createMut = useMutation({
    mutationFn: createAlert,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alerts"] }); setCreateOpen(false); form.resetFields(); },
    onError: () => { msg.error("Ошибка создания алерта"); },
  });
  const toggleMut = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateAlert(id, { active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
  const deleteMut = useMutation({
    mutationFn: deleteAlert,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
  const readAllMut = useMutation({
    mutationFn: markAllRead,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alert-matches"] }); qc.invalidateQueries({ queryKey: ["alert-unread"] }); },
  });

  return (
    <Drawer
      title="Алерты"
      open={open}
      onClose={onClose}
      width={480}
      extra={
        <Button size="small" onClick={() => setCreateOpen(true)} icon={<PlusOutlined />}>
          Создать
        </Button>
      }
    >
      {ctxHolder}
      <Typography.Title level={5}>Активные алерты</Typography.Title>
      <List
        size="small"
        dataSource={alerts}
        locale={{ emptyText: "Нет алертов" }}
        renderItem={(a) => (
          <List.Item
            actions={[
              <Switch
                key="toggle"
                size="small"
                checked={a.active}
                onChange={(checked) => toggleMut.mutate({ id: a.id, active: checked })}
              />,
              <Tooltip title="Удалить" key="del">
                <Button
                  type="text" size="small" danger icon={<DeleteOutlined />}
                  onClick={() => Modal.confirm({
                    title: `Удалить алерт "${a.name}"?`,
                    onOk: () => deleteMut.mutate(a.id),
                    okText: "Да", cancelText: "Нет",
                  })}
                />
              </Tooltip>,
            ]}
          >
            <List.Item.Meta
              title={a.name}
              description={
                <Space wrap size={[4, 4]}>
                  {a.keywords.map((k) => <Tag key={k} color="blue">{k}</Tag>)}
                  {a.countries.map((c) => <Tag key={c} color="green">{c}</Tag>)}
                </Space>
              }
            />
          </List.Item>
        )}
      />

      <div style={{ marginTop: 24, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Typography.Title level={5} style={{ margin: 0 }}>Последние совпадения</Typography.Title>
        {matches.length > 0 && (
          <Button size="small" onClick={() => readAllMut.mutate()}>Отметить все прочитанными</Button>
        )}
      </div>
      <List
        size="small"
        style={{ marginTop: 8 }}
        dataSource={matches}
        locale={{ emptyText: "Нет совпадений" }}
        renderItem={(m) => (
          <List.Item>
            <List.Item.Meta
              title={
                <Space>
                  {!m.read && <Badge status="processing" />}
                  <Link to={`/news/${m.article_id}`} onClick={onClose}>
                    {m.article_title}
                  </Link>
                </Space>
              }
              description={`${m.alert_name} · ${m.article_country} · ${new Date(m.matched_at).toLocaleDateString("ru")}`}
            />
          </List.Item>
        )}
      />

      <Modal
        title="Новый алерт"
        open={createOpen}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={(v) => createMut.mutate({
          name: v.name,
          keywords: v.keywords ? v.keywords.split(",").map((s: string) => s.trim()).filter(Boolean) : [],
          countries: v.countries || [],
        })}>
          <Form.Item name="name" label="Название" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="keywords" label="Ключевые слова (через запятую)">
            <Input placeholder="торговля, экспорт, инвестиции" />
          </Form.Item>
          <Form.Item name="countries" label="Страны">
            <Select mode="multiple" placeholder="Все страны"
              options={COUNTRY_CODES.map((c) => ({ value: c, label: c }))} />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: "right" }}>
            <Button onClick={() => { setCreateOpen(false); form.resetFields(); }} style={{ marginRight: 8 }}>Отмена</Button>
            <Button type="primary" htmlType="submit" loading={createMut.isPending}>Создать</Button>
          </Form.Item>
        </Form>
      </Modal>
    </Drawer>
  );
}

function AppLayout() {
  const { logout, username } = useAuth();
  const [alertsOpen, setAlertsOpen] = useState(false);
  const qc = useQueryClient();

  const { data: unreadCount = 0 } = useQuery({
    queryKey: ["alert-unread"],
    queryFn: fetchUnreadCount,
    refetchInterval: 60000,
  });

  const menuItems = [
    { key: "news", icon: <FileTextOutlined />, label: <Link to="/news">Реестр новостей</Link> },
    { key: "dashboard", icon: <BarChartOutlined />, label: <Link to="/dashboard">Аналитика</Link> },
    { key: "summarize", icon: <ReadOutlined />, label: <Link to="/summarize">Суммаризация</Link> },
    { key: "bookmarks", icon: <BookOutlined />, label: <Link to="/bookmarks">Закладки</Link> },
    { key: "settings", icon: <CloudDownloadOutlined />, label: <Link to="/settings">Сборщики</Link> },
    { key: "users", icon: <TeamOutlined />, label: <Link to="/users">Пользователи</Link> },
    {
      key: "alerts",
      icon: <Badge count={unreadCount} size="small"><BellOutlined /></Badge>,
      label: <span onClick={() => setAlertsOpen(true)} style={{ cursor: "pointer" }}>Алерты</span>,
    },
  ];

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
              <Route path="/settings/maps/:mapId/detail" element={<ScraperDetail />} />
              <Route path="/bookmarks" element={<Bookmarks />} />
              <Route path="/users" element={<Users />} />
            </Routes>
          </Suspense>
        </Content>
      </Layout>
      <AlertsDrawer open={alertsOpen} onClose={() => { setAlertsOpen(false); qc.invalidateQueries({ queryKey: ["alert-unread"] }); }} />
    </Layout>
  );
}

function App() {
  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
}

export default App;
