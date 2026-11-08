import { Link } from "react-router-dom";
import { ClipboardCheck, Mic, MonitorPlay, ShieldCheck } from "lucide-react";
import { Badge } from "../components/Layout";
import { useLanguages } from "./Workspace";

export default function Landing() {
  const { langs } = useLanguages();
  return (
    <div>
      <section className="mx-auto grid max-w-[1200px] gap-10 px-4 pb-10 pt-12 lg:grid-cols-[1.1fr_0.9fr] lg:pt-20">
        <div>
          <Badge tone="saffron">Voice-first · Gnani Prisma + Timbre</Badge>
          <h1 className="mt-5 font-display text-4xl font-bold leading-[1.08] sm:text-6xl">
            Government and healthcare services. <span className="text-saffron-dark">In your language.</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg text-ink-soft">
            Speak naturally. GramSetu helps you understand requirements and complete supported online tasks with you.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/app" className="btn-primary px-6 py-4 text-lg"><Mic className="h-5 w-5" aria-hidden />Start speaking</Link>
            <Link to="/judge" className="btn-ghost px-6 py-4 text-lg">Explore demo</Link>
          </div>
          <p className="mt-6 text-sm text-ink-soft">
            Verified languages today: {langs.length ? langs.map((l) => `${l.native} (${l.english})`).join(" · ") : "loading…"}
          </p>
        </div>
        <div className="rounded-2xl border border-line bg-card p-5 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">A real turn, as it happens in the app</p>
          <div className="mt-4 space-y-3 text-[15px]">
            <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-ink px-4 py-3 text-white" lang="kn-IN">ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು.</div>
            <div className="max-w-[90%] rounded-2xl rounded-bl-sm border border-line bg-white px-4 py-3" lang="kn-IN">ಯಾವ ವಿಭಾಗ? ಸಾಮಾನ್ಯ ವೈದ್ಯಕೀಯ, ಮಕ್ಕಳ ವೈದ್ಯರು, ಮೂಳೆ, ಅಥವಾ ಕಿವಿ-ಮೂಗು-ಗಂಟಲು.</div>
            <div className="rounded-lg border-2 border-verified bg-verified-light px-4 py-3 text-sm">
              <b className="text-verified">Verified</b> — booking found in the demo clinic's records before GramSetu said “done”.
            </div>
          </div>
          <p className="mt-4 text-xs text-ink-faint">Transcript text above is the sample request used in our end-to-end test. The live workspace shows your own speech.</p>
        </div>
      </section>

      <section className="mx-auto max-w-[1200px] px-4 py-8">
        <ol className="grid gap-4 md:grid-cols-3">
          {[
            [Mic, "Speak in your language.", "Gnani Prisma writes down what you said. You can read and correct it before anything happens."],
            [ClipboardCheck, "Review your task.", "GramSetu asks only for what is missing, speaks it back with Gnani Timbre, and waits for your approval."],
            [MonitorPlay, "Watch GramSetu complete supported actions.", "A real browser fills the demo portal step by step. Codes and the final submit always stay with you."],
          ].map(([Icon, title, body], i) => {
            const I = Icon as typeof Mic;
            return (
              <li key={i} className="rounded-xl border border-line bg-card p-5">
                <span className="grid h-10 w-10 place-items-center rounded-full bg-saffron-light text-saffron-dark"><I className="h-5 w-5" aria-hidden /></span>
                <p className="mt-3 text-lg font-semibold">{i + 1}. {title as string}</p>
                <p className="mt-1 text-ink-soft">{body as string}</p>
              </li>
            );
          })}
        </ol>
      </section>

      <section className="mx-auto max-w-[1200px] px-4 py-6">
        <div className="flex gap-3 rounded-xl border border-line bg-white p-5">
          <ShieldCheck className="h-6 w-6 shrink-0 text-ink" aria-hidden />
          <div className="text-sm">
            <p className="font-semibold">Demo workflows — honest by design</p>
            <p className="mt-1 text-ink-soft">
              The two supported tasks (a PM-KISAN-style scheme form and a clinic booking) run on locally hosted demo portals clearly marked
              “not an official government website”. Scheme guidance quotes the official PM-KISAN site with a retrieval date, and GramSetu
              never declares anyone eligible. Nothing is sent to real government or hospital systems.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
