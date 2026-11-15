import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { History as HistoryIcon, Trash2 } from "lucide-react";
import { deleteChat, listChats } from "../lib/api";
import { Button, Card, EmptyState, ErrorBanner, PageHeader, Spinner } from "../components/ui";
import { errorMessage, formatDate } from "../lib/utils";

export default function History() {
  const qc = useQueryClient();
  const { data: chats = [], isLoading, error } = useQuery({ queryKey: ["chats"], queryFn: listChats });
  const remove = useMutation({
    mutationFn: deleteChat,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chats"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return (
    <div>
      <PageHeader title="Chat History" subtitle="Saved conversations stay on this computer." />
      {isLoading && <Spinner label="Loading conversations" />}
      <ErrorBanner message={error ? errorMessage(error) : remove.error ? errorMessage(remove.error) : null} />
      {!isLoading && chats.length === 0 && (
        <EmptyState
          icon={<HistoryIcon className="h-10 w-10" />}
          title="No conversations yet"
          text="Your questions and the answers with page references will be listed here."
          action={
            <Link to="/chat" className="rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark">
              Start a chat
            </Link>
          }
        />
      )}
      <div className="space-y-3">
        {chats.map((c) => (
          <Card key={c.id} className="flex flex-wrap items-center justify-between gap-3">
            <Link to={`/chat?chat=${c.id}`} className="min-w-0 flex-1 hover:text-brand">
              <p className="truncate font-medium">{c.title}</p>
              <p className="mt-1 text-xs text-ink-soft">
                {c.message_count} messages · updated {formatDate(c.updated_at)}
              </p>
            </Link>
            <Button
              variant="danger"
              aria-label={`Delete conversation ${c.title}`}
              disabled={remove.isPending}
              onClick={() => {
                if (window.confirm("Delete this conversation?")) remove.mutate(c.id);
              }}
            >
              <Trash2 className="h-4 w-4" aria-hidden /> Delete
            </Button>
          </Card>
        ))}
      </div>
    </div>
  );
}
