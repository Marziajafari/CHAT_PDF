import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Layers, RotateCcw } from "lucide-react";
import { generateFlashcards, listFlashcardSets, saveFlashcardProgress } from "../lib/api";
import type { CardStatus, FlashcardSet } from "../lib/api";
import DocumentPicker from "../components/DocumentPicker";
import { Button, Card, ErrorBanner, PageHeader, Spinner, inputClass } from "../components/ui";
import { errorMessage } from "../lib/utils";

export default function Flashcards() {
  const qc = useQueryClient();
  const [docIds, setDocIds] = useState<string[]>([]);
  const [count, setCount] = useState(10);
  const [active, setActive] = useState<FlashcardSet | null>(null);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [progress, setProgress] = useState<Record<string, CardStatus>>({});
  const [error, setError] = useState<string | null>(null);
  const activeId = useRef<string | null>(null);

  const { data: saved = [] } = useQuery({ queryKey: ["flashcard-sets"], queryFn: listFlashcardSets });

  const open = (set: FlashcardSet) => {
    activeId.current = set.id;
    setActive(set);
    setProgress(set.progress);
    setIndex(0);
    setFlipped(false);
  };

  const generate = useMutation({
    mutationFn: () => generateFlashcards(docIds[0], count),
    onMutate: () => setError(null),
    onSuccess: (set) => {
      open(set);
      qc.invalidateQueries({ queryKey: ["flashcard-sets"] });
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const save = useMutation({
    mutationFn: (p: Record<string, CardStatus>) => saveFlashcardProgress(activeId.current!, p),
    onError: (e) => setError(errorMessage(e)),
  });

  // keyboard: arrows to move, space to flip
  useEffect(() => {
    if (!active) return;
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight") go(1);
      if (e.key === "ArrowLeft") go(-1);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  });

  const go = (step: number) => {
    if (!active) return;
    setIndex((i) => Math.min(active.cards.length - 1, Math.max(0, i + step)));
    setFlipped(false);
  };

  const mark = (status: CardStatus) => {
    const next = { ...progress, [String(index)]: status };
    setProgress(next);
    save.mutate(next);
    if (active && index < active.cards.length - 1) go(1);
  };

  if (!active) {
    return (
      <div>
        <PageHeader title="Flashcards" subtitle="Turn a document into question-and-answer cards." />
        <Card>
          <div className="grid gap-4 sm:grid-cols-2">
            <DocumentPicker value={docIds} onChange={setDocIds} />
            <label className="block text-sm font-medium">
              Number of cards
              <input
                type="number"
                min={1}
                max={30}
                className={`${inputClass} mt-1`}
                value={count}
                onChange={(e) => setCount(Math.min(30, Math.max(1, Number(e.target.value) || 1)))}
              />
            </label>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button onClick={() => generate.mutate()} disabled={docIds.length === 0 || generate.isPending}>
              <Layers className="h-4 w-4" aria-hidden /> Generate flashcards
            </Button>
            {generate.isPending && <Spinner label="Writing cards… this can take a few minutes" />}
          </div>
        </Card>
        <div className="mt-4">
          <ErrorBanner message={error} />
        </div>
        {saved.length > 0 && (
          <Card className="mt-6">
            <h2 className="mb-3 font-semibold">Saved sets</h2>
            <ul className="space-y-2">
              {saved.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-3 text-sm">
                  <span className="truncate">{s.title}</span>
                  <Button variant="secondary" onClick={() => open(s)}>
                    Study
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    );
  }

  const card = active.cards[index];
  const known = Object.values(progress).filter((s) => s === "known").length;
  const revise = Object.values(progress).filter((s) => s === "revise").length;
  const status = progress[String(index)];

  return (
    <div>
      <PageHeader
        title="Flashcards"
        subtitle={`Card ${index + 1} of ${active.cards.length}`}
        actions={
          <Button variant="secondary" onClick={() => setActive(null)}>
            <RotateCcw className="h-4 w-4" aria-hidden /> All sets
          </Button>
        }
      />

      <div className="mb-4">
        <div className="mb-1 flex justify-between text-xs text-ink-soft">
          <span>{known} known</span>
          <span>{revise} to revise</span>
        </div>
        <div className="flex h-2 overflow-hidden rounded-full bg-white" role="progressbar" aria-valuenow={known} aria-valuemin={0} aria-valuemax={active.cards.length}>
          <div className="bg-ok" style={{ width: `${(known / active.cards.length) * 100}%` }} />
          <div className="bg-warn" style={{ width: `${(revise / active.cards.length) * 100}%` }} />
        </div>
      </div>

      <div className="flip-scene mx-auto h-72 max-w-xl">
        <button
          type="button"
          aria-label={flipped ? "Showing answer. Click to show question" : "Showing question. Click to show answer"}
          onClick={() => setFlipped((f) => !f)}
          data-flipped={flipped}
          className="flip-card h-full w-full text-left"
        >
          <div className="flip-face flex flex-col justify-between rounded-2xl border border-line bg-white p-6 shadow-sm">
            <span className="text-xs text-ink-soft">{card.key_concept || "Question"}</span>
            <p className="text-lg font-semibold">{card.question}</p>
            <span className="text-xs text-ink-soft">Click to reveal the answer</span>
          </div>
          <div className="flip-face flip-back flex flex-col justify-between rounded-2xl border border-brand/30 bg-brand/5 p-6 shadow-sm">
            <span className="text-xs text-ink-soft">Answer{card.source_page ? ` · page ${card.source_page}` : ""}</span>
            <p className="text-base">{card.answer}</p>
            <span className="text-xs text-ink-soft">Click to see the question</span>
          </div>
        </button>
      </div>

      <div className="mx-auto mt-6 flex max-w-xl flex-wrap items-center justify-between gap-3">
        <Button variant="secondary" onClick={() => go(-1)} disabled={index === 0}>
          <ChevronLeft className="h-4 w-4" aria-hidden /> Previous
        </Button>
        <div className="flex gap-2">
          <Button variant={status === "revise" ? "primary" : "secondary"} onClick={() => mark("revise")}>
            Revise later
          </Button>
          <Button variant={status === "known" ? "primary" : "secondary"} onClick={() => mark("known")}>
            I know this
          </Button>
        </div>
        <Button variant="secondary" onClick={() => go(1)} disabled={index === active.cards.length - 1}>
          Next <ChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
      <div className="mx-auto mt-4 max-w-xl">
        <ErrorBanner message={error} />
      </div>
    </div>
  );
}
