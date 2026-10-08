import { ExtractionRecord, ExtractedFields, Job, Ticket } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const NULLABLE = [
  "product", "category", "severity", "requested_action",
  "refund_amount", "deadline", "escalated",
];

function cleanPayload(fields: Record<string, any>) {
  const out: Record<string, any> = {};
  for (const [k, v] of Object.entries(fields)) {
    if (v === undefined) continue;
    if ((k === "deadline" || k === "refund_amount") && (v === "" || v === null)) {
      out[k] = null;
    } else if (k === "refund_amount" && v !== null && v !== "") {
      out[k] = Number(v);
    } else {
      out[k] = v;
    }
  }
  return out;
}


function formatError(body: any): string {
  const d = body?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d))
    return d.map((e: any) => `${(e.loc ?? []).slice(1).join(".")}: ${e.msg}`).join("; ");
  return "Request failed";
}
export async function fetchTickets(params?: {
  search?: string;
  channel?: string;
  limit?: number;
  offset?: number;
}): Promise<{ tickets: Ticket[]; total: number }> {
  const query = new URLSearchParams();
  if (params?.search) query.set("search", params.search);
  if (params?.channel && params.channel !== "all") query.set("channel", params.channel);
  if (params?.limit !== undefined) query.set("limit", String(params.limit));
  if (params?.offset !== undefined) query.set("offset", String(params.offset));

  const res = await fetch(`${API_BASE}/api/tickets?${query.toString()}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch tickets: ${res.statusText}`);
  }
  return res.json();
}

export async function createJob(ticketIds: string[]): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticket_ids: ticketIds }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to create extraction job");
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch job: ${res.statusText}`);
  }
  return res.json();
}

export async function getJobResults(jobId: string): Promise<ExtractionRecord[]> {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}/results`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch job results: ${res.statusText}`);
  }
  return res.json();
}

export async function patchRecord(
  recordId: string,
  patch: Partial<ExtractedFields>
): Promise<ExtractionRecord> {
  const res = await fetch(`${API_BASE}/api/records/${recordId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cleanPayload(patch as Record<string, any>)),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const errList = errorData.detail?.errors;
    if (Array.isArray(errList) && errList.length > 0) {
      throw new Error(errList.join(", "));
    }
    throw new Error(formatError(errorData));
  }
  return res.json();
}

export function getExportUrl(jobId: string): string {
  return `${API_BASE}/api/jobs/${jobId}/export.csv`;
}
