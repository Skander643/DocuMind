import type {
  ChatRequest,
  ChatResponse,
  DocumentInfo,
  EvalSummary,
  HealthResponse,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

function authHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  const key = import.meta.env.VITE_API_KEY;
  if (key) {
    headers.set("X-API-Key", key);
  }
  return headers;
}

async function parseError(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      return String((body as { detail: unknown }).detail);
    }
  } catch {
    /* ignore */
  }
  return response.statusText;
}

export function documentFileUrl(docId: string, page?: number): string {
  const path = `${BASE}/api/documents/${encodeURIComponent(docId)}/file`;
  return page != null ? `${path}#page=${page}` : path;
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${BASE}/health`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<HealthResponse>;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const response = await fetch(`${BASE}/api/documents`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<DocumentInfo[]>;
}

export async function uploadDocuments(files: File[]): Promise<DocumentInfo[]> {
  const body = new FormData();
  for (const file of files) {
    body.append("files", file);
  }
  const response = await fetch(`${BASE}/api/documents`, {
    method: "POST",
    headers: authHeaders(),
    body,
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<DocumentInfo[]>;
}

export async function deleteDocument(docId: string): Promise<void> {
  const response = await fetch(`${BASE}/api/documents/${encodeURIComponent(docId)}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (!response.ok) throw new Error(await parseError(response));
}

export async function reindexDocument(docId: string): Promise<DocumentInfo> {
  const response = await fetch(
    `${BASE}/api/documents/${encodeURIComponent(docId)}/reindex`,
    { method: "POST", headers: authHeaders() },
  );
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<DocumentInfo>;
}

export async function getEvalSummary(): Promise<EvalSummary> {
  const response = await fetch(`${BASE}/api/eval/summary`);
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<EvalSummary>;
}

export async function sendChat(body: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(await parseError(response));
  return response.json() as Promise<ChatResponse>;
}
