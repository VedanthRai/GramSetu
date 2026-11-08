"""Secret and privacy scan of the working tree AND the full git history (documented grep; complements gitleaks).

  python scripts/secret_scan.py          # exit code 1 if anything is found

Looks for: the actual values of every *KEY*/*TOKEN*/*SECRET* variable in .env (by 12-character fragments, never
printed), generic key patterns (Gnani `vach_…`, Anthropic `sk-ant-…`, OpenAI `sk-…`, AWS, private keys), a committed
.env file, and Indian personal-data patterns (Aadhaar-like 12 digits, PAN, real-looking phone numbers other than the
synthetic 9876543210 used in the demo). Results: demo-output/qc/secret_scan.md
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "gnani key pattern": r"vach_[A-Za-z0-9_\-]{12,}",
    "anthropic key pattern": r"sk-ant-[A-Za-z0-9_\-]{12,}",
    "openai-style key": r"\bsk-[A-Za-z0-9]{32,}",
    "aws access key": r"\bAKIA[0-9A-Z]{16}\b",
    "private key block": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "PAN-like id": r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
}
ALLOWED_PHONES = {"9876543210", "9876501234"}  # synthetic numbers used in the demo and tests
ALLOWED = {"1234 5678 9012", "123456789012"}       # placeholder Aadhaar used in redaction tests
FAKE_KEY_PREFIX = "vach_ABCD"                      # deliberately fake key in backend/tests (sanitiser test)
BINARY = {".wav", ".mp4", ".webm", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".db"}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def key_values() -> list[str]:
    env = ROOT / ".env"
    out = []
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if re.search(r"KEY|TOKEN|SECRET", k) and len(v.strip()) >= 12:
                out.append(v.strip())
    return out


def scan_text(label: str, text: str, frags: set[str]) -> list[str]:
    hits = []
    if any(f in text for f in frags):
        hits.append(f"{label}: contains a fragment of a configured secret")
    for name, pat in PATTERNS.items():
        for m in re.finditer(pat, text):
            if name == "PAN-like id" and m.group(0) in ("ABCDE1234F",):
                continue
            if name == "gnani key pattern" and m.group(0).startswith(FAKE_KEY_PREFIX):
                continue
            hits.append(f"{label}: {name}")
            break
    for m in re.finditer(r"(?<![\w.])[6-9]\d{9}(?![\w.])", text):
        if m.group(0) not in ALLOWED_PHONES:
            hits.append(f"{label}: phone-number-like digits ({m.group(0)[:2]}…{m.group(0)[-2:]})")
            break
    for m in re.finditer(r"(?<![\w.])\d{4}\s?\d{4}\s?\d{4}(?![\w.])", text):
        if m.group(0) in ALLOWED:
            continue
        hits.append(f"{label}: 12-digit (Aadhaar-like) number")
        break
    return hits


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    keys = key_values()
    frags = {k[i:i + 12] for k in keys for i in range(0, max(1, len(k) - 12), 4)}
    report = ["# Secret and privacy scan", ""]
    ignored = git("check-ignore", ".env").strip() == ".env"
    tracked_env = bool(git("ls-files", ".env").strip())
    ever_env = bool(git("log", "--all", "--format=%H", "--", ".env").strip())
    report += [f"- `.env` ignored by git: **{ignored}**; tracked now: **{tracked_env}**; ever committed: **{ever_env}**",
               f"- configured secrets checked (values never printed): {len(keys)}"]
    hits: list[str] = []
    # working tree: tracked + untracked-but-not-ignored files
    files = [f for f in git("ls-files", "-co", "--exclude-standard").splitlines() if f]
    for f in files:
        p = ROOT / f
        if not p.is_file() or p.stat().st_size > 20_000_000 or p.suffix.lower() in BINARY:
            continue
        txt = p.read_bytes().decode("utf-8", "ignore")
        hits += scan_text(f"tree:{f}", txt, frags)
    # full history: every patch of every commit on every ref
    hist = git("log", "-p", "--all", "--no-color")
    commits = len(git("rev-list", "--all").split())
    hits += scan_text("git history", hist, frags)
    # demo outputs: also scan ignored output folders (captions, logs, posts, EDL)
    extra = [p for d in ("demo-output/final", "demo-output/edit", "demo-output/posts", "demo-output/qc", "docs/submission")
             for p in (ROOT / d).rglob("*") if p.is_file() and p.suffix in (".srt", ".json", ".md", ".txt", ".log")]
    for p in extra:
        hits += scan_text(f"output:{p.relative_to(ROOT)}", p.read_bytes().decode("utf-8", "ignore"), frags)
    hits = sorted(set(hits))
    report += [f"- working-tree files scanned: {len(files)}; commits scanned (all refs, full patches): {commits}; "
               f"output files scanned: {len(extra)}", "", "## Findings", ""]
    report += [f"- {h}" for h in hits] or ["- none"]
    (ROOT / "demo-output" / "qc").mkdir(parents=True, exist_ok=True)
    (ROOT / "demo-output" / "qc" / "secret_scan.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 1 if (hits or not ignored or tracked_env or ever_env) else 0


if __name__ == "__main__":
    sys.exit(main())
