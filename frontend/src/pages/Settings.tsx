import { CheckCircle2, KeyRound, Loader2, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Card } from "../components/ui";
import type { Status } from "../types";

const groups = [
  { title: "AI engine (LLM)", desc: "Powers the executive-recruiter reasoning, talent mapping and candidate assessment. One is enough.", fields: [
    { key: "OPENAI_API_KEY", label: "OpenAI API key", secret: true }, { key: "OPENAI_MODEL", label: "OpenAI model", placeholder: "gpt-4o" },
    { key: "ANTHROPIC_API_KEY", label: "Anthropic API key", secret: true }, { key: "ANTHROPIC_MODEL", label: "Anthropic model", placeholder: "claude-sonnet-4-5" }] },
  { title: "Web search (LinkedIn & open-web X-ray)", desc: "Used to run LinkedIn X-ray and open-web searches automatically. One is enough.", fields: [
    { key: "SERPER_API_KEY", label: "Serper.dev API key", secret: true }, { key: "TAVILY_API_KEY", label: "Tavily API key", secret: true },
    { key: "BRAVE_API_KEY", label: "Brave Search API key", secret: true }, { key: "SERPAPI_API_KEY", label: "SerpAPI key", secret: true }] },
  { title: "GitHub", desc: "Optional personal access token (no scopes needed) for higher API rate limits.", fields: [{ key: "GITHUB_TOKEN", label: "GitHub token", secret: true }] },
];

export default function Settings({ onSaved }: { onSaved: (s: Status) => void }) {
  const [current, setCurrent] = useState<Record<string, string | boolean>>({});
  const [vals, setVals] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState(false);
  useEffect(() => { api.settings().then(setCurrent); }, []);

  async function save() {
    setBusy(true);
    const s = await api.saveSettings(Object.fromEntries(Object.entries(vals).filter(([, v]) => v.trim())));
    onSaved(s); setCurrent(await api.settings()); setVals({}); setBusy(false); setOk(true); setTimeout(() => setOk(false), 2000);
  }

  return (
    <div className="p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      <div><h1 className="text-2xl font-semibold text-slate-900">Integrations</h1><p className="text-sm text-slate-500 mt-1">Keys are stored locally on the server (data/settings.json) and never sent to the browser.</p></div>
      {groups.map((g) => (
        <Card key={g.title} title={g.title} icon={<KeyRound className="h-4 w-4 text-brand-600" />}>
          <p className="text-sm text-slate-500 mb-4">{g.desc}</p>
          <div className="grid sm:grid-cols-2 gap-4">{g.fields.map((f) => (
            <div key={f.key}>
              <div className="label flex items-center justify-between">{f.label}{f.secret && current[f.key] === true && <Badge tone="green"><CheckCircle2 className="h-3 w-3" />Connected</Badge>}</div>
              <input className="input" type={f.secret ? "password" : "text"} placeholder={f.secret ? (current[f.key] ? "•••••••• (saved)" : "Paste key") : (String(current[f.key] || "") || f.placeholder)} value={vals[f.key] ?? ""} onChange={(e) => setVals({ ...vals, [f.key]: e.target.value })} />
            </div>
          ))}</div>
        </Card>
      ))}
      <div className="flex justify-end"><button className="btn-primary" disabled={busy || !Object.values(vals).some((v) => v.trim())} onClick={save}>{busy ? <Loader2 className="h-4 w-4 animate-spin" /> : ok ? <CheckCircle2 className="h-4 w-4" /> : <Save className="h-4 w-4" />}{ok ? "Saved" : "Save"}</button></div>
    </div>
  );
}
