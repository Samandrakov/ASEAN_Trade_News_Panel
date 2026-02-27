import { api } from "./client";

export async function downloadExport(params: {
  country?: string;
  date_from?: string;
  date_to?: string;
  search?: string;
  tag_type?: string;
  tag_value?: string;
  format: "csv" | "xlsx";
}): Promise<void> {
  const response = await api.post("/export", params, {
    responseType: "blob",
  });
  const blob = new Blob([response.data]);
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const ext = params.format === "xlsx" ? "xlsx" : "csv";
  a.download = `export.${ext}`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}
