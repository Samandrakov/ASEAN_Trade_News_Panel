import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import { PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import type { Dayjs } from "dayjs";
import { Link } from "react-router-dom";
import { fetchCountries, fetchNews, fetchTags } from "../api/news";
import { fetchFeeds, createFeed, deleteFeed } from "../api/feeds";
import type { Article, NewsFilters, FeedFilters, SavedFeed } from "../types";

const { RangePicker } = DatePicker;
const { Search } = Input;

const COUNTRY_NAMES: Record<string, string> = {
  ID: "Индонезия",
  VN: "Вьетнам",
  MY: "Малайзия",
};

const TAG_COLORS: Record<string, string> = {
  country_mention: "blue",
  topic: "green",
  sector: "purple",
  sentiment: "orange",
};

const FEED_COLOR_OPTIONS = [
  { value: "blue", label: "Синий" },
  { value: "green", label: "Зелёный" },
  { value: "red", label: "Красный" },
  { value: "orange", label: "Оранжевый" },
  { value: "purple", label: "Фиолетовый" },
  { value: "cyan", label: "Голубой" },
];

const FILTER_LABELS: Record<string, string> = {
  country: "Страна",
  tag_type: "Тип тега",
  tag_value: "Тег",
  date_from: "Дата от",
  date_to: "Дата до",
  search: "Поиск",
};

function describeFilters(filters: NewsFilters): string {
  const parts: string[] = [];
  if (filters.country) parts.push(`${FILTER_LABELS.country}: ${COUNTRY_NAMES[filters.country] || filters.country}`);
  if (filters.tag_value) parts.push(`${FILTER_LABELS.tag_value}: ${filters.tag_value}`);
  if (filters.date_from) parts.push(`${FILTER_LABELS.date_from}: ${filters.date_from}`);
  if (filters.date_to) parts.push(`${FILTER_LABELS.date_to}: ${filters.date_to}`);
  if (filters.search) parts.push(`${FILTER_LABELS.search}: "${filters.search}"`);
  return parts.join(", ");
}

export default function NewsArchive() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<NewsFilters>({
    page: 1,
    page_size: 20,
  });
  const [activeFeedId, setActiveFeedId] = useState<number | null>(null);
  const [searchValue, setSearchValue] = useState("");
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveForm] = Form.useForm();

  const { data, isLoading } = useQuery({
    queryKey: ["news", filters],
    queryFn: () => fetchNews(filters),
  });

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: fetchCountries,
  });

  const { data: tags } = useQuery({
    queryKey: ["tags"],
    queryFn: fetchTags,
  });

  const { data: feeds } = useQuery({
    queryKey: ["feeds"],
    queryFn: fetchFeeds,
  });

  const createMutation = useMutation({
    mutationFn: createFeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feeds"] });
      message.success("Подборка сохранена");
      setShowSaveModal(false);
      saveForm.resetFields();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteFeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feeds"] });
      message.success("Подборка удалена");
    },
  });

  const topicTags = tags?.filter((t) => t.tag_type === "topic") || [];
  const sectorTags = tags?.filter((t) => t.tag_type === "sector") || [];
  const countryMentionTags =
    tags?.filter((t) => t.tag_type === "country_mention") || [];

  const hasActiveFilters = !!(
    filters.country ||
    filters.tag_type ||
    filters.tag_value ||
    filters.date_from ||
    filters.date_to ||
    filters.search
  );

  // Determine which tag select should show a value
  const topicValue = filters.tag_type === "topic" ? filters.tag_value : undefined;
  const sectorValue = filters.tag_type === "sector" ? filters.tag_value : undefined;
  const countryMentionValue = filters.tag_type === "country_mention" ? filters.tag_value : undefined;

  const dateRange: [Dayjs, Dayjs] | null =
    filters.date_from && filters.date_to
      ? [dayjs(filters.date_from), dayjs(filters.date_to)]
      : null;

  const updateFilter = (patch: Partial<NewsFilters>) => {
    setActiveFeedId(null);
    setFilters((f) => ({ ...f, ...patch, page: 1 }));
  };

  const loadFeed = (feed: SavedFeed) => {
    const parsed: FeedFilters = JSON.parse(feed.filters_json);
    const newFilters: NewsFilters = {
      page: 1,
      page_size: filters.page_size,
      country: parsed.country,
      tag_type: parsed.tag_type,
      tag_value: parsed.tag_value,
      date_from: parsed.date_from,
      date_to: parsed.date_to,
      search: parsed.search,
    };
    setFilters(newFilters);
    setSearchValue(parsed.search || "");
    setActiveFeedId(feed.id);
  };

  const resetFilters = () => {
    setFilters({ page: 1, page_size: filters.page_size });
    setSearchValue("");
    setActiveFeedId(null);
  };

  const handleDeleteFeed = (feedId: number, feedName: string) => {
    Modal.confirm({
      title: "Удалить подборку",
      content: `Удалить подборку «${feedName}»?`,
      okText: "Удалить",
      okType: "danger",
      cancelText: "Отмена",
      onOk: () => {
        if (activeFeedId === feedId) {
          resetFilters();
        }
        deleteMutation.mutate(feedId);
      },
    });
  };

  const handleSaveFeed = () => {
    saveForm.validateFields().then((values) => {
      const filtersToSave: FeedFilters = {};
      if (filters.country) filtersToSave.country = filters.country;
      if (filters.tag_type) filtersToSave.tag_type = filters.tag_type;
      if (filters.tag_value) filtersToSave.tag_value = filters.tag_value;
      if (filters.date_from) filtersToSave.date_from = filters.date_from;
      if (filters.date_to) filtersToSave.date_to = filters.date_to;
      if (filters.search) filtersToSave.search = filters.search;

      createMutation.mutate({
        name: values.name,
        description: values.description || undefined,
        filters_json: JSON.stringify(filtersToSave),
        color: values.color || undefined,
      });
    });
  };

  const columns: ColumnsType<Article> = [
    {
      title: "Дата",
      dataIndex: "published_date",
      key: "date",
      width: 110,
      render: (d: string | null) =>
        d ? dayjs(d).format("YYYY-MM-DD") : "Н/Д",
      sorter: (a, b) =>
        (a.published_date || "").localeCompare(b.published_date || ""),
    },
    {
      title: "Заголовок",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (title: string, record: Article) => (
        <Tooltip title={title}>
          <Link to={`/news/${record.id}`}>{title}</Link>
        </Tooltip>
      ),
    },
    {
      title: "Источник",
      dataIndex: "source_display",
      key: "source",
      width: 140,
    },
    {
      title: "Страна",
      dataIndex: "country",
      key: "country",
      width: 100,
      render: (c: string) => COUNTRY_NAMES[c] || c,
    },
    {
      title: "Категория",
      dataIndex: "category",
      key: "category",
      width: 130,
      render: (c: string | null) =>
        c ? <Tag>{c}</Tag> : <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: "Слов",
      dataIndex: "word_count",
      key: "word_count",
      width: 70,
      render: (w: number | null) => w || "-",
      sorter: (a, b) => (a.word_count || 0) - (b.word_count || 0),
    },
    {
      title: "Теги",
      key: "tags",
      width: 280,
      render: (_: unknown, record: Article) => (
        <Space size={[0, 4]} wrap>
          {record.tags.slice(0, 5).map((t) => (
            <Tag
              key={`${t.tag_type}-${t.tag_value}`}
              color={TAG_COLORS[t.tag_type]}
            >
              {t.tag_value}
            </Tag>
          ))}
          {record.tags.length > 5 && (
            <Tag>+{record.tags.length - 5}</Tag>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={3}>Реестр новостей</Typography.Title>
      <Typography.Paragraph type="secondary">
        Структурированный архив экономических новостей Индонезии, Вьетнама и
        Малайзии
      </Typography.Paragraph>

      {/* Feed bar */}
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap size="small">
          <Tag
            color={activeFeedId === null && !hasActiveFilters ? "blue" : undefined}
            style={{ cursor: "pointer", fontSize: 13, padding: "2px 10px" }}
            onClick={resetFilters}
          >
            Все новости
          </Tag>
          {feeds?.map((feed) => (
            <Tag
              key={feed.id}
              color={activeFeedId === feed.id ? (feed.color || "blue") : (feed.color || undefined)}
              closable
              style={{
                cursor: "pointer",
                fontSize: 13,
                padding: "2px 10px",
                opacity: activeFeedId === feed.id ? 1 : 0.7,
              }}
              onClick={() => loadFeed(feed)}
              onClose={(e) => {
                e.preventDefault();
                handleDeleteFeed(feed.id, feed.name);
              }}
            >
              {feed.name}
            </Tag>
          ))}
          <Button
            type="dashed"
            size="small"
            icon={<PlusOutlined />}
            onClick={() => setShowSaveModal(true)}
            disabled={!hasActiveFilters}
          >
            Сохранить подборку
          </Button>
        </Space>
      </Card>

      {/* Filters */}
      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Select
            placeholder="Страна"
            allowClear
            value={filters.country}
            style={{ width: 160 }}
            onChange={(v) => updateFilter({ country: v })}
            options={
              countries?.map((c) => ({
                value: c.code,
                label: `${COUNTRY_NAMES[c.code] || c.name} (${c.count})`,
              })) || []
            }
          />
          <Select
            placeholder="Тема"
            allowClear
            value={topicValue}
            style={{ width: 180 }}
            onChange={(v) =>
              updateFilter({
                tag_type: v ? "topic" : undefined,
                tag_value: v,
              })
            }
            options={topicTags.map((t) => ({
              value: t.tag_value,
              label: `${t.tag_value} (${t.count})`,
            }))}
          />
          <Select
            placeholder="Сектор"
            allowClear
            value={sectorValue}
            style={{ width: 180 }}
            onChange={(v) =>
              updateFilter({
                tag_type: v ? "sector" : undefined,
                tag_value: v,
              })
            }
            options={sectorTags.map((t) => ({
              value: t.tag_value,
              label: `${t.tag_value} (${t.count})`,
            }))}
          />
          <Select
            placeholder="Упоминание страны"
            allowClear
            value={countryMentionValue}
            style={{ width: 180 }}
            onChange={(v) =>
              updateFilter({
                tag_type: v ? "country_mention" : undefined,
                tag_value: v,
              })
            }
            options={countryMentionTags.map((t) => ({
              value: t.tag_value,
              label: `${t.tag_value} (${t.count})`,
            }))}
          />
          <RangePicker
            value={dateRange}
            onChange={(dates) => {
              updateFilter({
                date_from: dates?.[0]?.format("YYYY-MM-DD"),
                date_to: dates?.[1]?.format("YYYY-MM-DD"),
              });
            }}
          />
          <Search
            placeholder="Поиск по статьям..."
            allowClear
            value={searchValue}
            style={{ width: 250 }}
            onChange={(e) => setSearchValue(e.target.value)}
            onSearch={(v) => updateFilter({ search: v || undefined })}
          />
        </Space>
      </Card>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{
          current: data?.page || 1,
          pageSize: data?.page_size || 20,
          total: data?.total || 0,
          onChange: (page, pageSize) =>
            setFilters((f) => ({ ...f, page, page_size: pageSize })),
          showSizeChanger: true,
          showTotal: (total) => `Всего: ${total} статей`,
        }}
      />

      {/* Save feed modal */}
      <Modal
        title="Сохранить подборку"
        open={showSaveModal}
        onOk={handleSaveFeed}
        onCancel={() => {
          setShowSaveModal(false);
          saveForm.resetFields();
        }}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={createMutation.isPending}
        destroyOnClose
      >
        <Form form={saveForm} layout="vertical">
          <Form.Item
            name="name"
            label="Название подборки"
            rules={[{ required: true, message: "Введите название" }]}
          >
            <Input placeholder="Например: Торговля РФ-АСЕАН" />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea
              rows={2}
              placeholder="Краткое описание подборки (необязательно)"
            />
          </Form.Item>
          <Form.Item name="color" label="Цвет">
            <Select
              placeholder="Выберите цвет"
              allowClear
              options={FEED_COLOR_OPTIONS}
            />
          </Form.Item>
        </Form>
        <Typography.Text type="secondary">
          Текущие фильтры: {describeFilters(filters) || "нет"}
        </Typography.Text>
      </Modal>
    </div>
  );
}
