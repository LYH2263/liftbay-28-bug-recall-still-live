// 全站唯一的接口层：共享类型、端点 helper、呼梯状态口径。

export type CallStatus = "waiting" | "frozen" | "assigned" | "rejected";

export type Building = {
  id: number;
  name: string;
  floors: number;
  recall_floor: number;
  recall_active: boolean;
};

export type Car = {
  id: number;
  building_id: number;
  label: string;
  floor: number;
  direction: "up" | "down" | "idle";
  load: number;
  capacity: number;
};

export type Call = {
  id: number;
  building_id: number;
  floor: number;
  direction: "up" | "down";
  passengers: number;
  status: CallStatus;
  assigned_car_id: number | null;
  score: string;
  created_at: string;
};

export type CongestionRow = { floor: number; passengers: number };
export type ReplayLog = {
  id: number;
  call_id: number | null;
  car_id: number | null;
  detail: string;
  created_at: string;
};

export const STATUS_META: Record<CallStatus, { label: string; cls: string }> = {
  waiting: { label: "待派", cls: "status-pill status-waiting" },
  frozen: { label: "已冻结", cls: "recall-badge" },
  assigned: { label: "已派工", cls: "status-pill status-assigned" },
  rejected: { label: "已拒绝", cls: "status-pill status-rejected" },
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    // FastAPI 错误体为 {"detail": "..."}，优先展示中文原因（如召回 409）
    let msg = res.statusText;
    try {
      const data = await res.json();
      msg = data?.detail ?? msg;
    } catch {
      const text = await res.text().catch(() => "");
      if (text) msg = text;
    }
    throw new Error(msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const getBuildings = () => api<Building[]>("/buildings");
export const getCars = () => api<Car[]>("/cars");
export const getCalls = () => api<Call[]>("/calls");
export const getCongestion = () => api<CongestionRow[]>("/congestion");
export const getReplay = () => api<ReplayLog[]>("/replay");

export const createCall = (body: {
  building_id: number;
  floor: number;
  direction: "up" | "down";
  passengers: number;
}) => api<Call>("/calls", { method: "POST", body: JSON.stringify(body) });

export const dispatchCall = (call_id: number) =>
  api<Call>("/dispatch", { method: "POST", body: JSON.stringify({ call_id }) });

export const setRecall = (building_id: number, active: boolean) =>
  api<Building>(`/buildings/${building_id}/recall`, {
    method: "POST",
    body: JSON.stringify({ active }),
  });
