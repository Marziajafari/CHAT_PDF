import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

export function renderWithProviders(ui: ReactElement, route = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

export const readyDoc = {
  id: "doc1",
  original_filename: "biology.pdf",
  upload_date: "2026-01-01T10:00:00",
  processing_status: "ready" as const,
  page_count: 10,
  file_size: 2048,
  chunk_count: 25,
  error_message: null,
};
