#!/usr/bin/env python3
"""Measure real per-video view counts from a YouTube channel's /videos tab.

This is what the vetting rubric in SKILL.md means by "pull the distribution,
not the headline follower count." Subscriber counts are vanity; the median
view count over a real batch of recent uploads is what a sponsorship actually
buys.

Parses ytInitialData out of the page source directly rather than going through
an API, so there's no key to manage. The /videos tab excludes Shorts (they live
on /shorts), and anything <= 90s is dropped as a Shorts safety net regardless.

Usage:
    python3 measure_youtube_medians.py @SomeChannelHandle @AnotherHandle
    # writes measured.json with the full per-video breakdown
"""
import json
import re
import subprocess
import statistics
import sys

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def fetch(url):
    return subprocess.run(
        ["curl", "-sL", "-A", UA, "--compressed", url],
        capture_output=True, text=True, timeout=90).stdout


def extract_initial_data(html):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not m:
        m = re.search(r'ytInitialData"\]\s*=\s*(\{.*?\});', html, re.S)
    if not m:
        return None
    return json.loads(m.group(1))


def walk(node, out):
    """Collect video-ish dicts from either the legacy videoRenderer shape or
    the newer lockupViewModel shape. YouTube has changed this at least once;
    expect it to change again, and check both before assuming a run silently
    returned zero results because the layout moved out from under this parser."""
    if isinstance(node, dict):
        if "videoRenderer" in node:
            out.append(("videoRenderer", node["videoRenderer"]))
        if "lockupViewModel" in node:
            out.append(("lockupViewModel", node["lockupViewModel"]))
        for v in node.values():
            walk(v, out)
    elif isinstance(node, list):
        for v in node:
            walk(v, out)


def text_of(obj):
    if not isinstance(obj, dict):
        return ""
    if "simpleText" in obj:
        return obj["simpleText"]
    if "runs" in obj:
        return "".join(r.get("text", "") for r in obj["runs"])
    if "content" in obj:
        return obj["content"]
    return ""


def parse_views(s):
    s = s.replace(",", "").replace("\xa0", " ")
    m = re.search(r"([\d.]+)\s*([KMB]?)\s*views?", s, re.I)
    if not m:
        return None
    n = float(m.group(1))
    mult = {"": 1, "K": 1_000, "M": 1_000_000, "B": 1_000_000_000}[m.group(2).upper()]
    return int(n * mult)


def parse_duration(s):
    parts = [p for p in s.strip().split(":") if p.isdigit()]
    if not parts:
        return None
    secs = 0
    for p in parts:
        secs = secs * 60 + int(p)
    return secs


def flatten_lockup(vm):
    """lockupViewModel buries the view count and duration inside metadata rows
    and overlays rather than a clean top-level field, so this pulls them out of
    the raw JSON blob with regex instead of a clean field path."""
    title = text_of(vm.get("metadata", {}).get("lockupMetadataViewModel", {}).get("title", {}))
    blob = json.dumps(vm)
    views = parse_views(blob) if "views" in blob else None
    dur = None
    dm = re.search(r'"text":"(\d{1,2}:\d{2}(?::\d{2})?)"', blob)
    if dm:
        dur = parse_duration(dm.group(1))
    age = None
    am = re.search(r'"(\d+ (?:second|minute|hour|day|week|month|year)s? ago)"', blob)
    if am:
        age = am.group(1)
    return title, views, dur, age


def measure(handle, limit=30):
    url = f"https://www.youtube.com/{handle}/videos"
    html = fetch(url)
    data = extract_initial_data(html)
    if data is None:
        return {"handle": handle, "error": "could not extract ytInitialData"}

    subs = None
    sm = re.search(r'"([\d.]+[KMB]?) subscribers"', html)
    if sm:
        subs = sm.group(1)

    found = []
    walk(data, found)
    videos, seen = [], set()
    for kind, node in found:
        if kind == "videoRenderer":
            title = text_of(node.get("title", {}))
            views = parse_views(text_of(node.get("viewCountText", {})))
            dur = parse_duration(text_of(node.get("lengthText", {})))
            age = text_of(node.get("publishedTimeText", {}))
            vid = node.get("videoId")
        else:
            title, views, dur, age = flatten_lockup(node)
            vid = node.get("contentId")
        if not vid or vid in seen or views is None:
            continue
        seen.add(vid)
        videos.append({"id": vid, "title": title[:70], "views": views,
                       "dur_s": dur, "age": age})

    longform = [v for v in videos if (v["dur_s"] or 999) > 90]
    sample = longform[:limit]
    vs = sorted(v["views"] for v in sample)
    if not vs:
        return {"handle": handle, "subs": subs, "error": "no view counts parsed",
                "raw_found": len(videos)}
    return {
        "handle": handle, "subs": subs, "counted": len(sample),
        "median": int(statistics.median(vs)), "mean": int(statistics.mean(vs)),
        "min": vs[0], "max": vs[-1],
        "newest_age": sample[0]["age"] if sample else None,
        "ages": [v["age"] for v in sample[:12]],
        "videos": sample,
    }


if __name__ == "__main__":
    results = []
    for h in sys.argv[1:]:
        r = measure(h)
        results.append(r)
        if "error" in r:
            print(f"\n=== {h}  ERROR: {r['error']}  subs={r.get('subs')}")
            continue
        print(f"\n=== {h}  subs={r['subs']}  counted={r['counted']}")
        print(f"    median={r['median']:,}  mean={r['mean']:,}  "
              f"range={r['min']:,}-{r['max']:,}  newest={r['newest_age']}")
        print(f"    first 12 ages: {r['ages']}")
        for v in r["videos"]:
            print(f"      {v['views']:>9,}  {v['age'] or '?':>14}  {v['title']}")
    with open("measured.json", "w") as f:
        json.dump(results, f, indent=1)
