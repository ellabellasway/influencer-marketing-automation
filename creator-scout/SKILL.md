---
name: creator-scout
description: Turn a niche into a ranked, contactable creator list with an interactive dashboard. Discovers accounts three independent ways, scores them by actual engagement (not follower count), and resolves public contact paths. Requires the ScrapeCreators MCP connector.
---

# Creator Scout

A niche in, a ranked dashboard out. This skill exists because follower count is the
single most misleading number in influencer research: an account with 300K followers
and a dead feed will out-rank, on paper, an account with 30K followers whose last ten
posts each pulled real engagement. Scout ranks on the second thing.

**Requires the ScrapeCreators MCP connector.** Run a keyword `ToolSearch` (try
`instagram profile scrape` or `tiktok search keyword`) before promising a run. If
nothing comes back, say the connector isn't attached and stop there.

Read `reference/gotchas.md` before touching the scoring math. It documents specific
failure modes discovered while building this (pinned posts, null like-counts, TikTok's
follower-based rate lying) and every one of them produces a confident, plausible,
wrong number if you skip the fix.

## Inputs

Ask only for what changes the run; use the defaults otherwise.

| Input | Default | Notes |
|---|---|---|
| `platform` | instagram | Instagram and TikTok both verified end to end. Adding another platform means confirming field paths on one real account first, see `reference/platforms.md`. |
| `niche keywords` | — | Required: 2-3 bio/profile phrases, 2-3 hashtags, 1-2 native search phrases. Show the list back to the user before spending API credits on it. |
| `follower range` | none | Applied after scoring, not during discovery — a hard filter during discovery would throw away the "found by two methods" signal. |
| `result cap` | none | A cut-off applied to the ranked list, never to discovery. |

Settle two things early: whether the user wants engagement measured against
**followers** (Instagram convention) or **views** (the only honest number on
TikTok, see gotchas), and whether contact resolution should cover the whole list
or just the top N.

## Pipeline

Set a scratch cache directory once per run; large API responses spill there instead
of filling context, and every script below reads from disk with `--cache-dir`:

```bash
CACHE="$(dirname "$CLAUDE_SCRATCHPAD" 2>/dev/null || pwd)/tool-results"
```

### 1. Discover, three independent ways

Fire all searches in one parallel batch:

- **profile/bio search** per keyword — matches accounts whose bio *or* recent
  captions contain the phrase, which means brands and off-topic accounts will
  slip in. Don't filter them out silently; that's the user's call, not yours.
- **hashtag search** per hashtag
- **native keyword/reels search** per phrase — the richest source for platforms
  whose Google-indexed search is thin (see `reference/gotchas.md` §1)

```bash
python3 scripts/collect_pool.py --cache-dir "$CACHE" --out output/raw-pool.json \
  --platform instagram --queries "query one,query two,query three"
```

Read its stdout. It reports how many accounts were found by two or more methods
(the strongest signal in the whole pipeline) and flags anything that looks like
a labeling mixup between search results.

### 2. Enrich

One profile call per candidate, pulling bio, follower count, and the last 10-12
posts in the same call. That is a deliberate choice: two calls per creator doubles
both cost and wall-clock for information the first call already returned.

```bash
python3 scripts/enrich.py --cache-dir "$CACHE" --pool output/raw-pool.json \
  --platform instagram --out output/enriched.json \
  --min-followers 5000 --max-followers 500000 --max-age-days 60
```

Computes mean **and** median engagement (a 10-12 post mean is routinely wrecked
by one viral outlier, see gotchas §3), drops anything silent past `--max-age-days`,
and writes `output/run-meta.json` recording everything dropped and why.

### 3. Resolve contacts

Bio emails come out of the text automatically. Link-in-bio pages (Linktree, Komi,
and similar) return their content inline from the API rather than to disk, so hand
those fields to the script rather than expecting it to fetch them itself:

```bash
python3 scripts/contacts.py --enriched output/enriched.json \
  --linkinbio scratch/linkinbio.json --top 40
```

Talent-management domains get tagged separately from personal addresses. The
outreach you'd write to a manager is not the outreach you'd write to the creator,
so don't present one as the other.

### 4. Build the dashboard

```bash
python3 scripts/build_dashboard.py --enriched output/enriched.json \
  --meta output/run-meta.json --out output/creator-pool.html \
  --title "Creator Pool" --platform instagram --niche "your niche here"
```

Self-contained HTML, zero network calls, dark-mode aware. Open it and click
through the filters before handing it over — a filter that silently returns zero
results is worse than no dashboard at all.

## Reporting back

State plainly, every time:

- how many were found, how many survived each filter, and why
- who was dropped and why a creator missing from the list is not the same as a
  creator who was never found (the run-meta file exists specifically so you can
  tell the difference)
- the mean/median split for anyone whose numbers look too good, with the actual
  worst example named
- which contacts are agency addresses rather than personal ones
- credits spent

This tool ranks by engagement. It does not vet for brand fit, tone, or whether the
audience is actually who you think it is — say so, don't let the ranking imply
otherwise.

## Scope

Sources public bios, public posts, and creators' own link-in-bio pages for
partnership outreach. Don't use it to compile personal information beyond a
business contact path, and don't send anything on anyone's behalf without
explicit sign-off from whoever owns that relationship.
