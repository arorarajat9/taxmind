export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export interface Citation {
  section: string;
  snippet: string;
  source: string;
  confidence: number;
}

export interface BlockedITC {
  invoice_number: string;
  supplier: string | null;
  description: string | null;
  tax: number;
  reason: string | null;
  citation: Citation | null;
}

export interface ReconLine {
  invoice_number: string;
  gstin: string | null;
  supplier: string | null;
  status: string;
  book_tax: number;
  gstr2a_tax: number;
  tax_difference: number;
  itc_at_risk: number;
  note: string;
}

export interface AuditEntry {
  timestamp: string;
  agent: string;
  entity_ref: string;
  decision: string;
  rationale: string;
  citation: Citation | null;
  confident: boolean;
}

export interface Anomaly {
  entity_ref: string;
  rule: string;
  message: string;
  severity: string;
}

export interface Analysis {
  mode: string;
  knowledge_backend: string;
  orchestration?: string;
  counts: {
    sales_rows: number;
    purchase_rows: number;
    gstr2a_rows: number;
    anomalies: number;
  };
  itc_summary: {
    itc_blocked_value: number;
    itc_eligible_value: number;
    uncertain_count: number;
  };
  reconciliation: {
    lines: ReconLine[];
    summary: {
      matched: number;
      mismatched: number;
      missing_in_2a: number;
      missing_in_books: number;
      total_itc_at_risk: number;
      total_book_itc: number;
    };
  };
  anomalies: Anomaly[];
  blocked_itc: BlockedITC[];
  gstr1: any;
  gstr3b: {
    outward_taxable_value: number;
    outward_tax: number;
    itc_available: number;
    itc_reversed: number;
    net_tax_payable: number;
  };
  gstr3b_detail: Record<string, number>;
  audit_log: AuditEntry[];
  audit_cited_count: number;
  download_url: string;
}

export async function runDemo(): Promise<Analysis> {
  const r = await fetch(`${API_BASE}/api/demo`);
  if (!r.ok) throw new Error(`Demo failed: ${r.status}`);
  return r.json();
}

export async function analyzeFiles(files: {
  sales?: File;
  purchase?: File;
  gstr2a?: File;
}): Promise<Analysis> {
  const fd = new FormData();
  if (files.sales) fd.append("sales", files.sales);
  if (files.purchase) fd.append("purchase", files.purchase);
  if (files.gstr2a) fd.append("gstr2a", files.gstr2a);
  const r = await fetch(`${API_BASE}/api/analyze`, { method: "POST", body: fd });
  if (!r.ok) throw new Error(`Analyze failed: ${r.status}`);
  return r.json();
}

export async function queryKB(question: string): Promise<{
  question: string;
  answer: string;
  citations: Citation[];
  confidence: number;
  backend: string;
}> {
  const r = await fetch(`${API_BASE}/api/kb/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!r.ok) throw new Error(`KB query failed: ${r.status}`);
  return r.json();
}

export function inr(n: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n || 0);
}
