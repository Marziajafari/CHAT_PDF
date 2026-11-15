import { useRef, useState } from "react";
import type { DragEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, FileText, Loader2, Search, Trash2, UploadCloud, XCircle } from "lucide-react";
import { deleteDocument, listDocuments, uploadDocument } from "../lib/api";
import type { DocumentInfo } from "../lib/api";
import { Button, Card, EmptyState, ErrorBanner, PageHeader, Spinner, inputClass } from "../components/ui";
import { errorMessage, formatBytes, formatDate } from "../lib/utils";

function StatusBadge({ doc }: { doc: DocumentInfo }) {
  if (doc.processing_status === "ready") {
    return (
      <span className="inline-flex items-center gap-1 text-ok">
        <CheckCircle2 className="h-4 w-4" aria-hidden /> Ready
      </span>
    );
  }
  if (doc.processing_status === "failed") {
    return (
      <span className="inline-flex items-center gap-1 text-bad">
        <XCircle className="h-4 w-4" aria-hidden /> Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-warn">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Processing
    </span>
  );
}

export default function Documents() {
  const qc = useQueryClient();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    // keep polling while any document is still being processed
    refetchInterval: (query) =>
      query.state.data?.some((d) => d.processing_status === "processing") ? 2000 : false,
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file, setProgress),
    onMutate: () => {
      setError(null);
      setProgress(0);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["documents"] }),
    onError: (e) => setError(errorMessage(e)),
    onSettled: () => setProgress(null),
  });

  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const handleFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted.");
      return;
    }
    upload.mutate(file);
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const visible = docs.filter((d) => d.original_filename.toLowerCase().includes(search.toLowerCase()));

  return (
    <div>
      <PageHeader title="My Documents" subtitle="Upload lecture notes or textbooks as PDF. They stay on this computer." />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed bg-white px-6 py-10 text-center transition-colors ${
          dragging ? "border-brand bg-brand/5" : "border-line"
        }`}
      >
        <UploadCloud className="h-10 w-10 text-accent" aria-hidden />
        <p className="font-medium">Drag a PDF here, or choose a file</p>
        <p className="text-xs text-ink-soft">PDF only, up to 20 MB. Scanned (image-only) PDFs are not supported.</p>
        <input
          ref={inputRef}
          data-testid="file-input"
          aria-label="PDF file"
          type="file"
          accept=".pdf,application/pdf"
          className="sr-only"
          onChange={(e) => {
            handleFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <Button onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
          Choose PDF
        </Button>
        {progress !== null && (
          <div className="w-full max-w-sm" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-2 overflow-hidden rounded-full bg-canvas">
              <div className="h-full bg-gradient-to-r from-brand to-accent transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="mt-1 text-xs text-ink-soft">{progress < 100 ? `Uploading… ${progress}%` : "Checking the file…"}</p>
          </div>
        )}
      </div>

      <div className="mt-4">
        <ErrorBanner message={error} />
      </div>

      <div className="mt-6 flex items-center gap-2">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-ink-soft" aria-hidden />
          <input
            aria-label="Search documents"
            placeholder="Search documents"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={`${inputClass} pl-9`}
          />
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {isLoading ? (
          <Spinner label="Loading documents" />
        ) : docs.length === 0 ? (
          <EmptyState
            icon={<FileText className="h-10 w-10" />}
            title="No documents yet"
            text="Upload a PDF above. StudyMate reads it, splits it into passages and prepares it for questions, summaries and quizzes."
          />
        ) : visible.length === 0 ? (
          <p className="text-sm text-ink-soft">No documents match “{search}”.</p>
        ) : (
          visible.map((d) => (
            <Card key={d.id} className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{d.original_filename}</p>
                <p className="mt-1 text-xs text-ink-soft">
                  {d.page_count ?? "?"} pages · {formatBytes(d.file_size)} · {formatDate(d.upload_date)}
                  {d.processing_status === "ready" && ` · ${d.chunk_count} passages`}
                </p>
                {d.error_message && <p className="mt-1 text-xs text-bad">{d.error_message}</p>}
              </div>
              <div className="flex items-center gap-3 text-sm">
                <StatusBadge doc={d} />
                <Button
                  variant="danger"
                  aria-label={`Delete ${d.original_filename}`}
                  disabled={remove.isPending}
                  onClick={() => {
                    if (window.confirm(`Delete “${d.original_filename}”? Its passages and study sets will be removed.`)) {
                      remove.mutate(d.id);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4" aria-hidden /> Delete
                </Button>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
