#!/usr/bin/env python3
"""
Stage 1: merge discovery results into one deduped candidate pool.

Scans a directory of cached API responses (large responses that spilled to disk
because they exceeded the model's context window) plus an optional file of
results that came back small enough to stay inline, and writes a deduped pool
of candidate handles.

    python3 collect_pool.py --cache-dir DIR --out output/raw-pool.json \\
        --platform instagram [--inline scratch/inline-results.json]

--inline expects: {"<query label>": [{"handle": ..., "url": ..., "follower_count": ...,
                                        "bio": ...}, ...], ...}

Cache files are matched loosely by filename substring so this works across
whatever a given MCP connector happens to name its tool-result dumps; adjust
the MATCHERS dict below if a new connector uses different tool names.
"""
import argparse
import collections
import glob
import json
import os
import sys

MATCHERS = {
    "profile_search": ["search_profiles", "search_users"],
    "hashtag": ["search_hashtag"],
    "native": ["reels_search", "search_keyword", "instagram_search", "tiktok_search"],
}


def load_json(path):
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def upsert(pool, handle, url, followers, bio, source):
    h = (handle or "").strip().lstrip("@")
    if not h:
        return
    record = pool.setdefault(h, {
        "handle": h,
        "profile_url": url,
        "follower_count": followers,
        "bio": bio,
        "sources": [],
    })
    if not record["bio"] and bio:
        record["bio"] = bio
    if record["follower_count"] is None and followers is not None:
        record["follower_count"] = followers
    if source not in record["sources"]:
        record["sources"].append(source)


def find_cache_files(cache_dir, kind):
    hits = []
    for pattern in MATCHERS[kind]:
        hits.extend(glob.glob(os.path.join(cache_dir, f"*{pattern}*")))
    return sorted(set(hits))


def harvest_instagram_style(payload):
    """Yields (handle, url, followers, bio) tuples from a variety of shapes
    the Instagram-adjacent endpoints tend to return."""
    if not payload:
        return
    for key in ("profiles", "users"):
        for row in payload.get(key, []) or []:
            yield (
                row.get("username") or row.get("handle"),
                row.get("url"),
                row.get("follower_count"),
                row.get("biography") or row.get("bio"),
            )
    for post in payload.get("posts", []) or []:
        owner = post.get("owner") or {}
        yield (owner.get("username"), None, owner.get("follower_count"), None)
    for reel in payload.get("reels", []) or []:
        owner = reel.get("owner") or {}
        yield (owner.get("username"), None, owner.get("follower_count"), None)


def harvest_tiktok_style(payload):
    if not payload:
        return
    for item in payload.get("search_item_list", []) or payload.get("aweme_list", []) or []:
        author = item.get("author") or {}
        yield (
            author.get("unique_id"),
            None,
            author.get("follower_count"),
            author.get("signature"),
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--platform", choices=["instagram", "tiktok"], default="instagram")
    ap.add_argument("--inline")
    args = ap.parse_args()

    pool = collections.OrderedDict()
    harvest = harvest_instagram_style if args.platform == "instagram" else harvest_tiktok_style

    if args.inline and os.path.exists(args.inline):
        for label, rows in (load_json(args.inline) or {}).items():
            for row in rows:
                upsert(pool, row.get("handle") or row.get("username"), row.get("url"),
                       row.get("follower_count"), row.get("bio") or row.get("biography"),
                       f"profile_search:{label}")

    for kind in ("profile_search", "hashtag", "native"):
        for path in find_cache_files(args.cache_dir, kind):
            payload = load_json(path)
            for handle, url, followers, bio in harvest(payload):
                upsert(pool, handle, url, followers, bio, f"{kind}:{os.path.basename(path)[:24]}")

    records = list(pool.values())
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)

    by_method = collections.Counter()
    for r in records:
        for s in r["sources"]:
            by_method[s.split(":")[0]] += 1
    multi_method = [r["handle"] for r in records
                     if len({s.split(":")[0] for s in r["sources"]}) > 1]

    print(f"unique candidates: {len(records)}")
    for method, count in by_method.items():
        print(f"  via {method:<16}: {count}")
    print(f"  found by 2+ methods: {len(multi_method)}")
    print(f"  missing bio (native search doesn't return one): "
          f"{len([r for r in records if not r['bio']])}")
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    sys.exit(main())
