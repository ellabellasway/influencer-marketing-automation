#!/usr/bin/env python3
"""
Stage 2: compute engagement metrics from cached profile+post responses.

    python3 enrich.py --cache-dir DIR --pool output/raw-pool.json \\
        --out output/enriched.json --platform instagram \\
        [--min-followers 5000] [--max-followers 500000] [--max-age-days 60]

Never calls the API itself; only parses what's already sitting in the cache
directory. Three rules matter here, see reference/gotchas.md for why:

  1. "last active" = the MAXIMUM post timestamp in the sample, not the first
     item in the list (pinned posts break chronological order)
  2. Instagram engagement = (likes + comments) / followers.
     TikTok engagement = (likes + comments) / views. Do not swap these.
  3. compute both the mean and the median; a small sample is routinely
     dominated by one outlier post
"""
import argparse
import collections
import datetime
import glob
import json
import os
import sys
import time


def median(values):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[mid])
    return (ordered[mid - 1] + ordered[mid]) / 2


def likes_from_instagram_node(node):
    primary = (node.get("edge_liked_by") or {}).get("count")
    fallback = (node.get("edge_media_preview_like") or {}).get("count")
    if isinstance(primary, int) and primary >= 0:
        return primary, False
    if isinstance(fallback, int) and fallback >= 0:
        return fallback, True
    return None, True


def pinned_count(timestamps):
    """Videos/posts scanned from the head; count how many sit ahead of where
    they'd chronologically belong (see gotchas.md #1)."""
    count = 0
    for i in range(len(timestamps) - 1):
        if timestamps[i] < max(timestamps[i + 1:]):
            count += 1
        else:
            break
    return count


def load_instagram_profile(path):
    try:
        payload = json.load(open(path))
    except Exception:
        return None
    user = (payload.get("data") or {}).get("user")
    if not user or not user.get("username"):
        return None
    edges = (user.get("edge_owner_to_timeline_media") or {}).get("edges") or []
    if not edges:
        return None

    likes, comments, stamps, hidden = [], [], [], 0
    for edge in edges:
        node = edge.get("node") or {}
        val, used_fallback = likes_from_instagram_node(node)
        if val is not None:
            likes.append(val)
            if used_fallback:
                hidden += 1
        c = (node.get("edge_media_to_comment") or {}).get("count")
        if isinstance(c, int) and c >= 0:
            comments.append(c)
        if node.get("taken_at_timestamp"):
            stamps.append(node["taken_at_timestamp"])

    return {
        "handle": user["username"],
        "bio": user.get("biography"),
        "followers": (user.get("edge_followed_by") or {}).get("count"),
        "likes": likes, "comments": comments, "views": [],
        "stamps": stamps, "hidden_likes": hidden,
        "posts_analyzed": len(edges),
    }


def load_tiktok_profile(path):
    try:
        payload = json.load(open(path))
    except Exception:
        return None
    items = payload.get("aweme_list") or []
    if not items:
        return None
    author = items[0].get("author") or {}
    handle = author.get("unique_id")
    if not handle:
        return None

    likes, comments, views, stamps = [], [], [], []
    for item in items:
        stats = item.get("statistics") or {}
        if isinstance(stats.get("digg_count"), int):
            likes.append(stats["digg_count"])
        if isinstance(stats.get("comment_count"), int):
            comments.append(stats["comment_count"])
        if isinstance(stats.get("play_count"), int) and stats["play_count"] > 0:
            views.append(stats["play_count"])
        if item.get("create_time"):
            stamps.append(item["create_time"])

    return {
        "handle": handle,
        "bio": author.get("signature"),
        "followers": author.get("follower_count"),
        "likes": likes, "comments": comments, "views": views,
        "stamps": stamps, "hidden_likes": 0,
        "posts_analyzed": len(items),
    }


