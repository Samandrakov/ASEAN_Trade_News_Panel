import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Card,
  Descriptions,
  Divider,
  Spin,
  Tag,
  Typography,
} from "antd";
import { ArrowLeftOutlined, LinkOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { useNavigate, useParams } from "react-router-dom";
import { fetchArticle } from "../api/news";

const TAG_COLORS: Record<string, string> = {
  country_mention: "blue",
  topic: "green",
  sector: "purple",
  sentiment: "orange",
};

const TAG_LABELS: Record<string, string> = {
  country_mention: "Country Mentions",
  topic: "Topics",
  sector: "Sectors",
  sentiment: "Sentiment",
};

export default function ArticleDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: article, isLoading } = useQuery({
    queryKey: ["article", id],
    queryFn: () => fetchArticle(Number(id)),
    enabled: !!id,
  });

  if (isLoading) return <Spin size="large" />;
  if (!article) return <div>Article not found</div>;

  const tagsByType = article.tags.reduce(
    (acc, t) => {
      if (!acc[t.tag_type]) acc[t.tag_type] = [];
      acc[t.tag_type].push(t);
      return acc;
    },
    {} as Record<string, typeof article.tags>
  );

  return (
    <div>
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(-1)}
        style={{ marginBottom: 16 }}
      >
        Back to registry
      </Button>

      <Card>
        <Typography.Title level={3}>{article.title}</Typography.Title>

        <Descriptions column={2} style={{ marginBottom: 16 }} bordered size="small">
          <Descriptions.Item label="Source">
            {article.source_display}
          </Descriptions.Item>
          <Descriptions.Item label="Source Country">
            {article.country}
          </Descriptions.Item>
          <Descriptions.Item label="Category">
            {article.category || "N/A"}
          </Descriptions.Item>
          <Descriptions.Item label="Author">
            {article.author || "N/A"}
          </Descriptions.Item>
          <Descriptions.Item label="Published">
            {article.published_date
              ? dayjs(article.published_date).format("MMMM D, YYYY")
              : "N/A"}
          </Descriptions.Item>
          <Descriptions.Item label="Scraped">
            {dayjs(article.scraped_at).format("MMMM D, YYYY HH:mm")}
          </Descriptions.Item>
          <Descriptions.Item label="Word Count">
            {article.word_count || "N/A"}
          </Descriptions.Item>
          <Descriptions.Item label="URL">
            <a href={article.url} target="_blank" rel="noreferrer">
              Original
            </a>
          </Descriptions.Item>
        </Descriptions>

        {Object.entries(tagsByType).map(([type, typeTags]) => (
          <div key={type} style={{ marginBottom: 12 }}>
            <Typography.Text strong>
              {TAG_LABELS[type] || type}:{" "}
            </Typography.Text>
            {typeTags.map((t) => (
              <Tag key={`${t.tag_type}-${t.tag_value}`} color={TAG_COLORS[t.tag_type]}>
                {t.tag_value}
              </Tag>
            ))}
          </div>
        ))}

        {article.summary && (
          <>
            <Divider />
            <Typography.Title level={5}>AI Summary</Typography.Title>
            <Typography.Paragraph>{article.summary}</Typography.Paragraph>
          </>
        )}

        <Divider />
        <Typography.Title level={5}>Full Text</Typography.Title>
        <Typography.Paragraph
          style={{ whiteSpace: "pre-wrap", lineHeight: 1.8 }}
        >
          {article.body}
        </Typography.Paragraph>

        <Divider />
        <Button
          type="link"
          icon={<LinkOutlined />}
          href={article.url}
          target="_blank"
        >
          Read original article
        </Button>
      </Card>
    </div>
  );
}
