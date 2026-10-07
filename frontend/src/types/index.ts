export interface Ticket {
  id: string;
  subject: string;
  body: string;
  channel: string;
  received_at: string;
  from_email: string;
  attachments: number;
}

export type Product =
  | "Zen Orchestrator"
  | "Zen Studio"
  | "Zen Connect"
  | "Zen Insights"
  | "Zen Vault";

export type Category =
  | "outage"
  | "billing"
  | "bug"
  | "feature_request"
  | "how_to"
  | "churn_risk";

export type Severity = "low" | "medium" | "high" | "critical";

export type RequestedAction =
  | "refund"
  | "credit"
  | "fix"
  | "callback"
  | "information"
  | "none";

export interface ExtractedFields {
  company: string;
  product: Product;
  category: Category;
  severity: Severity;
  requested_action: RequestedAction;
  refund_amount?: number | null;
  deadline?: string | null;
  escalated: boolean;
}

export interface ExtractionRecord {
  id: string;
  ticket_id: string;
  job_id: string;
  status: "done" | "needs_review" | "failed";
  extracted: ExtractedFields | null;
  raw_output: any;
  validation_errors: string[] | null;
  retry_count: number;
  confidence: Record<string, number>;
  edited_fields: string[];
  ticket?: Ticket | null;
}

export interface Job {
  id: string;
  status: "queued" | "running" | "completed" | "failed";
  ticket_ids: string[];
  total: number;
  queued: number;
  running: number;
  completed: number;
  done: number;
  needs_review: number;
  failed: number;
  progress_percent: number;
}
