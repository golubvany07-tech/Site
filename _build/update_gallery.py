#!/usr/bin/env python3
"""
Refresh the homepage/blog "Gallery" photo pool.

  1. Pull new photos from the lab's public Telegram channel (t.me/s/chusov_lab),
     skipping posts that are just introducing a new lab member (those already
     get their own "welcome" news post and shouldn't crowd the Gallery), and
     skipping anything that doesn't read like it's actually about people --
     the Gallery is meant to be photos of people, not reaction schemes,
     sample-vial shots, or "chemistry fact of the week" graphics.
  2. Pull new "event" photos from the site's own news items (site_data.json) --
     conferences, defenses, competitions, outreach courses -- again skipping
     anything about someone joining/leaving the lab, and skipping plain
     "new article published" posts (their cover is a paper/graphic, not an
     event photo).
  3. Cap the pool at MAX_POOL entries, dropping the oldest ones once it grows
     past that, so the Gallery keeps trending toward what's newest as new
     posts appear -- not just growing forever.

Writes _build/gallery_pool.json, which _build/build.py loads in place of a
hardcoded LAB_LIFE_POOL literal to render the Gallery on the homepage and the
blog page.

Meant to run on a schedule via .github/workflows/gallery-refresh.yml (see
that file for the cron), but is safe to run by hand too:

    python3 _build/update_gallery.py

Classification is heuristic (keyword-based) for anything not seen before;
_build/gallery_manual_overrides.json lets a person hand-correct one post by
slug ({"some-post-slug": true} to force-include, false to force-exclude)
without touching this script.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POOL_PATH = os.path.join(ROOT, "_build", "gallery_pool.json")
OVERRIDES_PATH = os.path.join(ROOT, "_build", "gallery_manual_overrides.json")
SITE_DATA_PATH = os.path.join(ROOT, "_build", "site_data.json")
TELEGRAM_DIR = os.path.join(ROOT, "assets", "img", "telegram")

CHANNEL = "chusov_lab"
MAX_POOL = 28
PAGES_TO_FETCH = 3  # newest page + a couple of ?before= pages of backlog
UA = "Mozilla/5.0 (compatible; ChusovLabGalleryBot/1.0; +https://github.com/golubvany07-tech/Site)"

# Telegram post ids already featured as full cards on the blog page's
# "From @chusov_lab" section (see build_news() in build.py) -- skip these so
# the Gallery doesn't duplicate a photo that's already shown elsewhere.
FEATURED_TG_IDS = {"103", "105", "108", "111", "112", "117"}

# A post is "about an event" if its title/text contains one of these --
# conferences, competitions, defenses, outreach, etc. Plain publication
# announcements ("New article published in ...") deliberately don't match,
# since their cover is a paper/graphic rather than an event photo.
EVENT_PATTERNS = [
    r"conference", r"symposium", r"congress", r"championship", r"contest",
    r"competition", r"took part", r"participat", r"defend", r"\bthesis\b",
    r"\btheses\b", r"award", r"ceremony", r"outreach", r"course for",
    r"olympiad", r"workshop", r"seminar", r"forum",
    r"конференц", r"симпозиум",
    r"конгресс", r"чемпионат",
    r"конкурс", r"участ", r"защит",
    r"курс по", r"олимпиад",
    r"семинар",
]
EVENT_RE = re.compile("|".join(EVENT_PATTERNS), re.IGNORECASE)

# A post is "about a person joining/leaving" if it matches one of these --
# excluded from the Gallery even when it also happens to match an event
# keyword above (this list wins).
PERSONNEL_PATTERNS = [
    r"welcome to the lab", r"welcome to our lab",
    r"has left our laboratory", r"has left the lab",
    r"entered our lab as", r"graduated in our lab",
    r"знакомства? с участник",
    r"продолжаем знакомств",
    r"добро пожаловать в лаборатори",
    r"присоединился к (?:нашей )?лаборатори",
    r"покинула? (?:нашу )?лаборатори",
]
PERSONNEL_RE = re.compile("|".join(PERSONNEL_PATTERNS), re.IGNORECASE)

# Telegram photos go straight into the Gallery pool -- unlike a site-news
# cover (picked by hand when the post is written), a raw channel photo could
# just as easily be a reaction scheme, a row of sample vials, or a
# "chemistry fact of the week" graphic with no one in it. Text
# classification can't look at the photo itself, so require the post text to
# actually read like it's ABOUT people -- an event/talk/defense (the same
# signal as is_event_post) or an introduction/interview with a lab member --
# rather than accepting every non-forwarded, non-personnel post that happens
# to have a photo attached.
PEOPLE_HINT_PATTERNS = [
    r"представление участник", r"знакомств\w* с участник",
    r"interview with", r"team member", r"lab member",
    r"интервью с",
]
PEOPLE_HINT_RE = re.compile("|".join(PEOPLE_HINT_PATTERNS), re.IGNORECASE)


def is_likely_people_post(text):
    return bool(is_event_post(text) or PEOPLE_HINT_RE.search(text or ""))


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def is_event_post(text):
    return bool(EVENT_RE.search(text or ""))


def is_personnel_post(text):
    return bool(PERSONNEL_RE.search(text or ""))


def parse_telegram_posts(html):
    """Split the t.me/s/<channel> preview HTML into per-post records."""
    chunks = re.split(
        r'(?=<div class="tgme_widget_message[^"]*"\s+data-post=")', html
    )
    posts = []
    for chunk in chunks:
        m = re.search(r'data-post="%s/(\d+)"' % re.escape(CHANNEL), chunk)
        if not m:
            continue
        post_id = m.group(1)
        date_m = re.search(
            r'tgme_widget_message_date"[^>]*><time datetime="([^"]+)"', chunk
        )
        date = date_m.group(1) if date_m else ""
        text_m = re.search(
            r'tgme_widget_message_text[^"]*"\s+dir="auto">([\s\S]*?)</div>', chunk
        )
        text = re.sub(r"<[^>]+>", "", text_m.group(1)).strip() if text_m else ""
        text = (
            text.replace("&quot;", '"').replace("&amp;", "&").replace("&#39;", "'")
        )
        photo_urls = re.findall(
            r"tgme_widget_message_photo_wrap[^\"]*\"[^>]*background-image:url\('([^']+)'\)",
            chunk,
        )
        is_forwarded = "tgme_widget_message_forwarded_from" in chunk
        posts.append(
            {
                "id": post_id,
                "date": date,
                "text": text,
                "photo_urls": photo_urls,
                "forwarded": is_forwarded,
            }
        )
    return posts


def fetch_channel_posts(pages=PAGES_TO_FETCH):
    """Fetch the newest page plus a couple of older ?before= pages, so a
    fresh pool has some backlog to seed from; routine runs mostly see posts
    already marked seen and just skip them."""
    all_posts = []
    before = None
    for _ in range(pages):
        url = f"https://t.me/s/{CHANNEL}" + (f"?before={before}" if before else "")
        try:
            html = fetch(url).decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as e:
            print(f"WARN: could not fetch {url}: {e}", file=sys.stderr)
            break
        posts = parse_telegram_posts(html)
        if not posts:
            break
        all_posts.extend(posts)
        oldest_id = min(int(p["id"]) for p in posts)
        if before is not None and oldest_id >= int(before):
            break
        before = oldest_id
        time.sleep(1)
    by_id = {p["id"]: p for p in all_posts}
    return [by_id[k] for k in sorted(by_id, key=int)]


def optimize_and_save(raw_bytes, dest_path, max_dim=1400, quality=82):
    try:
        import io

        from PIL import Image

        im = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        w, h = im.size
        scale = min(1.0, max_dim / max(w, h))
        if scale < 1.0:
            im = im.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
        im.save(dest_path, "JPEG", quality=quality, optimize=True)
        return True
    except Exception as e:
        print(f"WARN: could not optimize image for {dest_path}: {e}", file=sys.stderr)
        return False


def ingest_telegram(pool, seen_tg_ids, overrides):
    os.makedirs(TELEGRAM_DIR, exist_ok=True)
    try:
        posts = fetch_channel_posts()
    except Exception as e:
        print(f"WARN: Telegram fetch failed entirely: {e}", file=sys.stderr)
        return 0
    added = 0
    for p in posts:
        if p["id"] in seen_tg_ids or p["id"] in FEATURED_TG_IDS:
            continue
        seen_tg_ids.add(p["id"])  # mark processed either way, match or not
        if p["forwarded"] or not p["photo_urls"] or is_personnel_post(p["text"]):
            continue
        eligible = overrides.get(f"tg:{p['id']}")
        if eligible is None:
            eligible = is_likely_people_post(p["text"])
        if not eligible:
            continue
        photo_url = p["photo_urls"][0]
        try:
            raw = fetch(photo_url)
        except (urllib.error.URLError, OSError) as e:
            print(f"WARN: could not download {photo_url}: {e}", file=sys.stderr)
            continue
        fname = f"tg-auto-{p['id']}.jpg"
        dest = os.path.join(TELEGRAM_DIR, fname)
        if not optimize_and_save(raw, dest):
            continue
        alt = p["text"][:110].strip()
        alt = (alt + "…") if len(p["text"]) > 110 else alt
        alt = alt or "Photo from our Telegram channel"
        pool.append(
            {
                "img": f"img/telegram/{fname}",
                "anchor": "",
                "alt": alt,
                "cls": "",
                "source": f"telegram:{p['id']}",
            }
        )
        added += 1
    return added


def ingest_site_news(pool, seen_slugs, overrides):
    data = load_json(SITE_DATA_PATH, {"news": []})
    added = 0
    for n in data.get("news", []):
        slug = n.get("slug")
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)
        cover = n.get("cover")
        if not cover:
            continue
        title_and_body = f"{n.get('title', '')} {n.get('body_md', '')}"
        eligible = overrides.get(slug)
        if eligible is None:
            eligible = is_event_post(title_and_body) and not is_personnel_post(
                title_and_body
            )
        if not eligible:
            continue
        pool.append(
            {
                "img": cover,
                "anchor": slug,
                "alt": n.get("title", ""),
                "cls": "",
                "source": f"news:{slug}",
            }
        )
        added += 1
    return added


def main():
    state = load_json(
        POOL_PATH, {"items": [], "seen_telegram_ids": [], "seen_news_slugs": []}
    )
    pool = state.get("items", [])
    seen_tg = set(state.get("seen_telegram_ids", []))
    seen_slugs = set(state.get("seen_news_slugs", []))
    overrides = load_json(OVERRIDES_PATH, {})

    added_tg = ingest_telegram(pool, seen_tg, overrides)
    added_news = ingest_site_news(pool, seen_slugs, overrides)

    # Keep the pool from growing forever -- drop the oldest entries once
    # we're over the cap, so the Gallery keeps trending toward what's newest.
    overflow = len(pool) - MAX_POOL
    if overflow > 0:
        pool = pool[overflow:]

    state["items"] = pool
    state["seen_telegram_ids"] = sorted(seen_tg, key=int)
    state["seen_news_slugs"] = sorted(seen_slugs)
    save_json(POOL_PATH, state)

    print(
        f"Gallery pool refreshed: +{added_tg} from Telegram, +{added_news} from "
        f"site news, total now {len(pool)}"
    )


if __name__ == "__main__":
    main()
