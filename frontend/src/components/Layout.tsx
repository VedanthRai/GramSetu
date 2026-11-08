import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Link } from "react-router-dom";
import { Wifi, WifiOff } from "lucide-react";

const NAV = [
  ["/app", "Workspace"],
  ["/judge", "Judge mode"],
  ["/speak-your-way", "Speak your way"],
  ["/history", "History"],
  ["/sources", "Sources"],
  ["/eval", "Evaluation"],
  ["/status", "Status"],
  ["/settings", "Settings"],
  ["/privacy", "Privacy"],
] as const;

export function useOnline(): boolean {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  return online;
}

export function Logo({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
        <rect width="32" height="32" rx="7" fill="#1b2a41" />
        <path d="M5 21c4-7 18-7 22 0" stroke="#d9771f" strokeWidth="3" fill="none" strokeLinecap="round" />
        <path d="M9 21v4M16 18v7M23 21v4" stroke="#fffdf9" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
      <span className="font-display text-xl font-bold tracking-tight text-ink">GramSetu</span>
    </span>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const online = useOnline();
  const [open, setOpen] = useState(false);
  return (
    <div className="min-h-screen bg-paper text-ink">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-ink focus:px-3 focus:py-2 focus:text-white">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-line bg-paper/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] items-center gap-4 px-4 py-3">
          <Link to="/" aria-label="GramSetu home"><Logo /></Link>
          <nav aria-label="Main" className="ml-4 hidden flex-1 gap-1 lg:flex">
            {NAV.map(([to, label]) => (
              <NavLink key={to} to={to}
                className={({ isActive }) => `rounded-md px-3 py-2 text-sm font-medium ${isActive ? "bg-ink text-white" : "text-ink-soft hover:bg-line/60"}`}>
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3">
            <span role="status" className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${online ? "bg-line/60 text-ink-soft" : "bg-danger-light text-danger"}`}>
              {online ? <Wifi className="h-3.5 w-3.5" aria-hidden /> : <WifiOff className="h-3.5 w-3.5" aria-hidden />}
              {online ? "Online" : "Offline — voice needs internet"}
            </span>
            <button className="rounded-md border border-line px-3 py-2 text-sm lg:hidden" aria-expanded={open} aria-controls="mobile-nav" onClick={() => setOpen((o) => !o)}>
              Menu
            </button>
          </div>
        </div>
        {open && (
          <nav id="mobile-nav" aria-label="Main" className="grid grid-cols-2 gap-1 border-t border-line px-4 py-2 lg:hidden">
            {NAV.map(([to, label]) => (
              <NavLink key={to} to={to} onClick={() => setOpen(false)} className="rounded-md px-3 py-3 text-sm hover:bg-line/60">{label}</NavLink>
            ))}
          </nav>
        )}
      </header>
      <main id="main">{children}</main>
      <footer className="mt-16 border-t border-line">
        <div className="mx-auto max-w-[1500px] px-4 py-6 text-xs text-ink-soft">
          GramSetu is an AI assistant. Speech by Gnani Prisma (recognition) and Gnani Timbre (voice). Demo workflows run on
          locally hosted demo portals — GramSetu does not submit anything to real government or hospital systems.
        </div>
      </footer>
    </div>
  );
}

export function Card({ children, className = "", title, action, id }: { children: ReactNode; className?: string; title?: ReactNode; action?: ReactNode; id?: string }) {
  return (
    <section id={id} className={`rounded-xl border border-line bg-card shadow-[0_1px_0_rgba(27,42,65,0.04)] ${className}`}>
      {title && (
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-soft">{title}</h2>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "saffron" | "verified" | "danger" | "ink"; children: ReactNode }) {
  const tones = {
    neutral: "bg-line/70 text-ink-soft",
    saffron: "bg-saffron-light text-saffron-dark",
    verified: "bg-verified-light text-verified",
    danger: "bg-danger-light text-danger",
    ink: "bg-ink text-white",
  } as const;
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone]}`}>{children}</span>;
}

export function PageHeader({ title, sub }: { title: string; sub?: ReactNode }) {
  return (
    <div className="mx-auto max-w-[1100px] px-4 pb-4 pt-8">
      <h1 className="font-display text-3xl font-bold">{title}</h1>
      {sub && <p className="mt-2 max-w-3xl text-ink-soft">{sub}</p>}
    </div>
  );
}
