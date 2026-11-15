import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import {
  BookOpen,
  FileText,
  Gauge,
  GraduationCap,
  History,
  Layers,
  ListChecks,
  Menu,
  MessageSquare,
  Settings,
  X,
} from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: Gauge, end: true },
  { to: "/documents", label: "My Documents", icon: FileText },
  { to: "/chat", label: "AI Chat", icon: MessageSquare },
  { to: "/summaries", label: "Summaries", icon: BookOpen },
  { to: "/quiz", label: "Quiz Generator", icon: ListChecks },
  { to: "/flashcards", label: "Flashcards", icon: Layers },
  { to: "/history", label: "Chat History", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const [open, setOpen] = useState(false);

  return (
    <div className="min-h-screen md:flex">
      <header className="flex items-center justify-between border-b border-line bg-white px-4 py-3 md:hidden">
        <span className="flex items-center gap-2 font-bold">
          <GraduationCap className="h-5 w-5 text-brand" aria-hidden /> StudyMate AI
        </span>
        <button aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen(!open)} className="rounded-lg p-2 hover:bg-canvas">
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </header>

      <aside
        className={`${open ? "block" : "hidden"} w-full shrink-0 border-r border-line bg-white md:sticky md:top-0 md:block md:h-screen md:w-64`}
      >
        <div className="hidden items-center gap-2 px-6 py-6 text-lg font-bold md:flex">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-gradient-to-br from-brand to-accent text-white">
            <GraduationCap className="h-5 w-5" aria-hidden />
          </span>
          StudyMate AI
        </div>
        <nav aria-label="Main" className="flex flex-col gap-1 px-3 pb-6">
          {links.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand/10 text-brand" : "text-ink-soft hover:bg-canvas hover:text-ink"
                }`
              }
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 p-4 md:p-8">
        <div className="mx-auto max-w-5xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
