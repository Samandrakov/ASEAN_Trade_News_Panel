import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  Col,
  Collapse,
  Drawer,
  Input,
  message,
  Modal,
  Row,
  Statistic,
  Table,
  Tag,
  Typography,
  Space,
} from "antd";
import {
  ArrowLeftOutlined,
  PlayCircleOutlined,
  EditOutlined,
  StopOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import {
  fetchRunsBySource,
  fetchSourceDetailStats,
  fetchSourceArticles,
  fetchSourceArticleDetail,
  fetchPipelineStatus,
  triggerScrape,
  cancelScrapeRun,
  pollRunLogs,
} from "../api/scrape";
import { fetchScrapeMap, updateScrapeMap } from "../api/scrapeMaps";
import type {
  ScrapeRun,
  SourceArticle,
  SourceArticleDetail,
  ScrapeLogEntry,
} from "../types";

dayjs.extend(relativeTime);

const STATUS_COLOR: Record<string, string> = {
  success: "green",
  failed: "red",
  running: "blue",
  partial: "orange",
  cancelled: "default",
};

const MAX_DRAWER_LOGS = 500;

export default function ScraperDetail() {
  const { mapId } = useParams<{ mapId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [cronModalOpen, setCronModalOpen] = useState(false);
  const [cronValue, setCronValue] = useState("");
  const [drawerRunId, setDrawerRunId] = useState<number | null>(null);
  const [drawerLogs, setDrawerLogs] = useState<ScrapeLogEntry[]>([]);
  const lastLogIdRef = useRef(0);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Expanded article body cache (load on demand)
  const [expandedBodies, setExpandedBodies] = useState<Record<number, SourceArticleDetail | null>>({});

  // Queries
  const { data: mapData } = useQuery({
    queryKey: ["scrape-map", mapId],
    queryFn: () => fetchScrapeMap(mapId!),
    enabled: !!mapId,
  });

  const { data: detailStats } = useQuery({
    queryKey: ["source-detail-stats", mapId],
    queryFn: () => fetchSourceDetailStats(mapId!),
    enabled: !!mapId,
    refetchInterval: 30000,
  });

  const { data: pipelineStatus } = useQuery({
    queryKey: ["pipeline-status"],
    queryFn: fetchPipelineStatus,
    refetchInterval: (query) =>
      query.state.data?.running ? 3000 : 15000,
  });
  const runningRunIds = pipelineStatus?.running_run_ids ?? [];
  const isAnyRunning = pipelineStatus?.running ?? false;

  const { data: runs } = useQuery({
    queryKey: ["source-runs", mapId],
    queryFn: () => fetchRunsBySource(mapId!, 30),
    enabled: !!mapId,
    refetchInterval: isAnyRunning ? 5000 : 30000,
  });

  const { data: articles } = useQuery({
    queryKey: ["source-articles", mapId],
    queryFn: () => fetchSourceArticles(mapId!, 50),
    enabled: !!mapId,
    staleTime: 30000,
  });

  // Live log polling
  const scrollToBottom = useCallback(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, []);

  const isDrawerRunActive = drawerRunId !== null && runningRunIds.includes(drawerRunId);

  useEffect(() => {
    if (drawerRunId === null) {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
      setDrawerLogs([]);
      lastLogIdRef.current = 0;
      return;
    }

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
      if (pollIntervalRef.current) { clearInterval(pollIntervalRef.current); pollIntervalRef.current = null; }
    };
  }, [drawerRunId, isDrawerRunActive, scrollToBottom]);

  // Mutations
  const triggerMutation = useMutation({
    mutationFn: () => triggerScrape([mapId!]),
    onSuccess: () => {
      message.success(`Сбор запущен: ${mapId}`);
      queryClient.invalidateQueries({ queryKey: ["source-runs", mapId] });
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] });
    },
    onError: () => message.warning("Этот источник уже запущен"),
  });

  const cancelRunMutation = useMutation({
    mutationFn: (runId: number) => cancelScrapeRun(runId),
    onSuccess: () => {
      message.info("Запрос на отмену отправлен");
      queryClient.invalidateQueries({ queryKey: ["pipeline-status"] });
      queryClient.invalidateQueries({ queryKey: ["source-runs", mapId] });
    },
  });

  const cronMutation = useMutation({
    mutationFn: (cron: string) => updateScrapeMap(mapId!, { cron_expression: cron || null }),
    onSuccess: () => {
      message.success("Расписание обновлено");
      setCronModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ["scrape-map", mapId] });
      queryClient.invalidateQueries({ queryKey: ["scrape-maps"] });
    },
    onError: (err: Error) => message.error(err.message || "Ошибка"),
  });

  // Load article body on expand
  const onExpandArticle = async (expanded: boolean, record: SourceArticle) => {
    if (!expanded || expandedBodies[record.id] !== undefined) return;
    try {
      const detail = await fetchSourceArticleDetail(mapId!, record.id);
      setExpandedBodies((prev) => ({ ...prev, [record.id]: detail }));
    } catch {
      setExpandedBodies((prev) => ({ ...prev, [record.id]: null }));
    }
  };

  // Parse sitemap JSON
  let parsedSitemap: object | null = null;
  try {
    if (mapData?.sitemap_json) parsedSitemap = JSON.parse(mapData.sitemap_json);
  } catch { /* ignore */ }

  // Runs table
  const runsColumns = [
    { title: "Статус", dataIndex: "status", key: "status", width: 100, render: (s: string) => <Tag color={STATUS_COLOR[s] || "default"}>{s}</Tag> },
    { title: "Начало", dataIndex: "started_at", key: "started_at", render: (d: string) => dayjs(d).format("YYYY-MM-DD HH:mm") },
    { title: "Найдено", dataIndex: "articles_found", key: "articles_found", width: 90 },
    { title: "Новых", dataIndex: "articles_new", key: "articles_new", width: 80 },
    { title: "Ошибка", dataIndex: "error_message", key: "error_message", ellipsis: true, render: (e: string | null) => e ? <Typography.Text type="danger" ellipsis>{e}</Typography.Text> : null },
    {
      title: "Логи", key: "logs", width: 100,
      render: (_: unknown, record: ScrapeRun) => (
        <Button size="small" icon={<FileTextOutlined />} onClick={(e) => { e.stopPropagation(); setDrawerRunId(record.id); }}>Открыть</Button>
      ),
    },
  ];

  // Articles table
  const articlesColumns = [
    { title: "Заголовок", dataIndex: "title", key: "title", ellipsis: true },
    { title: "Категория", dataIndex: "category", key: "category", width: 120, render: (c: string | null) => c || "—" },
    { title: "Дата публикации", dataIndex: "published_date", key: "published_date", width: 140, render: (d: string | null) => d ? dayjs(d).format("YYYY-MM-DD") : "—" },
    { title: "Слов", dataIndex: "word_count", key: "word_count", width: 80 },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate("/settings")}>Назад к сборщикам</Button>
      </Space>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{mapData?.name || mapId}</Typography.Title>
          <Space style={{ marginTop: 4 }}>
            <Tag>{mapData?.country || ""}</Tag>
            <Tag color={mapData?.active ? "green" : "default"}>{mapData?.active ? "Активен" : "Выключен"}</Tag>
          </Space>
        </div>
        <Space>
          <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => triggerMutation.mutate()} loading={triggerMutation.isPending}>Запустить сбор</Button>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/settings/maps/${mapId}`)}>Редактировать карту</Button>
        </Space>
      </div>

      {/* Stats */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card><Statistic title="Всего запусков" value={detailStats?.total_runs ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title="Успешных" value={detailStats?.success_runs ?? 0} valueStyle={{ color: "#52c41a" }} /></Card></Col>
        <Col span={6}><Card><Statistic title="Ошибок" value={detailStats?.failed_runs ?? 0} valueStyle={{ color: "#ff4d4f" }} /></Card></Col>
        <Col span={6}><Card><Statistic title="Статей собрано" value={detailStats?.total_articles ?? 0} /></Card></Col>
      </Row>

      {/* Schedule */}
      <Card size="small" style={{ marginBottom: 16 }} title="Расписание"
        extra={<Button size="small" icon={<ClockCircleOutlined />} onClick={() => { setCronValue(mapData?.cron_expression || ""); setCronModalOpen(true); }}>Редактировать</Button>}
      >
        {mapData?.cron_expression
          ? <Typography.Text>Cron: <Tag color="purple">{mapData.cron_expression}</Tag></Typography.Text>
          : <Typography.Text type="secondary">Глобальное расписание (интервал по умолчанию)</Typography.Text>
        }
        {detailStats?.last_run_at && (
          <Typography.Text type="secondary" style={{ marginLeft: 16 }}>Последний запуск: {dayjs(detailStats.last_run_at).fromNow()}</Typography.Text>
        )}
      </Card>

      {/* Runs */}
      <Card title="Последние запуски" style={{ marginBottom: 16 }}>
        <Table columns={runsColumns} dataSource={runs || []} rowKey="id" pagination={{ pageSize: 10 }} size="small"
          onRow={(record) => ({ onClick: () => setDrawerRunId(record.id), style: { cursor: "pointer" } })}
        />
      </Card>

      {/* Articles — body loaded on expand */}
      <Card title={`Собранные статьи (${articles?.length ?? 0})`} style={{ marginBottom: 16 }}>
        <Table
          columns={articlesColumns}
          dataSource={articles || []}
          rowKey="id"
          pagination={{ pageSize: 10 }}
          size="small"
          expandable={{
            onExpand: onExpandArticle,
            expandedRowRender: (record: SourceArticle) => {
              const detail = expandedBodies[record.id];
              if (detail === undefined) return <Typography.Text type="secondary">Загрузка...</Typography.Text>;
              if (detail === null) return <Typography.Text type="danger">Ошибка загрузки</Typography.Text>;
              return (
                <pre style={{
                  maxHeight: 400, overflow: "auto", background: "#f5f5f5", padding: 12, borderRadius: 6,
                  fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word",
                }}>
                  {JSON.stringify({
                    id: detail.id, url: detail.url, title: detail.title, author: detail.author,
                    country: detail.country, category: detail.category,
                    published_date: detail.published_date, scraped_at: detail.scraped_at,
                    word_count: detail.word_count, body: detail.body,
                  }, null, 2)}
                </pre>
              );
            },
          }}
        />
      </Card>

      {/* Sitemap JSON */}
      <Collapse
        items={[{
          key: "json", label: "JSON карты сбора",
          children: parsedSitemap
            ? <pre style={{ maxHeight: 500, overflow: "auto", background: "#f5f5f5", padding: 12, borderRadius: 6, fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{JSON.stringify(parsedSitemap, null, 2)}</pre>
            : <Typography.Text type="secondary">Нет данных</Typography.Text>,
        }]}
        style={{ marginBottom: 16 }}
      />

      {/* Cron Modal */}
      <Modal title="Расписание сбора (cron)" open={cronModalOpen} onCancel={() => setCronModalOpen(false)}
        onOk={() => cronMutation.mutate(cronValue)} okText="Сохранить" cancelText="Отмена" confirmLoading={cronMutation.isPending} destroyOnClose>
        <Typography.Paragraph type="secondary">
          Введите cron-выражение для расписания сбора этого источника. Оставьте пустым для глобального расписания.
        </Typography.Paragraph>
        <Input value={cronValue} onChange={(e) => setCronValue(e.target.value)} placeholder="0 */6 * * *" style={{ fontFamily: "'Consolas', 'Monaco', monospace" }} />
        <Typography.Text type="secondary" style={{ display: "block", marginTop: 8, fontSize: 12 }}>
          Примеры: "0 */6 * * *" (каждые 6 часов), "0 8 * * *" (ежедневно в 8:00), "0 0 * * 1" (каждый понедельник)
        </Typography.Text>
      </Modal>

      {/* Drawer */}
      <Drawer title={`Запуск #${drawerRunId}`} open={drawerRunId !== null} onClose={() => setDrawerRunId(null)} width={700} destroyOnClose>
        {isDrawerRunActive && (
          <Button danger icon={<StopOutlined />} onClick={() => cancelRunMutation.mutate(drawerRunId!)} loading={cancelRunMutation.isPending} style={{ marginBottom: 16 }}>
            Отменить этот запуск
          </Button>
        )}
        <Typography.Title level={5} style={{ marginBottom: 8 }}>
          Записи лога ({drawerLogs.length})
          {isDrawerRunActive && <Tag color="blue" style={{ marginLeft: 8, fontWeight: "normal" }}>обновляется...</Tag>}
        </Typography.Title>
        <div ref={logContainerRef} style={{
          maxHeight: "calc(100vh - 200px)", overflow: "auto", background: "#1e1e1e", borderRadius: 6,
          padding: "12px 16px", fontFamily: "'Consolas', 'Monaco', monospace", fontSize: 12, lineHeight: 1.6,
        }}>
          {drawerLogs.length === 0
            ? <span style={{ color: "#666" }}>Нет записей лога.</span>
            : drawerLogs.map((entry) => (
              <div key={entry.id} style={{ marginBottom: 2 }}>
                <span style={{ color: "#888" }}>{dayjs(entry.timestamp).format("HH:mm:ss")}</span>{" "}
                <span style={{ color: entry.level === "ERROR" ? "#ff4d4f" : entry.level === "WARNING" ? "#faad14" : "#91caff" }}>[{entry.level}]</span>{" "}
                <span style={{ color: "#d4d4d4" }}>{entry.message}</span>
              </div>
            ))
          }
        </div>
      </Drawer>
    </div>
  );
}
