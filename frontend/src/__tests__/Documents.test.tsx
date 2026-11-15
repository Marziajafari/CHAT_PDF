import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import * as api from "../lib/api";
import Documents from "../pages/Documents";
import { readyDoc, renderWithProviders } from "../test/render";

vi.mock("../lib/api", async () => (await import("../test/apiMock")).makeApiMock());

test("empty state is shown when there are no documents", async () => {
  renderWithProviders(<Documents />);
  expect(await screen.findByText("No documents yet")).toBeInTheDocument();
});

test("uploading a PDF calls the API", async () => {
  const user = userEvent.setup();
  vi.mocked(api.uploadDocument).mockResolvedValue({ ...readyDoc, processing_status: "processing" });
  renderWithProviders(<Documents />);

  const file = new File(["%PDF-1.4 test"], "notes.pdf", { type: "application/pdf" });
  await user.upload(screen.getByTestId("file-input"), file);

  await waitFor(() => expect(api.uploadDocument).toHaveBeenCalled());
  expect(vi.mocked(api.uploadDocument).mock.calls[0][0]).toBe(file);
});

test("upload errors from the backend are displayed", async () => {
  const user = userEvent.setup();
  vi.mocked(api.uploadDocument).mockRejectedValue(new Error("This PDF is password-protected."));
  renderWithProviders(<Documents />);

  await user.upload(screen.getByTestId("file-input"), new File(["x"], "locked.pdf", { type: "application/pdf" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("password-protected");
});

test("documents are listed and can be searched", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listDocuments).mockResolvedValue([
    readyDoc,
    { ...readyDoc, id: "doc2", original_filename: "history.pdf" },
  ]);
  renderWithProviders(<Documents />);

  expect(await screen.findByText("biology.pdf")).toBeInTheDocument();
  await user.type(screen.getByLabelText("Search documents"), "hist");
  expect(screen.queryByText("biology.pdf")).not.toBeInTheDocument();
  expect(screen.getByText("history.pdf")).toBeInTheDocument();
});
