---
name: creator-partnerships
description: Vet, reach out to, and track creator sponsorships end to end. Encodes a vetting rubric that catches vanity reach, a mandatory prior-contact check, a spend-decision rule, a first-touch outreach template, and a UTM/attribution convention for measuring what a deal actually returned.
---

# Creator Partnerships

A paid-creator channel fails in the same few ways every time: pitching someone
you're already mid-conversation with because nobody checked first, buying reach
that turns out to be a stale account with a big follower count and a dead feed,
and closing a deal with no way to later prove whether it made money. This skill
is the checklist that stops all three.

**Every send stays with a human.** This skill drafts. It never sends, posts, or
DMs on anyone's behalf. Treat that as a hard rule, not a default you can turn off.

## Before any outreach: the prior-contact check (mandatory, no exceptions)

Search your own inbox for the creator's name, handle, and email domain before
writing a single word. Teams that skip this cold-pitch people they were already
mid-thread with, which reads as either careless or slightly unhinged to the
person on the other end. If a thread exists, continue it. Check drafts too, so
two people on your team don't reach out twice.

## The vetting rubric (reach is not the metric)

- **Median views/likes across their last 20-30 posts beats follower count, every
  time.** A big following with a thin recent median is vanity reach, not
  audience. Example of the trap: a creator with hundreds of thousands of
  followers whose actual recent uploads pull a few thousand views is not a
  "big" placement, they're a small one wearing a big number. Always pull the
  distribution, never the headline follower count alone.
- **Audience fit matters more than raw size.** Write down, in one sentence, who
  your buyer actually is (role, company size, seniority, whatever's specific to
  your product), then check whether a creator's *stated* audience or a public
  breakdown of their own actually matches it. A creator whose audience is mostly
  hobbyists is the wrong buy at any reach if your product needs professionals,
  and the reverse is just as true.
- **Default to an integrated placement, not a bumper.** A mention woven into
  the content performs differently from a pre-roll slapped in front of it;
  don't buy the cheaper unit assuming it behaves like the more expensive one.
- **Weight the platform where the creator's engagement actually lives.** The
  same person's post can flop on one platform and land hard on another (a
  LinkedIn post that draws real comment threads versus the same idea posted to
  X that gets a few hundred views is a real, observed pattern, not a hypothetical).
  Check where their engagement genuinely concentrates before assuming their
  best platform is the one with the most followers.

## The spend rule

**Weak audience fit AND weak recent engagement means park it. Don't run a paid
pilot on that combination no matter how attractive the headline reach looks.**
Illustrative example, not a rule to copy literally: if your typical pilot spend
is $X and a rubric check would have told you the real reach is a fraction of
what the follower count implies, that pilot should never have been committed.
Strong fit plus strong engagement justifies a real pilot. Strong on only one
axis means negotiate a smaller unit, or a trade (product access, an affiliate
code) before any cash spend.

## First-touch outreach

Keep it short, specific, and honest about what you're asking for.

1. Open with the person's name.
2. One paragraph: what your product is, in your own fixed one-line description
   (write this once, reuse it verbatim every time so your positioning doesn't
   drift pitch to pitch), plus one clause on why *this* creator specifically —
   reference something real they made, not a category ("your videos about X"
   is weaker than naming the actual piece).
3. Ask for interest and their rates. **Never ask for their view averages** —
   you should already have pulled those yourself before reaching out; asking
   signals you didn't do the homework the rubric above calls for.
4. Hand the creative concept to the creator with a direction, not a spec. They
   know their audience and format better than you do.
5. Sign off with your name and role. Skip the flourishes.

Never say "we'll build it for you", never knock how they normally run
sponsorships, and never counter or anchor on price before you've actually seen
their rates.

## Launch kit (only after a signed agreement)

- **A unique, single-use discount code per creator**, so redemptions trace back
  to the specific deal even if your analytics stack loses the thread elsewhere.
  If your billing platform's coupons aren't visible in your CRM, log the code
  in your own tracking sheet as the source of truth.
- **A consistent UTM convention on every link you hand out**:
  `?utm_source=<platform>&utm_medium=creator&utm_campaign=<creator-slug>&utm_content=<placement>`.
  Fixing `utm_medium=creator` as a constant is what lets you filter every
  creator deal in one query later, across whatever tools you use.
- **Hand over the code and the tagged link only after the contract is signed**,
  not before.
- **Push for a specific, strong call to action** in the caption or description
  itself. Impressions and reach are usually fine; a vague CTA in the actual
  placement is the more common leak.
- **Log the deal in one place**, keyed by the same creator slug you used in the
  UTM tag, so cost-per-acquisition is computable later without archaeology.

## Attribution: how to tell if a deal actually worked

- **Traffic:** filter your analytics tool by `medium = creator` rather than by
  campaign name; campaign values drift and go missing in ways the medium tag
  doesn't.
- **Revenue:** in most CRMs, a contact's own record undercounts, because deal
  or company-level revenue often isn't joined back to the contact who actually
  converted. Check whether revenue in your system lives on the account/company
  object rather than the individual lead, and join accordingly before you
  conclude a deal underperformed.
- **Two traps worth checking for specifically:** an internal team member's own
  email showing up as a "conversion" from a creator campaign (a false positive,
  not a result), and legacy tagging conventions that don't match your current
  `utm_medium` standard sitting uncorrected in old links.

## Before it ships

Run any outreach draft, brief, or creator-facing copy through a voice and
clarity pass before it goes out. A pitch that reads like a form letter performs
worse than one that reads like a specific person wrote it to a specific person.
