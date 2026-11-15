import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle } from "lucide-react";
import type { ReactNode } from "react";
import { getSystemStatus } from "../lib/api";
import { Button, Card, ErrorBanner, PageHeader, Spinner } from "../components/ui";
import { errorMessage } from "../lib/utils";

function Row({ label, ok, children }: { label: string; ok: boolean; children?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line py-3 last:border-0">
      <div>
        <p className="font-medium">{label}</p>
        <div className="mt-0.5 text-sm text-ink-soft">{children}</div>
      </div>
      {ok ? (
        <span className="flex items-center gap-1 text-sm text-ok">
          <CheckCircle2 className="h-4 w-4" aria-hidden /> OK
        </span>
      ) : (
        <span className="flex items-center gap-1 text-sm text-bad">
          <XCircle className="h-4 w-4" aria-hidden /> Problem
        </span>
      )}
    </div>
  );
}

export default function Settings() {
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["system-status"],
    queryFn: getSystemStatus,
  });

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Status of the local services behind StudyMate AI."
        actions={
          <Button variant="secondary" onClick={() => refetch()} disabled={isFetching}>
            Refresh status
          </Button>
        }
      />
      {isLoading && <Spinner label="Checking services" />}
      <ErrorBanner message={error ? errorMessage(error) : null} />
      {data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <h2 className="mb-1 font-semibold">Services</h2>
            <Row label="Backend (FastAPI)" ok={data.backend === "ok"}>
              {data.app} version {data.version}
            </Row>
            <Row label="Ollama" ok={data.ollama.reachable && data.ollama.model_available}>
              {!data.ollama.reachable
                ? "Not reachable. Start it with “ollama serve”."
                : !data.ollama.model_available
                  ? `Running, but model “${data.ollama.model}” is missing. Run: ollama pull ${data.ollama.model}`
                  : `Current model: ${data.ollama.model}`}
            </Row>
            <Row label="Embedding model" ok={true}>
              {data.embeddings.model} ({data.embeddings.loaded ? "loaded in memory" : "loads on first use"})
            </Row>
            <Row label="Database (SQLite)" ok={data.database.status === "ok"}>
              {data.database.documents} documents stored
            </Row>
            <Row label="Vector store (ChromaDB)" ok={data.vector_store.status === "ok"}>
              {data.vector_store.chunks} passages indexed
            </Row>
          </Card>
          <Card>
            <h2 className="mb-3 font-semibold">Local application information</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-ink-soft">Chat model</dt><dd>{data.ollama.model}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-soft">Passage size</dt><dd>{data.config.chunk_size} characters</dd></div>
              <div className="flex justify-between"><dt className="text-ink-soft">Passage overlap</dt><dd>{data.config.chunk_overlap} characters</dd></div>
              <div className="flex justify-between"><dt className="text-ink-soft">Passages per answer</dt><dd>{data.config.top_k}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-soft">Relevance threshold</dt><dd>{data.config.relevance_threshold}</dd></div>
              <div className="flex justify-between"><dt className="text-ink-soft">Upload limit</dt><dd>{data.config.max_upload_mb} MB</dd></div>
            </dl>
            <p className="mt-4 text-xs text-ink-soft">
              Change these values in <code>backend/.env</code> and restart the backend. Your documents never leave this computer.
            </p>
            {data.ollama.installed_models.length > 0 && (
              <p className="mt-3 text-xs text-ink-soft">Installed Ollama models: {data.ollama.installed_models.join(", ")}</p>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
