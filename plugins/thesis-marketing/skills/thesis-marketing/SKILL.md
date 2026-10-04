---
name: thesis-marketing
description: Remembers a Fish School organizer's investment thesis and turns it into marketing content - social posts (X, LinkedIn, Telegram, Farcaster, Instagram, Threads), SEO articles, thesis landing pages, post ideas and content calendars - without ever soliciting investment. Use when someone wants to set up, change or promote their investment thesis, write posts or SEO content about it, or plan content around it.
---

# thesis-marketing

Remembers the user's investment thesis and writes content that makes the right people go read it. One rule overrides everything: **content never offers an investment or asks for money.** The call to action always points to the thesis, never to the fund.

Scripts do the remembering and the checking; you do the writing. Run scripts from this skill's folder: `python3 scripts/<name>.py`.

## Step 0 — every session, before anything else

Run `python3 scripts/thesis_store.py status`.

- `has_thesis: true` → greet the user by name, name the active thesis in one line, and do what they asked.
- `has_thesis: false` → if the conversation or project files contain a block starting `<<<THESIS-CARD v1`, save it to a file and run `thesis_store.py import-card --file <file>`. Otherwise run **Setup**.
- `storage` says ephemeral (claude.ai) → files reset between chats. After setup or any change, give the user their thesis card (`thesis_store.py card`) and tell them to paste it into the Project instructions or knowledge so the next chat remembers it.

## What the user can ask for

| Request | Do this | Read |
|---|---|---|
| First time, or "set up my thesis" | **Setup** below | `references/setup.md` |
| "Change / update my thesis", "new link", "undo" | **Change** below | `references/setup.md` |
| A post for a platform, or "rewrite this" | **Write a post** below | `references/platforms.md`, `references/writing.md` |
| SEO article, blog post, thesis landing page | **SEO content** below | `references/seo.md` |
| Post ideas | 5-10 angles from the thesis, one line each, numbered; offer to write any | `references/writing.md` |
| Content plan / calendar | **Calendar** below | `references/calendar.md` |
| Turn one piece into many | Repurpose: write one post per platform from the source, each checked | `references/platforms.md` |
| Past drafts | `thesis_store.py history` | — |

Always read `references/compliance.md` once per session before writing anything.

## Setup

1. Ask whether they already have a thesis file. If they have `thesis.json` from the thesis-builder skill, run `thesis_store.py import-builder <path>`. Tell them which offering terms were left out and why.
2. Otherwise collect the fields in `references/setup.md`, conversationally, a few at a time. Pasted text is fine: extract the fields from it and confirm.
3. Build the SEO keyword set (`references/seo.md`, "Keyword set") and confirm it with the user.
4. Write the JSON to a temp file and run `thesis_store.py save --file <file> --activate`. Show the `warnings` it returns.
5. Optional: the user's name and School (`thesis_store.py profile --name ... --school ...`), and 1-3 voice samples (`profile --voice-file <file>`).

## Change

- One field: `thesis_store.py set <field> --value "..."`, or `--value-file` for long text.
- Several fields or a rewrite: `save --file <file> --slug <slug>` (it merges and keeps the old version).
- Undo: `versions`, then `restore <n>`.
- Several theses: `list`, `activate <slug>`, `delete <slug>` (confirm first).

After any change, say in one line what changed. On claude.ai, give the new card.

## Write a post

1. Settle platform, format and tone. Ask in one short message unless the user already said, or offer "same as last time". Formats: single, thread, long-form, announcement, insight, story. Tones: professional, conversational, bold, educational, witty, personal.
2. The input is either a **topic** (write from scratch) or **their text** (rewrite it; keep their facts). Use any reference links they give as source material. If you can browse, read them; never invent facts, numbers or quotes.
3. Draft the post around the active thesis (`references/writing.md`). For a thread, separate parts with a line containing only `---`.
4. Save the draft to a temp file and run:
   `python3 scripts/check_post.py --file <draft> --platform <p> --format <f> --link <thesis link> [--forbid "<each not_for_posts item>"]`
5. The script exits 1 when `ok` is false. Never chain `log-post` after it. If `ok` is false: rewrite to fix every `block` issue, check again. At most two rewrites. If it still fails, show the draft with the remaining issues listed and say it must not be posted as is.
6. Show the result: each post (or thread part) in its own ```text block so it copies cleanly, then one line: platform · characters/limit · "Compliance check passed" or the warnings.
7. Offer: new version · shorter · longer · stronger CTA · another tone · adapt to another platform. Any typed change is a refinement of the last draft.
8. Only when the user says they're keeping a draft (not automatically), run `thesis_store.py log-post --file <draft> --platform <p>`.

## SEO content

Read `references/seo.md` and follow its templates for articles and landing pages. Every page is checked with `python3 scripts/seo_check.py --file <page.md> --kind article|landing --jsonld`. Fix `block` issues; fix `warn` issues unless fixing would hurt the writing, and say which you left. Deliver the page as Markdown with front matter, followed by the JSON-LD in a ```json block for the site's `<head>`.

If other SEO or marketing skills are installed (keyword research, SEO audit, content creation), you may use them for research and structure. This skill's compliance and SEO checks still run last on anything you deliver.

## Calendar

Follow `references/calendar.md`. Every item names platform, format, angle and the thesis point it supports. Write the first two items in full only if asked.

## Hard rules

- Never write: invest with me/us, join my (or the) fund/School/club, back me, I'm raising, fundraising, minimums, allocation or spots, deadlines or urgency, return figures, guarantees, fund terms (lockups, check size, fees). Full list: `references/compliance.md`.
- The CTA points to the thesis link: read it, discuss it, follow it, DM to compare notes.
- Nothing from the user's `not_for_posts` list appears in any content.
- Do not invent search volumes, rankings or statistics. Say "estimate" or leave them out unless a tool gave you the number.
- Do not state anything about Fish Network's products as fact beyond what the user told you.
