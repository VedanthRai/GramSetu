import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { PageHeader } from "../components/Layout";
import Workspace, { type Scenario } from "./Workspace";

const SCENARIO: Scenario = {
  id: "codemix",
  title: "Speak your way — mix Hindi and English",
  language: "hi-IN",
  prompt: "Kal morning appointment chahiye, Bengaluru clinic, general doctor",
};

export default function SpeakYourWay() {
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => { api.languages().then((r) => setNote(`${r.code_mixed.status}: ${r.code_mixed.note}`)).catch(() => undefined); }, []);
  return (
    <div>
      <PageHeader title="Speak your way" sub="People switch languages mid-sentence. Try mixing Hindi and English and watch the transcript, the interpretation and the result." />
      <div className="mx-auto max-w-[1100px] px-4">
        <p className="rounded-md border border-saffron bg-saffron-light/50 p-3 text-sm">
          <b>Honest status:</b> a dedicated code-mixed recognition mode is {note ?? "loading…"} This screen uses the verified Hindi (hi-IN) model,
          which also handles common English words; results on heavily mixed speech may vary.
        </p>
      </div>
      <Workspace scenario={SCENARIO} />
    </div>
  );
}
