import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  message,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { PlayCircleOutlined, ReloadOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { fetchScrapeRuns, triggerScrape } from "../api/scrape";
import type { ScrapeRun } from "../types";

const SOURCES = [
  { key: "jakarta_post", name: "The Jakarta Post", country: "ID" },
  { key: "kompas", name: "Kompas.com", country: "ID" },
  { key: "antara", name: "Antara News", country: "ID" },
  { key: "vnexpress", name: "VnExpress International", country: "VN" },
  { key: "vietnam_news", name: "Vietnam News", country: "VN" },
  { key: "tuoitre", name: "Tuoi Tre News", country: "VN" },
  { key: "thestar", name: "The Star", country: "MY" },
  { key: "malaymail", name: "Malay Mail", country: "MY" },
  { key: "bernama", name: "Bernama", country: "MY" },
];

export default function Settings() {
  const queryClient = useQueryClient();

  const { data: runs, isLoading } = useQuery({
    queryKey: ["scrape-runs"],
    queryFn: () => fetchScrapeRuns(50),
    refetchInterval: 10000,
  });

  const triggerAll = useMutation({
    mutationFn: () => triggerScrape(),
    onSuccess: () => {
      message.success("Scraping started for all sources");
      queryClient.invalidateQueries({ queryKey: ["scrape-runs"] });
    },
  });

  const triggerOne = useMutation({
    mutationFn: (source: string) => triggerScrape([source]),
    onSuccess: (_, source) => {
      message.success(`Scraping started for ${source}`);
      queryClient.invalidateQueries({ queryKey: ["scrape-runs"] });
    },
  });

  const statusColor: Record<string, string> = {
    success: "green",
    failed: "red",
    running: "blue",
    partial: "orange",
  };

  const runsColumns = [
    {
      title: "Source",
      dataIndex: "source",
      key: "source",
    },
    {
      title: "Started",
      dataIndex: "started_at",
      key: "started_at",
      render: (d: string) => dayjs(d).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (s: string) => (
        <Tag color={statusColor[s] || "default"}>{s}</Tag>
      ),
    },
    {
      title: "Found",
      dataIndex: "articles_found",
      key: "articles_found",
    },
    {
      title: "New",
      dataIndex: "articles_new",
      key: "articles_new",
    },
    {
      title: "Error",
      dataIndex: "error_message",
      key: "error_message",
      ellipsis: true,
      render: (e: string | null) =>
        e ? (
          <Typography.Text type="danger" ellipsis>
            {e}
          </Typography.Text>
        ) : null,
    },
  ];

  return (
    <div>
      <Typography.Title level={3}>Scraper Settings</Typography.Title>

      <Card title="Sources" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: "100%" }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => triggerAll.mutate()}
            loading={triggerAll.isPending}
            size="large"
          >
            Run All Scrapers
          </Button>

          <Table
            dataSource={SOURCES}
            rowKey="key"
            pagination={false}
            columns={[
              { title: "Source", dataIndex: "name", key: "name" },
              { title: "Country", dataIndex: "country", key: "country" },
              {
                title: "Action",
                key: "action",
                render: (_: unknown, record: (typeof SOURCES)[0]) => (
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => triggerOne.mutate(record.key)}
                  >
                    Scrape
                  </Button>
                ),
              },
            ]}
          />
        </Space>
      </Card>

      <Card title="Recent Scrape Runs">
        <Table
          columns={runsColumns}
          dataSource={runs || []}
          rowKey="id"
          loading={isLoading}
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}
