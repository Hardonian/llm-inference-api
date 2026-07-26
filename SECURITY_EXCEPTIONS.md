# Security Exceptions (Known, Unfixable Upstream)

## ecdsa 0.19.2 — PYSEC-2026-1325 (Minerva timing attack)

- **Status:** ACCEPTED RISK — no upstream fix available (`fix_versions: []`).
- **Path:** transitive dependency via `python-jose[cryptography]` → `ecdsa`.
- **Details:** The pure-Python `ecdsa` package is vulnerable to the Minerva
  timing side-channel on P-256 signing. Upstream maintainers state constant-time
  operation is out of scope for a pure-Python implementation; no patched
  release exists as of 2026-07-26.
- **Mitigation:** `python-jose` is installed with the `[cryptography]` extra,
  so JOSE crypto operations use the `cryptography` backend (OpenSSL,
  constant-time) rather than `ecdsa`. The vulnerable code path is not used by
  this service for signing.
- **Review:** Re-check on dependency bumps; remove this exception if
  `python-jose` drops the `ecdsa` dependency or a fixed `ecdsa` release ships.
