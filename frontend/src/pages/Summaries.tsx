import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { BookOpen, Check, Copy } from "lucide-react";
import { summarize } from "../lib/api";
import type { Summary } from "../lib/api";
import DocumentPicker from "../components/DocumentPicker";
import { Button, Card, ErrorBanner, PageHeader, Spinner } from "../components/ui";
import { errorMessage } from "../lib/utils";

function toText(s: Summary): string {
  const lines = ["SUMMARY", s.summary, "", "KEY CONCEPTS", ...s.key_concepts.map((c) => `- ${c}`)];
  lines.push("", "DEFINITIONS", ...s.definitions.map((d) => `- ${d.term}: ${d.definition}`));
  lines.push("", "EXAM NOTES", ...s.exam_notes.map((n) => `- ${n}`));
  return lines.join("\n");
}

export default function Summaries() {
  const [docIds, setDocIds] = useState<string[]>([]);
  const [mode, setMode] = useState<"short" | "detailed">("short");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useMutation({
    mutationFn: () => summarize(docIds[0], mode),
    onMutate: () => setError(null),
    onError: (e) => setError(errorMessage(e)),
  });

  const copy = async (s: Summary) => {
    try {
      await navigator.clipboard.writeText(toText(s));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setError("Copying is not allowed by this browser.");
    }
  };

  const result = run.data;

  return (
    <div>
      <PageHeader title="Summaries" subtitle="Large documents are summarised section by section, then combined." />
      <Card>
        <div className="grid gap-4 sm:grid-cols-2">
          <DocumentPicker value={docIds} onChange={setDocIds} />
          <fieldset>
            <legend className="text-sm font-medium">Length</legend>
            <div className="mt-1 flex gap-2">
              {(["short", "detailed"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  aria-pressed={mode === m}
                  onClick={() => setMode(m)}
                  className={`rounded-xl border px-4 py-2 text-sm font-medium ${
                    mode === m ? "border-brand bg-brand text-white" : "border-line bg-white hover:bg-canvas"
                  }`}
                >
                  {m === "short" ? "Short summary" : "Detailed summary"}
                </button>
              ))}
            </div>
          </fieldset>
        </div>
        <div className="mt-4 flex items-center gap-3">
          <Button onClick={() => run.mutate()} disabled={docIds.length === 0 || run.isPending}>
            <BookOpen className="h-4 w-4" aria-hidden /> Generate summary
          </Button>
          {run.isPending && <Spinner label="Summarising… this can take a few minutes on a laptop" />}
        </div>
      </Card>

      <div className="mt-4">
        <ErrorBanner message={error} />
      </div>

      {result && (
        <div className="mt-4 space-y-4">
          <Card>
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-semibold">Summary</h2>
              <Button variant="secondary" onClick={() => copy(result)}>
                {copied ? <Check className="h-4 w-4" aria-hidden /> : <Copy className="h-4 w-4" aria-hidden />}
                {copied ? "Copied" : "Copy summary"}
              </Button>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{result.summary}</p>
            <p className="mt-3 text-xs text-ink-soft">
              Built from {result.sections_used} of {result.sections_total} sections.
            </p>
          </Card>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <h2 className="mb-2 font-semibold">Key concepts</h2>
              {result.key_concepts.length === 0 ? (
                <p className="text-sm text-ink-soft">None found.</p>
              ) : (
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {result.key_concepts.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              )}
            </Card>
            <Card>
              <h2 className="mb-2 font-semibold">Examination notes</h2>
              {result.exam_notes.length === 0 ? (
                <p className="text-sm text-ink-soft">None found.</p>
              ) : (
                <ul className="list-disc space-y-1 pl-5 text-sm">
                  {result.exam_notes.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
          <Card>
            <h2 className="mb-2 font-semibold">Definitions</h2>
            {result.definitions.length === 0 ? (
              <p className="text-sm text-ink-soft">None found.</p>
            ) : (
              <dl className="space-y-2 text-sm">
                {result.definitions.map((d, i) => (
                  <div key={i}>
                    <dt className="font-medium">{d.term}</dt>
                    <dd className="text-ink-soft">{d.definition}</dd>
                  </div>
                ))}
              </dl>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