def newest_per_handle(cache_dir, loader, filename_hint):
    best = {}
    for path in glob.glob(os.path.join(cache_dir, f"*{filename_hint}*")):
        parsed = loader(path)
        if not parsed:
            continue
        mtime = os.path.getmtime(path)
        h = parsed["handle"]
        if h not in best or mtime > best[h][0]:
            best[h] = (mtime, parsed)
    return {h: v[1] for h, v in best.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache-dir", required=True)
    ap.add_argument("--pool", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--platform", choices=["instagram", "tiktok"], default="instagram")
    ap.add_argument("--min-followers", type=int, default=0)
    ap.add_argument("--max-followers", type=int, default=10**12)
    ap.add_argument("--max-age-days", type=int, default=60)
    ap.add_argument("--limit", type=int, default=0, help="0 = keep everyone")
    args = ap.parse_args()

    now = time.time()
    cutoff = now - args.max_age_days * 86400

    with open(args.pool) as fh:
        pool = {r["handle"]: r for r in json.load(fh)}

    if args.platform == "instagram":
        profiles = newest_per_handle(args.cache_dir, load_instagram_profile, "instagram_profile")
    else:
        profiles = newest_per_handle(args.cache_dir, load_tiktok_profile, "profile_videos")

    rows, no_data, stale, out_of_range = [], [], [], []

    for handle, base in pool.items():
        p = profiles.get(handle)
        if not p:
            no_data.append(handle)
            continue

        followers = p["followers"] or base.get("follower_count")
        if followers is None:
            no_data.append(handle)
            continue
        if not (args.min_followers <= followers <= args.max_followers):
            out_of_range.append((handle, followers))
            continue

        avg_likes = round(sum(p["likes"]) / len(p["likes"]), 1) if p["likes"] else None
        avg_comments = round(sum(p["comments"]) / len(p["comments"]), 1) if p["comments"] else None
        med_likes, med_comments = median(p["likes"]), median(p["comments"])
        last_ts = max(p["stamps"]) if p["stamps"] else None
        pinned = pinned_count(p["stamps"]) if p["stamps"] else 0

        if args.platform == "tiktok" and p["views"]:
            per_post = [(l + c) / v * 100 for l, c, v in zip(p["likes"], p["comments"], p["views"]) if v]
            engagement = round(sum(per_post) / len(per_post), 3) if per_post else None
            engagement_median = round(median(per_post), 3) if per_post else None
        elif avg_likes is not None and avg_comments is not None and followers:
            engagement = round((avg_likes + avg_comments) / followers * 100, 3)
            engagement_median = (round((med_likes + med_comments) / followers * 100, 3)
                                 if med_likes is not None and med_comments is not None else None)
        else:
            engagement, engagement_median = None, None

        skew = round(max(p["likes"]) / med_likes, 1) if p["likes"] and med_likes else None

        record = {
            "handle": handle,
            "profile_url": base.get("profile_url") or f"https://www.{args.platform}.com/@{handle}",
            "bio": p["bio"] or base.get("bio"),
            "sources": base.get("sources", []),
            "follower_count": followers,
            "avg_likes": avg_likes, "avg_comments": avg_comments,
            "engagement_rate": engagement,
            "median_likes": med_likes, "median_comments": med_comments,
            "engagement_rate_median": engagement_median,
            "top_post_vs_median": skew,
            "last_post_date": (datetime.datetime.fromtimestamp(last_ts, datetime.timezone.utc)
                                .strftime("%Y-%m-%d") if last_ts else None),
            "days_since_last_post": int((now - last_ts) // 86400) if last_ts else None,
            "posts_analyzed": p["posts_analyzed"],
            "pinned_in_sample": pinned,
            "likes_hidden_posts": p["hidden_likes"],
        }

        if last_ts is None or last_ts < cutoff:
            stale.append((handle, record["days_since_last_post"]))
            continue
        rows.append(record)

    rows.sort(key=lambda r: (r["engagement_rate"] is None, -(r["engagement_rate"] or 0)))
    truncated = 0
    if args.limit and len(rows) > args.limit:
        truncated = len(rows) - args.limit
        rows = rows[:args.limit]

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(rows, fh, indent=2, ensure_ascii=False)

    meta = {
        "platform": args.platform,
        "sourced": len(pool), "kept": len(rows),
        "stale": [list(x) for x in sorted(stale, key=lambda x: -(x[1] or 0))],
        "out_of_range": [list(x) for x in out_of_range],
        "unavailable": no_data,
        "truncated_by_limit": truncated,
        "max_age_days": args.max_age_days,
        "follower_range": [args.min_followers,
                            None if args.max_followers >= 10**12 else args.max_followers],
    }
    meta_path = os.path.join(os.path.dirname(os.path.abspath(args.out)), "run-meta.json")
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)

    print(f"sourced          : {len(pool)}")
    print(f"outside range    : {len(out_of_range)}")
    print(f"stale            : {len(stale)}")
    print(f"no data          : {len(no_data)} -> {no_data}")
    print(f"kept             : {len(rows)}")
    skewed = [r for r in rows if (r["top_post_vs_median"] or 0) >= 5]
    print(f"viral-skewed (top post >= 5x median): {len(skewed)}")
    print(f"\nwrote {args.out} and {meta_path}")


if __name__ == "__main__":
    sys.exit(main())
