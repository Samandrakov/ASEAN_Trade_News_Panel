import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, Modal, Table, Tag, Tooltip, Typography, message } from "antd";
import { DeleteOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { fetchBookmarks, deleteBookmarkByArticle } from "../api/bookmarks";
import { COUNTRY_NAMES } from "../constants";
import type { Bookmark } from "../types";

export default function Bookmarks() {
  const queryClient = useQueryClient();
  const [msg, ctxHolder] = message.useMessage();

  const { data: bookmarks, isLoading } = useQuery({
    queryKey: ["bookmarks"],
    queryFn: fetchBookmarks,
  });

  const removeMut = useMutation({
    mutationFn: (article_id: number) => deleteBookmarkByArticle(article_id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bookmarks"] });
      msg.success("Закладка удалена");
    },
  });

  const columns: ColumnsType<Bookmark> = [
    {
      title: "Заголовок",
      dataIndex: "article_title",
      key: "title",
      ellipsis: true,
      render: (title: string | null, record: Bookmark) =>
        title ? (
          <Tooltip title={title}>
            <Link to={`/news/${record.article_id}`}>{title}</Link>
          </Tooltip>
        ) : (
          <Typography.Text type="secondary">Статья удалена</Typography.Text>
        ),
    },
    {
      title: "Источник",
      dataIndex: "article_source_display",
      key: "source",
      width: 150,
      render: (v: string | null) => v || "-",
    },
    {
      title: "Страна",
      dataIndex: "article_country",
      key: "country",
      width: 120,
      render: (c: string | null) =>
        c ? <Tag>{COUNTRY_NAMES[c] || c}</Tag> : "-",
    },
    {
      title: "Добавлено",
      dataIndex: "created_at",
      key: "created_at",
      width: 130,
      render: (d: string) => dayjs(d).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "",
      key: "actions",
      width: 50,
      render: (_: unknown, record: Bookmark) => (
        <Tooltip title="Удалить из закладок">
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() =>
              Modal.confirm({
                title: "Удалить закладку?",
                onOk: () => removeMut.mutate(record.article_id),
                okText: "Да",
                cancelText: "Нет",
              })
            }
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div>
      {ctxHolder}
      <Typography.Title level={3} style={{ marginBottom: 4 }}>
        Закладки
      </Typography.Title>
      <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
        Сохранённые статьи для быстрого доступа
      </Typography.Paragraph>
      <Table
        columns={columns}
        dataSource={bookmarks || []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, showSizeChanger: true }}
        locale={{ emptyText: "Нет закладок" }}
      />
    </div>
  );
}
