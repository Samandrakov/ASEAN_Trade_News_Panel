import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Form,
  Input,
  Modal,
  Switch,
  Table,
  Tooltip,
  Typography,
  message,
} from "antd";
import { DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { api } from "../api/client";
import type { User } from "../types";

async function fetchUsers(): Promise<User[]> {
  const { data } = await api.get<User[]>("/users");
  return data;
}

async function createUser(params: {
  username: string;
  password: string;
}): Promise<User> {
  const { data } = await api.post<User>("/users", params);
  return data;
}

async function toggleUser(
  id: number,
  is_active: boolean,
): Promise<User> {
  const { data } = await api.put<User>(`/users/${id}`, null, {
    params: { is_active },
  });
  return data;
}

async function deleteUser(id: number): Promise<void> {
  await api.delete(`/users/${id}`);
}

export default function Users() {
  const queryClient = useQueryClient();
  const [msg, ctxHolder] = message.useMessage();
  const [createOpen, setCreateOpen] = useState(false);
  const [form] = Form.useForm();

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: fetchUsers,
  });

  const createMut = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      msg.success("Пользователь создан");
      setCreateOpen(false);
      form.resetFields();
    },
    onError: () => {
      msg.error("Ошибка создания пользователя");
    },
  });

  const toggleMut = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      toggleUser(id, is_active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteUser,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      msg.success("Пользователь удалён");
    },
  });

  const columns: ColumnsType<User> = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 60,
    },
    {
      title: "Имя пользователя",
      dataIndex: "username",
      key: "username",
    },
    {
      title: "Активен",
      dataIndex: "is_active",
      key: "is_active",
      width: 100,
      render: (active: boolean, record: User) => (
        <Switch
          checked={active}
          size="small"
          onChange={(checked) =>
            toggleMut.mutate({ id: record.id, is_active: checked })
          }
        />
      ),
    },
    {
      title: "",
      key: "actions",
      width: 50,
      render: (_: unknown, record: User) => (
        <Tooltip title="Удалить">
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() =>
              Modal.confirm({
                title: `Удалить пользователя "${record.username}"?`,
                onOk: () => deleteMut.mutate(record.id),
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
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <Typography.Title level={3} style={{ marginBottom: 4 }}>
            Пользователи
          </Typography.Title>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
            Управление учётными записями
          </Typography.Paragraph>
        </div>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setCreateOpen(true)}
        >
          Создать
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={users || []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={false}
        locale={{ emptyText: "Нет пользователей" }}
      />

      <Modal
        title="Новый пользователь"
        open={createOpen}
        onCancel={() => {
          setCreateOpen(false);
          form.resetFields();
        }}
        footer={null}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(v) =>
            createMut.mutate({ username: v.username, password: v.password })
          }
        >
          <Form.Item
            name="username"
            label="Имя пользователя"
            rules={[{ required: true, message: "Введите имя" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="password"
            label="Пароль"
            rules={[
              { required: true, message: "Введите пароль" },
              { min: 4, message: "Минимум 4 символа" },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: "right" }}>
            <Button
              onClick={() => {
                setCreateOpen(false);
                form.resetFields();
              }}
              style={{ marginRight: 8 }}
            >
              Отмена
            </Button>
            <Button
              type="primary"
              htmlType="submit"
              loading={createMut.isPending}
            >
              Создать
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
