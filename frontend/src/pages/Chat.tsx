import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Plus, Send, Trash2 } from "lucide-react";
import { deleteChat, getChat, sendChat } from "../lib/api";
import type { ChatMessage } from "../lib/api";
import DocumentPicker from "../components/DocumentPicker";
import { Button, Card, EmptyState, ErrorBanner, PageHeader, inputClass } from "../components/ui";
import { errorMessage } from "../lib/utils";

function Bubble({ message }: { message: ChatMessage }) {
  const mine = message.role === "user";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          mine ? "bg-brand text-white" : "border border-line bg-white text-ink"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {!mine && message.sources && message.sources.length > 0 && (
          <details className="mt-3 border-t border-line pt-2 text-xs text-ink-soft">
            <summary className="cursor-pointer font-medium text-ink">Sources ({message.sources.length})</summary>
            <ul className="mt-2 space-y-2">
              {message.sources.map((s, i) => (
                <li key={i} className="rounded-lg bg-canvas p-2">
                  <p className="font-medium text-ink">
                    {s.filename} · page {s.page_number}
                  </p>
                  <p className="mt-1">{s.excerpt}</p>
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}

export default function Chat() {
  const qc = useQueryClient();
  const [params, setParams] = useSearchParams();
  const chatParam = params.get("chat");
  const [chatId, setChatId] = useState<string | null>(chatParam);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Open a saved conversation (from Chat History or the dashboard)
  useEffect(() => {
    if (!chatParam) return;
    getChat(chatParam)
      .then((c) => {
        setChatId(c.id);
        setMessages(c.messages);
        setSelected(c.document_ids);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [chatParam]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages.length]);

  const send = useMutation({
    mutationFn: (question: string) => sendChat({ question, chat_id: chatId, document_ids: selected }),
    onSuccess: (res) => {
      setChatId(res.chat_id);
      setMessages((m) => [...m, { role: "assistant", content: res.answer, sources: res.sources }]);
      qc.invalidateQueries({ queryKey: ["chats"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => setError(errorMessage(e)),
  });

  const submit = () => {
    const question = input.trim();
    if (!question || send.isPending) return;
    setError(null);
    setMessages((m) => [...m, { role: "user", content: question }]);
    setInput("");
    send.mutate(question);
  };

  const newChat = () => {
    setChatId(null);
    setMessages([]);
    setError(null);
    setParams({});
  };

  const clearConversation = async () => {
    try {
      if (chatId) await deleteChat(chatId);
      qc.invalidateQueries({ queryKey: ["chats"] });
      newChat();
    } catch (e) {
      setError(errorMessage(e));
    }
  };

  return (
    <div>
      <PageHeader
        title="AI Chat"
        subtitle="Answers come from your uploaded documents, with page references."
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={newChat}>
              <Plus className="h-4 w-4" aria-hidden /> New chat
            </Button>
            <Button variant="danger" onClick={clearConversation} disabled={messages.length === 0}>
              <Trash2 className="h-4 w-4" aria-hidden /> Clear conversation
            </Button>
          </div>
        }
      />

      <Card className="mb-4">
        <DocumentPicker multiple value={selected} onChange={setSelected} label="Search in" />
      </Card>

      <div className="min-h-[320px] space-y-3 rounded-2xl bg-canvas">
        {messages.length === 0 && !send.isPending ? (
          <EmptyState
            icon={<MessageSquare className="h-10 w-10" />}
            title="Ask your first question"
            text="Pick documents above (or leave empty to search all of them), then ask about a concept, a definition or a page."
          />
        ) : (
          messages.map((m, i) => <Bubble key={i} message={m} />)
        )}
        {send.isPending && (
          <div className="flex justify-start">
            <div role="status" className="rounded-2xl border border-line bg-white px-4 py-3 text-sm text-ink-soft">
              Thinking
              <span className="ml-1 inline-flex gap-0.5" aria-hidden>
                <span className="animate-bounce">.</span>
                <span className="animate-bounce [animation-delay:150ms]">.</span>
                <span className="animate-bounce [animation-delay:300ms]">.</span>
              </span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="mt-3">
        <ErrorBanner message={error} />
      </div>

      <div className="mt-3 flex items-end gap-2">
        <textarea
          aria-label="Your question"
          rows={2}
          maxLength={2000}
          placeholder="Ask a question about your documents…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          className={`${inputClass} resize-none`}
        />
        <Button onClick={submit} disabled={!input.trim() || send.isPending} aria-label="Send">
          <Send className="h-4 w-4" aria-hidden /> Send
        </Button>
      </div>
    </div>
  );
}
