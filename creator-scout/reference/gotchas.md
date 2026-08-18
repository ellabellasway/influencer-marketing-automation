# Data-quality landmines

Every item here showed up in a real run and produced (or nearly produced) a
confidently wrong answer. The scripts already handle each of these; this file is
here so a future edit doesn't "simplify" the handling back out.

## 1. Pinned posts break chronological order

A creator's grid or feed can surface up to a few pinned posts before anything else,
and pinned posts are frequently old. Using the first item in a post list as "most
recent" will misjudge which accounts are actually still active — an account posting
weekly gets flagged stale because its pin is fourteen months old, while a genuinely
dead account with no pins reads as fresher than it is.

**Recency has to be the maximum timestamp across the whole sample, never the first
item.** This is the single most dangerous bug in the pipeline, because the wrong
answer looks exactly as plausible as the right one until you check by hand.

## 2. Missing like counts are not zero

Like counts can come back null, or come back as a sentinel negative value, or the
post can be flagged as having likes hidden entirely. These are three different
states and treating them the same corrupts an average:

1. take the primary like-count field if it's a non-negative integer
2. otherwise take a fallback/preview count field, if the API offers one and it's
   non-negative
3. otherwise the value is genuinely unavailable — record it as unavailable, not zero

Watch the comparison logic here specifically: in most languages `null < 0`
evaluates true, so a naive "drop anything negative" filter will silently also drop
every null. Test the two conditions separately.

A creator hiding likes on every sampled post should show an engagement rate of
"not measurable," never "0%." Zero implies you measured and it was bad; a dash
means you couldn't measure it at all. Confusing the two makes a fine account look
dead.

## 3. A ten-to-twelve-post mean is dominated by one outlier

This isn't an edge case, it's closer to a coin flip. In one real batch, roughly
half the accounts sampled had a single post at five times or more their own median.
Illustrative shape of the problem:

| pattern | mean engagement | median engagement | top post vs. median |
|---|---|---|---|
| one viral post carrying an otherwise-quiet account | 12% | 0.3% | ~40x |
| one viral post, moderately active account | 9% | 1.1% | ~8x |
| genuinely consistent account | 3.1% | 2.9% | ~1.1x |

Compute both numbers, always. Lead with whichever the user asked for, but let the
other one ride along in the same record and surface it in the dashboard's toggle.
Reporting only the mean will get someone pitched to a creator whose typical post
does nothing.

Rough sanity check: organic engagement on most platforms clusters in the low
single digits. A number above roughly 15% is a viral spike, a very small account,
or a bug in the parser — go look at the raw post list before trusting it.

## 4. Some accounts break the transport, deterministically

A handful of profiles will fail on the exact same call with a parse error, every
time, regardless of retry count or concurrency. This is not flakiness. Confirm it
isn't by retrying once; if it fails identically a second time, it's the account,
not the network.

Fallback ladder:

1. retry once, to rule out genuine transience
2. try the lighter-weight "basic profile by ID" call if the connector offers one —
   smaller payload, survives some of what breaks the full profile call, but
   usually returns bio and follower count with no posts
3. if both fail, record the handle as unavailable and say so in the output

Never let a failed account vanish silently. A creator missing from the final
dashboard is indistinguishable from a creator who was never found, and only one
of those is true.

## 5. TikTok's engagement math is not Instagram's

Covered in `platforms.md`, repeated here because it's the mistake most likely to
slip through a code review: TikTok's For You page distributes far past a creator's
follower count, so `(likes + comments) / followers` can read over 100% for a
completely legitimate account. Use `(likes + comments) / views`. If you see a
follower-based rate above roughly 20%, that's the tell that the wrong denominator
snuck in somewhere.

## 6. Search results routinely include off-topic and brand accounts

Bio and caption search match on text, not intent. A search for a niche term will
return brand accounts, agencies selling services in that space rather than
creators making content about it, and accounts that mentioned the term exactly
once in an unrelated post. Expect roughly a fifth of a raw pool to be noise of
this kind.

Don't filter it out before showing the user. Whether an agency account or a
borderline-relevant brand counts as "in scope" is a judgment call that belongs to
whoever is going to do the outreach, not to the script.

## 7. Reels/video search results often don't echo the query back

If a search endpoint returns results without labeling which query produced them,
and you're running several queries in the same pass, label results by call order
and then verify: check that a distinctive word from each query actually appears
in that query's own result set before trusting the mapping. Getting this wrong
means creators end up attributed to the wrong search term, which quietly corrupts
the "found by two methods" signal that's supposed to be the strongest part of the
ranking.

## 8. Large API responses will exceed the context window, and that's fine

A full profile-plus-posts response is routinely several hundred kilobytes. Let it
spill to disk rather than fighting it — that's what `--cache-dir` is for. Parse
the cached files with the scripts, never by reading the raw response back into a
model's context.

## 9. Link-in-bio pages hide contacts the bio itself doesn't have

Resolving a Linktree- or Komi-style page can surface an email that appears nowhere
in the visible bio, sometimes sitting in a description field rather than the
page's dedicated email field. Regex the whole payload, not just the field that's
supposed to hold an email.

## 10. Management-domain emails are not personal emails

An address on a known talent-management or agency domain is the *correct* contact
for a paid placement, but it is not the creator, and the pitch you'd write to a
manager differs from a cold note to an individual creator. Tag these separately;
never present one as the other.
