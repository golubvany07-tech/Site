#!/usr/bin/env python3
"""Static site generator for the Chusov Group site (chemcatgroup.com redesign).

Usage:  python3 _build/build.py
Reads _build/site_data.json, writes *.html into the project root.
Wording policy: all visible copy is verbatim from the original site wherever it existed.
"""
import html
import json
import os
import re
from datetime import datetime
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = json.load(open(os.path.join(ROOT, "_build", "site_data.json"), encoding="utf-8"))


def _load(name, default):
    path = os.path.join(ROOT, "_build", name)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else default


CSS_VER = str(int(os.path.getmtime(os.path.join(ROOT, "css", "style.css"))))  # cache-bust CSS on change
PUB_META = _load("pub_meta.json", {})          # authors + citation counts per publication
PEOPLE_PUBS = _load("people_pubs.json", {})    # per-person publication lists + stats
PROFILES = _load("profiles.json", {})          # verified external profiles per person
COLAB = _load("colab_meta.json", {})           # colab.ws metrics/ids/interests (layered as supplement)
COLAB_PEOPLE = COLAB.get("people", {})
COLAB_ARTS = COLAB.get("articles", {})
PUB_BY_N = {p["n"]: p for p in DATA["pubs"]}
N_PUBS = len(DATA["pubs"])

E = html.escape

# Where the site is actually served. Defaults to the GitHub Pages project URL;
# override for the custom domain:  SITE_URL=https://www.chemcatgroup.com python3 _build/build.py
SITE_URL = os.environ.get("SITE_URL", "https://fkliuev.github.io/chemcatgroup").rstrip("/")
_host = urlparse(SITE_URL).hostname or ""
BASE_PATH = (urlparse(SITE_URL).path or "").rstrip("/") + "/"  # "/chemcatgroup/" or "/"
IS_GH_PAGES = _host.endswith("github.io")                      # no CNAME on github.io

# Privacy-friendly analytics snippet (no cookies). Paste a GoatCounter/Plausible
# <script>…</script> here to enable it site-wide; empty string = analytics disabled.
ANALYTICS = ""


def meta_month():
    iso = PEOPLE_PUBS.get("_fetched") or PUB_META.get("_fetched") or ""
    try:
        return datetime.fromisoformat(iso).strftime("%B %Y")
    except Exception:
        return ""


def _bare_doi(url):
    if not url:
        return None
    m = re.search(r"(10\.\d{4,9}/[^\s?#]+?)(?:\?|#|$)", url)
    return m.group(1).rstrip("/.").lower() if m else None


def cited_of(n):
    rec = PUB_META.get(str(n)) or {}
    c = rec.get("cited_by")
    if c is None:  # supplement: fall back to colab.ws citation count where Crossref has none
        doi = _bare_doi((PUB_BY_N.get(n) or {}).get("doi"))
        if doi:
            c = (COLAB_ARTS.get(doi) or {}).get("citations")
    return c


# alumni without personal pages on the old site -> slugs used for their new pages
ALUM_SLUG = {
    "Alexei Moskovets": "alexei-moskovets",
    "Niyaz Yagafarov": "niyaz-yagafarov",
    "Pavel Kolesnikov": "pavel-kolesnikov",
    "Vasilii Fastovskiy": "vasilii-fastovskiy",
    "Mariya Makarova": "mariya-makarova",
    "Karim Muratov": "karim-muratov",
    "Ekaterina Kuchuk": "ekaterina-kuchuk",
    "Sofiya Runikhina": "sofiya-runikhina",
    "Alexey Tsygankov": "alexey-tsygankov",
    "Vladimir Ostrovskii": "vladimir-ostrovskii",
    "Max Shandybo": "max-shandybo",
    "Natalia Lebedeva": "natalya-lebedeva",
}

PROFILE_LABEL = {
    "scholar": "Google Scholar",
    "orcid": "ORCID",
    "istina": "ИСТИНА",
    "scopus": "Scopus",
    "researchgate": "ResearchGate",
    "other": "Profile",
}

SOCIALS = [
    ("Twitter / X", "https://x.com/chusovgroup"),
    ("Telegram", "https://t.me/chusov_lab"),
    ("Facebook", "https://www.facebook.com/Chusovgroup-443516203118101/"),
    ("Instagram", "https://www.instagram.com/chusovgroup/"),
]

NAV = [
    ("research.html", "Research"),
    ("publications.html", "Publications"),
    ("people.html", "Personnel"),
    ("alumni.html", "Alumni"),
    ("news.html", "Blog"),
    ("media.html", "Media"),
]


# ---------------------------------------------------------------- helpers

def typeset(s):
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def ref_html(p):
    """Journal reference with italic journal name and bold year."""
    ref = typeset(p["journal_ref"])
    m = re.match(r"^(.*?)[,.]?\s*((?:19|20)\d{2})(.*)$", ref)
    if m:
        j, y, rest = m.groups()
        out = f"<em>{E(j.strip().rstrip(',.'))}.</em> <strong>{E(y)}</strong>{E(rest)}"
    else:
        out = E(ref)
    if p.get("impact"):
        out += f' <span class="if">(IF {E(p["impact"])})</span>'
    return out


def md_inline(s):
    parts = []
    pos = 0
    pattern = re.compile(r"\[([^\]]+)\]\((\S+?)\)|(?<![(\[])(https?://[^\s)\]<>]+)")
    for m in pattern.finditer(s):
        parts.append(E(s[pos:m.start()]))
        if m.group(3):
            u = m.group(3).rstrip(".,;")
            tail = m.group(3)[len(u):]
            parts.append(f'<a href="{E(u)}" rel="noopener">{E(u)}</a>{E(tail)}')
        else:
            txt, url = m.group(1), m.group(2)
            if txt.startswith("#"):
                parts.append(E(txt))
            else:
                parts.append(f'<a href="{E(url)}" rel="noopener">{E(txt)}</a>')
        pos = m.end()
    parts.append(E(s[pos:]))
    return "".join(parts)


def md_block(md, alt_ctx=""):
    fallback_alt = f"Illustration: {alt_ctx}" if alt_ctx else ""
    out = []
    for para in re.split(r"\n\s*\n", md.strip()):
        para = para.strip()
        if not para:
            continue
        img = re.match(r"^!\[([^\]]*)\]\((\S+)\)$", para)
        if img:
            out.append(f'<figure><img src="assets/{E(img.group(2))}" alt="{E(img.group(1) or fallback_alt)}" loading="lazy"></figure>')
            continue
        if para.startswith("### "):
            out.append(f"<h4>{md_inline(para[4:])}</h4>")
            continue
        if all(l.lstrip().startswith("- ") for l in para.splitlines()):
            items = "".join(f"<li>{md_inline(l.lstrip()[2:])}</li>" for l in para.splitlines())
            out.append(f"<ul>{items}</ul>")
            continue
        chunks = re.split(r"!\[([^\]]*)\]\((\S+?)\)", para)
        if len(chunks) > 1:
            i = 0
            while i < len(chunks):
                if i % 3 == 0:
                    if chunks[i].strip():
                        out.append(f"<p>{md_inline(chunks[i].strip())}</p>")
                    i += 1
                else:
                    out.append(f'<figure><img src="assets/{E(chunks[i + 1])}" alt="{E(chunks[i] or fallback_alt)}" loading="lazy"></figure>')
                    i += 2
            continue
        out.append(f"<p>{md_inline(para)}</p>")
    return "\n".join(out)


def fmt_date(iso):
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return d.strftime("%d %b %Y").lstrip("0")
    except Exception:
        return iso or ""


def fields_html(p, keys=("education", "email", "interests", "hobby")):
    """Person details in the same field style the old member pages used."""
    label = {"education": "Education", "email": "Email",
             "interests": "Scientific interests", "hobby": "Hobby"}
    rows = []
    for k in keys:
        v = p.get(k)
        if not v:
            continue
        if k == "email":
            v = f'<a href="mailto:{E(v)}">{E(v)}</a>'
        else:
            v = E(v)
        rows.append(f"<p><b>{label[k]}:</b> {v}</p>")
    return f'<div class="fields">{"".join(rows)}</div>' if rows else ""


