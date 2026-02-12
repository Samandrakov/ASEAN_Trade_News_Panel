import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  DatePicker,
  Select,
  Space,
  Spin,
  Typography,
} from "antd";
import { fetchCountries, summarizeArticles } from "../api/news";
import type { SummarizeResponse } from "../types";

const { RangePicker } = DatePicker;

export default function Summarize() {
  const [country, setCountry] = useState<string | undefined>();
  const [dateRange, setDateRange] = useState<
    [string | undefined, string | undefined]
  >([undefined, undefined]);
  const [result, setResult] = useState<SummarizeResponse | null>(null);

  const { data: countries } = useQuery({
    queryKey: ["countries"],
    queryFn: fetchCountries,
  });

  const mutation = useMutation({
    mutationFn: summarizeArticles,
    onSuccess: (data) => setResult(data),
  });

  const handleSummarize = () => {
    mutation.mutate({
      country,
      date_from: dateRange[0],
      date_to: dateRange[1],
      max_articles: 50,
    });
  };

  return (
    <div>
      <Typography.Title level={3}>News Summarization</Typography.Title>
      <Typography.Paragraph type="secondary">
        Generate an analytical summary of collected news using Claude AI. Focus
        on Russia-ASEAN trade cooperation prospects.
      </Typography.Paragraph>

      <Card style={{ marginBottom: 16 }}>
        <Space wrap size="middle">
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
          <RangePicker
            onChange={(dates) => {
              setDateRange([
                dates?.[0]?.format("YYYY-MM-DD"),
                dates?.[1]?.format("YYYY-MM-DD"),
              ]);
            }}
          />
          <Button
            type="primary"
            size="large"
            onClick={handleSummarize}
            loading={mutation.isPending}
          >
            Generate Summary
          </Button>
        </Space>
      </Card>

      {mutation.isPending && (
        <Card>
          <Spin size="large" />
          <Typography.Paragraph style={{ marginTop: 16 }}>
            Generating summary... This may take a minute.
          </Typography.Paragraph>
        </Card>
      )}

      {result && (
        <Card
          title={`Summary (${result.articles_count} articles analyzed)`}
        >
          <div
            style={{
              whiteSpace: "pre-wrap",
              lineHeight: 1.8,
              fontSize: 15,
            }}
          >
            {result.summary}
          </div>
        </Card>
      )}

      {mutation.isError && (
        <Card>
          <Typography.Text type="danger">
            Error generating summary. Please check that ANTHROPIC_API_KEY is
            configured and try again.
          </Typography.Text>
        </Card>
      )}
    </div>
  );
}
