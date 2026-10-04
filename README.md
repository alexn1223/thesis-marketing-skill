# Thesis Marketing

A skill for Claude and Codex. It remembers a Fish School organizer's investment thesis and turns it into content that sends people to read it. Content never offers an investment.

## What it does

| Ask for | You get |
|---|---|
| "Set up my thesis" | A short interview, or paste your thesis, or import `thesis.json` from the thesis-builder skill. Saved once and remembered. |
| "Change my thesis / link", "undo that" | One field or the whole thesis updated; every earlier version is kept |
| "Write an X post about …" | Posts for X, LinkedIn, Telegram, Farcaster, Instagram and Threads; 6 formats and 6 tones; rewrites of your own text; reference links as sources |
| "Write an SEO article / thesis page" | Markdown with title, meta description, slug, FAQ and schema.org JSON-LD, checked for SEO basics |
| "Post ideas", "content plan" | Angles built from your key points and the questions people search for, and a 2-week calendar |
| "Turn this into posts" | One piece adapted for every platform |

Every draft runs through `check_post.py` before you see it. The check blocks "invest with me", "join the School", "I'm raising", return figures, urgency, and fund terms such as lockups and check sizes. Each CTA points to your thesis link.

## Install

**Claude Code**
```
/plugin marketplace add alexn1223/thesis-marketing-skill
/plugin install thesis-marketing@thesis-marketing-skill
```

**Codex**
```
codex plugin marketplace add alexn1223/thesis-marketing-skill
codex plugin add thesis-marketing@thesis-marketing-skill
```

**claude.ai** (Pro, Max, Team or Enterprise): Settings → Capabilities → Skills → upload `dist/thesis-marketing.zip`. Files reset between chats on claude.ai. After setup, the skill gives you a **thesis card**. Paste it into your Project's instructions and every chat in that Project remembers your thesis.

## Where your thesis is stored

`~/.thesis-marketing/` on your computer (set `THESIS_MARKETING_HOME` to move it). The folder holds plain JSON: `theses/`, `profile.json`, and `posts.jsonl` for drafts you kept. Nothing is sent anywhere by the skill itself.

## For maintainers

- Skill: `plugins/thesis-marketing/skills/thesis-marketing/`. Claude manifest: `.claude-plugin/`. Codex manifest: `.codex-plugin/`. Marketplaces: `.claude-plugin/marketplace.json` (Claude) and `.agents/plugins/marketplace.json` (Codex).
- Scripts use the Python standard library only (3.9+).
- Tests: `uvx --with pytest pytest tests`.
- claude.ai zip: `./package.sh`.
- The phrase lists in `scripts/check_post.py` match `fish-post-bot/src/fishpost/compliance.py`. Change both together. Both need counsel review.