def shell(*, title, desc, active, body, page="index.html", prefix="", og_image=None, og_type="website"):
    # prefix = relative path back to site root ("" for root pages, "../" for pages in a subfolder)
    og_abs = f"{SITE_URL}/" + (og_image or "assets/img/misc/hero-sketch.jpg")
    nav_items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        nav_items.append(f'<a href="{prefix}{href}"{cur}>{label}</a>')
    socials = " · ".join(f'<a href="{E(u)}" rel="noopener">{E(n)}</a>' for n, u in SOCIALS)
    canonical = f"{SITE_URL}/{page}" if page != "index.html" else f"{SITE_URL}/"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<meta name="keywords" content="group of effective catalysis, группа эффективного катализа, Denis Chusov, Chemistry for me, Денис Чусов">
<link rel="canonical" href="{canonical}">
<meta property="og:site_name" content="chemistryforme">
<meta property="og:type" content="{og_type}">
<meta property="og:url" content="{canonical}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:image" content="{og_abs}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{E(title)}">
<meta name="twitter:description" content="{E(desc)}">
<meta name="twitter:image" content="{og_abs}">
<link rel="icon" type="image/png" href="{prefix}assets/img/misc/favicon.png">
<link rel="stylesheet" href="{prefix}css/style.css?v={CSS_VER}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800;900&family=Fraunces:ital,wght@1,500;1,600&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
{ANALYTICS}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="wrap">
    <a class="brand" href="{prefix}index.html">
      <img src="{prefix}assets/img/misc/logo.png" alt="Group of Effective Catalysis — logo" width="60" height="60">
      <span>
        <span class="brand-name">Group of Effective Catalysis</span>
        <span class="brand-sub">chemistry for me</span>
      </span>
    </a>
    <input class="nav-toggle" type="checkbox" id="nav-toggle" aria-label="Toggle menu">
    <label class="nav-burger" for="nav-toggle" aria-hidden="true"><span></span><span></span><span></span></label>
    <nav class="nav" aria-label="Main">
      {"".join(nav_items)}
    </nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <div class="wrap">
    <img class="foot-logo" src="{prefix}assets/img/misc/logo.png" alt="" width="78" height="78" loading="lazy">
    <p class="foot-tg"><a href="https://t.me/chusov_lab" rel="noopener">Subscribe on Telegram — <b>@chusov_lab</b></a></p>
    <p class="foot-line"><a href="mailto:chden@ya.ru">chden@ya.ru</a></p>
    <p class="foot-line">Moscow, Russia, 119334</p>
    <p class="foot-social">{socials}</p>
    <p class="foot-line" style="margin-top:10px"><a href="{prefix}open-positions.html">Open positions</a> · <a href="https://colab.ws/labs/765" rel="noopener">Lab on colab.ws</a></p>
    <p class="foot-copy">©2026 by Chemistry for me</p>
  </div>
</footer>
<script src="{prefix}js/effects.js" defer></script>
</body>
</html>
"""


def page_head(title, sub=None):
    s = f'<p class="sub">{sub}</p>' if sub else ""
    return f"""
<div class="page-head">
  <div class="wrap">
    <h1>{title}</h1>
    {s}
  </div>
