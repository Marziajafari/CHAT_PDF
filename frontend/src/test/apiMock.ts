import { vi } from "vitest";

/** Every function of lib/api replaced by a mock that resolves to an empty-but-valid value. */
export function makeApiMock() {
  const emptyDashboard = {
    total_documents: 0,
    total_questions: 0,
    total_quizzes_completed: 0,
    average_quiz_score: null,
    recent_documents: [],
    recent_chats: [],
    activity: [],
  };
  return {
    http: {},
    listDocuments: vi.fn().mockResolvedValue([]),
    uploadDocument: vi.fn().mockResolvedValue({}),
    deleteDocument: vi.fn().mockResolvedValue(undefined),
    sendChat: vi.fn(),
    listChats: vi.fn().mockResolvedValue([]),
    getChat: vi.fn(),
    deleteChat: vi.fn().mockResolvedValue(undefined),
    summarize: vi.fn(),
    generateQuiz: vi.fn(),
    submitQuiz: vi.fn(),
    listQuizHistory: vi.fn().mockResolvedValue([]),
    generateFlashcards: vi.fn(),
    listFlashcardSets: vi.fn().mockResolvedValue([]),
    saveFlashcardProgress: vi.fn(),
    getDashboard: vi.fn().mockResolvedValue(emptyDashboard),
    getSystemStatus: vi.fn(),
  };
}
