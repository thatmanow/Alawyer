import axios from "axios";
import { ElMessage } from "element-plus";

const http = axios.create({ baseURL: "", timeout: 300000 });

http.interceptors.request.use((config) => {
  const token = localStorage.getItem("alawyer-token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

http.interceptors.response.use(
  (resp) => resp.data,
  (err) => {
    const msg =
      err?.response?.data?.detail ||
      (typeof err?.response?.data?.detail === "object" && err.response.data.detail.msg) ||
      err.message ||
      "请求失败";
    if (err?.response?.status === 401) {
      localStorage.removeItem("alawyer-token");
      localStorage.removeItem("alawyer-user");
      if (!location.pathname.startsWith("/cover")) location.href = "/cover";
    }
    return Promise.reject(new Error(typeof msg === "string" ? msg : "请求失败"));
  }
);

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export interface ChatSource {
  doc_id: number;
  doc_name: string;
  snippet: string;
  score: number;
}

export const authApi = {
  register: (data: { username: string; password: string; nickname?: string }) =>
    http.post("/api/auth/register", data) as Promise<any>,
  login: (data: { username: string; password: string }) =>
    http.post("/api/auth/login", data) as Promise<any>,
  me: () => http.get("/api/users/me") as Promise<any>,
};

export const dashboardApi = {
  summary: () => http.get("/api/dashboard/summary") as Promise<any>,
};

export const chatApi = {
  ask: (question: string, history: { role: string; content: string }[] = []) =>
    http.post("/api/chat/ask", { question, history }) as Promise<any>,
  history: (limit = 50) =>
    http.get("/api/chat/history", { params: { limit } }) as Promise<any>,
};

export const contractApi = {
  upload: (file: File, name: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    return http.post("/api/contracts/upload", form) as Promise<any>;
  },
  list: () => http.get("/api/contracts/list") as Promise<any>,
  detail: (id: number) => http.get(`/api/contracts/${id}`) as Promise<any>,
  review: (id: number) => http.post(`/api/contracts/${id}/review`) as Promise<any>,
  remove: (id: number) => http.delete(`/api/contracts/${id}`) as Promise<any>,
  lawyerReview: (id: number, data: { verdict: string; score: number; comment: string }) =>
    http.put(`/api/contracts/${id}/lawyer-review`, data) as Promise<any>,
};

export const kbApi = {
  list: () => http.get("/api/kb/list") as Promise<any>,
  content: (id: number) => http.get(`/api/kb/${id}/content`) as Promise<any>,
  update: (id: number, data: { name?: string; content?: string }) =>
    http.put(`/api/kb/${id}`, data) as Promise<any>,
  upload: (file: File, name: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("name", name);
    return http.post("/api/kb/upload", form) as Promise<any>;
  },
  remove: (id: number) => http.delete(`/api/kb/${id}`) as Promise<any>,
};

export const userApi = {
  updateMe: (data: { nickname?: string; avatar?: string }) =>
    http.put("/api/users/me", data) as Promise<any>,
  changePassword: (data: { old_password: string; new_password: string }) =>
    http.put("/api/users/me/password", data) as Promise<any>,
  updateStatus: (status: string) => http.put("/api/users/me/status", { status }) as Promise<any>,
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return http.post("/api/users/me/avatar", form) as Promise<any>;
  },
  list: (block: string, page: number, search: string) =>
    http.get(`/api/users/list`, { params: { block, page, search } }) as Promise<any>,
  updateRole: (id: number, role: string) =>
    http.put(`/api/users/${id}/role`, { role }) as Promise<any>,
};

export { errMsg };