</div>"""


def write(name, content):
    path = os.path.join(ROOT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", name)


# ---------------------------------------------------------------- shared

# Curated real-photo pool for the "Gallery" mosaics on the homepage
# and the blog: event/crowd shots and graphical highlights rather than
# portraits of specific staff, so a tile never shows someone who has since
# left the group. JS (lablife-rotate, in effects.js) swaps tiles in from this
# pool over time. Every entry links to a real post on the site.
GALLERY_POOL_STATE = json.load(open(os.path.join(ROOT, "_build", "gallery_pool.json"), encoding="utf-8"))
LAB_LIFE_POOL = GALLERY_POOL_STATE["items"]


# ---------------------------------------------------------------- home

def build_home():
    mascot_section = '<section class="section mascot-section">\n  <div class="wrap mascot-wrap">\n    <div class="mascot-copy">\n      <span class="k">Say hello</span>\n      <h2>Our mascot never stops experimenting</h2>\n      <p>Click the wheel to set our mascot running and start a reaction — watch the mix separate as it distills. Purely for fun, not our actual lab data.</p>\n    </div>\n    <div class="mascot-rig" id="mascot-rig">\n  <svg viewBox="0 0 640 380" role="img" aria-label="Illustration of the lab\'s mascot squirrel running in a wheel next to a distillation set-up">\n    <rect x="0" y="308" width="640" height="72" fill="#6b4e34"></rect>\n    <rect x="0" y="308" width="640" height="7" fill="#7d5c3e"></rect>\n\n    <path d="M 160 311 C 160 320 150 324 120 324 C 70 324 66 316 64 306 L 60 296" fill="none" stroke="#c9c4b8" stroke-width="7" stroke-linecap="round"></path>\n    <path d="M 302 305 C 240 322 190 322 160 311" fill="none" stroke="#c9c4b8" stroke-width="7" stroke-linecap="round"></path>\n\n    <g id="mascot-wheel-control" tabindex="0" role="button" aria-label="Click the wheel to set the mascot running and start a reaction">\n      <path d="M 128 258 C 96 258 78 232 84 202 C 89 176 112 158 140 156 C 158 155 168 166 160 178 C 152 188 136 186 128 196 C 118 208 122 224 138 232 C 150 238 150 248 138 254 Z" fill="#ff7a26" stroke="#2a2a2a" stroke-width="3"></path>\n      <path d="M 118 176 C 106 186 100 200 104 214" fill="none" stroke="#fff" stroke-width="9" stroke-linecap="round" opacity="0.9"></path>\n      <path id="leg-back" class="mascot-leg" d="M136 284 Q120 300 100 298" fill="none" stroke="#2a2a2a" stroke-width="7" stroke-linecap="round"></path>\n      <ellipse id="paw-back" cx="97" cy="298" rx="8" ry="5.5" fill="#ff7a26" stroke="#2a2a2a" stroke-width="2.5"></ellipse>\n      <path d="M 108 250 C 100 268 108 288 130 294 C 152 300 176 292 190 274 C 200 262 198 246 184 240 C 166 232 132 234 108 250 Z" fill="#ff7a26" stroke="#2a2a2a" stroke-width="3"></path>\n      <path d="M 120 274 C 130 288 158 292 176 280 C 168 292 144 298 126 290 C 118 286 116 280 120 274 Z" fill="#fff8ee" stroke="#2a2a2a" stroke-width="2"></path>\n      <path id="leg-front" class="mascot-leg" d="M182 282 Q198 298 216 292" fill="none" stroke="#2a2a2a" stroke-width="7" stroke-linecap="round"></path>\n      <ellipse id="paw-front" cx="218" cy="291" rx="8" ry="5.5" fill="#ff7a26" stroke="#2a2a2a" stroke-width="2.5"></ellipse>\n      <circle cx="210" cy="232" r="26" fill="#ff7a26" stroke="#2a2a2a" stroke-width="3"></circle>\n      <path d="M 196 210 C 194 198 204 194 212 202 C 208 208 202 212 196 210 Z" fill="#ff7a26" stroke="#2a2a2a" stroke-width="3"></path>\n      <path d="M 224 234 C 238 230 248 236 246 246 C 244 254 232 258 222 252 C 216 248 216 238 224 234 Z" fill="#fff8ee" stroke="#2a2a2a" stroke-width="2.5"></path>\n      <circle cx="216" cy="224" r="8.5" fill="#fff"></circle>\n      <circle cx="216" cy="224" r="8.5" fill="none" stroke="#2a2a2a" stroke-width="2"></circle>\n      <circle cx="218" cy="225" r="4.5" fill="#1a1a1a"></circle>\n      <circle cx="220" cy="222" r="1.4" fill="#fff"></circle>\n      <circle cx="245" cy="240" r="3.2" fill="#1a1a1a"></circle>\n      <path d="M 232 250 Q 238 256 246 250" fill="none" stroke="#2a2a2a" stroke-width="2" stroke-linecap="round"></path>\n      <g id="mascot-wheel">\n        <circle cx="160" cy="230" r="82" fill="none" stroke="#3a3a3a" stroke-width="5"></circle>\n        <line x1="160" y1="230" x2="242" y2="230" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="218" y2="288" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="160" y2="312" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="102" y2="288" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="78" y2="230" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="102" y2="172" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="160" y2="148" stroke="#3a3a3a" stroke-width="3"></line>\n        <line x1="160" y1="230" x2="218" y2="172" stroke="#3a3a3a" stroke-width="3"></line>\n      </g>\n      <circle cx="160" cy="230" r="7" fill="#3a3a3a"></circle>\n    </g>\n\n    <rect x="332" y="112" width="7" height="196" fill="#4a4f53" stroke="#2a2a2a" stroke-width="1.5"></rect>\n    <rect x="312" y="300" width="70" height="10" rx="2" fill="#5c6266" stroke="#2a2a2a" stroke-width="1.5"></rect>\n    <g>\n      <rect x="339" y="214" width="16" height="9" rx="2" fill="#8a8f94" stroke="#2a2a2a" stroke-width="2"></rect>\n      <path d="M355 216 C 368 213 376 225 366 235 C 361 240 354 237 354 230" fill="none" stroke="#2a2a2a" stroke-width="3" stroke-linecap="round"></path>\n    </g>\n\n    <rect x="298" y="292" width="88" height="16" rx="3" fill="#262626" stroke="#2a2a2a" stroke-width="1.5"></rect>\n    <rect x="304" y="288" width="76" height="6" rx="3" fill="#4a4a4a"></rect>\n    <circle cx="316" cy="300" r="4.5" fill="#1a1a1a" stroke="#6a6a6a" stroke-width="1"></circle>\n    <line x1="316" y1="300" x2="316" y2="297" stroke="#ccc" stroke-width="1.4"></line>\n\n    <rect x="332" y="196" width="16" height="46" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2"></rect>\n    <circle cx="340" cy="262" r="42" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2"></circle>\n    <clipPath id="clip-pot"><circle cx="340" cy="262" r="40"></circle></clipPath>\n    <rect id="liquid-pot" x="298" y="236" width="84" height="68" fill="#f2c230" clip-path="url(#clip-pot)"></rect>\n    <ellipse cx="322" cy="234" rx="10" ry="16" fill="#fff" fill-opacity="0.35" transform="rotate(-18 322 234)"></ellipse>\n    <ellipse cx="340" cy="298" rx="10" ry="3.5" fill="#3a3a3a" opacity="0.7"></ellipse>\n    <path d="M333 200 L340 206 M333 208 L342 216 M334 216 L343 224" stroke="#2a2a2a" stroke-width="1.1" opacity="0.65"></path>\n\n    <rect x="330" y="140" width="20" height="56" rx="6" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2"></rect>\n    <path d="M340 190 C 348 186 348 180 340 177 C 332 174 332 168 340 165 C 348 162 348 156 340 153 C 332 150 332 144 340 141" fill="none" stroke="#6a6f73" stroke-width="3.4" stroke-linecap="round"></path>\n    <path d="M333 144 L340 150 M333 150 L341 158" stroke="#2a2a2a" stroke-width="1.1" opacity="0.65"></path>\n\n    <path d="M332 140 L332 108 C332 100 348 100 348 108 L348 118 L372 138 L364 148 L348 132 L348 140 Z" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2" stroke-linejoin="round"></path>\n    <path d="M330 108 L350 108 L347 96 L333 96 Z" fill="#b9906a" stroke="#2a2a2a" stroke-width="2" stroke-linejoin="round"></path>\n    <rect x="331" y="93" width="18" height="5" rx="1.5" fill="#c9a876" stroke="#2a2a2a" stroke-width="1.6"></rect>\n    <path d="M362 141 L367 146 M358 137 L363 142" stroke="#2a2a2a" stroke-width="1.1" opacity="0.65"></path>\n\n    <g>\n      <path d="M368 138 L520 256 L520 272 L368 154 Z" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2"></path>\n      <path d="M370 144 L518 260" fill="none" stroke="#9fc6c0" stroke-width="1.6" stroke-dasharray="5 6" opacity="0.9"></path>\n      <g transform="translate(388,148) rotate(38)">\n        <rect x="-5.5" y="-15" width="11" height="16" rx="2.5" fill="#7fa8c9" fill-opacity="0.55" stroke="#2a2a2a" stroke-width="2"></rect>\n      </g>\n      <g transform="translate(500,248) rotate(38)">\n        <rect x="-5.5" y="-15" width="11" height="16" rx="2.5" fill="#7fa8c9" fill-opacity="0.55" stroke="#2a2a2a" stroke-width="2"></rect>\n      </g>\n    </g>\n\n    <rect x="452" y="176" width="7" height="132" fill="#4a4f53" stroke="#2a2a2a" stroke-width="1.5"></rect>\n    <g>\n      <rect x="440" y="192" width="16" height="9" rx="2" fill="#8a8f94" stroke="#2a2a2a" stroke-width="2" transform="rotate(38 448 196)"></rect>\n      <path d="M456 190 C468 184 478 194 470 206 C465 213 456 210 456 202" fill="none" stroke="#2a2a2a" stroke-width="3" stroke-linecap="round"></path>\n    </g>\n\n    <path d="M520 254 C 540 260 548 268 548 280" fill="none" stroke="#fff" stroke-opacity="0.35" stroke-width="12"></path>\n    <path d="M520 254 C 540 260 548 268 548 280" fill="none" stroke="#2a2a2a" stroke-width="2.2"></path>\n    <path d="M514 246 L520 252 M510 242 L516 248" stroke="#2a2a2a" stroke-width="1.1" opacity="0.65"></path>\n\n    <rect x="538" y="276" width="18" height="14" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2"></rect>\n    <circle cx="547" cy="306" r="28" fill="#fff" fill-opacity="0.28" stroke="#2a2a2a" stroke-width="2.2"></circle>\n    <clipPath id="clip-receiver"><circle cx="547" cy="306" r="26"></circle></clipPath>\n    <rect id="liquid-receiver" x="519" y="332" width="56" height="0" fill="#4caf5e" clip-path="url(#clip-receiver)"></rect>\n    <ellipse cx="535" cy="288" rx="7" ry="11" fill="#fff" fill-opacity="0.35" transform="rotate(-18 535 288)"></ellipse>\n\n    <rect x="586" y="200" width="7" height="108" fill="#4a4f53" stroke="#2a2a2a" stroke-width="1.5"></rect>\n    <rect x="570" y="300" width="46" height="10" rx="2" fill="#5c6266" stroke="#2a2a2a" stroke-width="1.5"></rect>\n    <g>\n      <rect x="571" y="252" width="16" height="9" rx="2" fill="#8a8f94" stroke="#2a2a2a" stroke-width="2"></rect>\n      <path d="M571 254 C 560 251 552 261 559 270 C 563 275 570 273 571 267" fill="none" stroke="#2a2a2a" stroke-width="3" stroke-linecap="round"></path>\n    </g>\n\n    <g id="mascot-speech" opacity="0">\n      <rect x="14" y="6" width="300" height="72" rx="14" fill="#0d2b26"></rect>\n      <path d="M46 78 L36 98 L64 78 Z" fill="#0d2b26"></path>\n      <text id="mascot-speech-text" x="164" y="34" text-anchor="middle" font-family="Space Grotesk, sans-serif" font-size="16" font-weight="600" fill="#fff">\n        <tspan id="mascot-speech-l1" x="164" dy="0">Fizz!</tspan>\n        <tspan id="mascot-speech-l2" x="164" dy="23" font-size="14.5"></tspan>\n      </text>\n    </g>\n\n    <a href="#publications" id="mascot-jump" opacity="0" aria-label="Jump to our publications">\n      <circle cx="80" cy="112" r="15" fill="#f2b807" stroke="#0d2b26" stroke-width="2"></circle>\n      <path d="M73 108 L80 115 L87 108" fill="none" stroke="#0d2b26" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>\n    </a>\n  </svg>\n</div>\n  </div>\n</section>\n'
    pubs = DATA["pubs"]
    top3 = [p for p in pubs if p.get("toc_local")][:3]
    pub_cells = "".join(f"""
      <a class="pub-cell" href="{E(p["doi"])}" rel="noopener">
        <div class="pub-cell-img"><img src="assets/{E(p['toc_local'])}" alt="Graphical abstract" loading="lazy"></div>
        <span class="k">{E(typeset(p["journal_ref"]))}</span>
        <span class="t">{E(p["title"])}</span>
      </a>""" for p in top3)

    directions = [
        "Carbon Monoxide as reducing agent",
        "Selective reductive amination",
        "Simplified Eschweiler-Clarke",
        "Fluoride activated catalysis",
        "Simple metal salts as catalysts",
    ]
    dir_items = "".join(
        f'<li><span class="dot"></span><a href="research.html">{E(d)}</a></li>' for d in directions)

    people = DATA["people"]
    people_flush = "".join(f"""
      <a class="flush-row people-row" href="people/{E(p["slug"])}.html">
        <img src="assets/{E(p["photo"])}" alt="" loading="lazy">
        <span><span class="n">{E(p["name"])}</span><span class="r">{E("Principal Investigator" if p["slug"] == "denis-chusov" else (p["role"] or p["group_role"]))}</span></span>
      </a>""" for p in people[:3])

    news = DATA["news"][:5]
    news_flush = "".join(f"""
      <a class="flush-row" href="news.html#{E(n["slug"])}">
        <span class="k">{E(fmt_date(n["date"]))}</span>
        <span class="t">{E(n["title"])}</span>
      </a>""" for n in news)

    media_top = [DATA["media"][6], DATA["media"][11], DATA["media"][2], DATA["media"][8]]
    media_flush = "".join(f"""
      <a class="flush-row" href="{E(m["url"])}" rel="noopener">
        <span class="t">{E(m["title"])} <span class="k">— {E(outlet_of(m["url"]))}</span></span>
      </a>""" for m in media_top if m["thumb"])

    # photo collage from the group's own blog photos, drawn from the shared
    # people-free LAB_LIFE_POOL (defined above build_home) so it never shows
    # someone who has since left the group; rotated client-side over time.
    lablife_visible = LAB_LIFE_POOL[:8]
    lablife = "".join(f"""
      <a class="ph {t['cls']}" href="{'news.html#' + E(t['anchor']) if t['anchor'] else 'news.html'}" data-img="{E(t['img'])}"><img src="assets/{E(t['img'])}" alt="{E(t['alt'])}" loading="lazy"></a>"""
                      for t in lablife_visible)
    lablife_pool_json = json.dumps(LAB_LIFE_POOL).replace("</", "<\/")

    body = f"""
