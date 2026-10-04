# Thesis fields

Collect these in the user's own words. Required: `title`, `statement`, `body`. Ask for `link` early because every CTA uses it.

| Field | What to ask | Notes |
|---|---|---|
| `title` | A short name for the thesis | e.g. "Agents need wallets" |
| `school` | Fish School name | optional |
| `statement` | The thesis in one or two sentences | ≤ 280 characters; propose a compression of their words and let them edit |
| `body` | The full thesis | paste or file; keep their text as is |
| `why_now` | Why this is the moment | their words only, no narrative you supply |
| `edge` | Why they see it before others | their words only, no label on it |
| `sectors`, `stage`, `chains` | The space | lists |
| `audience` | Who should read posts about it | founders, operators, other investors, users… |
| `key_points` | 3-5 arguments that make it true | propose from the body, user confirms |
| `link` | Where readers can see the thesis or School page | the CTA target |
| `keywords` | SEO keyword set, primary first | see `seo.md` |
| `questions` | Questions people search about this space | see `seo.md` |
| `not_for_posts` | Anything to keep out of public content | names, numbers, deals, terms |

## Save

Write the fields as one JSON object to a temp file:

```json
{"title": "...", "statement": "...", "body": "...", "link": "https://...", "key_points": ["...", "..."], "keywords": ["primary keyword", "..."]}
```

Then `python3 scripts/thesis_store.py save --file /tmp/thesis.json --activate`.

Unknown fields are dropped and reported. Offering terms (check size, lockups, allocations, exits, fees) are never stored for marketing. If the user offers them, say they belong in the private School documents, not in content.

## Change and undo

- `set <field> --value "..."` changes one field; the old version is kept.
- `versions` lists earlier versions; `restore <n>` brings one back.
- `card` prints a portable thesis card. On claude.ai, where files reset between chats, the user keeps this card in their Project.
