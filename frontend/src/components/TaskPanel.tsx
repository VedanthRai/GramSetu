import { useState } from "react";
import { CheckCircle2, Download, FileText, Printer, ShieldCheck, TriangleAlert, XCircle } from "lucide-react";
import type { LangCode, SessionSnapshot, SummaryLine } from "../lib/api";
import { synthesizeBlob } from "../audio/player";
import { INTENT_LABEL, STATE_LABEL, ui } from "../lib/ui";
import type { SessionApi } from "../lib/useSession";
import { Badge, Card } from "./Layout";

const STAGES = [
  ["Understand", ["IDLE", "INTERPRETING", "NEEDS_CLARIFICATION"]],
  ["Review", ["PREVIEWING_TASK", "AWAITING_CONSENT"]],
  ["Act", ["EXECUTING", "AWAITING_USER_ACTION", "PAUSED_FOR_CONFIRMATION"]],
  ["Verify", ["VERIFYING", "COMPLETED"]],
] as const;

const SOURCE_BADGE: Record<string, { label: string; tone: "neutral" | "saffron" | "ink" }> = {
  user_spoken: { label: "You said", tone: "neutral" },
  user_corrected: { label: "You corrected", tone: "saffron" },
  derived: { label: "Derived", tone: "ink" },
  system_default: { label: "Default", tone: "ink" },
};

export function TaskPanel({ s, language, voice }: { s: SessionApi; language: LangCode; voice: string | null }) {
  const session = s.session;
  if (!session) return <Card title="Task" className="p-6 text-ink-soft">Starting…</Card>;
  const task = session.task;
  const stageIndex = STAGES.findIndex(([, states]) => (states as readonly string[]).includes(session.state));
  const lastApproval = [...session.messages].reverse().find((m) => m.kind === "approval");

  return (
    <Card id="task-panel" title="Task" action={<Badge tone={session.state === "COMPLETED" ? "verified" : session.state === "FAILED" ? "danger" : "neutral"}>{STATE_LABEL[session.state] ?? session.state}</Badge>}>
      <div className="space-y-5 px-4 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Service</p>
          <p className="mt-1 text-lg font-semibold">{task ? INTENT_LABEL[task.intent] ?? task.intent : "Not chosen yet — just say what you need"}</p>
        </div>

        <ol className="grid grid-cols-4 gap-2" aria-label="Progress">
          {STAGES.map(([name], i) => (
            <li key={name} aria-current={i === stageIndex ? "step" : undefined}
              className={`rounded-md border px-2 py-2 text-center text-xs font-semibold ${i < stageIndex || session.state === "COMPLETED" ? "border-ink bg-ink text-white" : i === stageIndex ? "border-saffron bg-saffron-light text-saffron-dark" : "border-line text-ink-faint"}`}>
              {name}
            </li>
          ))}
        </ol>

        {task && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">What GramSetu knows</p>
            <FieldTable lines={session.summary} />
            {task.missing_fields.length > 0 && (
              <p className="mt-3 text-sm text-ink-soft">
                Still needed: {task.missing_fields.map((f) => f.replace(/_/g, " ")).join(", ")}
              </p>
            )}
          </div>
        )}

        {session.state === "PREVIEWING_TASK" && (
          <ActionBox tone="saffron" title="Check the summary">
            <p className="text-sm">If everything is right, confirm it. To change something, just say it (for example “no, make it Friday”).</p>
            <button className="btn-primary mt-3" onClick={() => void s.review()}><CheckCircle2 className="h-4 w-4" aria-hidden />{ui("looksRight", language)}</button>
          </ActionBox>
        )}

        {session.state === "AWAITING_CONSENT" && task && (
          <ActionBox tone="saffron" title="Your approval is needed to start">
            <ul className="list-disc space-y-1 pl-5 text-sm">
              <li>Portal: {task.portal_id === "demo_scheme" ? "GramSetu demo scheme portal (local, not official)" : "GramSetu demo clinic portal (local, not official)"}</li>
              <li>GramSetu will open the portal in an isolated browser and enter the details above.</li>
              <li>It will stop for any one-time code and ask you again before the final submit.</li>
            </ul>
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-primary" onClick={() => void s.approve("start")}><ShieldCheck className="h-4 w-4" aria-hidden />{ui("approveStart", language)}</button>
              <button className="btn-ghost" onClick={() => void s.cancel()}>{ui("cancel", language)}</button>
            </div>
          </ActionBox>
        )}

        {session.state === "PAUSED_FOR_CONFIRMATION" && (
          <ActionBox tone="saffron" title="Final approval">
            <p className="text-sm font-medium" lang={language}>{lastApproval?.text}</p>
            <dl className="mt-2 text-sm">
              <div className="flex gap-2"><dt className="text-ink-soft">Portal:</dt><dd>{lastApproval?.portal}</dd></div>
              <div className="flex gap-2"><dt className="text-ink-soft">Consequence:</dt><dd>{lastApproval?.consequence}</dd></div>
            </dl>
            {lastApproval?.summary && <div className="mt-2"><FieldTable lines={lastApproval.summary} /></div>}
            <div className="mt-3 flex flex-wrap gap-2">
              <button className="btn-primary" onClick={() => void s.approve("final")}><ShieldCheck className="h-4 w-4" aria-hidden />{ui("approveFinal", language)}</button>
              <button className="btn-ghost" onClick={() => void s.cancel()}>{ui("cancel", language)}</button>
            </div>
          </ActionBox>
        )}

        {session.state === "COMPLETED" && session.result && (
          <div className="rounded-lg border-2 border-verified bg-verified-light p-4" data-testid="verified-receipt">
            <p className="flex items-center gap-2 font-semibold text-verified"><CheckCircle2 className="h-5 w-5" aria-hidden />Verified from the portal's stored record</p>
            <p className="mt-1 text-sm">{session.result.description}</p>
            {session.result.reference && <p className="mt-2 font-mono text-lg font-bold">Demo reference: {session.result.reference}</p>}
          </div>
        )}
        {session.state === "FAILED" && (
          <div className="rounded-lg border border-danger bg-danger-light p-4 text-sm">
            <p className="flex items-center gap-2 font-semibold text-danger"><XCircle className="h-5 w-5" aria-hidden />Not completed</p>
            <p className="mt-1">GramSetu could not confirm the result, so nothing is marked done. You can start again; anything already stored is detected and not repeated.</p>
          </div>
        )}
        {session.summary_card && <SummaryCardView card={session.summary_card} language={language} voice={voice} />}

        {task?.intent === "clinic_appointment" && (
          <p className="flex gap-2 rounded-md bg-line/50 p-3 text-xs text-ink-soft">
            <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
            GramSetu is an AI assistant. It books appointments only; it does not diagnose or suggest treatment. In an emergency call 112.
          </p>
        )}
      </div>
    </Card>
  );
}