<section class="hero">
  <div class="wrap">
    <div class="hero-emblem">
      <img src="assets/img/misc/emblem-hero.png" width="900" height="912" alt="Group of Effective Catalysis emblem" loading="eager">
    </div>
    <div class="hero-copy">
      <h1>Waste gas<br><span class="c-accent">in.</span><br>Molecules<br><span class="c-accent2">out.</span></h1>
      <p class="lede">Steel is being produced in big amounts every year. Carbon monoxide is the main
      waste in this production and it should be used for industry use. Reducing without external
      source of hydrogen allows to avoid hydrogenation functional and protecting groups. Group of
      Effective Catalysis, INEOS RAS.</p>
      <div class="hero-actions">
        <a class="btn" href="research.html">What We Do</a>
        <a class="btn ghost" href="people.html">Meet the Team</a>
      </div>
    </div>
  </div>
</section>

{mascot_section}
<section class="section" id="publications">
  <div class="wrap">
    <div class="section-head">
      <h2>Publications</h2>
      <a class="more" href="publications.html">All {N_PUBS} papers</a>
    </div>
    <div class="pub-flush">{pub_cells}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="two-col">
      <div>
        <div class="section-head"><h2>Research</h2><a class="more" href="research.html">Read More</a></div>
        <p>Steel is being produced in big amounts every year. Carbon monoxide is the main waste
        in this production and it should be used for industry use.</p>
        <p style="margin-top:10px">Reducing without external source of hydrogen allows to avoid
        hydrogenation functional and protecting groups.</p>
        <ul class="dir-dots">{dir_items}</ul>
      </div>
      <div>
        <div class="section-head"><h2>People</h2><a class="more" href="people.html">Learn More</a></div>
        <div class="flush-list">{people_flush}</div>
      </div>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Gallery</h2>
      <a class="more" href="news.html">Read More</a>
    </div>
    <div class="lablife" id="gallery-home">{lablife}</div>
    <script type="application/json" id="gallery-home-pool">{lablife_pool_json}</script>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="two-col">
      <div>
        <div class="section-head"><h2>News</h2><a class="more" href="news.html">Read More</a></div>
        <div class="flush-list">{news_flush}</div>
      </div>
      <div>
        <div class="section-head"><h2>Media</h2><a class="more" href="media.html">Read More</a></div>
        <div class="flush-list">{media_flush}</div>
      </div>
    </div>
  </div>
</section>

"""
    write("index.html", shell(
        title="Group Of Effective Catalysis | ChemCatGroup | Denis Chusov",
        desc="Official web page of Group of Effective Catalysis",
        active=None, body=body))


# ---------------------------------------------------------------- publications

def build_publications():
    pubs = DATA["pubs"]
    total = len(pubs)
    by_year = {}
    for p in pubs:
        by_year.setdefault(p["year"], []).append(p)
    years = sorted(by_year, reverse=True)

    year_bar = " ".join(f'<a href="#y{y}">{y}</a>' for y in years)
    blocks = []
    for y in years:
        rows = []
        for p in by_year[y]:
            num = total - (p["n"] - 1)
            if p["toc_local"]:
                toc = (f'<a class="toc" href="{E(p["doi"])}" rel="noopener" tabindex="-1" aria-hidden="true">'
                       f'<img src="assets/{E(p["toc_local"])}" alt="" loading="lazy"></a>')
                cls = "pub-row"
            else:
                toc = ""
                cls = "pub-row no-toc"
            rows.append(f"""
    <article class="{cls}" id="p{p["n"]}">
      <span class="num">{num}.</span>
      {toc}
      <div>
        <h3><a href="{E(p["doi"])}" rel="noopener">{E(p["title"])}</a></h3>
        <p class="ref">{ref_html(p)}{' <span class="draft-tag">draft</span>' if p.get("draft") else ""}</p>
        <p class="links">DOI: <a href="{E(p["doi"])}" rel="noopener">{E(p["doi"].replace("https://doi.org/", "").replace("https://", ""))}</a>{f'<span class="cited"> · Citations: {cited_of(p["n"])}</span>' if cited_of(p["n"]) else ''}</p>
      </div>
    </article>""")
        blocks.append(f'<section class="year-block" id="y{y}"><h2>{y}</h2>{"".join(rows)}</section>')

    body = f"""
{page_head("Publications", sub=f"{total} papers, {years[-1]}–{years[0]}")}
<div class="wrap">
  <nav class="year-bar" aria-label="Years">{year_bar}</nav>
  {"".join(blocks)}
