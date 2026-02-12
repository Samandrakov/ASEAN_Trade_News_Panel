import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Card,
  DatePicker,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { fetchCountries, fetchNews, fetchTags } from "../api/news";
import type { Article, NewsFilters } from "../types";

const { RangePicker } = DatePicker;
const { Search } = Input;

const COUNTRY_NAMES: Record<string, string> = {
  ID: "Indonesia",
  VN: "Vietnam",
  MY: "Malaysia",
};

const TAG_COLORS: Record<string, string> = {
  country_mention: "blue",
  topic: "green",
  sector: "purple",
  sentiment: "orange",
};

export default function NewsArchive() {
  const [filters, setFilters] = useState<NewsFilters>({
    page: 1,
    page_size: 20,
  });

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

  const topicTags = tags?.filter((t) => t.tag_type === "topic") || [];
  const sectorTags = tags?.filter((t) => t.tag_type === "sector") || [];
  const countryMentionTags =
    tags?.filter((t) => t.tag_type === "country_mention") || [];

  const columns: ColumnsType<Article> = [
    {
      title: "Date",
      dataIndex: "published_date",
      key: "date",
      width: 110,
      render: (d: string | null) =>
        d ? dayjs(d).format("YYYY-MM-DD") : "N/A",
      sorter: (a, b) =>
        (a.published_date || "").localeCompare(b.published_date || ""),
    },
    {
      title: "Title",
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
      title: "Source",
      dataIndex: "source_display",
      key: "source",
      width: 140,
    },
    {
      title: "Country",
      dataIndex: "country",
      key: "country",
      width: 100,
      render: (c: string) => COUNTRY_NAMES[c] || c,
    },
    {
      title: "Category",
      dataIndex: "category",
      key: "category",
      width: 130,
      render: (c: string | null) =>
        c ? <Tag>{c}</Tag> : <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: "Words",
      dataIndex: "word_count",
      key: "word_count",
      width: 70,
      render: (w: number | null) => w || "-",
      sorter: (a, b) => (a.word_count || 0) - (b.word_count || 0),
    },
    {
      title: "Tags",
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
      <Typography.Title level={3}>News Registry</Typography.Title>
      <Typography.Paragraph type="secondary">
        Structured archive of economic news from Indonesia, Vietnam, and Malaysia
      </Typography.Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
          <Select
            placeholder="Source country"
            allowClear
            style={{ width: 160 }}
            onChange={(v) =>
              setFilters((f) => ({ ...f, country: v, page: 1 }))
            }
            options={
              countries?.map((c) => ({
                value: c.code,
                label: `${c.name} (${c.count})`,
              })) || []
            }
          />
          <Select
            placeholder="Topic"
            allowClear
            style={{ width: 180 }}
            onChange={(v) =>
              setFilters((f) => ({
                ...f,
                tag_type: v ? "topic" : undefined,
                tag_value: v,
                page: 1,
              }))
            }
            options={topicTags.map((t) => ({
              value: t.tag_value,
              label: `${t.tag_value} (${t.count})`,
            }))}
          />
          <Select
            placeholder="Sector"
            allowClear
            style={{ width: 180 }}
            onChange={(v) =>
              setFilters((f) => ({
                ...f,
                tag_type: v ? "sector" : undefined,
                tag_value: v,
                page: 1,
              }))
            }
            options={sectorTags.map((t) => ({
              value: t.tag_value,
              label: `${t.tag_value} (${t.count})`,
            }))}
          />
          <Select
            placeholder="Country mention"
            allowClear
            style={{ width: 180 }}
            onChange={(v) =>
              setFilters((f) => ({
                ...f,
                tag_type: v ? "country_mention" : undefined,
                tag_value: v,
                page: 1,
              }))
            }
            options={countryMentionTags.map((t) => ({
              value: t.tag_value,
              label: `${t.tag_value} (${t.count})`,
            }))}
          />
          <RangePicker
            onChange={(dates) => {
              setFilters((f) => ({
                ...f,
                date_from: dates?.[0]?.format("YYYY-MM-DD"),
                date_to: dates?.[1]?.format("YYYY-MM-DD"),
                page: 1,
              }));
            }}
          />
          <Search
            placeholder="Search articles..."
            allowClear
            style={{ width: 250 }}
            onSearch={(v) =>
              setFilters((f) => ({ ...f, search: v || undefined, page: 1 }))
            }
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
          showTotal: (total) => `Total: ${total} articles`,
        }}
      />
    </div>
  );
}
