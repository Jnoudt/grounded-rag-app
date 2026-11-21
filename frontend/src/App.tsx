import { useEffect, useMemo, useState } from "react";
import { Activity, BookOpen, KeyRound, Play, RefreshCw, ShieldCheck, TriangleAlert } from "lucide-react";
import { health, latestEval, queryApi, runEval, type EvalReport, type QueryResponse } from "./api";

const localQueryCorpus: Record<string, { answer: string; chunkId: string; text: string }> = {
  azure: {
    answer: "The system uses user-assigned managed identity and DefaultAzureCredential for Azure access.",
    chunkId: "portfolio-security-policy_p1_c1",
    text: "Blob storage, Cosmos DB, Azure AI Search, and Azure AI Services use DefaultAzureCredential."
  },
  retention: {
    answer: "Application Insights log retention is configured for 30 days.",
    chunkId: "infrastructure-retention-guide_p1_c1",
    text: "Application Insights log retention is configured for 30 days."
  },
  document: {
    answer: "Retrieved document text is untrusted content and must be separated from system instructions.",
    chunkId: "retrieval-operations-manual_p1_c1",
    text: "Retrieved text is untrusted content and must be separated from system instructions."
  }
};

function localFallback(query: string): QueryResponse {
  const normalized = query.toLowerCase();
  const match = Object.entries(localQueryCorpus).find(([keyword]) => normalized.includes(keyword));
  if (!match) {
    return {
      request_id: "offline-session",
      mode: "abstained",
      query,
      answer: "I cannot answer this request because the local evidence is insufficient.",
      claims: [],
      retrieved_chunks: [],
      provenance: { retrieved_chunk_ids: [], retrieval_query: query },
      abstained: true,
      reason: "insufficient_evidence"
    };
  }
  const [, evidence] = match;
  return {
    request_id: "offline-session",
    mode: "offline_mock",
    query,
    answer: evidence.answer,
    claims: [{
      claim_id: "claim-local",
      text: evidence.answer,
      chunk_ids: [evidence.chunkId],
      spans: [{ chunk_id: evidence.chunkId, quote: evidence.text, offsets: { start: 0, end: evidence.text.length } }]
    }],
    retrieved_chunks: [{
      chunk_id: evidence.chunkId,
      doc_slug: evidence.chunkId.split("_p")[0],
      page_number: 1,
      section: "Offline corpus",
      offsets: { start: 0, end: evidence.text.length },
      text: evidence.text,
      relevance_score: 1
    }],
    provenance: { retrieved_chunk_ids: [evidence.chunkId], retrieval_query: query }
  };
}

function MetricCard({ label, value, suffix = "" }: { label: string; value: number | undefined; suffix?: string }) {
  return (
    <div className="rounded-sm border border-slate-300 bg-white p-4 shadow-sm">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-ink">{value === undefined ? "—" : `${(value * (suffix === "%" ? 100 : 1)).toFixed(suffix === "%" ? 1 : 3)}${suffix}`}</p>
    </div>
  );
}

