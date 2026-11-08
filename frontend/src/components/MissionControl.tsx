import { useEffect, useMemo, useState } from "react";
import { CircleDot, Globe2, HelpCircle, KeyRound, Lock, OctagonX, Smartphone } from "lucide-react";
import { api, type LangCode, type TimelineEvent } from "../lib/api";
import { ui } from "../lib/ui";
import type { SessionApi } from "../lib/useSession";
import { Badge, Card } from "./Layout";

const ACTIVE = new Set(["EXECUTING", "AWAITING_USER_ACTION", "PAUSED_FOR_CONFIRMATION", "VERIFYING"]);
const ACTOR_TONE: Record<string, string> = {
  prisma: "bg-saffron", timbre: "bg-saffron", reasoning: "bg-ink", gramsetu: "bg-ink-soft", user: "bg-ink",
  policy: "bg-[#6b4fa1]", browser: "bg-[#2c6e8f]", verifier: "bg-verified", guard: "bg-danger",
};

export function MissionControl({ s, language, compact = false }: { s: SessionApi; language: LangCode; compact?: boolean }) {
  const session = s.session;
  const shots = session?.screenshots ?? [];
  const [picked, setPicked] = useState<string | null>(null);
  const latest = shots[shots.length - 1] ?? null;
  const shown = picked && shots.includes(picked) ? picked : latest;
  const timeline = useMemo(() => s.events.filter((e) => e.kind !== "message" && e.kind !== "screenshot"), [s.events]);
  const lastShotEvent = [...s.events].reverse().find((e) => e.kind === "screenshot");
  const running = session?.plan.find((p) => p.status === "running") ?? session?.plan.find((p) => p.status === "proposed");
  const active = session ? ACTIVE.has(session.state) : false;

  useEffect(() => setPicked(null), [latest]);

  return (
    <Card id="mission-control" title="Browser Mission Control" action={<Badge tone="neutral">live screenshots</Badge>} className="flex min-h-0 flex-col">
      <div className="space-y-4 px-4 py-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1 rounded bg-line/60 px-2 py-1 font-mono"><Lock className="h-3 w-3" aria-hidden />{location.host}</span>
          <span className="inline-flex items-center gap-1 rounded bg-line/60 px-2 py-1 font-mono"><Globe2 className="h-3 w-3" aria-hidden />{String(lastShotEvent?.data.route ?? "—")}</span>
          <Badge tone="neutral">origin allow-list: this server only</Badge>
          {active && (
            <button className="ml-auto inline-flex items-center gap-1 rounded-md bg-danger px-3 py-1.5 text-sm font-semibold text-white" onClick={() => void s.cancel()}>
              <OctagonX className="h-4 w-4" aria-hidden />Interrupt
            </button>
          )}
        </div>

        <div className="overflow-hidden rounded-lg border border-line bg-[#e9e4d8]">
          {shown && session ? (
            <img src={`/api/sessions/${session.id}/screenshot?name=${shown}`} alt={`Portal screenshot ${shown}: ${lastShotEvent?.description ?? ""}`} className="block w-full" />
          ) : (
            <div className="grid aspect-[11/8] place-items-center p-6 text-center text-sm text-ink-soft">
              The demo portal appears here once you approve a task. Every step is shown as a screenshot; sensitive fields are masked.
            </div>
          )}
        </div>
        {shots.length > 1 && !compact && (
          <div className="flex gap-1 overflow-x-auto pb-1" aria-label="Screenshot history">
            {shots.map((n) => (
              <button key={n} onClick={() => setPicked(n)} aria-label={`Show screenshot ${n}`} aria-pressed={n === shown}
                className={`h-12 w-16 shrink-0 overflow-hidden rounded border ${n === shown ? "border-saffron ring-2 ring-saffron" : "border-line"}`}>
                <img src={`/api/sessions/${session!.id}/screenshot?name=${n}`} alt="" className="h-full w-full object-cover object-top" />
              </button>
            ))}
          </div>
        )}

        {session?.state === "AWAITING_USER_ACTION" && <SecureCodePanel s={s} language={language} />}

        {running && active && (
          <div className="rounded-md border border-line bg-white p-3 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">Current action</p>
            <p className="mt-1 font-mono text-xs">{running.action_type} → {running.target || "—"}</p>
            <p className="mt-1">{running.explanation}</p>
          </div>
        )}

        {session && session.plan.length > 0 && !compact && (
          <details className="rounded-md border border-line bg-white" open={active}>
            <summary className="cursor-pointer px-3 py-2 text-sm font-semibold">Plan ({session.plan.filter((p) => p.status === "succeeded").length}/{session.plan.length} done) · why each step</summary>
            <ol className="space-y-1 px-3 pb-3 text-sm">
              {session.plan.map((p) => (
                <li key={p.action_id} className="flex items-start gap-2">
                  <StepDot status={p.status} />
                  <span className="min-w-0">
                    <span className="font-mono text-[11px] text-ink-faint">{p.action_type}{p.requires_authorization ? " · needs your approval" : ""}</span>
                    <span className="block">{p.explanation}</span>
                    {p.error_message && <span className="block text-xs text-danger">{p.error_message}</span>}
                  </span>
                </li>
              ))}
            </ol>
          </details>
        )}

        <Timeline events={timeline} />
      </div>
    </Card>
  );
}

