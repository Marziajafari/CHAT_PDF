import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import * as api from "../lib/api";
import Quiz from "../pages/Quiz";
import { readyDoc, renderWithProviders } from "../test/render";

vi.mock("../lib/api", async () => (await import("../test/apiMock")).makeApiMock());

test("full quiz flow: generate, answer, submit and see results", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listDocuments).mockResolvedValue([readyDoc]);
  vi.mocked(api.generateQuiz).mockResolvedValue({
    quiz_id: "q1",
    document_id: "doc1",
    difficulty: "easy",
    warning: null,
    questions: [
      { question: "What do plants absorb?", options: ["Light", "Sound", "Metal", "Glass"] },
      { question: "Where is chlorophyll found?", options: ["Roots", "Chloroplasts", "Bones", "Clouds"] },
    ],
  });
  vi.mocked(api.submitQuiz).mockResolvedValue({
    quiz_id: "q1",
    score: 1,
    total: 2,
    results: [
      { question: "What do plants absorb?", options: ["Light", "Sound", "Metal", "Glass"], selected: 0, correct_index: 0, correct: true, explanation: "Plants absorb light." },
      { question: "Where is chlorophyll found?", options: ["Roots", "Chloroplasts", "Bones", "Clouds"], selected: 0, correct_index: 1, correct: false, explanation: "It is in chloroplasts." },
    ],
  });

  renderWithProviders(<Quiz />);

  await user.selectOptions(await screen.findByLabelText("Document"), "doc1");
  await user.click(screen.getByRole("button", { name: /generate quiz/i }));

  expect(await screen.findByText("What do plants absorb?")).toBeInTheDocument();
  expect(screen.getByText("Question 1 of 2")).toBeInTheDocument();

  await user.click(screen.getByLabelText("Light"));
  await user.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByText("Where is chlorophyll found?")).toBeInTheDocument();

  const submit = screen.getByRole("button", { name: "Submit quiz" });
  expect(submit).toBeDisabled(); // not every question answered yet
  await user.click(screen.getByLabelText("Roots"));
  expect(submit).toBeEnabled();
  await user.click(submit);

  expect(await screen.findByText("1 / 2")).toBeInTheDocument();
  expect(screen.getByText(/Plants absorb light\./)).toBeInTheDocument();
  expect(screen.getByText(/It is in chloroplasts\./)).toBeInTheDocument();
  expect(api.submitQuiz).toHaveBeenCalledWith("q1", [0, 0]);

  await user.click(screen.getByRole("button", { name: "Retry quiz" }));
  expect(screen.getByText("Question 1 of 2")).toBeInTheDocument();
});

test("generation errors are shown", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listDocuments).mockResolvedValue([readyDoc]);
  vi.mocked(api.generateQuiz).mockRejectedValue(new Error("The model did not produce any valid questions."));
  renderWithProviders(<Quiz />);

  await user.selectOptions(await screen.findByLabelText("Document"), "doc1");
  await user.click(screen.getByRole("button", { name: /generate quiz/i }));
  expect(await screen.findByRole("alert")).toHaveTextContent("did not produce any valid questions");
});
