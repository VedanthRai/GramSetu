import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { api, type EvalResults, type Language, type LangCode, type PortalInfo, type SourcesDoc, type TimelineEvent } from "../lib/api";
import { Badge, Card, PageHeader } from "../components/Layout";
import { Timeline } from "../components/MissionControl";
import { ProviderStrip, useProviders } from "../components/StatusBits";
import { useSettings } from "../lib/settings";
import { INTENT_LABEL } from "../lib/ui";

export function History() {
  const [rows, setRows] = useState<Awaited<ReturnType<typeof api.history>>["tasks"] | null>(null);
  useEffect(() => { api.history().then((r) => setRows(r.tasks)).catch(() => setRows([])); }, []);
  return (
    <div>
      <PageHeader title="Task history" sub="Tasks on this server. Transcripts are not stored unless you opt in under Settings. Open a task to replay its sanitised timeline." />
      <div className="mx-auto max-w-[1100px] px-4">
        {rows === null ? <div className="h-32 animate-pulse rounded-xl bg-line/50" /> : rows.length === 0 ? (
          <p className="rounded-xl border border-line bg-card p-6 text-ink-soft">No tasks yet. <Link className="underline" to="/app">Start speaking</Link>.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-line bg-card">
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-ink-faint"><tr><th className="p-3">When</th><th className="p-3">Task</th><th className="p-3">Lang</th><th className="p-3">Status</th><th className="p-3">Demo reference</th><th className="p-3" /></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-line">
                    <td className="p-3 font-mono text-xs">{r.created_at.replace("T", " ").slice(0, 19)}</td>
                    <td className="p-3">{INTENT_LABEL[r.intent] ?? r.intent}</td>
                    <td className="p-3">{r.language}</td>
                    <td className="p-3"><Badge tone={r.status === "completed" ? "verified" : r.status === "failed" ? "danger" : "neutral"}>{r.status}</Badge></td>
                    <td className="p-3 font-mono">{r.data.reference ?? "—"}</td>
                    <td className="p-3"><Link className="font-semibold underline" to={`/replay/${r.session_id}`}>Replay</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export function Replay() {
  const { id = "" } = useParams();
  const [events, setEvents] = useState<TimelineEvent[] | null>(null);
  useEffect(() => { api.events(id).then((r) => setEvents(r.events)).catch(() => setEvents([])); }, [id]);
  const shots = (events ?? []).filter((e) => e.kind === "screenshot");
  const [i, setI] = useState(0);
  return (
    <div>
      <PageHeader title="Demo replay" sub="A sanitised replay of real recorded events, approvals and screenshots for one session. Nothing here is re-enacted." />
      <div className="mx-auto grid max-w-[1100px] gap-4 px-4 lg:grid-cols-[1.2fr_1fr]">
        <Card title={`Screenshots (${shots.length})`}>
          <div className="p-4">
            {shots.length ? (
              <>
                <img className="w-full rounded border border-line" src={`/api/sessions/${id}/screenshot?name=${String(shots[i]?.data.screenshot)}`} alt={shots[i]?.description} />
                <div className="mt-3 flex items-center gap-3">
                  <button className="btn-ghost" disabled={i === 0} onClick={() => setI(i - 1)}>Previous</button>
                  <span className="text-sm">{i + 1} / {shots.length} — {shots[i]?.description}</span>
                  <button className="btn-ghost ml-auto" disabled={i >= shots.length - 1} onClick={() => setI(i + 1)}>Next</button>
                </div>
              </>
            ) : <p className="text-ink-soft">No screenshots for this session (or it was deleted).</p>}
          </div>
        </Card>
        <Card title="Timeline"><div className="p-4"><Timeline events={(events ?? []).filter((e) => e.kind !== "message" && e.kind !== "screenshot")} max={500} /></div></Card>
      </div>
    </div>
  );
}

export function Sources() {
  const [doc, setDoc] = useState<SourcesDoc | null>(null);
  const [portals, setPortals] = useState<PortalInfo[]>([]);
  useEffect(() => {
    api.sources().then(setDoc).catch(() => undefined);
    api.portals().then((r) => setPortals(r.portals)).catch(() => undefined);
  }, []);
  return (
    <div>
      <PageHeader title="Sources and verification" sub="Every spoken scheme fact comes from this registry. Statements are copied from the official page; anything unverified is labelled as such." />
      <div className="mx-auto max-w-[1100px] space-y-4 px-4">
        {doc?.schemes.map((sc) => (
          <Card key={sc.scheme_id} title={sc.official_name} action={<Badge tone={sc.status === "verified" ? "verified" : "neutral"}>{sc.status}</Badge>}>
            <div className="space-y-3 p-4 text-sm">
              <p><a className="inline-flex items-center gap-1 font-semibold underline" href={sc.official_source_url} target="_blank" rel="noreferrer noopener">{sc.official_source_url}<ExternalLink className="h-3 w-3" aria-hidden /></a> · {sc.source_title}</p>
              <p className="text-ink-soft">{sc.jurisdiction} · retrieved {sc.retrieved_at.slice(0, 10)} · last verified {sc.last_verified_at.slice(0, 10)}</p>
              <ul className="space-y-2">
                {sc.statements.map((st) => (
                  <li key={st.id} className="rounded-md border border-line bg-white p-3"><Badge tone="ink">{st.kind}</Badge> <span className="ml-1">“{st.text}”</span></li>
                ))}
              </ul>
              <p className="rounded-md bg-saffron-light/60 p-3"><b>Required documents: {sc.required_documents.status}.</b> {sc.required_documents.note}</p>
              <p className="text-ink-soft">{sc.verification_notes}</p>
            </div>
          </Card>
        ))}
        {doc && <p className="text-xs text-ink-faint">{doc.retrieval_note}</p>}
        <Card title="Portal adapter registry">
          <div className="grid gap-3 p-4 md:grid-cols-2">
            {portals.map((p) => (
              <div key={p.portal_id} className="rounded-md border border-line bg-white p-3 text-sm">
                <p className="font-semibold">{p.name} <Badge tone={p.enabled ? "verified" : "neutral"}>{p.enabled ? "enabled" : "disabled"}</Badge></p>
                <p className="mt-1 font-mono text-xs">{p.route_prefix}</p>
                <p className="mt-1 text-ink-soft">Consequential (need approval): {p.consequential_targets.join(", ") || "—"}</p>
                <p className="text-ink-soft">User-only fields: {p.secret_targets.join(", ") || "—"}</p>
                <p className="text-ink-soft">Completion evidence: {p.completion_evidence}</p>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

export function Privacy() {
  return (
    <div>
      <PageHeader title="Privacy and consent" />
      <div className="mx-auto max-w-[900px] space-y-3 px-4 text-[15px] leading-relaxed">
        {[
          ["Microphone", "GramSetu listens only after you press the button and only while it is red (maximum 30 seconds). There is no background listening."],
          ["Audio", "Your recording is sent to Gnani Prisma to be written down. GramSetu does not keep raw audio."],
          ["Transcripts", "Not written to the database unless you turn on “Keep my history” in Settings. Ordinary server logs never contain full transcripts."],
          ["AI interpretation", "Only the minimum text is sent to the reasoning provider. Phone numbers and long digit sequences are removed first. One-time codes, passwords and ID numbers are never sent."],
          ["One-time codes", "You type them yourself into a secure box that passes them straight to the portal field. They are never shown, spoken, logged, stored or sent to a model. If you try to say one, GramSetu warns you instead."],
          ["Approvals", "Starting a task, accepting a declaration, submitting, booking and cancelling all need your explicit approval."],
          ["Deletion", "“Delete session” in the workspace removes that session's events, approvals, audit records and screenshots."],
          ["Demo data", "Portals, doctors, slots and records are synthetic. Use made-up names when you try the demo."],
        ].map(([h, b]) => (
          <div key={h} className="rounded-lg border border-line bg-card p-4"><p className="font-semibold">{h}</p><p className="text-ink-soft">{b}</p></div>
        ))}
      </div>
    </div>
  );
}

export function SettingsPage() {
  const { settings, update } = useSettings();
  const [langs, setLangs] = useState<Language[]>([]);
  useEffect(() => { api.languages().then((r) => setLangs(r.verified)).catch(() => undefined); }, []);
  const current = langs.find((l) => l.code === settings.language);
  return (
    <div>
      <PageHeader title="Settings" sub="Saved in this browser only." />
      <div className="mx-auto max-w-[700px] space-y-4 px-4">
        <Card><div className="space-y-5 p-5">
          <label className="block text-sm font-semibold">Language
            <select className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-base" value={settings.language}
              onChange={(e) => update({ language: e.target.value as LangCode, voice: null })}>
              {langs.map((l) => <option key={l.code} value={l.code}>{l.native} · {l.english}</option>)}
            </select>
          </label>
          <label className="block text-sm font-semibold">Voice (Gnani Timbre)
            <select className="mt-1 block w-full rounded-md border border-line bg-white px-3 py-2 text-base" value={settings.voice ?? ""}
              onChange={(e) => update({ voice: e.target.value || null })}>
              <option value="">Default ({current?.default_voice ?? "—"})</option>
              {current?.voices.map((v) => <option key={v} value={v}>{v} (verified)</option>)}
            </select>
            <span className="mt-1 block text-xs font-normal text-ink-faint">Only voices verified with this API key are listed.</span>
          </label>
          {([
            ["autoplay", "Speak every assistant message automatically"],
            ["voiceOnly", "Voice-only / low-literacy mode: one large Speak button, bigger text and choices, everything spoken"],
            ["retainHistory", "Keep my history (store transcripts for new sessions on this server)"],
          ] as const).map(([k, label]) => (
            <label key={k} className="flex items-start gap-3 text-sm">
              <input type="checkbox" className="mt-1 h-5 w-5 accent-[#1b2a41]" checked={settings[k]} onChange={(e) => update({ [k]: e.target.checked })} />
              <span>{label}</span>
            </label>
          ))}
        </div></Card>
      </div>
    </div>
  );
}

export function Status() {
  const { providers, usage } = useProviders(5000);
  return (
    <div>
      <PageHeader title="Providers and usage" sub="Each provider is reported separately. A failing provider is shown as failing — the app never pretends to be fully operational." />
      <div className="mx-auto max-w-[1100px] space-y-4 px-4">
        <ProviderStrip providers={providers} usage={usage} />
        <div className="grid gap-4 md:grid-cols-3">
          {providers && ([["Speech to text", providers.stt], ["Text to speech", providers.tts], ["Reasoning", providers.reasoning]] as const).map(([t, h]) => (
            <Card key={t} title={t}>
              <dl className="space-y-1 p-4 text-sm">
                <div className="flex justify-between"><dt className="text-ink-soft">Provider</dt><dd className="font-semibold">{h.label ?? h.name}</dd></div>
                <div className="flex justify-between"><dt className="text-ink-soft">Model</dt><dd>{h.model ?? "—"}</dd></div>
                {h.mode && <div className="flex justify-between"><dt className="text-ink-soft">Mode</dt><dd>{h.mode}</dd></div>}
                <div className="flex justify-between"><dt className="text-ink-soft">Configured</dt><dd>{h.configured ? "yes" : "no"}</dd></div>
                <div className="flex justify-between"><dt className="text-ink-soft">Reachable</dt><dd>{h.reachable === null ? "not called yet" : h.reachable ? "yes" : "no"}</dd></div>
                <div className="flex justify-between"><dt className="text-ink-soft">Last latency</dt><dd>{h.last_latency_ms != null ? `${h.last_latency_ms} ms` : "—"}</dd></div>
                <div><dt className="text-ink-soft">Last error</dt><dd className="break-words text-danger">{h.last_error ?? "none"}</dd></div>
              </dl>
            </Card>
          ))}
        </div>
        {usage && (
          <Card title={usage.label}>
            <div className="overflow-x-auto p-4">
              <p className="mb-2 text-sm text-ink-soft">{usage.official_balance_note}</p>
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-ink-faint"><tr><th className="p-2">Day</th><th className="p-2">API</th><th className="p-2">Calls</th><th className="p-2">Audio s</th><th className="p-2">TTS chars</th><th className="p-2">Cache hits</th><th className="p-2">Errors</th></tr></thead>
                <tbody>{usage.rows.map((r) => (
                  <tr key={r.day + r.kind} className="border-t border-line"><td className="p-2">{r.day}</td><td className="p-2">{r.kind.toUpperCase()}</td><td className="p-2">{r.calls}</td><td className="p-2">{r.audio_seconds.toFixed(1)}</td><td className="p-2">{r.chars}</td><td className="p-2">{r.cache_hits}</td><td className="p-2">{r.errors}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}

export function Evaluation() {
  const [r, setR] = useState<EvalResults | null>(null);
  useEffect(() => { api.evalResults().then(setR).catch(() => setR({ status: "pending evaluation" })); }, []);
  if (!r) return <PageHeader title="Evaluation" sub="Loading…" />;
  if (!r.metrics) return <PageHeader title="Evaluation" sub="Pending evaluation — run scripts/run_eval.py to produce results from a real run." />;
  return (
    <div>
      <PageHeader title="Evaluation" sub={`Results of the last real run (${r.run_at}). Reasoning provider: ${r.reasoning_provider}. Dataset: ${r.dataset_size} utterances. Every number shows its denominator.`} />
      <div className="mx-auto max-w-[1100px] space-y-4 px-4">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {r.metrics.map((m) => (
            <div key={m.name} className="rounded-xl border border-line bg-card p-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">{m.name}</p>
              <p className="mt-1 font-mono text-2xl font-bold">{m.value === null ? "pending" : `${m.value}${m.unit ?? ""}`}</p>
              {m.denominator !== undefined && <p className="text-xs text-ink-soft">{m.numerator} / {m.denominator}</p>}
              {m.note && <p className="mt-1 text-xs text-ink-soft">{m.note}</p>}
            </div>
          ))}
        </div>
        {r.stt && (
          <Card title={`Prisma transcription (n=${r.stt.sample_size})`}>
            <div className="overflow-x-auto p-4 text-sm">
              <p className="mb-2 text-ink-soft">{r.stt.note}</p>
              <table className="w-full"><thead className="text-left text-xs uppercase text-ink-faint"><tr><th className="p-2">Id</th><th className="p-2">Lang</th><th className="p-2">Reference</th><th className="p-2">Prisma output</th><th className="p-2">CER</th></tr></thead>
                <tbody>{r.stt.items.map((x) => <tr key={x.id} className="border-t border-line"><td className="p-2 font-mono">{x.id}</td><td className="p-2">{x.lang}</td><td className="p-2">{x.reference}</td><td className="p-2">{x.hypothesis}</td><td className="p-2 font-mono">{x.cer === null ? "script mismatch (excluded)" : x.cer.toFixed(3)}{x.audio === "timbre_noisy" ? " · noisy" : ""}</td></tr>)}</tbody></table>
            </div>
          </Card>
        )}
        {r.items && (
          <Card title="Per-utterance results">
            <div className="overflow-x-auto p-4 text-sm">
              <table className="w-full"><thead className="text-left text-xs uppercase text-ink-faint"><tr><th className="p-2">Id</th><th className="p-2">Lang</th><th className="p-2">Utterance</th><th className="p-2">Expected</th><th className="p-2">Got</th><th className="p-2">Fields</th></tr></thead>
                <tbody>{r.items.map((x) => (
                  <tr key={x.id} className="border-t border-line"><td className="p-2 font-mono">{x.id}</td><td className="p-2">{x.lang}</td><td className="p-2" lang={x.lang}>{x.text}</td><td className="p-2">{x.expected_intent}</td>
                    <td className="p-2"><Badge tone={x.intent_ok ? "verified" : "danger"}>{x.got_intent}</Badge></td><td className="p-2 font-mono">{x.fields_ok}/{x.fields_total}</td></tr>
                ))}</tbody></table>
            </div>
          </Card>
        )}
        {r.pending && r.pending.length > 0 && <p className="text-sm text-ink-soft">Pending evaluation: {r.pending.join("; ")}</p>}
      </div>
    </div>
  );
}
