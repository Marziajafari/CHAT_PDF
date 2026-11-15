import { screen } from "@testing-library/react";
import { vi } from "vitest";
import * as api from "../lib/api";
import Dashboard from "../pages/Dashboard";
import { readyDoc, renderWithProviders } from "../test/render";

vi.mock("../lib/api", async () => (await import("../test/apiMock")).makeApiMock());

test("dashboard shows statistics and recent documents", async () => {
  vi.mocked(api.getDashboard).mockResolvedValue({
    total_documents: 3,
    total_questions: 12,
    total_quizzes_completed: 2,
    average_quiz_score: 80,
    recent_documents: [readyDoc],
    recent_chats: [],
    activity: [{ date: "2026-01-01", questions: 2, quizzes: 1 }],
  });
  renderWithProviders(<Dashboard />);

  expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
  expect(await screen.findByText("12")).toBeInTheDocument();
  expect(screen.getByText("80%")).toBeInTheDocument();
  expect(screen.getByText("biology.pdf")).toBeInTheDocument();
  expect(screen.getByText(/No conversations yet/i)).toBeInTheDocument();
});

test("dashboard shows an error message when the backend fails", async () => {
  vi.mocked(api.getDashboard).mockRejectedValue(new Error("Backend down"));
  renderWithProviders(<Dashboard />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Backend down");
});