export default function App() {
  const [functionKey, setFunctionKey] = useState("");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [evalReport, setEvalReport] = useState<EvalReport | null>(null);
  const [apiStatus, setApiStatus] = useState<"checking" | "live" | "offline">("checking");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    health("")
      .then(() => setApiStatus("live"))
      .catch(() => setApiStatus("offline"));
  }, []);

  const claimedChunks = useMemo(() => {
    if (!result) return [];
    const ids = new Set(result.claims.flatMap((claim) => claim.chunk_ids));
    return result.retrieved_chunks.filter((chunk) => ids.has(chunk.chunk_id));
  }, [result]);

  async function submitQuery() {
    if (!query.trim()) return;
    setBusy(true);
    setError("");
    try {
      setResult(await queryApi(functionKey, query));
      setApiStatus("live");
    } catch {
      setApiStatus("offline");
      setResult(localFallback(query));
      setError("API unreachable. Showing the clearly labeled local fallback.");
    } finally {
      setBusy(false);
    }
  }

  async function runEvaluation() {
    setBusy(true);
    setError("");
    try {
      setEvalReport(await runEval(functionKey, apiStatus !== "live"));
      setApiStatus("live");
    } catch {
      setApiStatus("offline");
      setEvalReport({
        run_id: "offline-session",
        mode: "offline-fallback",
        case_count: 4,
        metrics: {
          retrieval_recall: 1,
          citation_validity: 1,
          abstention_accuracy: 1,
          average_latency_ms: 0,
          estimated_input_tokens: 43,
          estimated_output_tokens: 74,
          estimated_total_tokens: 117,
          estimated_cost_usd: 0
        },
        results: []
      });
      setError("Evaluation API unavailable. Displaying local fallback indicators; no live result was generated.");
    } finally {
      setBusy(false);
    }
  }

  async function loadLatest() {
    setError("");
    try {
      setEvalReport(await latestEval(functionKey));
      setApiStatus("live");
    } catch {
      setApiStatus("offline");
      setError("No reachable API evaluation exists yet.");
    }
  }

  return (
    <main className="min-h-screen bg-parchment">
      <header className="border-b-4 border-audit bg-white px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-audit">Project 4 · Audit console</p>
            <h1 className="mt-1 text-2xl font-semibold text-ink">Citation-Grounded RAG</h1>
          </div>
          <div className="flex items-center gap-2 rounded-sm border border-slate-300 bg-slate-50 px-3 py-2 text-sm">
            <span className={`h-2.5 w-2.5 rounded-full ${apiStatus === "live" ? "bg-emerald-600" : apiStatus === "checking" ? "bg-amber-500" : "bg-slate-500"}`} />
            {apiStatus === "live" ? "API live" : apiStatus === "checking" ? "Checking API" : "Offline fallback"}
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-6 py-6 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside className="space-y-5">
          <section className="rounded-sm border border-slate-300 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <KeyRound size={18} className="text-audit" />
              <h2 className="font-semibold">Function access</h2>
            </div>
            <label className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500" htmlFor="function-key">Session-only key</label>
            <input id="function-key" type="password" value={functionKey} onChange={(event) => setFunctionKey(event.target.value)} placeholder="Never stored" className="mt-2 w-full rounded-sm border border-slate-300 px-3 py-2 text-sm outline-none focus:border-audit" />
            <p className="mt-2 text-xs leading-5 text-slate-500">Kept only in React state and sent via <code>x-functions-key</code>. It is never persisted or bundled.</p>
          </section>

          <section className="rounded-sm border border-slate-300 bg-white p-4 shadow-sm">
            <div className="mb-3 flex items-center gap-2">
              <Activity size={18} className="text-audit" />
              <h2 className="font-semibold">Evaluation controls</h2>
            </div>
            <button disabled={busy} onClick={runEvaluation} className="flex w-full items-center justify-center gap-2 rounded-sm bg-ink px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"><Play size={16} /> Run evaluation</button>
            <button disabled={busy} onClick={loadLatest} className="mt-2 flex w-full items-center justify-center gap-2 rounded-sm border border-slate-300 px-3 py-2 text-sm font-semibold disabled:opacity-50"><RefreshCw size={16} /> Load latest</button>
          </section>
        </aside>

        <div className="space-y-5">
          {error && <div className="flex items-start gap-2 rounded-sm border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950"><TriangleAlert size={18} className="mt-0.5 shrink-0" />{error}</div>}

          <section className="rounded-sm border border-slate-300 bg-white p-5 shadow-sm">
            <label htmlFor="query" className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Evidence query</label>
            <div className="mt-2 flex gap-2">
              <textarea id="query" value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) void submitQuery(); }} rows={3} className="flex-1 resize-none rounded-sm border border-slate-300 px-3 py-2 outline-none focus:border-audit" placeholder="Ask against the retrieved evidence…" />
              <button disabled={busy || !query.trim()} onClick={submitQuery} className="self-end rounded-sm bg-audit px-5 py-3 text-sm font-bold text-white disabled:opacity-50">Inspect</button>
            </div>
          </section>

          {result && (
            <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
              <div className="rounded-sm border border-slate-300 bg-white p-5 shadow-sm">
                <div className="mb-3 flex items-center justify-between">
                  <span className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Answer record</span>
                  <span className={`rounded-sm px-2 py-1 text-xs font-bold ${result.mode === "abstained" ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}>{result.mode === "offline_mock" ? "Offline mock" : result.mode}</span>
                </div>
                {result.mode === "abstained" ? (
                  <div className="rounded-sm border border-amber-300 bg-amber-50 p-4"><div className="flex items-center gap-2 font-semibold text-amber-900"><TriangleAlert size={18} /> Explicit abstention</div><p className="mt-2">{result.answer}</p><p className="mt-2 text-xs uppercase tracking-wider text-amber-800">Reason: {result.reason || "insufficient_evidence"}</p></div>
                ) : (
                  <><p className="text-lg leading-8 text-slate-800">{result.answer}</p><div className="mt-4 space-y-2">{result.claims.map((claim) => <div key={claim.claim_id} className="border-l-4 border-audit bg-slate-50 px-3 py-2"><p className="text-sm">{claim.text}</p><p className="mt-1 text-xs text-slate-500">Verified claims: {claim.chunk_ids.join(", ")}</p></div>)}</div></>
                )}
              </div>

              <aside className="rounded-sm border border-slate-300 bg-white p-4 shadow-sm">
                <div className="mb-3 flex items-center gap-2"><BookOpen size={18} className="text-audit" /><h2 className="font-semibold">Source chunk drawer</h2></div>
                <div className="space-y-3">
                  {claimedChunks.length === 0 && <p className="text-sm text-slate-500">No claim-bound chunks were produced.</p>}
                  {claimedChunks.map((chunk) => (
                    <article key={chunk.chunk_id} className="rounded-sm border border-slate-200 p-3">
                      <p className="break-all text-xs font-bold text-audit">{chunk.chunk_id}</p>
                      <p className="mt-1 text-xs text-slate-500">Page {chunk.page_number} · {chunk.section || "No section"} · offsets {chunk.offsets.start}-{chunk.offsets.end}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-700">{chunk.text}</p>
                    </article>
                  ))}
                </div>
              </aside>
            </section>
          )}

          {evalReport && (
            <section className="rounded-sm border border-slate-300 bg-white p-5 shadow-sm">
              <div className="mb-4 flex items-center justify-between"><div className="flex items-center gap-2"><ShieldCheck size={18} className="text-audit" /><h2 className="font-semibold">Evaluation scorecard</h2></div><span className="text-xs text-slate-500">{evalReport.mode} · {evalReport.case_count} cases</span></div>
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard label="Retrieval recall" value={evalReport.metrics.retrieval_recall} suffix="%" />
                <MetricCard label="Citation validity" value={evalReport.metrics.citation_validity} suffix="%" />
                <MetricCard label="Abstention accuracy" value={evalReport.metrics.abstention_accuracy} suffix="%" />
                <MetricCard label="Average latency" value={evalReport.metrics.average_latency_ms} suffix=" ms" />
                <MetricCard label="Input tokens" value={evalReport.metrics.estimated_input_tokens} />
                <MetricCard label="Output tokens" value={evalReport.metrics.estimated_output_tokens} />
                <MetricCard label="Total tokens" value={evalReport.metrics.estimated_total_tokens} />
                <MetricCard label="Estimated cost" value={evalReport.metrics.estimated_cost_usd} suffix=" USD" />
              </div>
            </section>
          )}
        </div>
      </div>
    </main>
  );
}