</div>
"""
    write("publications.html", shell(
        title="Publications | ChemCatGroup",
        desc=f"Publications of the Group of Effective Catalysis (Denis Chusov lab), {years[-1]}–{years[0]}, with graphical abstracts and DOI links.",
        active="publications.html", body=body, page="publications.html"))


# ---------------------------------------------------------------- research

def build_research():
    directions = [
        {
            "k": "01",
            "title": "Carbon monoxide as a reducing agent",
            "img": "img/pubs/p70.jpg",
            "alt": "Graphical abstract: carbonyl and nitro compounds reduced with CO as the reductant",
            "body": "Steel is produced in enormous amounts every year, and carbon monoxide is its main "
                    "waste gas. We repurpose that waste stream as a reducing agent for organic synthesis "
                    "\u2014 turning a byproduct nobody wants into a tool for building molecules.",
            "pubs": [
                {"title": "Carbon monoxide as a selective reducing agent in organic chemistry",
                 "journal_ref": "Mend. Commun., 2018, 28 (2), 113\u2013122",
                 "doi": "https://doi.org/10.1016/j.mencom.2018.03.001"},
                {"title": "Syngas Instead of Hydrogen Gas as a Reducing Agent \u2014 A Strategy To Improve "
                          "the Selectivity and Efficiency of Organometallic Catalysts",
                 "journal_ref": "ACS Catal., 2022, 12, 5145\u20135154",
                 "doi": "https://doi.org/10.1021/acscatal.2c01000"},
            ],
        },
        {
            "k": "02",
            "title": "Selective reductive amination",
            "img": "img/pubs/p30.png",
            "alt": "Graphical abstract: selective reductive amination with H2 + CO and a Rh catalyst",
            "body": "Running reductions without an external source of hydrogen lets us skip the "
                    "hydrogenation-sensitive functional groups and protecting groups that conventional "
                    "methods force on a molecule, keeping routes shorter and the substrate scope wider.",
            "pubs": [
                {"title": "Syngas as a synergistic reducing agent for selective reductive amination"
                          "\u2014a mild route to bioactive amines",
                 "journal_ref": "New J. Chem., 2023, 47, 10514\u201310518",
                 "doi": "https://doi.org/10.1039/D3NJ01258A"},
                {"title": "Enhancing the efficiency of the ruthenium catalysts in the reductive amination "
                          "without an external hydrogen source",
                 "journal_ref": "J. Catal., 2022, 405, 404\u2013409",
                 "doi": "https://doi.org/10.1016/j.jcat.2021.12.018"},
            ],
        },
        {
            "k": "03",
            "title": "Simplified Eschweiler\u2013Clarke reaction",
            "img": "img/pubs/p17.gif",
            "alt": "Acid-free Eschweiler\u2013Clarke reaction scheme",
            "body": "The classic Eschweiler\u2013Clarke methylation runs in a large excess of formic acid, "
                    "which also strips off acid-sensitive protecting groups such as TBS, MOM and Boc. We "
                    "developed an acid-free version of the reaction that leaves those groups untouched.",
            "pubs": [
                {"title": "Simplified Version of the Eschweiler\u2013Clarke Reaction",
                 "journal_ref": "J. Org. Chem. 2024, 89, 5, 3580\u20133584",
                 "doi": "https://doi.org/10.1021/acs.joc.3c02476"},
            ],
        },
        {
            "k": "04",
            "title": "Fluoride-activated catalysis",
            "img": "img/pubs/p41.png",
            "alt": "Fluoride activation switching on a metal catalyst",
            "body": "A small, in-situ dose of fluoride ion can switch an ordinary metal catalyst into a "
                    "faster, more selective one. We've mapped this effect across ruthenium, nickel, "
                    "zirconium, hafnium, vanadium and cobalt catalysts \u2014 better yields and "
                    "enantioselectivity, sometimes at lower pressure, from the same catalyst that just "
                    "needed a little fluoride.",
            "pubs": [
                {"title": "Straightforward Access to High-Performance Organometallic Catalysts by "
                          "Fluoride Activation",
                 "journal_ref": "ACS Catal., 2021, 11, 13077\u201313084",
                 "doi": "https://doi.org/10.1021/acscatal.1c03785"},
                {"title": "Application of transition metal fluorides in catalysis",
                 "journal_ref": "Coord. Chem. Rev., 2024, 519, 216114",
                 "doi": "https://doi.org/10.1016/j.ccr.2024.216114"},
            ],
        },
        {
            "k": "05",
            "title": "Simple metal salts as catalysts",
            "img": "img/pubs/p23.jpg",
            "alt": "Chiral organic salt supported palladium nanoparticles",
            "body": "Instead of designing elaborate ligands, we use simple, chiral organic salts to support "
                    "and steer metal nanoparticles \u2014 for example directing palladium nanoparticles "
                    "toward the selective hydrogenation of nitroarenes.",
            "pubs": [
                {"title": "Chiral crystalline organic salts as supports of Pd nanoparticles forming "
                          "selective heterogeneous catalysts for hydrogenation of nitroarenes",
                 "journal_ref": "Mendeleev Commun., 2024, 34, 2, 204\u2013205",
                 "doi": "https://doi.org/10.1016/j.mencom.2024.02.014"},
                {"title": "Chiral Organic Salt Supported Pd Nanoparticles as Selective Heterogeneous "
                          "Catalysts of Hydrogenation Reactions",
                 "journal_ref": "ChemistrySelect, 2024, 9, 41, 831\u2013833",
                 "doi": "https://doi.org/10.1002/slct.202402788"},
            ],
        },
    ]

    def pub_li(pub):
        return f'<li><a href="{E(pub["doi"])}" rel="noopener">{E(pub["title"])}</a> <span class="jr">\u2014 {E(pub["journal_ref"])}</span></li>'

    rows = ""
    for d in directions:
        pubs_html = "".join(pub_li(p) for p in d["pubs"])
        rows += f"""
      <div class="r-row">
        <div class="r-media"><img src="assets/{E(d['img'])}" alt="{E(d['alt'])}" loading="lazy"></div>
        <div class="r-body">
          <span class="k">{E(d['k'])} \u2014 {E(d['title'].upper())}</span>
          <h2>{E(d['title'])}</h2>
          <p>{E(d['body'])}</p>
          <div class="r-pubs">
            <span class="r-pubs-label">Related publications</span>
            <ul>{pubs_html}</ul>
          </div>
        </div>
      </div>"""

    body = f"""
{page_head("Research", sub="Revealing the Mysteries of Science")}
<div class="wrap">
  <div class="research-intro">
    <p>The group works on practical, atom-economical catalysis: turning cheap, often-overlooked
    feedstocks \u2014 waste carbon monoxide, a pinch of fluoride, simple chiral salts \u2014 into
    reliable routes to complex molecules, with an eye on mild conditions and real waste reduction.
    Five directions run through that work, from an industrial waste gas repurposed as a reagent
    to metal catalysts switched on by a trace additive.</p>
  </div>
  <div class="r-rows">{rows}</div>
  <p style="margin-top:26px; font-size:14.5px; color:var(--muted)">Details on every direction are in the
  <a href="publications.html">publications</a>.</p>
