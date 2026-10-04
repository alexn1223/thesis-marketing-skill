#!/usr/bin/env python3
"""Remembers the user's thesis between sessions. Standard library only.

Storage: $THESIS_MARKETING_HOME, else ~/.thesis-marketing/
  profile.json            name, school, voice samples
  active                  slug of the thesis posts are built around
  theses/<slug>.json      current version of each thesis
  theses/<slug>.versions.jsonl   every earlier version (for undo)
  posts.jsonl             drafts the user kept

Every command prints JSON to stdout. Run `status` first in every session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

THESIS_FIELDS = {
    "title": str,  # short name, e.g. "Agents need wallets"
    "school": str,  # Fish School name
    "statement": str,  # one or two sentences, <= 280 chars
    "body": str,  # full thesis text in the user's words
    "why_now": str,
    "edge": str,
    "sectors": list,
    "stage": str,
    "chains": list,
    "audience": str,  # who should read posts about it
    "key_points": list,  # 3-5 arguments
    "keywords": list,  # SEO: primary keyword first
    "questions": list,  # SEO: questions people search for
    "link": str,  # where the CTA points (thesis or School page)
    "not_for_posts": list,  # anything the user wants kept out of public content
}

# Offering terms. Never imported into marketing content: a post that states them reads as an offer.
TERMS_FIELDS = {
    "check_size", "position_count", "target_allocation", "liquid_locked_split", "exit_liquidity",
    "lockups", "entry_exit_rules", "fund_size_target", "investor_eligibility", "points_incentives",
    "transparency", "governance", "instrument", "risk_profile", "time_horizon", "benchmark",
}

CARD_START = "<<<THESIS-CARD v1"
CARD_END = "THESIS-CARD>>>"


def home() -> Path:
    return Path(os.environ.get("THESIS_MARKETING_HOME") or Path.home() / ".thesis-marketing")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "thesis")[:48]


def out(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def fail(msg: str, code: int = 1) -> None:
    out({"ok": False, "error": msg})
    sys.exit(code)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def thesis_path(slug: str) -> Path:
    return home() / "theses" / f"{slug}.json"


def all_slugs() -> list[str]:
    d = home() / "theses"
    return sorted(p.stem for p in d.glob("*.json")) if d.exists() else []


def active_slug() -> str | None:
    try:
        slug = (home() / "active").read_text().strip()
    except FileNotFoundError:
        return None
    return slug if thesis_path(slug).exists() else None


def load(slug: str) -> dict:
    t = read_json(thesis_path(slug), None)
    if t is None:
        fail(f"no thesis named '{slug}'. Known: {all_slugs()}")
    return t


def clean_fields(data: dict) -> tuple[dict, list[str]]:
    """Keep known fields with the right type; report anything dropped."""
    kept, dropped = {}, []
    for k, v in data.items():
        if k not in THESIS_FIELDS:
            dropped.append(k)
            continue
        want = THESIS_FIELDS[k]
        if want is list and isinstance(v, str):
            v = [x.strip() for x in re.split(r"[,\n]", v) if x.strip()]
        if want is str and isinstance(v, list):
            v = ", ".join(map(str, v))
        if v is None:
            continue
        kept[k] = v
    return kept, dropped


def warnings_for(t: dict) -> list[str]:
    w = []
    if not t.get("link"):
        w.append("No link yet: CTAs will invite replies/DMs instead of pointing to the thesis.")
    if len(t.get("statement", "")) > 280:
        w.append("Statement is over 280 characters; shorten it so it fits in one X post.")
    if not t.get("keywords"):
        w.append("No SEO keywords yet: run the keyword step before writing articles.")
    return w


def save_thesis(data: dict, slug: str | None, activate: bool) -> dict:
    fields, dropped = clean_fields(data)
    if not slug:
        if not fields.get("title"):
            fail("a new thesis needs a 'title'")
        slug = slugify(fields["title"])
    path = thesis_path(slug)
    existing = read_json(path, None)
    if existing:
        # Keep the old version so a change can be undone.
        with (path.parent / f"{slug}.versions.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(existing, ensure_ascii=False) + "\n")
        thesis = {**existing, **fields, "updated_at": now()}
    else:
        thesis = {"slug": slug, **fields, "created_at": now(), "updated_at": now()}
    write_json(path, thesis)
    if activate or not active_slug():
        (home() / "active").write_text(slug)
    return {"ok": True, "slug": slug, "active": active_slug() == slug, "dropped_fields": dropped,
            "warnings": warnings_for(thesis), "thesis": thesis}


# --- commands -----------------------------------------------------------------

def cmd_status(_a) -> None:
    profile = read_json(home() / "profile.json", {})
    slug = active_slug()
    ephemeral = Path("/mnt/user-data").exists() or Path("/mnt/skills").exists()
    out({
        "ok": True,
        "home": str(home()),
        "storage": "ephemeral (claude.ai: files reset between chats, use the thesis card)" if ephemeral else "persistent",
        "has_thesis": slug is not None,
        "profile": profile,
        "active": load(slug) if slug else None,
        "theses": [{"slug": s, "title": read_json(thesis_path(s), {}).get("title", s), "active": s == slug}
                   for s in all_slugs()],
        "warnings": warnings_for(load(slug)) if slug else [],
    })


def _read_payload(a) -> dict:
    raw = Path(a.file).read_text(encoding="utf-8") if a.file and a.file != "-" else sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"input is not valid JSON: {e}")
    if not isinstance(data, dict):
        fail("input must be a JSON object")
    return data


def cmd_save(a) -> None:
    out(save_thesis(_read_payload(a), a.slug, a.activate))


def cmd_set(a) -> None:
    slug = a.slug or active_slug()
    if not slug:
        fail("no active thesis; run setup first")
    if a.field not in THESIS_FIELDS:
        fail(f"unknown field '{a.field}'. Fields: {sorted(THESIS_FIELDS)}")
    value = Path(a.value_file).read_text(encoding="utf-8").strip() if a.value_file else a.value
    if value is None:
        fail("give --value or --value-file")
    out(save_thesis({a.field: value}, slug, False))


def cmd_activate(a) -> None:
    load(a.slug)
    (home() / "active").write_text(a.slug)
    out({"ok": True, "active": a.slug})


def cmd_list(_a) -> None:
    slug = active_slug()
    out({"ok": True, "theses": [{**read_json(thesis_path(s), {}), "active": s == slug} for s in all_slugs()]})


def cmd_delete(a) -> None:
    load(a.slug)
    thesis_path(a.slug).unlink()
    remaining = all_slugs()
    if active_slug() is None:
        if remaining:
            (home() / "active").write_text(remaining[-1])
        else:
            (home() / "active").unlink(missing_ok=True)
    out({"ok": True, "deleted": a.slug, "active": active_slug()})


def cmd_versions(a) -> None:
    slug = a.slug or active_slug()
    path = home() / "theses" / f"{slug}.versions.jsonl"
    versions = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    out({"ok": True, "slug": slug, "count": len(versions),
         "versions": [{"n": i, "updated_at": v.get("updated_at"), "statement": v.get("statement", "")}
                      for i, v in enumerate(versions)]})


def cmd_restore(a) -> None:
    slug = a.slug or active_slug()
    path = home() / "theses" / f"{slug}.versions.jsonl"
    versions = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    if not 0 <= a.n < len(versions):
        fail(f"no version {a.n}; there are {len(versions)}")
    old = {k: v for k, v in versions[a.n].items() if k in THESIS_FIELDS}
    out(save_thesis(old, slug, False))


def cmd_profile(a) -> None:
    path = home() / "profile.json"
    profile = read_json(path, {})
    if a.name is not None:
        profile["name"] = a.name
    if a.school is not None:
        profile["school"] = a.school
    if a.voice_file:
        sample = Path(a.voice_file).read_text(encoding="utf-8").strip()[:2000]
        profile["voice_samples"] = (profile.get("voice_samples", []) + [sample])[-3:]
    if a.clear_voice:
        profile["voice_samples"] = []
    write_json(path, profile)
    out({"ok": True, "profile": profile})


def cmd_import_builder(a) -> None:
    """Import thesis.json from the thesis-builder skill. Offering terms are left out on purpose."""
    src = read_json(Path(a.path), None)
    if not isinstance(src, dict):
        fail(f"could not read {a.path} as a JSON object")
    sectors = src.get("sectors") or []
    data = {
        "title": src.get("fund_name") or "My thesis",
        "school": src.get("fund_name") or "",
        "statement": src.get("thesis_statement") or "",
        "why_now": src.get("macro_view") or "",
        "edge": src.get("edge") or "",
        "sectors": [s for s in sectors if s and s != "other"],
        "stage": src.get("stage") or "",
        "chains": src.get("chain_scope") or [],
    }
    data["body"] = "\n\n".join(x for x in (data["statement"], data["why_now"], data["edge"]) if x)
    data = {k: v for k, v in data.items() if v}
    result = save_thesis(data, None, True)
    result["left_out_terms"] = sorted(k for k in TERMS_FIELDS if src.get(k))
    result["note"] = "Offering terms (check size, lockups, allocations, exits) stay out of marketing content."
    out(result)


def cmd_card(a) -> None:
    slug = a.slug or active_slug()
    if not slug:
        fail("no active thesis")
    t = {k: v for k, v in load(slug).items() if k in THESIS_FIELDS}
    profile = read_json(home() / "profile.json", {})
    payload = json.dumps({"thesis": t, "profile": profile}, ensure_ascii=False, separators=(",", ":"))
    card = f"{CARD_START}\n{payload}\n{CARD_END}"
    out({"ok": True, "card": card})


def cmd_import_card(a) -> None:
    raw = Path(a.file).read_text(encoding="utf-8") if a.file and a.file != "-" else sys.stdin.read()
    m = re.search(re.escape(CARD_START) + r"\s*(\{.*\})\s*" + re.escape(CARD_END), raw, re.DOTALL)
    if not m:
        fail("no thesis card found in the input")
    data = json.loads(m.group(1))
    if data.get("profile"):
        write_json(home() / "profile.json", {**read_json(home() / "profile.json", {}), **data["profile"]})
    out(save_thesis(data.get("thesis", {}), None, True))


def cmd_log_post(a) -> None:
    text = Path(a.file).read_text(encoding="utf-8").strip()
    entry = {"at": now(), "thesis": active_slug(), "platform": a.platform, "kind": a.kind, "text": text}
    with (home() / "posts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    out({"ok": True})


def cmd_history(a) -> None:
    path = home() / "posts.jsonl"
    entries = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    out({"ok": True, "posts": entries[-a.limit:][::-1]})


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("save", help="create or update a thesis from JSON (file or stdin)")
    s.add_argument("--file", default="-")
    s.add_argument("--slug")
    s.add_argument("--activate", action="store_true")
    s.set_defaults(fn=cmd_save)
    s = sub.add_parser("set", help="change one field of a thesis")
    s.add_argument("field")
    s.add_argument("--value")
    s.add_argument("--value-file")
    s.add_argument("--slug")
    s.set_defaults(fn=cmd_set)
    s = sub.add_parser("activate")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_activate)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    s = sub.add_parser("delete")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_delete)
    s = sub.add_parser("versions")
    s.add_argument("--slug")
    s.set_defaults(fn=cmd_versions)
    s = sub.add_parser("restore")
    s.add_argument("n", type=int)
    s.add_argument("--slug")
    s.set_defaults(fn=cmd_restore)
    s = sub.add_parser("profile")
    s.add_argument("--name")
    s.add_argument("--school")
    s.add_argument("--voice-file")
    s.add_argument("--clear-voice", action="store_true")
    s.set_defaults(fn=cmd_profile)
    s = sub.add_parser("import-builder", help="import thesis.json from the thesis-builder skill")
    s.add_argument("path")
    s.set_defaults(fn=cmd_import_builder)
    s = sub.add_parser("card", help="print a portable thesis card")
    s.add_argument("--slug")
    s.set_defaults(fn=cmd_card)
    s = sub.add_parser("import-card")
    s.add_argument("--file", default="-")
    s.set_defaults(fn=cmd_import_card)
    s = sub.add_parser("log-post")
    s.add_argument("--file", required=True)
    s.add_argument("--platform", default="")
    s.add_argument("--kind", default="post")
    s.set_defaults(fn=cmd_log_post)
    s = sub.add_parser("history")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(fn=cmd_history)
    a = p.parse_args()
    home().mkdir(parents=True, exist_ok=True)
    a.fn(a)


if __name__ == "__main__":
    main()
