# Security policy

GramSetu is a hackathon prototype that runs locally against **demo portals with synthetic data**. It does not submit
anything to real government or hospital systems.

## Reporting a vulnerability

Please open a private security advisory on this repository (GitHub → Security → Report a vulnerability), or contact the
maintainer at `vedanthrai01@gmail.com`. Please do not open a public issue for security problems.

## Secrets

* API keys live only in `.env` (`GNANI_API_KEY`). `.env` is git-ignored and has never been committed (checked with `python scripts/secret_scan.py`, which scans the working tree and the full git history).
* Keys are read by the backend only; the browser never receives them. Logs pass through a sanitiser that redacts keys,
  OTPs, phone and Aadhaar-like numbers (`backend/app/core/logging.py`).
* If you fork this repo, never commit `.env`. If a key is ever exposed, rotate it in the Gnani dashboard immediately.

## Design safeguards

* **Approval gates:** nothing is typed into a portal until the user approves the reviewed summary; the final submit
  needs a second explicit approval.
* **OTPs** go from a secure input box straight into the portal field: never logged, stored, spoken or sent to a model.
  The voice path refuses OTP/PIN/password content with a scam warning.
* **Browser policy:** a 12-action allow-list, same-origin navigation only, and text on web pages is treated as data
  (a hidden prompt-injection probe in the demo portal is ignored and logged).
* **Verification:** a task is "done" only when the portal's stored record is found.
* **Emergencies:** medical-emergency phrases stop the flow and point to 112.
* **No public live deployment** of the real key by default. A public instance would need per-IP rate limits, a daily
  cap, an invite code and a kill switch first. The published "demo replay" page is static and makes no API calls.

See `docs/security.md` for the full threat model.
