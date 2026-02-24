import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Input,
  message,
  Modal,
  Popconfirm,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  PlayCircleOutlined,
  PlusOutlined,
  ImportOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FileTextOutlined,
  StopOutlined,
  EyeOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  cancelScrapeRun,
  fetchPipelineStatus,
  fetchScrapeRuns,
  pollRunLogs,
  fetchScrapeStats,
  triggerScrape,
} from "../api/scrape";
import {
  fetchScrapeMaps,
  toggleScrapeMap,
  deleteScrapeMap,
  createScrapeMap,
} from "../api/scrapeMaps";
import type {
  ScrapeRun,
  ScrapeMapSummary,
  SourceStats,
  ScrapeLogEntry,
  PipelineStatus,
} from "../types";

dayjs.extend(relativeTime);

const COUNTRY_FLAGS: Record<string, string> = {
  ID: "Индонезия",
  VN: "Вьетнам",
  MY: "Малайзия",
};

const STATUS_COLOR: Record<string, string> = {
  success: "green",
  failed: "red",
  running: "blue",
  partial: "orange",
  cancelled: "default",
};

// Max log entries to keep in drawer to avoid memory bloat
const MAX_DRAWER_LOGS = 500;

export default function Settings() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [drawerRunId, setDrawerRunId] = useState<number | null>(null);
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [importJson, setImportJson] = useState("");

  // Live log state for drawer
  const [drawerLogs, setDrawerLogs] = useState<ScrapeLogEntry[]>([]);
  const lastLogIdRef = useRef(0);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Queries — smart polling: fast when running, slow when idle
  const { data: pipelineStatus } = useQuery<PipelineStatus>({
    queryKey: ["pipeline-status"],
    queryFn: fetchPipelineStatus,
    refetchInterval: (query) =>
      query.state.data?.running ? 3000 : 15000,
  });
  const isRunning = pipelineStatus?.running ?? false;
  const runningRunIds = pipelineStatus?.running_run_ids ?? [];

  const { data: maps, isLoading: mapsLoading } = useQuery({
    queryKey: ["scrape-maps"],
    queryFn: () => fetchScrapeMaps(),
    refetchInterval: isRunning ? 10000 : 60000,
  });

  const { data: stats } = useQuery({
    queryKey: ["scrape-stats"],
    queryFn: fetchScrapeStats,
    refetchInterval: isRunning ? 10000 : 60000,
  });

  const { data: runs, isLoading: runsLoading } = useQuery({
    queryKey: ["scrape-runs"],
    queryFn: () => fetchScrapeRuns(30),
    refetchInterval: isRunning ? 5000 : 30000,
  });

  // Auto-scroll logs
  const scrollToBottom = useCallback(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, []);

  // Live log polling for drawer — only when open and run is active
  const isDrawerRunActive = drawerRunId !== null && runningRunIds.includes(drawerRunId);

  useEffect(() => {
    if (drawerRunId === null) {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
      setDrawerLogs([]);
      lastLogIdRef.current = 0;
      return;
    }

    // Initial fetch
    let cancelled = false;
    const fetchInitial = async () => {
      try {
        const logs = await pollRunLogs(drawerRunId, 0);
        if (cancelled) return;
        const trimmed = logs.length > MAX_DRAWER_LOGS ? logs.slice(-MAX_DRAWER_LOGS) : logs;
        setDrawerLogs(trimmed);
        if (logs.length > 0) lastLogIdRef.current = logs[logs.length - 1].id;
        setTimeout(scrollToBottom, 50);
      } catch { /* ignore */ }
    };
    fetchInitial();

    // Poll only if run is active
    if (isDrawerRunActive) {
      pollIntervalRef.current = setInterval(async () => {
        try {
          const newLogs = await pollRunLogs(drawerRunId, lastLogIdRef.current);
          if (newLogs.length > 0) {
            lastLogIdRef.current = newLogs[newLogs.length - 1].id;
            setDrawerLogs((prev) => {
              const merged = [...prev, ...newLogs];
              return merged.length > MAX_DRAWER_LOGS ? merged.slice(-MAX_DRAWER_LOGS) : merged;
            });
            setTimeout(scrollToBottom, 50);
          }
        } catch { /* ignore */ }
      }, 2000);
    }

    return () => {
      cancelled = true;
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [drawerRunId, isDrawerRunActive, scrollToBottom]);

  // Stats lookup
  const statsMap: Record<string, SourceStats> = {};
  stats?.forEach((s) => { statsMap[s.source] = s; });

  // Mutations
  const triggerAll = useMutation({
    mutationFn: () => triggerScrape(),
    onSuccess: () => {
      message.success("Сбор запущен для всех активных источников");
      queryClient.invalidateQueries({ queryKey: ["scrape-runs"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] });
    },
    onError: () => message.warning("Все источники уже запущены"),
  });

  const triggerOne = useMutation({
    mutationFn: (source: string) => triggerScrape([source]),
    onSuccess: (_, source) => {
      message.success(`Сбор запущен: ${source}`);
      queryClient.invalidateQueries({ queryKey: ["scrape-runs"] });
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] });
    },
    onError: () => message.warning("Этот источник уже запущен"),
  });

  const cancelRunMutation = useMutation({
    mutationFn: (runId: number) => cancelScrapeRun(runId),
    onSuccess: () => {
      message.info("Запрос на отмену отправлен");
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] });
      queryClient.invalidateQueries({ queryKey: ["scrape-runs"] });
    },
    onError: () => message.warning("Запуск не активен"),
  });

  const toggleMutation = useMutation({
    mutationFn: (mapId: string) => toggleScrapeMap(mapId),
    onSuccess: (data) => {
      message.success(`${data.map_id}: ${data.active ? "включён" : "выключен"}`);
      queryClient.invalidateQueries({ queryKey: ["scrape-maps"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (mapId: string) => deleteScrapeMap(mapId),
    onSuccess: () => {
      message.success("Карта удалена");
      queryClient.invalidateQueries({ queryKey: ["scrape-maps"] });
    },
    onError: () => message.error("Ошибка удаления карты"),
  });

  const importMutation = useMutation({
    mutationFn: (json: string) => createScrapeMap(json),
    onSuccess: () => {
      message.success("Карта импортирована");
      setImportModalOpen(false);
      setImportJson("");
      queryClient.invalidateQueries({ queryKey: ["scrape-maps"] });
    },
    onError: (err: Error) => message.error(err.message || "Ошибка импорта"),
  });

  // Find run info for a source
  const getRunForSource = (mapId: string): ScrapeRun | undefined =>
    runs?.find((r) => r.source === mapId && r.status === "running");

  // Table columns for maps
  const mapsColumns = [
    {
      title: "Источник",
      dataIndex: "name",
      key: "name",
      render: (name: string, record: ScrapeMapSummary) => (
        <a onClick={() => navigate(`/settings/maps/${record.map_id}/detail`)} style={{ cursor: "pointer" }}>
          <Typography.Text strong>{name}</Typography.Text>
          <br />
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{record.map_id}</Typography.Text>
        </a>
      ),
    },
    {
      title: "Страна", dataIndex: "country", key: "country", width: 110,
      render: (c: string) => <Tag>{COUNTRY_FLAGS[c] || c}</Tag>,
    },
    {
      title: "URL", dataIndex: "start_urls_count", key: "start_urls_count", width: 70, align: "center" as const,
    },
    {
      title: "Селекторы", dataIndex: "selectors_count", key: "selectors_count", width: 95, align: "center" as const,
    },
    {
      title: "Статьи", key: "articles", width: 100, align: "center" as const,
      render: (_: unknown, record: ScrapeMapSummary) => {
        const s = statsMap[record.map_id];
        return s ? <Typography.Text strong>{s.total_articles}</Typography.Text>
          : <Typography.Text type="secondary">0</Typography.Text>;
      },
    },
    {
      title: "Последний сбор", key: "last_scraped", width: 140,
      render: (_: unknown, record: ScrapeMapSummary) => {
        const s = statsMap[record.map_id];
        return s?.last_scraped
          ? <Typography.Text type="secondary" style={{ fontSize: 12 }}>{dayjs(s.last_scraped).fromNow()}</Typography.Text>
          : <Typography.Text type="secondary">Нет</Typography.Text>;
      },
    },
    {
      title: "Расписание", key: "cron", width: 120,
      render: (_: unknown, record: ScrapeMapSummary) =>
        record.cron_expression
          ? <Tag color="purple">{record.cron_expression}</Tag>
          : <Typography.Text type="secondary" style={{ fontSize: 12 }}>Общее</Typography.Text>,
    },
    {
      title: "Активен", dataIndex: "active", key: "active", width: 80,
      render: (active: boolean, record: ScrapeMapSummary) => (
        <Switch checked={active} size="small" onChange={() => toggleMutation.mutate(record.map_id)} />
      ),
    },
    {
      title: "Действия", key: "actions", width: 230,
      render: (_: unknown, record: ScrapeMapSummary) => {
        const runningRun = getRunForSource(record.map_id);
        return (
          <Space size="small">
            {runningRun
              ? <Tag color="blue">Сбор...</Tag>
              : <Button size="small" icon={<ReloadOutlined />} onClick={() => triggerOne.mutate(record.map_id)}>Собрать</Button>
            }
            <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/settings/maps/${record.map_id}/detail`)} />
            <Button size="small" icon={<EditOutlined />} onClick={() => navigate(`/settings/maps/${record.map_id}`)} />
            <Popconfirm title="Удалить эту карту?" onConfirm={() => deleteMutation.mutate(record.map_id)}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        );
      },
    },
  ];

  // Table columns for runs
  const runsColumns = [
    { title: "Источник", dataIndex: "source", key: "source" },
    {
      title: "Начало", dataIndex: "started_at", key: "started_at",
      render: (d: string) => dayjs(d).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "Статус", dataIndex: "status", key: "status",
      render: (s: string) => <Tag color={STATUS_COLOR[s] || "default"}>{s}</Tag>,
    },
    { title: "Найдено", dataIndex: "articles_found", key: "articles_found" },
    { title: "Новых", dataIndex: "articles_new", key: "articles_new" },
    {
      title: "Ошибка", dataIndex: "error_message", key: "error_message", ellipsis: true,
      render: (e: string | null) => e ? <Typography.Text type="danger" ellipsis>{e}</Typography.Text> : null,
    },
    {
      title: "Логи", key: "logs", width: 100,
      render: (_: unknown, record: ScrapeRun) => (
        <Button size="small" icon={<FileTextOutlined />} onClick={(e) => { e.stopPropagation(); setDrawerRunId(record.id); }}>
          Открыть
        </Button>
      ),
    },
  ];

  const currentDrawerRun = runs?.find((r) => r.id === drawerRunId);

  return (
    <div>
      <Typography.Title level={3}>Сборщики</Typography.Title>

      <Card
        title="Карты сбора"
        style={{ marginBottom: 16 }}
        extra={
          <Space>
            <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => triggerAll.mutate()} loading={triggerAll.isPending}>
              Запустить все
            </Button>
            <Button icon={<PlusOutlined />} onClick={() => navigate("/settings/maps/new")}>Создать</Button>
            <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>Импорт JSON</Button>
          </Space>
        }
      >
        {isRunning && (
          <Tag color="blue" style={{ fontSize: 14, padding: "4px 12px", marginBottom: 12 }}>
            Сбор выполняется...
          </Tag>
        )}
        <Table dataSource={maps || []} columns={mapsColumns} rowKey="map_id" loading={mapsLoading} pagination={false} size="small" />
      </Card>

      <Card title="Последние запуски">
        <Table
          columns={runsColumns}
          dataSource={runs || []}
          rowKey="id"
          loading={runsLoading}
          pagination={{ pageSize: 10 }}
          size="small"
          onRow={(record) => ({
            onClick: () => setDrawerRunId(record.id),
            style: { cursor: "pointer" },
          })}
        />
      </Card>

      {/* Run Detail Drawer */}
      <Drawer
        title={`Запуск #${drawerRunId} — ${currentDrawerRun?.source || ""}`}
        open={drawerRunId !== null}
        onClose={() => setDrawerRunId(null)}
        width={700}
        destroyOnClose
      >
        {currentDrawerRun && (
          <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="Источник">{currentDrawerRun.source}</Descriptions.Item>
            <Descriptions.Item label="Статус">
              <Tag color={STATUS_COLOR[currentDrawerRun.status] || "default"}>{currentDrawerRun.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Начало">{dayjs(currentDrawerRun.started_at).format("YYYY-MM-DD HH:mm:ss")}</Descriptions.Item>
            <Descriptions.Item label="Завершение">
              {currentDrawerRun.finished_at ? dayjs(currentDrawerRun.finished_at).format("YYYY-MM-DD HH:mm:ss") : "Выполняется..."}
            </Descriptions.Item>
            <Descriptions.Item label="Найдено статей">{currentDrawerRun.articles_found}</Descriptions.Item>
            <Descriptions.Item label="Новых">{currentDrawerRun.articles_new}</Descriptions.Item>
            {currentDrawerRun.finished_at && currentDrawerRun.started_at && (
              <Descriptions.Item label="Длительность" span={2}>
                {Math.round((new Date(currentDrawerRun.finished_at).getTime() - new Date(currentDrawerRun.started_at).getTime()) / 1000)} сек
              </Descriptions.Item>
            )}
            {currentDrawerRun.error_message && (
              <Descriptions.Item label="Ошибка" span={2}>
                <Typography.Text type="danger">{currentDrawerRun.error_message}</Typography.Text>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}

        {isDrawerRunActive && (
          <Button danger icon={<StopOutlined />} onClick={() => cancelRunMutation.mutate(drawerRunId!)} loading={cancelRunMutation.isPending} style={{ marginBottom: 16 }}>
            Отменить этот запуск
          </Button>
        )}

        <Typography.Title level={5} style={{ marginBottom: 8 }}>
          Записи лога ({drawerLogs.length})
          {isDrawerRunActive && <Tag color="blue" style={{ marginLeft: 8, fontWeight: "normal" }}>обновляется...</Tag>}
        </Typography.Title>

        <div
          ref={logContainerRef}
          style={{
            maxHeight: "calc(100vh - 420px)", overflow: "auto",
            background: "#1e1e1e", borderRadius: 6, padding: "12px 16px",
            fontFamily: "'Consolas', 'Monaco', monospace", fontSize: 12, lineHeight: 1.6,
          }}
        >
          {drawerLogs.length === 0
            ? <span style={{ color: "#666" }}>Нет записей лога для этого запуска.</span>
            : drawerLogs.map((entry) => (
              <div key={entry.id} style={{ marginBottom: 2 }}>
                <span style={{ color: "#888" }}>{dayjs(entry.timestamp).format("HH:mm:ss")}</span>{" "}
                <span style={{ color: entry.level === "ERROR" ? "#ff4d4f" : entry.level === "WARNING" ? "#faad14" : "#91caff" }}>
                  [{entry.level}]
                </span>{" "}
                <span style={{ color: "#d4d4d4" }}>{entry.message}</span>
              </div>
            ))
          }
        </div>
      </Drawer>

      {/* Import JSON Modal */}
      <Modal
        title="Импорт карты сбора (JSON)"
        open={importModalOpen}
        onCancel={() => { setImportModalOpen(false); setImportJson(""); }}
        onOk={() => {
          if (!importJson.trim()) { message.error("Вставьте JSON"); return; }
          try { JSON.parse(importJson); } catch { message.error("Некорректный JSON"); return; }
          importMutation.mutate(importJson);
        }}
        okText="Импортировать"
        cancelText="Отмена"
        confirmLoading={importMutation.isPending}
        width={700}
        destroyOnClose
      >
        <Typography.Paragraph type="secondary">
          Вставьте JSON карты из Chrome-расширения Web Scraper или создайте свою.
          Обязательные поля: _id, startUrls, selectors, _meta.
        </Typography.Paragraph>
        <Input.TextArea
          value={importJson}
          onChange={(e) => setImportJson(e.target.value)}
          rows={20}
          placeholder='{"_id": "my_source", "startUrls": [...], "selectors": [...], "_meta": {...}}'
          style={{ fontFamily: "'Consolas', 'Monaco', monospace", fontSize: 13 }}
        />
      </Modal>
    </div>
  );
}