function StepDot({ status }: { status: string }) {
  const c = status === "succeeded" ? "text-verified" : status === "running" ? "text-saffron" : status === "failed" || status === "rejected" ? "text-danger" : "text-line";
  return <CircleDot className={`mt-1 h-3.5 w-3.5 shrink-0 ${c}`} aria-label={status} />;
}

export function Timeline({ events, max = 60 }: { events: TimelineEvent[]; max?: number }) {
  if (!events.length) return <p className="text-sm text-ink-faint">The audit timeline fills with real events as they happen.</p>;
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">Audit timeline</p>
      <ol className="max-h-72 space-y-1.5 overflow-y-auto pr-1 text-sm" aria-live="polite">
        {events.slice(-max).map((e) => (
          <li key={e.id} className="flex gap-2">
            <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${ACTOR_TONE[e.actor] ?? "bg-ink-faint"}`} aria-hidden />
            <span className="font-mono text-[11px] text-ink-faint">{e.at.slice(11, 19)}</span>
            <span className="min-w-0">{e.description}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function SecureCodePanel({ s, language }: { s: SessionApi; language: LangCode }) {
  const [code, setCode] = useState("");
  const [sms, setSms] = useState<{ to: string; code: string } | null>(null);
  const sid = s.session?.id;
  useEffect(() => {
    if (!sid) return;
    let alive = true;
    const poll = () => api.demoSms(sid).then((r) => alive && setSms(r.message)).catch(() => undefined);
    void poll();
    const t = window.setInterval(poll, 1500);
    return () => { alive = false; window.clearInterval(t); };
  }, [sid]);
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <form className="rounded-lg border-2 border-saffron bg-saffron-light/50 p-3" autoComplete="off"
        onSubmit={(e) => { e.preventDefault(); const v = code; setCode(""); void s.secureInput(v); }}>
        <label htmlFor="otp-box" className="flex items-center gap-1 text-sm font-semibold"><KeyRound className="h-4 w-4" aria-hidden />{ui("secureCode", language)}</label>
        <input id="otp-box" type="password" inputMode="numeric" autoComplete="one-time-code" maxLength={8} value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} className="mt-2 w-full rounded-md border border-line bg-white px-3 py-2 font-mono text-xl tracking-[0.4em]" />
        <p className="mt-1 text-xs text-ink-soft">Goes straight into the portal field. Not shown, logged, stored, spoken or sent to any AI model.</p>
        <div className="mt-2 flex flex-wrap gap-2">
          <button className="btn-primary" disabled={code.length < 4}>{ui("submitCode", language)}</button>
          <button type="button" className="btn-ghost text-xs" onClick={() => void s.resume()}>{ui("doneInBrowser", language)}</button>
        </div>
      </form>
      <div className="rounded-[1.4rem] border-4 border-ink bg-white p-3" aria-label="Simulated phone">
        <p className="flex items-center gap-1 text-xs font-semibold text-ink-soft"><Smartphone className="h-4 w-4" aria-hidden />Your phone (simulated for the demo)</p>
        {sms ? (
          <div className="mt-2 rounded-lg bg-line/50 p-2 text-sm">
            <p className="text-xs text-ink-soft">To {sms.to}</p>
            <p>Demo portal code: <span className="font-mono text-lg font-bold">{sms.code}</span></p>
            <p className="text-xs text-danger">Never share this code with anyone.</p>
          </div>
        ) : <p className="mt-2 text-sm text-ink-faint">Waiting for SMS…</p>}
        <p className="mt-2 flex items-start gap-1 text-[11px] text-ink-faint"><HelpCircle className="h-3 w-3 shrink-0" aria-hidden />GramSetu's agent never reads this; only you see it, like your own phone.</p>
      </div>
    </div>
  );
}
