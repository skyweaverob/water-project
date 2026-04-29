/**
 * Thin API client. Server components call API_BASE_URL directly; client components
 * use these helpers and pass an X-Tenant-Id header. Tenant resolution is wired through
 * Clerk in production; for now we read NEXT_PUBLIC_DEMO_TENANT_ID for the demo.
 */

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const DEMO_TENANT = process.env.NEXT_PUBLIC_DEMO_TENANT_ID || "";

function headers(extra: HeadersInit = {}): HeadersInit {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  if (DEMO_TENANT) h["X-Tenant-Id"] = DEMO_TENANT;
  return { ...h, ...(extra as Record<string, string>) };
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { headers: headers(), cache: "no-store" });
  if (!r.ok) throw new Error(`GET ${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`POST ${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export async function apiStream(path: string, body: unknown): Promise<Response> {
  return fetch(`${BASE}${path}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(body),
    cache: "no-store",
  });
}

export const API_BASE = BASE;
