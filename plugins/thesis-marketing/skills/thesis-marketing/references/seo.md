# SEO playbook

The goal: people searching for the thesis space find the organizer's content and click through to the thesis.

## Keyword set (build once at setup, store in the thesis)

1. **Primary keyword:** the 2-4 word phrase someone types when they care about this thesis. Examples: "AI agent wallets", "onchain consumer apps", "stablecoin payments infrastructure". Not the fund name.
2. **Secondary keywords:** 4-8 close variants and sub-topics.
3. **Questions:** 5-10 real questions people search ("what are agent wallets", "how do AI agents pay for things"). These become FAQ entries and post ideas.
4. Group them by intent: *learn* (what/how/why) → articles; *compare* (X vs Y, best…) → comparison sections; *follow* (news, trends) → posts.

If you can search the web, check what currently ranks for the primary keyword and match the depth and format. Never state search volumes or difficulty unless a tool returned them. Otherwise call them estimates or leave them out.

Store with `thesis_store.py set keywords --value "primary, second, third"` and `set questions --value-file <file>` (one per line).

## Article template (`--kind article`)

```markdown
---
title: <30-60 chars, contains the primary keyword>
meta_description: <70-155 chars, contains the primary keyword, says what the reader gets>
slug: <primary-keyword-words-hyphenated>
primary_keyword: <primary keyword>
secondary_keywords: <comma list>
link: <thesis link>
author: <organizer name>
---

# <H1: contains the primary keyword>

<Intro: 2-3 short paragraphs. Primary keyword in the first 100 words. State the question the article answers.>

## <H2: a secondary keyword or a question>
## <H2>
## <H2>

## What this means for <audience>
<Tie it back to the thesis. Link the thesis with descriptive anchor text, not "click here".>

## FAQ
### <Question from the thesis questions list>
<Answer in 40-60 words, direct first sentence.>
### <Question>
<Answer>
```

- 700-1500 words. One H1. 3+ H2s. Short paragraphs.
- Link to the thesis at least once in the body, plus 1-2 credible external sources.
- The analysis is the content. The thesis link is the next step for readers who want more.

## Landing page template (`--kind landing`) — the public thesis page

Sections: H1 (the thesis in plain words, with the primary keyword) → the problem / why now → 3-5 key points as H2s → who this is for → FAQ → CTA ("Read the full thesis", "Follow updates", "Talk to the organizer"). 250-800 words. The page describes the thesis. It never describes terms, returns or how to invest.

## Distribution (after publishing)

1. One X thread and one LinkedIn post summarizing the article, linking to it.
2. One post per FAQ question over the following weeks, each linking to the article.
3. Telegram/Farcaster: a short take plus the link.
4. Refresh the article when the thesis changes (`thesis_store.py versions` shows what changed).

## Checks

`python3 scripts/seo_check.py --file page.md --kind article --jsonld` checks title, meta and slug length and keyword use, the H1, H2 count, the intro keyword, keyword stuffing, word count, sentence length, the thesis link and the FAQ, then runs the compliance check on everything. Put the printed `jsonld` in a `<script type="application/ld+json">` tag on the page.
