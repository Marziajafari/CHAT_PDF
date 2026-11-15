import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { FileText, Layers, ListChecks, MessageSquare, BookOpen } from "lucide-react";
import { getDashboard } from "../lib/api";
import { Card, ErrorBanner, PageHeader, Spinner } from "../components/ui";
import { errorMessage, formatDate } from "../lib/utils";

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <p className="text-sm text-ink-soft">{label}</p>
      <p className="mt-1 text-3xl font-bold">{value}</p>
    </Card>
  );
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });

  if (isLoading) return <Spinner label="Loading dashboard" />;
  if (error || !data) return <ErrorBanner message={errorMessage(error)} />;

  const maxActivity = Math.max(1, ...data.activity.map((a) => a.questions + a.quizzes));

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Welcome to StudyMate AI. Everything runs on your own computer." />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Documents uploaded" value={data.total_documents} />
        <Stat label="Questions asked" value={data.total_questions} />
        <Stat label="Quizzes completed" value={data.total_quizzes_completed} />
        <Stat label="Average quiz score" value={data.average_quiz_score === null ? "–" : `${data.average_quiz_score}%`} />
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        {[
          { to: "/documents", label: "Upload a PDF", icon: FileText },
          { to: "/chat", label: "Ask a question", icon: MessageSquare },
          { to: "/summaries", label: "Summarise", icon: BookOpen },
          { to: "/quiz", label: "Take a quiz", icon: ListChecks },
          { to: "/flashcards", label: "Study flashcards", icon: Layers },
        ].map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            className="inline-flex items-center gap-2 rounded-xl border border-line bg-white px-4 py-2 text-sm font-medium hover:border-brand hover:text-brand"
          >
            <Icon className="h-4 w-4" aria-hidden /> {label}
          </Link>
        ))}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="mb-3 font-semibold">Recent documents</h2>
          {data.recent_documents.length === 0 ? (
            <p className="text-sm text-ink-soft">No documents yet. Upload your first lecture PDF to get started.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.recent_documents.map((d) => (
                <li key={d.id} className="flex justify-between gap-3">
                  <span className="truncate">{d.original_filename}</span>
                  <span className="shrink-0 text-ink-soft">{formatDate(d.upload_date)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card>
          <h2 className="mb-3 font-semibold">Recent conversations</h2>
          {data.recent_chats.length === 0 ? (
            <p className="text-sm text-ink-soft">No conversations yet. Ask a question about a document.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {data.recent_chats.map((c) => (
                <li key={c.id}>
                  <Link to={`/chat?chat=${c.id}`} className="flex justify-between gap-3 hover:text-brand">
                    <span className="truncate">{c.title}</span>
                    <span className="shrink-0 text-ink-soft">{c.message_count} messages</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card className="mt-4">
        <h2 className="mb-1 font-semibold">Study activity, last 7 days</h2>
        <p className="mb-4 text-xs text-ink-soft">Questions asked plus quizzes completed per day</p>
        <div className="flex h-32 items-end gap-3" role="img" aria-label="Bar chart of study activity for the last seven days">
          {data.activity.map((a) => {
            const total = a.questions + a.quizzes;
            return (
              <div key={a.date} className="flex flex-1 flex-col items-center gap-1">
                <span className="text-xs text-ink-soft">{total}</span>
                <div
                  className="w-full rounded-t-md bg-gradient-to-t from-brand to-accent"
                  style={{ height: `${Math.max(4, (total / maxActivity) * 100)}%`, opacity: total ? 1 : 0.2 }}
                />
                <span className="text-xs text-ink-soft">{a.date.slice(5)}</span>
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
