"""Prepare a gemini-web2api cookie file from the cookie-sync extension export.

The extension's gemini-auth.json also contains accounts.google.com host-only cookies
(LSID, OSID, ...). A browser never sends those to gemini.google.com, and when the proxy
does, Gemini answers 401. This writes gemini-auth.clean.json without them and points the
proxy's config.json at it (plus the exported xsrf token / build label).

Usage: python -I backend/scripts/prepare_gemini_auth.py C:\\path\\to\\gemini-web2api
Prints cookie names only, never values.
"""

import json
import sys
from pathlib import Path

ACCOUNTS_ONLY = {"LSID", "OSID", "__Secure-OSID", "__Host-1PLSID", "__Host-3PLSID", "__Host-GAPS"}
REQUIRED = {"__Secure-1PSID", "__Secure-1PSIDTS"}


def main(proxy_dir: Path) -> None:
    auth = json.loads((proxy_dir / "gemini-auth.json").read_text(encoding="utf-8"))
    pairs = [p.split("=", 1) for p in auth["cookie"].split("; ") if "=" in p]
    kept = [(k, v) for k, v in pairs if k not in ACCOUNTS_ONLY]
    missing = REQUIRED - {k for k, _ in kept}
    if missing:
        sys.exit(f"export is missing {sorted(missing)}: sign in to gemini.google.com and export again")

    clean = dict(auth, cookie="; ".join(f"{k}={v}" for k, v in kept))
    clean_file = proxy_dir / "gemini-auth.clean.json"
    clean_file.write_text(json.dumps(clean), encoding="utf-8")

    config_file = proxy_dir / "config.json"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    config["cookie_file"] = str(clean_file)
    config["auth_user"] = auth.get("auth_user")
    config["xsrf_token"] = auth.get("xsrf_token")
    if auth.get("gemini_bl"):
        config["gemini_bl"] = auth["gemini_bl"]
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

    dropped = sorted(k for k, _ in pairs if k in ACCOUNTS_ONLY)
    print(f"kept {len(kept)} cookies, dropped {dropped}")
    print(f"config.json now uses {clean_file.name}; restart the proxy")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
