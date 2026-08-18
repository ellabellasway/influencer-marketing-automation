#!/usr/bin/env python3
"""
Stage 3: attach public contact paths to each ranked creator.

    python3 contacts.py --enriched output/enriched.json \\
        [--linkinbio scratch/linkinbio.json] [--top 40]

Bio emails are pulled from the text already sitting in enriched.json. Link-in-bio
pages (Linktree, Komi, and similar) come back inline from the API rather than to
disk, so they can't be read off a cache directory the way profile responses can.
Resolve those separately and hand the relevant fields to this script:

{
  "<handle>": {"service": "linktree", "resolved": true, "email": "a@b.com",
               "link_count": 14, "website": "https://...",
               "business_contact": "https://wa.me/...",
               "business_contact_label": "WhatsApp - partnerships"}
}

Only "service" is required; everything else may be null. Writes a "contact"
object back into enriched.json in place.
"""
import argparse
import collections
import glob
import json
import os
import re
import sys

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Talent-management domains: the right contact for a paid placement, but not
# the creator personally. Extend this list for your own space as you find more.
MANAGEMENT_DOMAINS = {
    "wme.com": "WME",
    "caa.com": "CAA",
    "uta.com": "UTA",
    "viralnation.com": "Viral Nation",
}
SOCIAL_HOSTS = ("instagram.com", "tiktok.com", "youtube.com", "facebook.com",
                 "twitter.com", "x.com", "threads.net")
LINK_HUB_HOSTS = ("linktr.ee", "komi.io", "pillar.io", "linkbio.co", "linkme.bio",
                   "bio.site", "beacons.ai")


def own_site_from_cache(cache_dir):
    """A creator's own external_url is a valid contact path when nothing else
    exists; pull it from cached profile responses rather than re-fetching."""
    sites = {}
    if not cache_dir:
        return sites
    for path in glob.glob(os.path.join(cache_dir, "*profile*")):
        try:
            payload = json.load(open(path))
        except Exception:
            continue
        user = (payload.get("data") or {}).get("user") or {}
        handle = user.get("username")
        if not handle:
            continue
        candidates = [user.get("external_url")]
        candidates += [b.get("url") for b in (user.get("bio_links") or [])]
        for url in candidates:
            if not url:
                continue
            low = url.lower()
            if any(h in low for h in LINK_HUB_HOSTS + SOCIAL_HOSTS):
                continue
            sites.setdefault(handle, url)
            break
    return sites


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enriched", required=True)
    ap.add_argument("--linkinbio")
    ap.add_argument("--cache-dir")
    ap.add_argument("--top", type=int, default=0, help="0 = every creator in the file")
    args = ap.parse_args()

    with open(args.enriched) as fh:
        rows = json.load(fh)

    linkhub = {}
    if args.linkinbio and os.path.exists(args.linkinbio):
        with open(args.linkinbio) as fh:
            linkhub = json.load(fh)

    own_sites = own_site_from_cache(args.cache_dir)
    scope = {r["handle"] for r in (rows[:args.top] if args.top else rows)}

    for r in rows:
        if r["handle"] not in scope:
            r["contact"] = None
            continue

        hub = linkhub.get(r["handle"], {})
        emails = list(dict.fromkeys(
            EMAIL.findall(r.get("bio") or "") + ([hub["email"]] if hub.get("email") else [])))
        website = hub.get("website") or own_sites.get(r["handle"])
        managed_by = [e for e in emails if e.split("@")[-1].lower() in MANAGEMENT_DOMAINS]

        channels = []
        if emails:
            channels.append("email")
        if hub.get("business_contact"):
            channels.append("business")
        if website:
            channels.append("website")
        if hub.get("service"):
            channels.append("link-hub")

        r["contact"] = {
            "emails": emails,
            "management_emails": managed_by,
            "management_names": [MANAGEMENT_DOMAINS[e.split("@")[-1].lower()] for e in managed_by],
            "business_contact": hub.get("business_contact"),
            "business_contact_label": hub.get("business_contact_label"),
            "website": website,
            "link_hub": ({"service": hub["service"], "resolved": bool(hub.get("resolved")),
                          "link_count": hub.get("link_count")} if hub.get("service") else None),
            "channels": channels,
            "best": ("email" if emails else "business" if hub.get("business_contact")
                     else "website" if website else "link-hub" if hub.get("service") else "none"),
        }

    with open(args.enriched, "w") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)

    scoped = [r for r in rows if r["contact"]]
    tally = collections.Counter(r["contact"]["best"] for r in scoped)
    managed = [r for r in scoped if r["contact"]["management_emails"]]
    none_found = [r["handle"] for r in scoped if r["contact"]["best"] == "none"]

    print(f"in scope        : {len(scoped)} of {len(rows)}")
    print(f"best path       : {dict(tally)}")
    print(f"direct email    : {len([r for r in scoped if r['contact']['emails']])}")
    print(f"management-owned: {len(managed)} -> "
          f"{[(r['handle'], r['contact']['management_names'][0]) for r in managed]}")
    print(f"no contact path : {len(none_found)} -> {none_found}")
    print(f"\nupdated {args.enriched}")


if __name__ == "__main__":
    sys.exit(main())
