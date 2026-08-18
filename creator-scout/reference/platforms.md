# Platform field maps

All tools referenced here are ScrapeCreators MCP tools. Find the current tool names
with a keyword `ToolSearch` rather than hard-coding them; connectors get renamed.

## Instagram — verified end to end

| Stage | Tool | Notes |
|---|---|---|
| Bio/profile search | a Google-indexed profile search tool | Matches captions as well as bios. Can return a server error on some query phrasings rather than an empty result — if a whole category of terms fails identically while an unrelated control query succeeds, that's the endpoint, not an absence of content. Fall back to the platform's own native account search, which returns real hashtag media counts and account snippets (no bio/follower count inline, so let the enrich stage fill those in). |
| Hashtag search | a Google-indexed hashtag search tool | Same caveat as above — verify against a hashtag you know has millions of real posts before trusting a 404 as "nothing here." |
| Native search | the platform's own ranked account/hashtag search | Not Google-indexed, one page of results, no posts. The reliable fallback when the Google-indexed tools misbehave on a whole topic. |
| Profile + posts | a single profile-detail tool, `trim` flag if offered | Returns the last 10-12 posts inline. One call per creator covers profile and posts together. |

Instagram post fields that matter (paths will vary by connector, confirm on one
account first):

```
followers   follower count on the user object
posts       the last 10-12 items in the timeline edge
  likes       primary like-count field, falling back to a preview/estimate
              field when the primary is null or negative (accounts can hide
              like counts — that's a real state, not a parsing bug)
  comments    comment-count field
  timestamp   post creation time — take the MAXIMUM across all posts for
              "last active," never the first item (see gotchas §1)
  pinned      a pinned-post flag or list, when present
```

## TikTok — verified end to end

| Stage | Tool | Notes |
|---|---|---|
| Keyword search | a keyword-search tool, flattened/trimmed mode if offered | In flattened mode, results carry the author object (with a real follower count) directly rather than nested under a wrapper object. Confirm which shape you're getting before writing a parser against it. |
| Hashtag search | a hashtag-search tool | Author follower counts on this endpoint can come back zeroed even when the same account's follower count is correct elsewhere — don't trust follower counts sourced from hashtag search. |
| Profile + posts | a per-handle video-listing tool | Returns a batch of recent videos (commonly fewer than Instagram's batch, plan your engagement window accordingly) with both the post stats and the author's real follower count in the same call. |

TikTok fields that matter:

```
likes       primary digg/like-count field
comments    comment-count field
views       play-count field — TikTok's real denominator, see below
timestamp   post creation time, unix seconds
followers   populated on the per-handle listing endpoint; treat any follower
            count sourced from a search endpoint as unreliable until you've
            cross-checked it against the per-handle call
```

**Do not compute engagement as (likes + comments) / followers on TikTok.** The
recommendation feed distributes far past a creator's follower count, so a
follower-based rate can exceed 100% for a real, non-fraudulent account and tells
you nothing. Use `(likes + comments) / views` instead. This is the single most
consequential difference between the two platforms' scoring math — get it backwards
and every ranking on the dashboard will be wrong in a way that looks plausible.

There is no pinned-post flag on TikTok the way there sometimes is on Instagram, but
pinned videos still appear first in a "most recent" sort. Detect the same way: scan
from the front of the list while each timestamp is older than the maximum of
everything after it; once that stops being true you've reached the real chronological
head.

## Adding a platform

1. Confirm the tool exists with a keyword `ToolSearch`.
2. Pull one real account and dump the top-level keys plus one post's keys before
   writing a single line of the parser.
3. Write the field paths into this file first. A wrong field path across sixty
   accounts wastes the whole run's API budget and produces confident, wrong output
   that looks exactly like correct output.
4. Only then run the full batch.
