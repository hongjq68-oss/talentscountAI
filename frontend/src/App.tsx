import clsx from "clsx";
import { Briefcase, LayoutDashboard, Plus, Search, Settings as SettingsIcon, Sparkles, Users } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";
import Dashboard from "./pages/Dashboard";
import JobDetail from "./pages/JobDetail";
import NewSearch from "./pages/NewSearch";
import Settings from "./pages/Settings";
import TalentPool from "./pages/TalentPool";
import type { Status } from "./types";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/jobs", label: "Searches", icon: Briefcase },
  { to: "/talent", label: "Talent Pool", icon: Users },
  { to: "/settings", label: "Integrations", icon: SettingsIcon },
];

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const navigate = useNavigate();
  useEffect(() => { api.status().then(setStatus).catch(() => {}); }, []);

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="hidden md:flex w-60 shrink-0 flex-col bg-ink-900 text-slate-300">
        <div className="flex items-center gap-2.5 px-5 h-16 border-b border-white/5">
          <div className="h-8 w-8 rounded-lg bg-brand-600 flex items-center justify-center"><Sparkles className="text-white" size={18} /></div>
          <div>
            <div className="text-white font-semibold leading-tight">TalentScout<span className="text-brand-400"> AI</span></div>
            <div className="text-[11px] text-slate-400">Sourcing agent</div>
          </div>
        </div>
        <div className="p-3">
          <button onClick={() => navigate("/new")} className="btn-primary w-full"><Plus className="h-4 w-4" />New search</button>
        </div>
        <nav className="px-3 space-y-0.5">
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => clsx("flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition", isActive ? "bg-white/10 text-white" : "hover:bg-white/5 hover:text-white")}>
              <n.icon className="h-4 w-4" />{n.label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto p-4 m-3 rounded-xl bg-white/5 text-xs space-y-1.5">
          <div className="text-slate-400 font-medium uppercase tracking-wide text-[10px]">Agent engine</div>
          <Dot ok={!!status?.llm} label={status?.llm ? `AI: ${status.llm}` : "AI: heuristic mode"} />
          <Dot ok={!!status?.search} label={status?.search ? `Web search: ${status.search}` : "Web search: manual links"} />
          <Dot ok={!!status?.github_token} label="GitHub API" />
        </div>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 shrink-0 bg-white border-b border-slate-200 flex items-center px-6 gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="h-4 w-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input className="input pl-9 bg-slate-50" placeholder="Search candidates, companies, skills…" onKeyDown={(e) => { if (e.key === "Enter") navigate(`/talent?q=${encodeURIComponent((e.target as HTMLInputElement).value)}`); }} />
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button onClick={() => navigate("/new")} className="btn-primary md:hidden"><Plus className="h-4 w-4" /></button>
            <div className="h-9 w-9 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-sm font-semibold">TA</div>
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/jobs" element={<Dashboard listOnly />} />
            <Route path="/new" element={<NewSearch status={status} />} />
            <Route path="/jobs/:id" element={<JobDetail />} />
            <Route path="/talent" element={<TalentPool />} />
            <Route path="/settings" element={<Settings onSaved={setStatus} />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}

function Dot({ ok, label }: { ok: boolean; label: string }) {
  return <div className="flex items-center gap-2"><span className={clsx("h-1.5 w-1.5 rounded-full", ok ? "bg-emerald-400" : "bg-amber-400")} />{label}</div>;
}
