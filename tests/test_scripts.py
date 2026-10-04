"""Runs the skill's scripts the way the agent does: as subprocesses that print JSON."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "plugins/thesis-marketing/skills/thesis-marketing/scripts"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def run(tmp_path, monkeypatch):
    home = tmp_path / "home"
    monkeypatch.setenv("THESIS_MARKETING_HOME", str(home))

    def _run(script: str, *args: str, stdin: str = "", ok: bool = True) -> dict:
        p = subprocess.run([sys.executable, str(SCRIPTS / script), *args], input=stdin, capture_output=True,
                           text=True, env={"THESIS_MARKETING_HOME": str(home), "PATH": "/usr/bin:/bin"})
        assert (p.returncode == 0) == ok, p.stderr + p.stdout
        return json.loads(p.stdout)

    return _run


THESIS = {
    "title": "Agents need wallets",
    "statement": "AI agents will hold and spend money onchain. The wallet and identity layer for them is underbuilt.",
    "body": "Agents will pay for compute, data and services...",
    "link": "https://example.com/thesis",
    "keywords": ["AI agent wallets", "agent payments"],
    "not_for_posts": ["Project Falcon"],
    "check_size": "$50k",  # not a thesis field: must be dropped
}


# --- memory -------------------------------------------------------------------

def test_status_empty_then_setup(run):
    s = run("thesis_store.py", "status")
    assert s["has_thesis"] is False and s["storage"] == "persistent"

    saved = run("thesis_store.py", "save", stdin=json.dumps(THESIS))
    assert saved["slug"] == "agents-need-wallets" and saved["active"]
    assert saved["dropped_fields"] == ["check_size"]

    s = run("thesis_store.py", "status")
    assert s["has_thesis"] and s["active"]["link"] == "https://example.com/thesis"
    assert "check_size" not in s["active"]


def test_change_versions_and_restore(run):
    run("thesis_store.py", "save", stdin=json.dumps(THESIS))
    run("thesis_store.py", "set", "link", "--value", "https://example.com/v2")
    run("thesis_store.py", "set", "keywords", "--value", "agent wallets, agent identity")
    s = run("thesis_store.py", "status")["active"]
    assert s["link"] == "https://example.com/v2" and s["keywords"] == ["agent wallets", "agent identity"]

    v = run("thesis_store.py", "versions")
    assert v["count"] == 2
    run("thesis_store.py", "restore", "0")
    assert run("thesis_store.py", "status")["active"]["link"] == "https://example.com/thesis"


def test_unknown_field_rejected(run):
    run("thesis_store.py", "save", stdin=json.dumps(THESIS))
    out = run("thesis_store.py", "set", "lockups", "--value", "12 months", ok=False)
    assert "unknown field" in out["error"]


def test_multiple_theses_activate_delete(run):
    run("thesis_store.py", "save", stdin=json.dumps(THESIS))
    run("thesis_store.py", "save", stdin=json.dumps({"title": "Stablecoin rails", "statement": "s", "body": "b"}))
    assert run("thesis_store.py", "status")["active"]["slug"] == "agents-need-wallets"  # first stays active
    run("thesis_store.py", "activate", "stablecoin-rails")
    assert run("thesis_store.py", "status")["active"]["slug"] == "stablecoin-rails"
    run("thesis_store.py", "delete", "stablecoin-rails")
    s = run("thesis_store.py", "status")
    assert s["active"]["slug"] == "agents-need-wallets" and len(s["theses"]) == 1


def test_card_round_trip(run, tmp_path):
    run("thesis_store.py", "save", stdin=json.dumps(THESIS))
    run("thesis_store.py", "profile", "--name", "Dana", "--school", "Agent Infra")
    card = run("thesis_store.py", "card")["card"]
    assert card.startswith("<<<THESIS-CARD v1")

    # A fresh environment (e.g. a new claude.ai chat) restores everything from the pasted card.
    import os

    fresh = tmp_path / "fresh"
    p = subprocess.run([sys.executable, str(SCRIPTS / "thesis_store.py"), "import-card"],
                       input=f"Here is my card:\n{card}\nthanks", capture_output=True, text=True,
                       env={**os.environ, "THESIS_MARKETING_HOME": str(fresh)})
    assert p.returncode == 0, p.stderr
    p = subprocess.run([sys.executable, str(SCRIPTS / "thesis_store.py"), "status"], capture_output=True, text=True,
                       env={**os.environ, "THESIS_MARKETING_HOME": str(fresh)})
    s = json.loads(p.stdout)
    assert s["active"]["statement"] == THESIS["statement"] and s["profile"]["name"] == "Dana"


def test_import_builder_leaves_terms_out(run):
    out = run("thesis_store.py", "import-builder", str(FIXTURES / "builder-thesis.json"))
    t = out["thesis"]
    assert t["title"] == "BASE Consumer Szn" and t["statement"].startswith("Pre-TGE consumer apps")
    assert "check_size" in out["left_out_terms"] and "exit_liquidity" in out["left_out_terms"]
    text = json.dumps(t)
    assert "$25k" not in text and "lockup" not in text.lower()


def test_history(run, tmp_path):
    run("thesis_store.py", "save", stdin=json.dumps(THESIS))
    draft = tmp_path / "d.txt"
    draft.write_text("A kept post")
    run("thesis_store.py", "log-post", "--file", str(draft), "--platform", "x")
    h = run("thesis_store.py", "history")
    assert h["posts"][0]["text"] == "A kept post" and h["posts"][0]["thesis"] == "agents-need-wallets"


# --- compliance ---------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    "Invest with me in agent wallets.",
    "Join the School before it fills up.",
    "We're raising now.",
    "12-month lockup, $25k check size.",
    "Only 3 spots left!",
    "Targeting 40% IRR.",
    "Send USDC to get in.",
])
def test_check_blocks_solicitation(run, bad):
    out = run("check_post.py", "--platform", "linkedin", stdin=bad, ok=False)
    assert out["ok"] is False


def test_check_passes_clean_post_and_measures(run):
    text = "Agents will need wallets before they need apps. Full thesis: https://example.com/thesis"
    out = run("check_post.py", "--platform", "x", "--link", "https://example.com/thesis", stdin=text)
    assert out["ok"] and out["issues"] == [] and out["limit"] == 280


def test_check_thread_forbid_and_instagram(run):
    out = run("check_post.py", "--platform", "x", "--format", "thread", stdin="one\n---\n" + "b" * 300, ok=False)
    assert not out["ok"] and len(out["parts"]) == 2
    out = run("check_post.py", "--forbid", "Project Falcon", stdin="We looked at Project Falcon.", ok=False)
    assert not out["ok"] and out["issues"][0]["code"] == "not_for_posts"
    out = run("check_post.py", "--platform", "instagram", stdin="Read it: https://example.com")
    assert any(i["code"] == "dead_link" for i in out["issues"])


# --- SEO ----------------------------------------------------------------------

GOOD_ARTICLE = """---
title: AI agent wallets: why agents need their own money
meta_description: AI agent wallets let software pay for compute, data and services. Here is how they work and why the layer matters now.
slug: ai-agent-wallets
primary_keyword: AI agent wallets
secondary_keywords: agent payments, agent identity
link: https://example.com/thesis
author: Dana
---