function ActionBox({ title, children, tone }: { title: string; children: React.ReactNode; tone: "saffron" }) {
  return (
    <div className={`rounded-lg border-2 p-4 ${tone === "saffron" ? "border-saffron bg-saffron-light/50" : ""}`} role="region" aria-label={title}>
      <p className="mb-2 font-semibold">{title}</p>
      {children}
    </div>
  );
}

export function FieldTable({ lines }: { lines: SummaryLine[] }) {
  if (!lines.length) return <p className="text-sm text-ink-faint">Nothing yet.</p>;
  return (
    <table className="w-full text-sm">
      <tbody>
        {lines.map((l) => (
          <tr key={l.field} className="border-b border-line last:border-0">
            <th scope="row" className="py-2 pr-3 text-left font-normal text-ink-soft">{l.label}</th>
            <td className="py-2 font-semibold">{l.value}</td>
            <td className="py-2 text-right">{SOURCE_BADGE[l.source_type] && <Badge tone={SOURCE_BADGE[l.source_type].tone}>{SOURCE_BADGE[l.source_type].label}</Badge>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SummaryCardView({ card, language, voice }: { card: NonNullable<SessionSnapshot["summary_card"]>; language: LangCode; voice: string | null }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const download = async () => {
    setBusy(true);
    setErr(null);
    try {
      const blob = await synthesizeBlob(card.message, language, voice ?? undefined);
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `gramsetu-${card.reference ?? "summary"}.wav`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      setErr("Audio could not be generated right now.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="summary-card rounded-lg border border-line bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-danger"><FileText className="h-4 w-4" aria-hidden />{card.demo_notice}</p>
          <p className="mt-1 font-semibold">{card.title}</p>
        </div>
        {card.reference && <span className="font-mono text-sm font-bold">{card.reference}</span>}
      </div>
      <p className="mt-2 text-sm" lang={language}>{card.message}</p>
      <div className="mt-2"><FieldTable lines={card.lines} /></div>
      <p className="mt-2 text-xs text-ink-faint">Created {new Date(card.created_at).toLocaleString()}</p>
      <div className="mt-3 flex flex-wrap gap-2 print:hidden">
        <button className="btn-ghost" onClick={() => window.print()}><Printer className="h-4 w-4" aria-hidden />Print</button>
        <button className="btn-ghost" onClick={() => void download()} disabled={busy}><Download className="h-4 w-4" aria-hidden />{busy ? "Preparing…" : "Download audio (Timbre)"}</button>
      </div>
      {err && <p role="alert" className="mt-2 text-xs text-danger">{err}</p>}
    </div>
  );
}
