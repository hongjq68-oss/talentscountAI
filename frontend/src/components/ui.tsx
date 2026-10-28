import clsx from "clsx";
import { Check, Copy } from "lucide-react";
import { useState, type ReactNode } from "react";

export function GithubIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (<svg viewBox="0 0 24 24" fill="currentColor" className={className}><path d="M12 .5C5.65.5.5 5.65.5 12a11.5 11.5 0 0 0 7.86 10.92c.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.53-1.33-1.28-1.69-1.28-1.69-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.04 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.58.23 2.75.11 3.04.74.81 1.19 1.83 1.19 3.09 0 4.41-2.69 5.38-5.25 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z"/></svg>);
}
export function LinkedinIcon({ className = "h-4 w-4" }: { className?: string }) {
  return (<svg viewBox="0 0 24 24" fill="currentColor" className={className}><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.48-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28ZM5.34 7.43a2.06 2.06 0 1 1 0-4.13 2.06 2.06 0 0 1 0 4.13ZM7.12 20.45H3.56V9h3.56v11.45ZM22.22 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.45c.98 0 1.78-.77 1.78-1.73V1.73C24 .77 23.2 0 22.22 0Z"/></svg>);
}

export function Card({ title, icon, action, children, className }: { title?: ReactNode; icon?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <div className={clsx("card", className)}>
      {title && (
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3.5">
          <div className="flex items-center gap-2 section-title">{icon}{title}</div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  );
}

const tones: Record<string, string> = {
  slate: "bg-slate-100 text-slate-700", blue: "bg-brand-50 text-brand-700", green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700", red: "bg-rose-50 text-rose-700", violet: "bg-violet-50 text-violet-700", cyan: "bg-cyan-50 text-cyan-700",
};
export function Badge({ children, tone = "slate", className }: { children: ReactNode; tone?: keyof typeof tones | string; className?: string }) {
  return <span className={clsx("chip", tones[tone] ?? tones.slate, className)}>{children}</span>;
}

export const stageTone: Record<string, string> = {
  Sourced: "slate", Shortlisted: "blue", Contacted: "violet", Interviewing: "amber", Offer: "cyan", Hired: "green", Rejected: "red",
};
export const tierTone: Record<string, string> = { Primary: "blue", Secondary: "violet", Adjacent: "cyan" };

export function scoreColor(s: number) {
  return s >= 70 ? "text-emerald-600" : s >= 45 ? "text-amber-600" : "text-slate-500";
}
export function ScoreRing({ score, size = 44 }: { score: number; size?: number }) {
  const r = (size - 6) / 2, c = 2 * Math.PI * r;
  const color = score >= 70 ? "#059669" : score >= 45 ? "#d97706" : "#94a3b8";
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#e2e8f0" strokeWidth={4} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={4} fill="none" strokeDasharray={c} strokeDashoffset={c - (c * Math.min(score, 100)) / 100} strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-slate-800">{score}</div>
    </div>
  );
}

export function Avatar({ name, src, size = 36 }: { name: string; src?: string; size?: number }) {
  if (src) return <img src={src} alt={name} className="rounded-full object-cover shrink-0" style={{ width: size, height: size }} />;
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join("");
  const hues = ["bg-brand-100 text-brand-700", "bg-violet-100 text-violet-700", "bg-emerald-100 text-emerald-700", "bg-amber-100 text-amber-700", "bg-rose-100 text-rose-700", "bg-cyan-100 text-cyan-700"];
  const h = hues[[...name].reduce((a, ch) => a + ch.charCodeAt(0), 0) % hues.length];
  return <div className={clsx("rounded-full flex items-center justify-center font-semibold shrink-0", h)} style={{ width: size, height: size, fontSize: size * 0.38 }}>{initials || "?"}</div>;
}

export function CopyButton({ text, label }: { text: string; label?: string }) {
  const [ok, setOk] = useState(false);
  return (
    <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => { navigator.clipboard.writeText(text); setOk(true); setTimeout(() => setOk(false), 1500); }}>
      {ok ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}{label && (ok ? "Copied" : label)}
    </button>
  );
}

export function Tabs({ tabs, value, onChange }: { tabs: { key: string; label: string; icon?: ReactNode; count?: number }[]; value: string; onChange: (k: string) => void }) {
  return (
    <div className="flex gap-1 border-b border-slate-200 overflow-x-auto">
      {tabs.map((t) => (
        <button key={t.key} onClick={() => onChange(t.key)}
          className={clsx("flex items-center gap-2 whitespace-nowrap px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition",
            value === t.key ? "border-brand-600 text-brand-700" : "border-transparent text-slate-500 hover:text-slate-800")}>
          {t.icon}{t.label}
          {t.count !== undefined && <span className={clsx("rounded-full px-1.5 text-xs", value === t.key ? "bg-brand-100 text-brand-700" : "bg-slate-100 text-slate-600")}>{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Empty({ icon, title, children }: { icon: ReactNode; title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-14 px-6">
      <div className="h-12 w-12 rounded-full bg-brand-50 text-brand-600 flex items-center justify-center mb-3">{icon}</div>
      <div className="font-semibold text-slate-900">{title}</div>
      <div className="text-sm text-slate-500 mt-1 max-w-md">{children}</div>
    </div>
  );
}

export function List({ items, icon }: { items?: string[]; icon?: ReactNode }) {
  if (!items?.length) return <div className="text-sm text-slate-400">—</div>;
  return (
    <ul className="space-y-2">
      {items.map((x, i) => (
        <li key={i} className="flex gap-2.5 text-sm text-slate-700">
          <span className="mt-0.5 shrink-0 text-brand-500">{icon ?? "•"}</span><span>{x}</span>
        </li>
      ))}
    </ul>
  );
}

export function timeAgo(iso: string) {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
