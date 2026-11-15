import { useQuery } from "@tanstack/react-query";
import { listDocuments } from "../lib/api";
import { inputClass } from "./ui";

interface Props {
  multiple?: boolean;
  value: string[];
  onChange: (ids: string[]) => void;
  label?: string;
}

/** Lists only documents that finished processing. */
export default function DocumentPicker({ multiple = false, value, onChange, label = "Document" }: Props) {
  const { data: docs = [], isLoading } = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const ready = docs.filter((d) => d.processing_status === "ready");

  if (isLoading) return <p className="text-sm text-ink-soft">Loading documents…</p>;
  if (ready.length === 0) {
    return <p className="text-sm text-ink-soft">No processed documents yet. Upload a PDF in My Documents first.</p>;
  }

  if (!multiple) {
    return (
      <label className="block text-sm font-medium">
        {label}
        <select
          className={`${inputClass} mt-1`}
          value={value[0] ?? ""}
          onChange={(e) => onChange(e.target.value ? [e.target.value] : [])}
        >
          <option value="">Choose a document…</option>
          {ready.map((d) => (
            <option key={d.id} value={d.id}>
              {d.original_filename}
            </option>
          ))}
        </select>
      </label>
    );
  }

  const toggle = (id: string) =>
    onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);

  return (
    <div>
      <p className="mb-2 text-sm font-medium">
        {label} <span className="font-normal text-ink-soft">({value.length === 0 ? "all documents" : `${value.length} selected`})</span>
      </p>
      <div className="flex flex-wrap gap-2">
        {ready.map((d) => (
          <button
            key={d.id}
            type="button"
            aria-pressed={value.includes(d.id)}
            onClick={() => toggle(d.id)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
              value.includes(d.id) ? "border-brand bg-brand text-white" : "border-line bg-white text-ink hover:bg-canvas"
            }`}
          >
            {d.original_filename}
          </button>
        ))}
      </div>
    </div>
  );
}
