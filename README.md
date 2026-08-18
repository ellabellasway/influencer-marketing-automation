# Creator Ops

Two [Claude Code](https://claude.com/claude-code) skills covering a creator
partnerships pipeline end to end: find the right people, decide who's actually
worth paying, and reach out without the mistakes that quietly waste a
sponsorship budget.

```
creator-scout           →   creator-partnerships
find + rank + contact         vet + spend decision + outreach + tracking
```

## Why two skills instead of one

They're genuinely different jobs. `creator-scout` is a data problem: search a
niche three independent ways, pull real engagement numbers instead of trusting
follower counts, resolve a public contact path. `creator-partnerships` is a
judgment problem: given a name and a set of numbers, should you actually pay
this person, what should you say to them, and how do you know afterward
whether it worked. Keeping them separate means you can run the vetting rubric
on a name someone handed you directly, without ever running discovery, or use
the discovery tool for research that has nothing to do with paid placements.

## creator-scout

Turns a niche (keywords, hashtags, a couple of search phrases) into a ranked,
contactable list of creators, plus a self-contained HTML dashboard you can
filter and sort. Instagram and TikTok are both verified end to end; adding a
platform means confirming field paths on one real account first (see
`creator-scout/reference/platforms.md`).

Requires the **ScrapeCreators** MCP connector — no API key lives in this repo,
the connector holds credentials server-side.

```bash
cp -R creator-scout ~/.claude/skills/
```

Then in Claude Code: `/creator-scout` (or just ask for it in a normal message —
Claude Code loads skills by matching what you're asking for against each
skill's description, not only by exact slash-command name).

## creator-partnerships

The vetting rubric, spend-decision rule, first-touch outreach template, launch
checklist, and attribution method for actually running a paid creator
sponsorship program. No API connector required — this one's process and a
YouTube median-views script (`creator-partnerships/scripts/measure_youtube_medians.py`),
not an automated pipeline.

```bash
cp -R creator-partnerships ~/.claude/skills/
```

## A typical run

1. `creator-scout` on your niche → a dashboard of candidates ranked by real
   engagement, not follower count.
2. Pick the ones worth a closer look → `measure_youtube_medians.py` (or the
   dashboard's own numbers, for Instagram/TikTok) to confirm the reach is real.
3. Run the vetting rubric in `creator-partnerships/SKILL.md` → decide who
   clears the bar and who gets parked.
4. Check for prior contact, draft the first-touch outreach, get a human's
   sign-off, send.
5. Once something's signed: tag the links, log the deal, and use the
   attribution method to find out later whether it actually worked.

## License

MIT. See `LICENSE`.
