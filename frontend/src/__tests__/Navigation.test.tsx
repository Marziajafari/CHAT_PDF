import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "../App";
import { renderWithProviders } from "../test/render";

vi.mock("../lib/api", async () => (await import("../test/apiMock")).makeApiMock());

test("sidebar links navigate between pages", async () => {
  const user = userEvent.setup();
  renderWithProviders(<App />);

  expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();

  const nav = screen.getByRole("navigation", { name: "Main" });
  const pages = ["My Documents", "AI Chat", "Summaries", "Quiz Generator", "Flashcards", "Chat History"];
  for (const label of pages) {
    await user.click(screen.getByRole("link", { name: label }));
    expect(await screen.findByRole("heading", { level: 1, name: label })).toBeInTheDocument();
  }
  expect(nav).toBeInTheDocument();
});
