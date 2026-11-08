import { useEffect, useState } from "react";
import { api, type AudioFixture } from "../lib/api";
import { Badge, PageHeader } from "../components/Layout";
import Workspace, { type Scenario, useLanguages } from "./Workspace";

const BASE: Omit<Scenario, "fixture">[] = [
  { id: "hi-scheme", title: "Hindi · scheme application", language: "hi-IN", prompt: "मैं किसान हूँ। मेरे पास दो एकड़ जमीन है। मुझे बताइए कि इस योजना के लिए क्या जानकारी चाहिए और डेमो फॉर्म भरने में मदद कीजिए।" },
  { id: "kn-clinic", title: "Kannada · doctor's appointment", language: "kn-IN", prompt: "ನನಗೆ ನಾಳೆ ಬೆಳಿಗ್ಗೆ ವೈದ್ಯರ ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್ ಬೇಕು. ಕನ್ನಡದಲ್ಲಿ ಸಹಾಯ ಮಾಡಿ." },
  { id: "ta-clinic", title: "Tamil · doctor's appointment", language: "ta-IN", prompt: "எனக்கு நாளை காலை சென்னையில் பொது மருத்துவர் சந்திப்பு வேண்டும்." },
  { id: "hi-correction", title: "Hindi · spoken correction", language: "hi-IN", prompt: "कल सुबह लखनऊ में सामान्य डॉक्टर चाहिए … (then) नहीं, शुक्रवार कर दो" },
];

export default function Judge() {
  const { langs } = useLanguages();
  const [fixtures, setFixtures] = useState<AudioFixture[]>([]);
  const [active, setActive] = useState<Scenario | null>(null);
  useEffect(() => { api.fixtures().then((r) => setFixtures(r.fixtures)).catch(() => undefined); }, []);
  const verified = new Set(langs.map((l) => l.code));
  const scenarios: Scenario[] = BASE.map((b) => {
    const f = fixtures.find((x) => x.language === b.language && b.id !== "hi-correction");
    return { ...b, fixture: f ? { name: f.name, label: f.label } : null };
  });

  if (active) {
    return (
      <div>
        <div className="mx-auto flex max-w-[1500px] items-center gap-3 px-4 pt-4">
          <button className="btn-ghost" onClick={() => setActive(null)}>← All scenarios</button>
          <Badge tone="saffron">Judge mode</Badge>
          <span className="text-sm text-ink-soft">Live Gnani calls. Fixtures are labelled and still go through live Prisma — never a canned transcript.</span>
        </div>
        <Workspace scenario={active} />
      </div>
    );
  }
  return (
    <div>
      <PageHeader title="Judge mode" sub="Four curated scenarios. Speak live, or use a clearly labelled audio fixture that is sent to Gnani Prisma for real. Provider status and measured latency stay visible throughout." />
      <div className="mx-auto grid max-w-[1100px] gap-4 px-4 md:grid-cols-2">
        {scenarios.map((sc) => {
          const ok = verified.has(sc.language);
          return (
            <div key={sc.id} className="flex flex-col rounded-xl border border-line bg-card p-5">
              <p className="text-lg font-semibold">{sc.title}</p>
              <p lang={sc.language} className="mt-2 flex-1 text-ink-soft">“{sc.prompt}”</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs">
                <Badge tone={ok ? "verified" : "neutral"}>{ok ? "Language verified with Prisma + Timbre" : "Language not yet verified — run the smoke test"}</Badge>
                {sc.fixture && <Badge tone="saffron">Fixture: {sc.fixture.label}</Badge>}
                <Badge tone="neutral">Sample phrase pending native review</Badge>
              </div>
              <button className="btn-primary mt-4 self-start" disabled={!ok} onClick={() => setActive(sc)}>Open scenario</button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
