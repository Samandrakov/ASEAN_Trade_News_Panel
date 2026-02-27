import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, Col, Empty, Row, Select, Space, Typography } from "antd";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  fetchSentimentTrend,
  fetchTagDistribution,
  fetchTimeline,
  fetchWordFrequency,
} from "../api/analytics";
import { fetchCountries } from "../api/news";
import WordCloud from "../components/WordCloud";
import { COUNTRY_NAMES } from "../constants";

const COLORS = [
  "#1677ff",
  "#52c41a",
  "#faad14",
  "#ff4d4f",
  "#722ed1",
  "#13c2c2",
  "#eb2f96",
  "#fa8c16",
  "#a0d911",
  "#2f54eb",
];

export default function Dashboard() {
  const [country, setCountry] = useState<string | undefined>();
  const [granularity, setGranularity] = useState("day");

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: fetchCountries,
  });

  const { data: timeline } = useQuery({
    queryKey: ["timeline", country, granularity],
    queryFn: () => fetchTimeline({ country, granularity }),
  });

  const { data: topicDist } = useQuery({
    queryKey: ["tag-dist-topic", country],
    queryFn: () => fetchTagDistribution({ tag_type: "topic", country }),
  });

  const { data: countryDist } = useQuery({
    queryKey: ["tag-dist-country", country],
    queryFn: () =>
      fetchTagDistribution({ tag_type: "country_mention", country }),
  });

  const { data: wordFreq } = useQuery({
    queryKey: ["word-frequency", country],
    queryFn: () => fetchWordFrequency({ country, top_n: 80 }),
  });

  const { data: sentimentTrend } = useQuery({
    queryKey: ["sentiment-trend", country, granularity],
    queryFn: () => fetchSentimentTrend({ country, granularity: granularity as "day" | "week" | "month" }),
  });

  return (
    <div>
      <Typography.Title level={3}>Аналитика</Typography.Title>
      <Typography.Paragraph type="secondary">
        Визуализация данных по собранным новостям
      </Typography.Paragraph>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="Все страны"
          allowClear
          style={{ width: 180 }}
          onChange={setCountry}
          options={
            countries?.map((c) => ({
              value: c.code,
              label: COUNTRY_NAMES[c.code] || c.name,
            })) || []
          }
        />
        <Select
          value={granularity}
          style={{ width: 140 }}
          onChange={setGranularity}
          options={[
            { value: "day", label: "По дням" },
            { value: "week", label: "По неделям" },
            { value: "month", label: "По месяцам" },
          ]}
        />
      </Space>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="Хронология публикаций">
            {timeline && timeline.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Area
                    type="monotone"
                    dataKey="count"
                    name="Статей"
                    stroke="#1677ff"
                    fill="#1677ff"
                    fillOpacity={0.3}
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Распределение по темам">
            {topicDist && topicDist.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <PieChart>
                  <Pie
                    data={topicDist}
                    dataKey="count"
                    nameKey="tag"
                    cx="50%"
                    cy="50%"
                    outerRadius={120}
                    label={((props: any) =>   // eslint-disable-line @typescript-eslint/no-explicit-any
                      `${props.tag ?? ""} (${((props.percent ?? 0) * 100).toFixed(0)}%)`
                    ) as any}
                  >
                    {topicDist.map((_, i) => (
                      <Cell
                        key={i}
                        fill={COLORS[i % COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных" />
            )}
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Упоминания стран">
            {countryDist && countryDist.length > 0 ? (
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={countryDist}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tag" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" name="Упоминаний">
                    {countryDist.map((_, i) => (
                      <Cell
                        key={i}
                        fill={COLORS[i % COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных" />
            )}
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Тренд тональности">
            {sentimentTrend && sentimentTrend.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={sentimentTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="period" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="positive" name="Позитивные" fill="#52c41a" stackId="a" />
                  <Bar dataKey="neutral" name="Нейтральные" fill="#8c8c8c" stackId="a" />
                  <Bar dataKey="negative" name="Негативные" fill="#ff4d4f" stackId="a" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <Empty description="Нет данных по настроениям (требуется LLM-тегирование)" />
            )}
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Облако слов">
            {wordFreq && wordFreq.length > 0 ? (
              <WordCloud words={wordFreq} />
            ) : (
              <Empty description="Нет данных" />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
