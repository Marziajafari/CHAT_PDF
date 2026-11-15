import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import * as api from "../lib/api";
import Chat from "../pages/Chat";
import { readyDoc, renderWithProviders } from "../test/render";

vi.mock("../lib/api", async () => (await import("../test/apiMock")).makeApiMock());

beforeEach(() => {
  vi.mocked(api.listDocuments).mockResolvedValue([readyDoc]);
});

test("shows the empty state first", async () => {
  renderWithProviders(<Chat />);
  expect(await screen.findByText("Ask your first question")).toBeInTheDocument();
});

test("displays the question, a loading indicator, then the answer with sources", async () => {
  const user = userEvent.setup();
  let resolveChat: (v: Awaited<ReturnType<typeof api.sendChat>>) => void = () => {};
  vi.mocked(api.sendChat).mockReturnValue(new Promise((res) => (resolveChat = res)));
  renderWithProviders(<Chat />);

  await user.type(screen.getByLabelText("Your question"), "What is photosynthesis?");
  await user.click(screen.getByRole("button", { name: "Send" }));

  expect(screen.getByText("What is photosynthesis?")).toBeInTheDocument();
  expect(await screen.findByText(/Thinking/)).toBeInTheDocument();

  resolveChat({
    answer: "Plants turn light into energy.",
    chat_id: "c1",
    info: {},
    sources: [{ document_id: "doc1", filename: "biology.pdf", page_number: 3, excerpt: "Plants use light.", score: 0.8 }],
  });

  expect(await screen.findByText("Plants turn light into energy.")).toBeInTheDocument();
  expect(screen.getByText(/biology\.pdf · page 3/)).toBeInTheDocument();
  expect(screen.queryByText(/Thinking/)).not.toBeInTheDocument();
  expect(api.sendChat).toHaveBeenCalledWith({ question: "What is photosynthesis?", chat_id: null, document_ids: [] });
});

test("shows a clear error when the AI request fails", async () => {
  const user = userEvent.setup();
  vi.mocked(api.sendChat).mockRejectedValue(new Error("Cannot reach Ollama."));
  renderWithProviders(<Chat />);

  await user.type(screen.getByLabelText("Your question"), "Hello?");
  await user.click(screen.getByRole("button", { name: "Send" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot reach Ollama.");
});

test("selected documents are sent with the question", async () => {
  const user = userEvent.setup();
  vi.mocked(api.sendChat).mockResolvedValue({ answer: "ok", chat_id: "c1", info: {}, sources: [] });
  renderWithProviders(<Chat />);

  await user.click(await screen.findByRole("button", { name: "biology.pdf" }));
  await user.type(screen.getByLabelText("Your question"), "Define osmosis");
  await user.click(screen.getByRole("button", { name: "Send" }));

  await waitFor(() =>
    expect(api.sendChat).toHaveBeenCalledWith({ question: "Define osmosis", chat_id: null, document_ids: ["doc1"] }),
  );
});
