export type Chunk = {
  chunk_id: string;
  doc_slug: string;
  page_number: number;
  section: string | null;
  offsets: { start: number; end: number };
  text: string;
  relevance_score: number | null;
};

export type QueryResponse = {
  request_id: string;
  trace_id?: string;
  mode: "grounded" | "offline_mock" | "abstained";
  query: string;
  answer: string;
  claims: Array<{
    claim_id: string;
    text: string;
    chunk_ids: string[];
    spans: Array<{ chunk_id: string; quote: string; offsets: { start: number; end: number } }>;
  }>;
  retrieved_chunks: Chunk[];
  provenance: {
    retrieved_chunk_ids: string[];
    retrieval_query: string;
  };
  abstained?: true;
  reason?: string;
  invalid_chunk_ids?: string[];
};

export type EvalReport = {
  run_id: string;
  mode: string;
  case_count: number;
  trace_id?: string;
  metrics: {
    retrieval_recall: number;
    citation_validity: number;
    abstention_accuracy: number;
    average_latency_ms: number;
    estimated_input_tokens: number;
    estimated_output_tokens: number;
    estimated_total_tokens: number;
    estimated_cost_usd: number;
  };
  results: unknown[];
};

async function apiFetch(path: string, key: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (key) headers.set("x-functions-key", key);
  if (init?.body) headers.set("Content-Type", "application/json");
  return fetch(path, { ...init, headers });
}

export async function health(key: string) {
  const response = await apiFetch("/api/health", key);
  if (!response.ok) throw new Error(`Health check failed (${response.status})`);
  return response.json();
}

export async function queryApi(key: string, query: string, topK = 5): Promise<QueryResponse> {
  const response = await apiFetch("/api/query", key, {
    method: "POST",
    body: JSON.stringify({ query, top_k: topK })
  });
  if (!response.ok) throw new Error(`Query failed (${response.status})`);
  return response.json();
}

export async function runEval(key: string, offline = true): Promise<EvalReport> {
  const response = await apiFetch("/api/eval/run", key, {
    method: "POST",
    body: JSON.stringify({ offline })
  });
  if (!response.ok) throw new Error(`Evaluation failed (${response.status})`);
  return response.json();
}

export async function latestEval(key: string): Promise<EvalReport> {
  const response = await apiFetch("/api/eval/latest", key);
  if (!response.ok) throw new Error(`Evaluation unavailable (${response.status})`);
  return response.json();
}
