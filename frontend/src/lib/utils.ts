import axios from "axios";

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      return detail.map((d: { msg?: string }) => d.msg ?? "Invalid input").join("; ");
    }
    if (err.code === "ERR_NETWORK") return "Cannot reach the StudyMate backend. Is it running on port 8000?";
    if (err.code === "ECONNABORTED") return "The request timed out. The local model may be overloaded.";
    return err.message;
  }
  if (err instanceof Error) return err.message;
  return "Something went wrong.";
}

// The backend stores UTC without a time-zone suffix, so add one before parsing.
export function parseDate(value: string): Date {
  return new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
}

export function formatDate(value: string): string {
  return parseDate(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
