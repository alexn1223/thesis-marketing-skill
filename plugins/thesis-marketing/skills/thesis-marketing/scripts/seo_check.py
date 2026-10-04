#!/usr/bin/env python3
"""Checks an SEO article or landing page written as Markdown with front matter. Standard library only.

  python3 seo_check.py --file article.md [--kind article|landing] [--jsonld]

Front matter (between --- lines at the top):
  title, meta_description, slug, primary_keyword, secondary_keywords (comma list), link, author

Prints JSON with "ok", "issues", "stats". Also runs the compliance check on the whole text.
--jsonld adds schema.org Article (and FAQPage if the page has an FAQ section) to the output.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from check_post import check as compliance_check  # noqa: E402

MIN_WORDS = {"article": 700, "landing": 250}


def parse(md: str) -> tuple[dict, str]:
    meta: dict[str, str] = {}
    body = md
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", md, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip().lower()] = v.strip().strip('"').strip("'")
        body = md[m.end():]
    return meta, body


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)


def plain(body: str) -> str:
    text = re.sub(r"```.*?```", " ", body, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^#+\s*", "", text, flags=re.MULTILINE)
    return re.sub(r"[*_`>|]", " ", text)


def contains(haystack: str, needle: str) -> bool:
    return bool(needle) and needle.lower() in haystack.lower()


def faq_pairs(body: str) -> list[tuple[str, str]]:
    m = re.search(r"^##\s+(FAQ|Frequently asked questions|Questions)\b.*?$(.*?)(?=^##\s|\Z)", body,
                  re.IGNORECASE | re.MULTILINE | re.DOTALL)
    if not m:
        return []
    pairs = []
    for q in re.finditer(r"^###\s+(.+?)\s*$\n(.*?)(?=^###\s|\Z)", m.group(2), re.MULTILINE | re.DOTALL):
        answer = " ".join(plain(q.group(2)).split())
        if answer:
            pairs.append((q.group(1).strip(), answer))
    return pairs


def jsonld(meta: dict, body: str) -> list[dict]:
    blocks = [{
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": meta.get("title", ""),
        "description": meta.get("meta_description", ""),
        "keywords": ", ".join(k for k in [meta.get("primary_keyword", "")] + meta.get("secondary_keywords", "").split(",") if k.strip()),
        **({"author": {"@type": "Person", "name": meta["author"]}} if meta.get("author") else {}),
        **({"mainEntityOfPage": meta["link"]} if meta.get("link") else {}),
    }]
    pairs = faq_pairs(body)
    if pairs:
        blocks.append({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}}
                           for q, a in pairs],
        })
    return blocks


def check(md: str, kind: str = "article") -> dict:
    meta, body = parse(md)
    issues: list[dict] = []

    def add(sev: str, code: str, msg: str) -> None:
        issues.append({"severity": sev, "code": code, "message": msg})

    kw = meta.get("primary_keyword", "")
    title = meta.get("title", "")
    desc = meta.get("meta_description", "")
    slug = meta.get("slug", "")
    text = plain(body)
    word_list = words(text)
    n_words = len(word_list)
    h1 = re.findall(r"^#\s+(.+)$", body, re.MULTILINE)
    h2 = re.findall(r"^##\s+(.+)$", body, re.MULTILINE)

    for field in ("title", "meta_description", "slug", "primary_keyword"):
        if not meta.get(field):
            add("block", "missing_meta", f"Front matter is missing '{field}'.")

    if title and not 30 <= len(title) <= 60:
        add("warn", "title_length", f"Title is {len(title)} characters; aim for 30-60 so it isn't cut off in search.")
    if title and kw and not contains(title, kw):
        add("warn", "title_keyword", f"Title does not contain the primary keyword '{kw}'.")
    if desc and not 70 <= len(desc) <= 155:
        add("warn", "meta_length", f"Meta description is {len(desc)} characters; aim for 70-155.")
    if desc and kw and not contains(desc, kw):
        add("warn", "meta_keyword", "Meta description does not contain the primary keyword.")
    if slug and (not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug) or len(slug) > 60):
        add("warn", "slug_format", "Slug should be lowercase words joined by hyphens, under 60 characters.")
    if slug and kw and not all(t in slug for t in words(kw.lower()) if len(t) > 3):
        add("warn", "slug_keyword", "Slug does not contain the main words of the primary keyword.")

    if len(h1) != 1:
        add("block" if not h1 else "warn", "h1", f"Page has {len(h1)} H1 headings; it needs exactly one.")
    elif kw and not contains(h1[0], kw):
        add("warn", "h1_keyword", "The H1 does not contain the primary keyword.")
    if len(h2) < (3 if kind == "article" else 2):
        add("warn", "structure", f"Only {len(h2)} H2 sections; add more so the page answers related searches.")

    first_100 = " ".join(word_list[:100])
    if kw and not contains(first_100, kw):
        add("warn", "intro_keyword", "The primary keyword is not in the first 100 words.")
    kw_count = len(re.findall(re.escape(kw), text, re.IGNORECASE)) if kw else 0
    density = round(100 * kw_count * max(1, len(words(kw))) / n_words, 2) if n_words else 0.0
    if kw and density > 2.5:
        add("warn", "keyword_stuffing", f"Primary keyword density is {density}%; above 2.5% reads as stuffing.")
    if n_words < MIN_WORDS.get(kind, 0):
        add("warn", "thin", f"{n_words} words; a {kind} usually needs at least {MIN_WORDS[kind]} to rank.")

    sentences = [s for s in re.split(r"[.!?]+\s", text) if words(s)]
    avg_sentence = round(sum(len(words(s)) for s in sentences) / len(sentences), 1) if sentences else 0.0
    if avg_sentence > 22:
        add("warn", "long_sentences", f"Average sentence is {avg_sentence} words; aim for under 22.")

    link = meta.get("link", "")
    if link and link not in body:
        add("warn", "missing_link", "The page never links to the thesis.")
    if kind == "article" and not faq_pairs(body):
        add("warn", "no_faq", "No FAQ section (## FAQ with ### questions). FAQs win 'People also ask' results.")

    comp = compliance_check(f"{title}\n{desc}\n{body}", platform="", fmt="single")
    issues += [i for i in comp["issues"] if i["code"] not in ("missing_link",)]

    return {
        "ok": not any(i["severity"] == "block" for i in issues),
        "issues": issues,
        "stats": {"words": n_words, "h2": len(h2), "keyword_uses": kw_count, "keyword_density_pct": density,
                  "avg_sentence_words": avg_sentence, "faq_questions": len(faq_pairs(body)),
                  "title_chars": len(title), "meta_chars": len(desc)},
        "_meta": meta,
        "_body": body,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", default="-")
    p.add_argument("--kind", choices=["article", "landing"], default="article")
    p.add_argument("--jsonld", action="store_true", help="also output schema.org JSON-LD blocks")
    a = p.parse_args()
    md = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
    result = check(md, a.kind)
    meta, body = result.pop("_meta"), result.pop("_body")
    if a.jsonld:
        result["jsonld"] = jsonld(meta, body)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
