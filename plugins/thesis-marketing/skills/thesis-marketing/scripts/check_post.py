#!/usr/bin/env python3
"""Checks a draft before the user sees it. Standard library only.

  python3 check_post.py --platform x --format single --link https://... --file draft.txt

Prints JSON: {"ok": bool, "issues": [...], "parts": [...], "lengths": [...]}
"ok" is false (and the exit code is 1) when any issue has severity "block". Fix blocks before showing the draft.
The phrase lists are a first pass and need counsel review. Keep them in sync with fish-post-bot.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

LIMITS = {"x": 280, "linkedin": 3000, "telegram": 4096, "farcaster": 320, "instagram": 2200, "threads": 500}
LINKS_NOT_CLICKABLE = {"instagram"}
THREAD_SEPARATOR = "---"

# (code, pattern, message). Case-insensitive.
BLOCK_RULES = [
    ("solicitation", r"\binvest(ing)?\s+(with|alongside)\s+(me|us)\b", "Asks readers to invest with the author."),
    ("solicitation", r"\binvest\s+in\s+(my|our)\b", "Asks readers to invest in the author's vehicle."),
    ("solicitation", r"\b(i'?m|i am|we'?re|we are|currently|now)\s+(raising|fundraising)\b", "Says the author is raising money."),
    ("solicitation", r"\bfund-?raising\b", "Mentions fundraising."),
    ("solicitation", r"\braising\s+(a\s+)?(fund|round|capital|money|\$)", "Mentions raising capital."),
    ("solicitation", r"\b(join|get into|get in on)\s+(my|our|the|this)\s+(fish\s+)?(fund|school|club|pool|syndicate|spv)\b", "Invites readers to join an investment vehicle."),
    ("solicitation", r"\bback\s+(me|us)\b", "Asks readers to back the author."),
    ("solicitation", r"\b(commit|allocate|deploy)\s+(capital|funds|money|usdc)\b", "Asks readers to commit money."),
    ("solicitation", r"\b(send|deposit|transfer)\s+(usdc|eth|funds|money|\$)", "Asks readers to send money."),
    ("solicitation", r"\bminimum\s+(investment|ticket|check|commitment)\b", "States an investment minimum."),
    ("solicitation", r"\b(lp|allocation)\s+spots?\b", "Offers allocation."),
    ("terms", r"\b(lock-?ups?|redemption (window|period)|check size|ticket size|management fee|carried interest|2\s*(and|&)\s*20)\b", "States fund terms. Terms belong in the private School docs, not public content."),
    ("urgency", r"\b(\d+\s+)?spots?\s+(left|remaining)\b", "Uses scarcity to push a decision."),
    ("urgency", r"\b(last chance|don'?t miss out|fomo|before it closes|closing soon|limited spots)\b", "Uses urgency to push a decision."),
    ("returns", r"\b\d+(\.\d+)?\s*x\s+(return|returns|upside|gains?)\b", "States a return multiple."),
    ("returns", r"\b\d+(\.\d+)?\s*x\b(?=[^.\n]{0,40}\b(return|upside|gain|profit|money|investment)s?\b)", "States a return multiple."),
    ("returns", r"\b\d+(\.\d+)?\s*%\s*(apy|apr|yield|returns?|gains?|irr|roi)\b", "States a yield or return figure."),
    ("returns", r"\b(guarantee[ds]?|risk[- ]free|can'?t lose|sure thing|passive income|get rich)\b", "Promises an outcome."),
    ("returns", r"\b(100|1000)x\b|\bto the moon\b", "Hype about returns."),
]

WARN_RULES = [
    ("soft_language", r"\b(profits?|profitable|returns?|yields?|upside|moonshot)\b", "Talks about financial outcomes. Check it reads as analysis, not a promise."),
    ("soft_language", r"\b(invest|investing|investors?)\b", "Uses the word 'invest'. Fine for analysis; make sure it is not an offer."),
    ("soft_language", r"\b(financial advice|not financial advice|nfa)\b", "Disclaimers like 'NFA' signal an offer. Usually better removed."),
]

LINK_RE = re.compile(r"https?://\S+")
SEPARATOR_RE = re.compile(rf"^\s*{re.escape(THREAD_SEPARATOR)}\s*$", re.MULTILINE)


def split_parts(text: str, fmt: str) -> list[str]:
    if fmt != "thread":
        return [text.strip()]
    parts = [p.strip() for p in SEPARATOR_RE.split(text)]
    return [p for p in parts if p] or [text.strip()]


def effective_length(part: str, platform: str) -> int:
    if platform == "x":
        return len(LINK_RE.sub("x" * 23, part))  # X counts every link as 23 characters
    return len(part)


def check(text: str, platform: str = "", fmt: str = "single", link: str = "", forbid: list[str] | None = None) -> dict:
    issues: list[dict] = []

    def add(sev: str, code: str, msg: str) -> None:
        if not any(i["code"] == code and i["message"] == msg for i in issues):
            issues.append({"severity": sev, "code": code, "message": msg})

    for code, pattern, msg in BLOCK_RULES:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            add("block", code, f'{msg} ("{m.group(0)}")')

    for phrase in forbid or []:
        if phrase.strip() and phrase.strip().lower() in text.lower():
            add("block", "not_for_posts", f'Contains "{phrase.strip()}", which the user marked as not for public posts.')

    if not issues:  # soft warnings are noise once something blocks
        for code, pattern, msg in WARN_RULES:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                add("warn", code, f'{msg} ("{m.group(0)}")')

    parts = split_parts(text, fmt)
    lengths = [effective_length(p, platform) for p in parts]
    limit = LIMITS.get(platform)
    if limit:
        for n, length in enumerate(lengths, start=1):
            if length > limit:
                where = f"Part {n}" if fmt == "thread" else "Post"
                add("block", "too_long", f"{where} is {length} characters; {platform} allows {limit}.")

    if link and platform not in LINKS_NOT_CLICKABLE and link not in text:
        add("warn", "missing_link", "The thesis link is not in the text.")
    if platform in LINKS_NOT_CLICKABLE and LINK_RE.search(text):
        add("warn", "dead_link", f"Links are not clickable on {platform}; say 'link in bio' instead.")

    return {
        "ok": not any(i["severity"] == "block" for i in issues),
        "issues": issues,
        "parts": parts,
        "lengths": lengths,
        "limit": limit,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", default="-", help="draft text file, or - for stdin")
    p.add_argument("--platform", default="", choices=["", *LIMITS], help="empty for articles and pages")
    p.add_argument("--format", default="single", help="'thread' splits parts on a line containing only ---")
    p.add_argument("--link", default="", help="the thesis link the CTA should use")
    p.add_argument("--forbid", action="append", default=[], help="phrase that must not appear (repeatable)")
    a = p.parse_args()
    text = sys.stdin.read() if a.file == "-" else Path(a.file).read_text(encoding="utf-8")
    result = check(text, a.platform, a.format, a.link, a.forbid)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result["ok"] else 1)  # non-zero so a chained `&& log-post` never runs on a failed draft


if __name__ == "__main__":
    main()
