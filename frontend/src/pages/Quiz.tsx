import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ListChecks, XCircle } from "lucide-react";
import { generateQuiz, listQuizHistory, submitQuiz } from "../lib/api";
import type { Quiz as QuizData, QuizResult } from "../lib/api";
import DocumentPicker from "../components/DocumentPicker";
import { Button, Card, ErrorBanner, PageHeader, Spinner, inputClass } from "../components/ui";
import { errorMessage, formatDate } from "../lib/utils";

type Phase = "setup" | "taking" | "results";

export default function Quiz() {
  const qc = useQueryClient();
  const [phase, setPhase] = useState<Phase>("setup");
  const [docIds, setDocIds] = useState<string[]>([]);
  const [difficulty, setDifficulty] = useState("medium");
  const [count, setCount] = useState(5);
  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [answers, setAnswers] = useState<(number | null)[]>([]);
  const [current, setCurrent] = useState(0);
  const [result, setResult] = useState<QuizResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: history = [] } = useQuery({ queryKey: ["quiz-history"], queryFn: listQuizHistory });

  const generate = useMutation({
    mutationFn: () => generateQuiz({ document_id: docIds[0], difficulty, num_questions: count }),
    onMutate: () => setError(null),
    onSuccess: (q) => {
      setQuiz(q);
      setAnswers(q.questions.map(() => null));
      setCurrent(0);
      setResult(null);
      setPhase("taking");
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const submit = useMutation({
    mutationFn: () => submitQuiz(quiz!.quiz_id, answers),
    onMutate: () => setError(null),
    onSuccess: (r) => {
      setResult(r);
      setPhase("results");
      qc.invalidateQueries({ queryKey: ["quiz-history"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const retake = () => {
    if (!quiz) return;
    setAnswers(quiz.questions.map(() => null));
    setCurrent(0);
    setResult(null);
    setPhase("taking");
  };

  const newQuiz = () => {
    setQuiz(null);
    setResult(null);
    setPhase("setup");
  };

  if (phase === "setup") {
    return (
      <div>
        <PageHeader title="Quiz Generator" subtitle="Multiple-choice questions written from your document." />
        <Card>
          <div className="grid gap-4 sm:grid-cols-3">
            <DocumentPicker value={docIds} onChange={setDocIds} />
            <label className="block text-sm font-medium">
              Difficulty
              <select className={`${inputClass} mt-1`} value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </label>
            <label className="block text-sm font-medium">
              Number of questions
              <input
                type="number"
                min={1}
                max={20}
                className={`${inputClass} mt-1`}
                value={count}
                onChange={(e) => setCount(Math.min(20, Math.max(1, Number(e.target.value) || 1)))}
              />
            </label>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <Button onClick={() => generate.mutate()} disabled={docIds.length === 0 || generate.isPending}>
              <ListChecks className="h-4 w-4" aria-hidden /> Generate quiz
            </Button>
            {generate.isPending && <Spinner label="Writing questions… this can take a few minutes" />}
          </div>
        </Card>
        <div className="mt-4">
          <ErrorBanner message={error} />
        </div>

        <Card className="mt-6">
          <h2 className="mb-3 font-semibold">Previous attempts</h2>
          {history.length === 0 ? (
            <p className="text-sm text-ink-soft">No completed quizzes yet.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {history.map((h) => (
                <li key={h.id} className="flex justify-between gap-3">
                  <span className="truncate">
                    {h.document_name ?? "Deleted document"} · {h.difficulty}
                  </span>
                  <span className="shrink-0 text-ink-soft">
                    {h.score}/{h.total_questions} · {formatDate(h.completed_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    );
  }

  if (phase === "taking" && quiz) {
    const q = quiz.questions[current];
    const last = current === quiz.questions.length - 1;
    const answeredAll = answers.every((a) => a !== null);
    return (
      <div>
        <PageHeader title="Quiz Generator" subtitle={`Question ${current + 1} of ${quiz.questions.length}`} />
        {quiz.warning && <p className="mb-3 text-sm text-warn">{quiz.warning}</p>}
        <div
          className="mb-4 h-2 overflow-hidden rounded-full bg-white"
          role="progressbar"
          aria-valuenow={current + 1}
          aria-valuemin={1}
          aria-valuemax={quiz.questions.length}
        >
          <div className="h-full bg-gradient-to-r from-brand to-accent" style={{ width: `${((current + 1) / quiz.questions.length) * 100}%` }} />
        </div>
        <Card>
          <h2 className="mb-4 text-lg font-semibold">{q.question}</h2>
          <div role="radiogroup" aria-label="Answer options" className="space-y-2">
            {q.options.map((opt, i) => (
              <label
                key={i}
                className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm ${
                  answers[current] === i ? "border-brand bg-brand/5" : "border-line hover:bg-canvas"
                }`}
              >
                <input
                  type="radio"
                  name={`q-${current}`}
                  checked={answers[current] === i}
                  onChange={() => setAnswers((a) => a.map((v, idx) => (idx === current ? i : v)))}
                />
                {opt}
              </label>
            ))}
          </div>
          <div className="mt-5 flex justify-between">
            <Button variant="secondary" onClick={() => setCurrent((c) => c - 1)} disabled={current === 0}>
              Previous
            </Button>
            {last ? (
              <Button onClick={() => submit.mutate()} disabled={!answeredAll || submit.isPending}>
                Submit quiz
              </Button>
            ) : (
              <Button onClick={() => setCurrent((c) => c + 1)}>Next</Button>
            )}
          </div>
          {last && !answeredAll && <p className="mt-3 text-xs text-ink-soft">Answer every question to submit.</p>}
        </Card>
        <div className="mt-4">
          <ErrorBanner message={error} />
        </div>
      </div>
    );
  }

  return (
    <div>
      <PageHeader title="Quiz Generator" subtitle="Results" />
      {result && (
        <>
          <Card className="mb-4 text-center">
            <p className="text-sm text-ink-soft">Your score</p>
            <p className="text-4xl font-bold">
              {result.score} / {result.total}
            </p>
            <div className="mt-4 flex justify-center gap-3">
              <Button onClick={retake}>Retry quiz</Button>
              <Button variant="secondary" onClick={newQuiz}>
                New quiz
              </Button>
            </div>
          </Card>
          <div className="space-y-3">
            {result.results.map((r, i) => (
              <Card key={i}>
                <p className="flex items-start gap-2 font-medium">
                  {r.correct ? (
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-ok" aria-label="Correct" />
                  ) : (
                    <XCircle className="mt-0.5 h-5 w-5 shrink-0 text-bad" aria-label="Incorrect" />
                  )}
                  {r.question}
                </p>
                <ul className="mt-3 space-y-1 text-sm">
                  {r.options.map((o, idx) => (
                    <li
                      key={idx}
                      className={`rounded-lg px-3 py-2 ${
                        idx === r.correct_index
                          ? "bg-ok/10 text-ok"
                          : idx === r.selected
                            ? "bg-bad/10 text-bad"
                            : "text-ink-soft"
                      }`}
                    >
                      {o}
                      {idx === r.correct_index && " (correct answer)"}
                      {idx === r.selected && idx !== r.correct_index && " (your answer)"}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 text-sm text-ink-soft">
                  <span className="font-medium text-ink">Explanation: </span>
                  {r.explanation}
                </p>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
