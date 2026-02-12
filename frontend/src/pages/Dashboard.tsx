import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, Col, Row, Select, Space, Typography } from "antd";
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
  fetchTagDistribution,
  fetchTimeline,
  fetchWordFrequency,
} from "../api/analytics";
import { fetchCountries } from "../api/news";
import WordCloud from "../components/WordCloud";

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

  return (
    <div>
      <Typography.Title level={3}>Analytics Dashboard</Typography.Title>

      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="All countries"
          allowClear
          style={{ width: 180 }}
          onChange={setCountry}
          options={
            countries?.map((c) => ({
              value: c.code,
              label: c.name,
            })) || []
          }
        />
        <Select
          value={granularity}
          style={{ width: 120 }}
          onChange={setGranularity}
          options={[
            { value: "day", label: "Daily" },
            { value: "week", label: "Weekly" },
            { value: "month", label: "Monthly" },
          ]}
        />
      </Space>

      <Row gutter={[16, 16]}>
        <Col span={24}>
          <Card title="Articles Timeline">
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={timeline || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke="#1677ff"
                  fill="#1677ff"
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Topics Distribution">
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={topicDist || []}
                  dataKey="count"
                  nameKey="tag"
                  cx="50%"
                  cy="50%"
                  outerRadius={120}
                  label={({ tag, percent }) =>
                    `${tag} (${(percent * 100).toFixed(0)}%)`
                  }
                >
                  {(topicDist || []).map((_, i) => (
                    <Cell
                      key={i}
                      fill={COLORS[i % COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Country Mentions">
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={countryDist || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="tag" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#52c41a">
                  {(countryDist || []).map((_, i) => (
                    <Cell
                      key={i}
                      fill={COLORS[i % COLORS.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>

        <Col span={24}>
          <Card title="Word Cloud">
            <WordCloud words={wordFreq || []} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