</div>
"""
    write("research.html", shell(
        title="Research | ChemCatGroup",
        desc="Research of the Group of Effective Catalysis: carbon monoxide as reducing agent, selective reductive amination, hydrogen borrowing, simplified Eschweiler-Clarke, fluoride activated catalysis.",
        active="research.html", body=body, page="research.html"))


# ---------------------------------------------------------------- people

def build_people():
    people = {p["slug"]: p for p in DATA["people"]}
    pi = people["denis-chusov"]

    groups = [
        ("Research staff", "img/misc/Me2CO.png",
         ["oleg-afanasyev", "evgeniya-podyacheva", "artemy-fatkulin", "andrey-kozlov", "klim-birukov"]),
        ("Ph.D. students", "img/misc/camphor.png",
         ["alexandra-balalaeva", "ilya-aniskin"]),
        ("Students", "img/misc/benzaldehyde.png",
         ["fedor-kluev", "olesya-zvereva", "mikhail-losev", "taisiya-brylova", "vasilii-korochancev",
          "ivan-golub", "ivan-smirnov", "danil-rakitianskii", "dmitrii-pozdniakov"]),
        ("Administrator", "img/misc/pyrrolidine.png", ["alexander-modin"]),
    ]

    sections = []
    for gname, molecule, slugs in groups:
        cards = []
        for s in slugs:
            p = people[s]
            role = p["role"] or p["group_role"]
            cards.append(f"""
    <article class="person-card">
      <a href="people/{E(s)}.html" tabindex="-1" aria-hidden="true"><img class="photo" src="assets/{E(p["photo"])}" alt="{E(p["name"])}" loading="lazy"></a>
      <div class="pad">
        <h3 class="n"><a href="people/{E(s)}.html">{E(p["name"])}</a></h3>
        <p class="r">{E(role)}</p>
        {fields_html(p)}
      </div>
    </article>""")
        sections.append(f"""
  <section class="group-section">
    <div class="group-head">
      <h2>{E(gname)}</h2>
      <img class="molecule" src="assets/{E(molecule)}" alt="" loading="lazy">
    </div>
    <div class="people-grid">{"".join(cards)}</div>
  </section>""")

    body = f"""
{page_head("People", sub="Our scientific warriors")}
<div class="wrap">
  <section class="group-section" style="margin-top:26px">
    <div class="group-head"><h2>Principal Investigator</h2></div>
    <article class="pi-card">
      <a href="people/denis-chusov.html" tabindex="-1" aria-hidden="true"><img class="photo" src="assets/{E(pi["photo"])}" alt="{E(pi["name"])}"></a>
      <div class="pad">
        <h3 class="n"><a href="people/denis-chusov.html">Prof. Dr. Denis Chusov</a></h3>
        <p class="r">Principal Investigator · {E(pi["role"])}</p>
        {fields_html(pi)}
        {profile_links_html("denis-chusov")}
        {stats_html("denis-chusov")}
      </div>
    </article>
  </section>

  {"".join(sections)}

  <p>Former members are on the <a href="alumni.html">Alumni</a> page.
  Open positions: <a href="open-positions.html">PhD in chemistry (аспирантура)</a>.</p>
</div>
"""
    write("people.html", shell(
        title="Personnel | ChemCatGroup",
        desc="Members of the Group of Effective Catalysis — Denis Chusov lab at INEOS RAS, Moscow.",
        active="people.html", body=body, page="people.html"))


# ---------------------------------------------------------------- alumni + former

def build_alumni():
    cards = []
    for a in DATA["alumni"]:
        slug = a["slug"] or ALUM_SLUG[a["name"]]
        after = md_inline(a["after"]) if a["after"] else ""
        photo = f'<a href="people/{E(slug)}.html" tabindex="-1" aria-hidden="true"><img class="photo" src="assets/{E(a["photo"])}" alt="{E(a["name"])}" loading="lazy"></a>' if a["photo"] else ""
        extra = fields_html(a, keys=("education", "interests")) if (a.get("education") or a.get("interests")) else ""
        cards.append(f"""
    <article class="alum-card">
      {photo}
      <div class="pad">
        <h3 class="n"><a href="people/{E(slug)}.html">{E(a["name"])}</a></h3>
        <p class="after">{after}</p>
        {extra}
      </div>
    </article>""")

    body = f"""
{page_head("Alumni")}
<div class="wrap">
  <div class="alumni-grid" style="margin-top:26px">{"".join(cards)}</div>
</div>
"""
    write("alumni.html", shell(
        title="Alumni | ChemCatGroup",
        desc="Alumni of the Group of Effective Catalysis and their current positions.",
        active="alumni.html", body=body, page="alumni.html"))

    fcards = []
    for a in DATA["former"]:
        photo = f'<a href="people/{E(a["slug"])}.html" tabindex="-1" aria-hidden="true"><img class="photo" src="assets/{E(a["photo"])}" alt="{E(a["name"])}" loading="lazy"></a>' if a["photo"] else ""
        fcards.append(f"""
    <article class="alum-card">
      {photo}
      <div class="pad">
        <h3 class="n"><a href="people/{E(a["slug"])}.html">{E(a["name"])}</a></h3>
        <p class="r" style="font-size:13px;color:var(--muted);font-style:italic">{E(a["role"] or "")}</p>
        {fields_html(a)}
      </div>
    </article>""")
    fbody = f"""
{page_head("Former members")}
<div class="wrap">
  <p style="margin-top:20px">Personal pages preserved from the previous version of the site.</p>
  <div class="alumni-grid" style="margin-top:22px">{"".join(fcards)}</div>
</div>
"""
    write("former-members.html", shell(
        title="Former members | ChemCatGroup",
        desc="Archived member pages from the previous version of the site.",
        active=None, body=fbody, page="former-members.html"))


# ---------------------------------------------------------------- news (blog)

def build_news():
    posts = DATA["news"]

    # Same curated, people-free pool used on the homepage -- a post cover can
    # be a close-up of whoever gave the talk, so picking straight from post
    # covers risked exactly the mix-up this section exists to avoid. The blog
    # page has room to show every photo in the pool (newest first), so it's a
    # scrollable carousel here instead of a small fixed mosaic.
    life_all = LAB_LIFE_POOL[::-1]
    life_tiles = "".join(f"""
      <a class="lc-item" href="{'#' + E(t['anchor']) if t['anchor'] else 'news.html'}">
        <img src="assets/{E(t['img'])}" alt="{E(t['alt'])}" loading="lazy">
        <span class="cap">{E(t['alt'])}</span>
      </a>""" for t in life_all)
    life_section = f"""
<div class="wrap">
  <div class="section-head" style="margin-top:8px">
    <h2>Gallery</h2>
  </div>
  <div class="lablife-carousel" id="gallery-blog">
    <button class="lc-arrow lc-prev" type="button" aria-label="Show previous photos">&#8249;</button>
    <div class="lc-track">{life_tiles}</div>
    <button class="lc-arrow lc-next" type="button" aria-label="Show more photos">&#8250;</button>
  </div>
