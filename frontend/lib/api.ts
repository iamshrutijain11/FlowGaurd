const rawBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").trim().replace(/\/+$/, "");
export const API_BASE = rawBase.endsWith("/api/v1") ? rawBase : `${rawBase}/api/v1`;
export const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK === "true";
export const getToken = () => typeof window !== "undefined" ? localStorage.getItem("fg_token") : null;

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const t = getToken();
  const headers: Record<string, string> = {
    ...(init.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(t ? { Authorization: `Bearer ${t}` } : {}),
    ...((init.headers as Record<string, string>) || {}),
  };
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const targetPath = cleanPath.startsWith("/api/v1") ? cleanPath.replace(/^\/api\/v1/, "") : cleanPath;
  const r = await fetch(`${API_BASE}${targetPath}`, { ...init, headers });
  let j: any;
  try {
    j = await r.json();
  } catch {
    if (!r.ok) throw new Error(`Request failed with status ${r.status}`);
    return {} as T;
  }
  if (!r.ok || j?.success === false) {
    const msg =
      j?.error?.message ||
      (typeof j?.error === "string" ? j.error : null) ||
      j?.message ||
      (typeof j?.detail === "string" ? j.detail : null) ||
      (Array.isArray(j?.detail) ? j.detail.map((d: any) => d?.msg || JSON.stringify(d)).join(", ") : null) ||
      `Request failed with status ${r.status}`;
    throw new Error(msg);
  }
  return (j?.data !== undefined ? j.data : j) as T;
}