# AI agent wallets explained

AI agent wallets are accounts that software agents control. {filler}

## How agent payments work
{filler}

## Why identity comes next
{filler}

## What builders should watch
{filler} Read the [full agent wallets thesis](https://example.com/thesis).

## FAQ
### What are AI agent wallets?
They are wallets controlled by software agents. An agent can hold funds and pay for services within limits a person sets.
### Who builds them?
Wallet providers and payment networks are shipping the first versions this year.
"""


def test_seo_good_article_passes_with_jsonld(run, tmp_path):
    filler = "Agents pay for compute and data. Each payment needs limits. Teams are testing this now. " * 20
    page = tmp_path / "a.md"
    page.write_text(GOOD_ARTICLE.format(filler=filler))
    out = run("seo_check.py", "--file", str(page), "--jsonld")
    assert out["ok"], out["issues"]
    assert not [i for i in out["issues"] if i["code"] in ("title_length", "meta_length", "h1", "missing_link")]
    types = [b["@type"] for b in out["jsonld"]]
    assert types == ["Article", "FAQPage"] and len(out["jsonld"][1]["mainEntity"]) == 2


def test_seo_bad_article_flagged(run, tmp_path):
    page = tmp_path / "b.md"
    page.write_text("---\ntitle: Hi\n---\nNo heading. Invest with me, 10x returns guaranteed.")
    out = run("seo_check.py", "--file", str(page), ok=False)
    codes = {i["code"] for i in out["issues"]}
    assert not out["ok"]
    assert {"missing_meta", "h1", "solicitation", "returns", "thin", "no_faq"} <= codes