</div>""" if life_tiles else ""

    # curated cards mirroring a handful of recent @chusov_lab posts -- photo
    # first, a short excerpt of the real post text, and a link out to the
    # actual post on Telegram. Text and photos are real, pulled from the
    # channel; kept short here since the full post lives on Telegram.
    TG_POSTS = [
        {
            "id": "117", "date": "2026-09-02T15:31:33+00:00",
            "text": "\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u0432 \u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u0438\u0438 \u041c\u0425\u041b \u0441\u0442\u0430\u0440\u0442\u043e\u0432\u0430\u043b \u043a\u0443\u0440\u0441 \u043f\u043e \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u043e\u043c\u0443 \u043f\u0440\u0430\u043a\u0442\u0438\u043a\u0443\u043c\u0443 \u043f\u043e \u043e\u0440\u0433\u0430\u043d\u0438\u0447\u0435\u0441\u043a\u043e\u0439 \u0445\u0438\u043c\u0438\u0438 \u0434\u043b\u044f 10 \u0445\u0438\u043c\u0438\u0447\u0435\u0441\u043a\u043e\u0433\u043e \u043a\u043b\u0430\u0441\u0441\u0430.",
            "img": "img/telegram/tg-117.jpg",
        },
        {
            "id": "112", "date": "2026-06-11T16:53:58+00:00",
            "text": "\u0421\u0442\u0430\u0432\u0440\u043e\u043f\u043e\u043b\u044c, \u0445\u0438\u043c\u0438\u044f, \u0445\u0438\u043c\u0438\u043a\u0438, \u044e\u0431\u0438\u043b\u0435\u0439 \u0410\u043b\u0435\u043a\u0441\u0430\u043d\u0434\u0440\u0430 \u0412\u0438\u043a\u0442\u043e\u0440\u043e\u0432\u0438\u0447\u0430 \u0410\u043a\u0441\u0451\u043d\u043e\u0432\u0430\u2026 \u0438 \u0432\u0434\u0440\u0443\u0433 \u0431\u0435\u0439\u0441\u0431\u043e\u043b?",
            "img": "img/telegram/tg-112.jpg",
        },
        {
            "id": "111", "date": "2026-06-08T09:01:39+00:00",
            "text": "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0435\u043c \u0437\u043d\u0430\u043a\u043e\u043c\u0441\u0442\u0432\u043e \u0441 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0430\u043c\u0438 \u043d\u0430\u0448\u0435\u0439 \u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u0438\u0438 \u2014 \u041c\u0438\u0445\u0430\u0438\u043b \u041b\u043e\u0441\u0435\u0432, \u043c\u0430\u0433\u0438\u0441\u0442\u0440\u0430\u043d\u0442 1-\u0433\u043e \u0433\u043e\u0434\u0430.",
            "img": "img/telegram/tg-111.jpg",
        },
        {
            "id": "108", "date": "2026-06-05T09:02:24+00:00",
            "text": "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0435\u043c \u0437\u043d\u0430\u043a\u043e\u043c\u0441\u0442\u0432\u043e \u0441 \u0443\u0447\u0430\u0441\u0442\u043d\u0438\u043a\u0430\u043c\u0438 \u043d\u0430\u0448\u0435\u0439 \u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440\u0438\u0438 \u2014 \u0418\u0432\u0430\u043d \u0421\u043c\u0438\u0440\u043d\u043e\u0432, \u043c\u0430\u0433\u0438\u0441\u0442\u0440\u0430\u043d\u0442 1-\u0433\u043e \u0433\u043e\u0434\u0430.",
            "img": "img/telegram/tg-108.jpg",
        },
        {
            "id": "105", "date": "2026-06-03T10:30:08+00:00",
            "text": "\u041d\u0430 \u0424\u0430\u043a\u0443\u043b\u044c\u0442\u0435\u0442\u0435 \u0425\u0438\u043c\u0438\u0438 \u041d\u0418\u0423 \u0412\u0428\u042d \u043f\u0440\u043e\u0448\u043b\u0438 \u0437\u0430\u0449\u0438\u0442\u044b \u0434\u0438\u043f\u043b\u043e\u043c\u043e\u0432. \u041f\u043e\u0437\u0434\u0440\u0430\u0432\u043b\u044f\u0435\u043c \u043d\u0430\u0448\u0438\u0445 \u0437\u0430\u043c\u0435\u0447\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0445 \u0441\u043e\u0442\u0440\u0443\u0434\u043d\u0438\u043a\u043e\u0432!",
            "img": "img/telegram/tg-105.jpg",
        },
        {
            "id": "103", "date": "2026-05-25T07:40:30+00:00",
            "text": "14\u201316 \u043c\u0430\u044f 2026 \u0433. \u0432 \u0433. \u0418\u0440\u043a\u0443\u0442\u0441\u043a\u0435 \u0441\u043e\u0441\u0442\u043e\u044f\u043b\u0441\u044f \u043a\u0435\u0439\u0441-\u0447\u0435\u043c\u043f\u0438\u043e\u043d\u0430\u0442 \u0434\u043b\u044f \u0441\u0442\u0443\u0434\u0435\u043d\u0442\u043e\u0432-\u0445\u0438\u043c\u0438\u043a\u043e\u0432 \u00abBRATSKCHEMSYNTEZ CHALLENGE 2026\u00bb.",
            "img": "img/telegram/tg-103.jpg",
        },
    ]

    tg_cards = "".join(f"""
      <a class="tg-card" href="https://t.me/chusov_lab/{E(p['id'])}" rel="noopener">
        <div class="tg-card-photo"><img src="assets/{E(p['img'])}" alt="Photo from the lab's Telegram channel" loading="lazy"></div>
        <div class="tg-card-body">
          <span class="tg-card-date">{E(fmt_date(p['date']))}</span>
          <p class="tg-card-text">{E(p['text'])}</p>
          <span class="more">Read on Telegram</span>
        </div>
      </a>""" for p in TG_POSTS)
    tg_section = f"""
<div class="wrap">
  <div class="section-head" style="margin-top:44px">
    <h2>From @chusov_lab</h2>
    <a class="more" href="https://t.me/chusov_lab" rel="noopener">Open channel</a>
  </div>
  <div class="tg-cards">{tg_cards}</div>
</div>"""

    by_year = {}
    for p in posts:
        y = p["date"][:4] if p["date"] else "Undated"
        by_year.setdefault(y, []).append(p)

    blocks = []
    for y in sorted(by_year, reverse=True):
        items = []
        for p in by_year[y]:
            body_html = md_block(p["body_md"], alt_ctx=p["title"]) if p["body_md"] else ""
            cover_html = ""
            if p["cover"] and p["cover"] not in p["body_md"]:
                cover_html = f'<figure><img src="assets/{E(p["cover"])}" alt="Illustration: {E(p["title"])}" loading="lazy"></figure>'
            items.append(f"""
    <article class="news-item" id="{E(p["slug"])}">
      <p class="date"><time datetime="{E((p["date"] or "")[:10])}">{E(fmt_date(p["date"]))}</time></p>
      <h3>{E(p["title"])}</h3>
      <div class="body">{body_html}{cover_html}</div>
    </article>""")
        blocks.append(f'<section class="news-year"><h2>{E(y)}</h2>{"".join(items)}</section>')

    body = f"""
{page_head("Blog")}
{life_section}
{tg_section}
<div class="wrap">
  {"".join(blocks)}
</div>
"""
    write("news.html", shell(
        title="Blog | ChemCatGroup",
        desc="Blog of the Group of Effective Catalysis: publications, defenses, conferences and lab life.",
        active="news.html", body=body, page="news.html"))


# ---------------------------------------------------------------- media

MEDIA_OUTLETS = {
    "hse.ru": "HSE University",
    "organic-chemistry.org": "Organic Chemistry Portal",
    "chemistryworld.com": "Chemistry World",
    "scientificrussia.ru": "Научная Россия",
    "meduza.io": "Meduza",
    "nplus1.ru": "N+1",
    "gazeta.ru": "Газета.Ru",
    "nature.com": "Nature",
    "hij.ru": "Химия и жизнь",
}


def outlet_of(url):
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
    if host in MEDIA_OUTLETS:
        return MEDIA_OUTLETS[host]
    return host.split(".")[0].capitalize()


def build_media():
    rows = []
    for m in DATA["media"]:
        thumb = f'<img src="assets/{E(m["thumb"])}" alt="" loading="lazy">' if m["thumb"] else ""
        rows.append(f"""
    <article class="media-item">
      <div class="thumb">{thumb}</div>
      <h3><a href="{E(m["url"])}" rel="noopener">{E(m["title"])}</a></h3>
      <span class="go"><a href="{E(m["url"])}" rel="noopener" tabindex="-1" aria-hidden="true">Read More</a></span>
    </article>""")
    body = f"""
{page_head("Media")}
<div class="wrap">
  <div style="margin-top:12px">{"".join(rows)}</div>
