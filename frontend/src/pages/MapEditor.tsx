import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Card,
  Input,
  message,
  Space,
  Typography,
  Alert,
  Spin,
  Descriptions,
} from "antd";
import { ArrowLeftOutlined, SaveOutlined, CheckOutlined } from "@ant-design/icons";
import { fetchScrapeMap, updateScrapeMap, createScrapeMap } from "../api/scrapeMaps";

export default function MapEditor() {
  const { mapId } = useParams<{ mapId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isNew = mapId === "new";

  const [jsonText, setJsonText] = useState("");
  const [parseError, setParseError] = useState<string | null>(null);

  const { data: mapData, isLoading } = useQuery({
    queryKey: ["scrape-map", mapId],
    queryFn: () => fetchScrapeMap(mapId!),
    enabled: !isNew && !!mapId,
  });

  useEffect(() => {
    if (mapData) {
      try {
        const parsed = JSON.parse(mapData.sitemap_json);
        setJsonText(JSON.stringify(parsed, null, 2));
      } catch {
        setJsonText(mapData.sitemap_json);
      }
    } else if (isNew) {
      const template = {
        _id: "new_source",
        startUrls: ["https://example.com/news"],
        sitemapSpecificationVersion: 1,
        rootSelector: { id: "_root", uuid: "0" },
        selectors: [
          {
            id: "article_links",
            type: "SelectorLink",
            uuid: "1",
            multiple: true,
            selector: "a[href]",
            parentSelectors: ["0"],
            extractAttribute: "href",
          },
          {
            id: "title",
            type: "SelectorText",
            uuid: "2",
            multiple: false,
            selector: "h1",
            parentSelectors: ["1"],
          },
          {
            id: "body",
            type: "SelectorText",
            uuid: "3",
            multiple: true,
            selector: "article",
            parentSelectors: ["1"],
          },
        ],
        _meta: {
          country: "",
          source_display: "New Source",
          url_filter_pattern: "",
          date_source: "selector",
          date_selector_formats: [],
          category_mapping: {},
          min_body_length: 200,
          author_selectors: [],
        },
      };
      setJsonText(JSON.stringify(template, null, 2));
    }
  }, [mapData, isNew]);

  const validateJson = () => {
    try {
      const data = JSON.parse(jsonText);
      if (!data._id) throw new Error("Missing _id");
      if (!data.startUrls) throw new Error("Missing startUrls");
      if (!data.selectors) throw new Error("Missing selectors");
      if (!data._meta) throw new Error("Missing _meta");
      if (!data._meta.country) throw new Error("Missing _meta.country");
      if (!data._meta.source_display) throw new Error("Missing _meta.source_display");
      setParseError(null);
      message.success("JSON валиден");
      return true;
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : "Invalid JSON";
      setParseError(errMsg);
      return false;
    }
  };

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (!validateJson()) throw new Error("Invalid JSON");
      if (isNew) {
        return createScrapeMap(jsonText);
      } else {
        return updateScrapeMap(mapId!, { sitemap_json: jsonText });
      }
    },
    onSuccess: () => {
      message.success(isNew ? "Карта создана" : "Карта обновлена");
      queryClient.invalidateQueries({ queryKey: ["scrape-maps"] });
      queryClient.invalidateQueries({ queryKey: ["scrape-map", mapId] });
      if (isNew) {
        navigate("/settings");
      }
    },
    onError: (err: Error) => {
      message.error(err.message || "Ошибка сохранения");
    },
  });

  let parsedMeta: Record<string, unknown> | null = null;
  try {
    const parsed = JSON.parse(jsonText);
    parsedMeta = parsed._meta || null;
  } catch {
    // ignore
  }

  if (isLoading) return <Spin size="large" />;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate("/settings")}
        >
          Назад к сборщикам
        </Button>
      </Space>

      <Typography.Title level={3}>
        {isNew ? "Создание карты сбора" : `Редактирование: ${mapData?.name || mapId}`}
      </Typography.Title>

      {parsedMeta && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="Идентификатор">
              {parsedMeta._id as string || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Источник">
              {(parsedMeta.source_display as string) || "—"}
            </Descriptions.Item>
            <Descriptions.Item label="Страна">
              {(parsedMeta.country as string) || "—"}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {parseError && (
        <Alert
          type="error"
          message="Ошибка валидации JSON"
          description={parseError}
          style={{ marginBottom: 16 }}
          closable
          onClose={() => setParseError(null)}
        />
      )}

      <Card
        title="JSON карты сбора"
        extra={
          <Space>
            <Button
              icon={<CheckOutlined />}
              onClick={validateJson}
            >
              Проверить
            </Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={() => saveMutation.mutate()}
              loading={saveMutation.isPending}
            >
              Сохранить
            </Button>
          </Space>
        }
      >
        <Input.TextArea
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          rows={30}
          style={{
            fontFamily: "'Consolas', 'Monaco', monospace",
            fontSize: 13,
          }}
        />
      </Card>
    </div>
  );
}
