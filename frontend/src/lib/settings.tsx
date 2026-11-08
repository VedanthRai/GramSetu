import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import type { LangCode } from "./api";

export interface Settings {
  language: LangCode;
  voice: string | null;
  autoplay: boolean;
  voiceOnly: boolean;
  retainHistory: boolean;
}

const DEFAULTS: Settings = { language: "hi-IN", voice: null, autoplay: true, voiceOnly: false, retainHistory: false };
const KEY = "gramsetu.settings.v1";

function load(): Settings {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...DEFAULTS, ...(JSON.parse(raw) as Partial<Settings>) } : DEFAULTS;
  } catch {
    return DEFAULTS;
  }
}

interface Ctx { settings: Settings; update: (p: Partial<Settings>) => void }
const SettingsContext = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(load);
  const update = useCallback((p: Partial<Settings>) => {
    setSettings((prev) => {
      const next = { ...prev, ...p };
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* storage unavailable: settings still apply for this visit */
      }
      return next;
    });
  }, []);
  const value = useMemo(() => ({ settings, update }), [settings, update]);
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Ctx {
  const c = useContext(SettingsContext);
  if (!c) throw new Error("SettingsProvider missing");
  return c;
}
