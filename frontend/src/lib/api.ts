import axios from "axios";

// The Vite dev server proxies /api to the FastAPI backend on port 8000.
// Timeouts are long because a 1B model on an 8 GB laptop can take minutes.
export const http = axios.create({ baseURL: "/api", timeout: 10 * 60 * 1000 });

export interface DocumentInfo {
  id: string;
  original_filename: string;
  upload_date: string;
  processing_status: "processing" | "ready" | "failed";
  page_count: number | null;
  file_size: number;
  chunk_count: number;
  error_message: string | null;
}

export interface Source {
  document_id: string;
  filename: string;
  page_number: number;
  excerpt: string;
  score: number;
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export interface ChatSummary {
  id: string;
  title: string;
  document_ids: string[];
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatDetail extends ChatSummary {
  messages: ChatMessage[];
}

export interface ChatResponse {
  answer: string;
  chat_id: string;
  sources: Source[];
  info: Record<string, unknown>;
}

export interface Summary {
  document_id: string;
  mode: string;
  summary: string;
  key_concepts: string[];
  definitions: { term: string; definition: string }[];
  exam_notes: string[];
  sections_total: number;
  sections_used: number;
}

export interface Quiz {
  quiz_id: string;
  document_id: string;
  difficulty: string;
  questions: { question: string; options: string[] }[];
  warning: string | null;
}

export interface QuizResult {
  quiz_id: string;
  score: number;
  total: number;
  results: {
    question: string;
    options: string[];
    selected: number | null;
    correct_index: number;
    correct: boolean;
    explanation: string;
  }[];
}

export interface QuizHistoryItem {
  id: string;
  document_id: string;
  document_name: string | null;
  difficulty: string;
  score: number;
  total_questions: number;
  completed_at: string;
}

export interface Flashcard {
  question: string;
  answer: string;
  key_concept: string;
  source_page: number | null;
}

export type CardStatus = "known" | "revise";

export interface FlashcardSet {
  id: string;
  document_id: string;
  title: string;
  cards: Flashcard[];
  progress: Record<string, CardStatus>;
  created_at: string;
}

export interface Dashboard {
  total_documents: number;
  total_questions: number;
  total_quizzes_completed: number;
  average_quiz_score: number | null;
  recent_documents: DocumentInfo[];
  recent_chats: ChatSummary[];
  activity: { date: string; questions: number; quizzes: number }[];
}

export interface SystemStatus {
  app: string;
  version: string;
  backend: string;
  ollama: { reachable: boolean; model: string; model_available: boolean; installed_models: string[] };
  embeddings: { backend: string; model: string; loaded: boolean };
  database: { status: string; documents: number };
  vector_store: { status: string; chunks: number };
  config: { chunk_size: number; chunk_overlap: number; top_k: number; relevance_threshold: number; max_upload_mb: number };
}

// ---- documents
export const listDocuments = () => http.get<DocumentInfo[]>("/documents").then((r) => r.data);

export const uploadDocument = (file: File, onProgress?: (percent: number) => void) => {
  const form = new FormData();
  form.append("file", file);
  return http
    .post<DocumentInfo>("/documents/upload", form, {
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100));
      },
    })
    .then((r) => r.data);
};

export const deleteDocument = (id: string) => http.delete(`/documents/${id}`).then(() => undefined);

// ---- chat
export const sendChat = (body: { question: string; chat_id: string | null; document_ids: string[] }) =>
  http.post<ChatResponse>("/chat", body).then((r) => r.data);
export const listChats = () => http.get<ChatSummary[]>("/chats").then((r) => r.data);
export const getChat = (id: string) => http.get<ChatDetail>(`/chats/${id}`).then((r) => r.data);
export const deleteChat = (id: string) => http.delete(`/chats/${id}`).then(() => undefined);

// ---- AI tools
export const summarize = (document_id: string, mode: "short" | "detailed") =>
  http.post<Summary>("/ai/summarize", { document_id, mode }).then((r) => r.data);
export const generateQuiz = (body: { document_id: string; difficulty: string; num_questions: number }) =>
  http.post<Quiz>("/ai/generate-quiz", body).then((r) => r.data);
export const submitQuiz = (quiz_id: string, answers: (number | null)[]) =>
  http.post<QuizResult>("/ai/submit-quiz", { quiz_id, answers }).then((r) => r.data);
export const listQuizHistory = () => http.get<QuizHistoryItem[]>("/ai/quiz-history").then((r) => r.data);
export const generateFlashcards = (document_id: string, num_cards: number) =>
  http.post<FlashcardSet>("/ai/generate-flashcards", { document_id, num_cards }).then((r) => r.data);
export const listFlashcardSets = () => http.get<FlashcardSet[]>("/ai/flashcard-sets").then((r) => r.data);
export const saveFlashcardProgress = (id: string, progress: Record<string, CardStatus>) =>
  http.patch<FlashcardSet>(`/ai/flashcard-sets/${id}/progress`, { progress }).then((r) => r.data);

// ---- dashboard / system
export const getDashboard = () => http.get<Dashboard>("/analytics/dashboard").then((r) => r.data);
export const getSystemStatus = () => http.get<SystemStatus>("/system/status").then((r) => r.data);