</div>
"""
    write("media.html", shell(
        title="Media | ChemCatGroup",
        desc="Press about the Group of Effective Catalysis: Nature highlight, Chemistry World, Organic Chemistry Portal, interviews.",
        active="media.html", body=body, page="media.html"))


# ---------------------------------------------------------------- personal pages

def profile_links_html(slug):
    rec = PROFILES.get(slug) or {}
    links = [dict(l) for l in rec.get("links", []) if l.get("url")]
    have = {l["type"] for l in links}
    cids = (COLAB_PEOPLE.get(slug) or {}).get("ids") or {}
    colab_links = {  # fill only the profile types the curated data is missing
        "scholar": f'https://scholar.google.com/citations?user={cids["scholar"]}' if cids.get("scholar") else None,
        "scopus": f'https://www.scopus.com/authid/detail.uri?authorId={cids["scopus"]}' if cids.get("scopus") else None,
        "orcid": f'https://orcid.org/{cids["orcid"]}' if cids.get("orcid") else None,
    }
    for t, u in colab_links.items():
        if u and t not in have:
            links.append({"type": t, "url": u}); have.add(t)
    if not links:
        return ""
    order = {"scholar": 0, "orcid": 1, "scopus": 2, "istina": 3, "researchgate": 4, "other": 9}
    links.sort(key=lambda l: order.get(l["type"], 9))
    items = "".join(
        f'<a href="{E(l["url"])}" rel="noopener">{PROFILE_LABEL.get(l["type"], "Profile")}</a>'
        for l in links)
    return f'<div class="profile-links">{items}</div>'


def stats_html(slug):
    st = PEOPLE_PUBS.get(slug)
    if not st or not st.get("n_pubs"):
        return ""
    parts = [f'<b>{st["n_pubs"]}</b> paper{"s" if st["n_pubs"] != 1 else ""} with the group']
    if st.get("citations"):
        parts.append(f'<b>{st["citations"]}</b> citations')
        parts.append(f'h-index <b>{st["h_index"]}</b>')
    line = " · ".join(parts)
    rec = PROFILES.get(slug) or {}
    cp = COLAB_PEOPLE.get(slug) or {}
    gs, used_colab = "", False
    if rec.get("scholar_citations"):
        gs = f' &nbsp;·&nbsp; Google Scholar (all works): <b>{rec["scholar_citations"]}</b> citations'
        if rec.get("scholar_h"):
            gs += f', h-index <b>{rec["scholar_h"]}</b>'
    elif cp.get("citations"):  # supplement: colab.ws all-works stats where no Scholar number exists
        gs = f' &nbsp;·&nbsp; colab.ws (all works): <b>{cp["citations"]}</b> citations'
        if cp.get("h_index"):
            gs += f', h-index <b>{cp["h_index"]}</b>'
        used_colab = True
    month = meta_month()
    src = "Crossref &amp; colab.ws" if used_colab else "Crossref"
    note = f'<span class="src">— {src}, {month}</span>' if month else ""
    return f'<p class="stats-line">{line}{gs} {note}</p>'


def person_pub_rows(slug, prefix=""):
    st = PEOPLE_PUBS.get(slug)
    if not st or not st["pubs"]:
        return ""
    rows = []
    for n in st["pubs"]:
        p = PUB_BY_N[n]
        num = N_PUBS - (n - 1)
        toc = ""
        if p["toc_local"]:
            toc = (f'<a class="toc" href="{E(p["doi"])}" rel="noopener" tabindex="-1" aria-hidden="true">'
                   f'<img src="{prefix}assets/{E(p["toc_local"])}" alt="" loading="lazy"></a>')
        cited = cited_of(n)
        cited_html = f' <span class="cited">· Citations: {cited}</span>' if cited else ""
        rows.append(f"""
    <article class="pub-row compact{'' if toc else ' no-toc'}">
      <span class="num">{num}.</span>
      {toc}
      <div>
        <h3><a href="{E(p["doi"])}" rel="noopener">{E(p["title"])}</a></h3>
        <p class="ref">{ref_html(p)}{cited_html}{' <span class="draft-tag">draft</span>' if p.get("draft") else ""}</p>
      </div>
    </article>""")
    return f"""
  <section class="section" style="padding-top:36px">
    <div class="section-head">
      <h2>Publications</h2>
      <a class="more" href="{prefix}publications.html">All group publications</a>
    </div>
    {"".join(rows)}
  </section>"""


def build_person_pages():
    records = []
    for p in DATA["people"]:
        records.append((p["slug"], p, "member"))
    for a in DATA["alumni"]:
        records.append((a["slug"] or ALUM_SLUG[a["name"]], a, "alumni"))
    for f in DATA["former"]:
        records.append((f["slug"], f, "former"))

    for slug, rec, kind in records:
        if not rec.get("interests"):  # supplement: colab.ws research interests where none are curated
            ci = (COLAB_PEOPLE.get(slug) or {}).get("interests_en")
            if ci:
                rec = {**rec, "interests": ", ".join(ci)}
        name = rec["name"]
        if slug == "denis-chusov":
            name = "Prof. Dr. Denis Chusov"
        if kind == "member":
            role = rec.get("role") or rec.get("group_role") or ""
            if slug == "denis-chusov":
                role = f"Principal Investigator · {role}"
            status = ""
        elif kind == "alumni":
            role = "Alumnus"
            after = md_inline(rec["after"]) if rec.get("after") else ""
            status = f'<p class="after-line">{after}</p>' if after else ""
        else:
            role = rec.get("role") or ""
            status = '<p class="after-line">Former member</p>'
        photo = f'<img class="photo" src="../assets/{E(rec["photo"])}" alt="{E(name)}">' if rec.get("photo") else ""
        photo_frame = f'<div class="profile-photo-frame">{photo}</div>' if photo else ""
        head_class = "profile-head" if photo else "profile-head no-photo"
        back = "people.html" if kind == "member" else "alumni.html"
        body = f"""
<div class="profile-head-band">
  <div class="wrap {head_class}">
    {photo_frame}
    <div>
      <p class="crumb"><a href="../{back}">{'Personnel' if kind == 'member' else 'Alumni'}</a> /</p>
      <h1>{E(name)}</h1>
      <p class="r">{E(role)}</p>
      {status}
    </div>
  </div>
</div>
<div class="wrap">
  <div class="profile-body">
    {fields_html(rec)}
    {profile_links_html(slug)}
    {stats_html(slug)}
  </div>
  {person_pub_rows(slug, prefix="../")}
</div>
"""
        write(f"people/{slug}.html", shell(
            title=f"{name} | ChemCatGroup",
            desc=f"{name} — Group of Effective Catalysis (Denis Chusov lab, INEOS RAS): profile, publications and citation statistics.",
            active="people.html" if kind == "member" else "alumni.html",
            body=body, page=f"people/{slug}.html", prefix="../",
            og_image=(f"assets/{rec['photo']}" if rec.get("photo") else None), og_type="profile"))


# ---------------------------------------------------------------- open positions

def build_positions():
    body = f"""
{page_head("Careers", sub="Get Involved")}
<div class="wrap">
  <div class="prose" style="margin-top:26px">
    <h2>PhD in chemistry (аспирантура)</h2>
    <p lang="ru">Мы всегда рады приветствовать активных молодых учёных, которые хотели бы переписать учебники.
    По вопросам поступления пишите на <a href="mailto:chden@ya.ru">chden@ya.ru</a>.</p>
  </div>
</div>
"""
    write("open-positions.html", shell(
        title="Open Positions | ChemCatGroup",
        desc="PhD positions in the Group of Effective Catalysis (Denis Chusov lab, INEOS RAS, Moscow).",
        active=None, body=body, page="open-positions.html"))


# ---------------------------------------------------------------- SEO / hosting files

def build_seo_files():
    base = f"{SITE_URL}/"
    roots = ["", "research.html", "publications.html", "people.html", "alumni.html",
             "news.html", "media.html", "open-positions.html", "former-members.html"]
    slugs = [p["slug"] for p in DATA["people"]]
    slugs += [a["slug"] or ALUM_SLUG[a["name"]] for a in DATA["alumni"]]
    slugs += [f["slug"] for f in DATA["former"]]
    urls = [base + r for r in roots] + [f"{base}people/{s}.html" for s in slugs]
    urls = list(dict.fromkeys(urls))  # dedupe, preserve order
    today = datetime.now().strftime("%Y-%m-%d")
    locs = "\n".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    write("sitemap.xml",
          '<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{locs}\n</urlset>\n")
    write("robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {base}sitemap.xml\n")
    if not IS_GH_PAGES:  # a CNAME forces a custom domain — only emit one when using it
        write("CNAME", _host + "\n")
    nf = f"""
<div class="wrap" style="padding:72px 24px;text-align:center">
  <h1 style="font-size:44px">404</h1>
  <p class="sub" style="font-size:18px;color:var(--muted);margin-top:8px">Page not found.</p>
  <p style="margin-top:22px"><a class="btn" href="{BASE_PATH}index.html">Back to home</a></p>
</div>
"""
    write("404.html", shell(title="Page not found | ChemCatGroup",
                            desc="The page you are looking for does not exist.",
                            active=None, body=nf, page="404.html", prefix=BASE_PATH))


# ---------------------------------------------------------------- run

build_home()
build_publications()
build_research()
build_people()
build_alumni()
build_news()
build_media()
build_positions()
build_person_pages()
build_seo_files()
print("done")
