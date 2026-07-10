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
    og_abs = "https://www.chemcatgroup.com/" + (og_image or "assets/img/misc/hero-sketch.jpg")
    nav_items = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        nav_items.append(f'<a href="{prefix}{href}"{cur}>{label}</a>')
    socials = " · ".join(f'<a href="{E(u)}" rel="noopener">{E(n)}</a>' for n, u in SOCIALS)
    canonical = f"https://www.chemcatgroup.com/{page}" if page != "index.html" else "https://www.chemcatgroup.com/"
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
{ANALYTICS}</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="wrap">
    <a class="brand" href="{prefix}index.html">
      <img src="{prefix}assets/img/misc/logo.png" alt="Group of Effective Catalysis — logo" width="42" height="42">
      <span>
        <span class="brand-name">Chemistry for me</span>
        <span class="brand-sub">Group of Effective Catalysis</span>
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
    <img class="foot-logo" src="{prefix}assets/img/misc/logo.png" alt="" width="54" height="54" loading="lazy">
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
<div class="wrap">
  <div class="page-head">
    <h1>{title}</h1>
    {s}
    <hr>
  </div>
</div>"""


def write(name, content):
    path = os.path.join(ROOT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", name)


# ---------------------------------------------------------------- home

def build_home():
    pubs = DATA["pubs"]
    top6 = [p for p in pubs if p["toc_local"]][:6]
    cards = []
    for p in top6:
        cards.append(f"""
      <a class="pub-card" href="{E(p["doi"])}" rel="noopener">
        <span class="thumb"><img src="assets/{E(p["toc_local"])}" alt="Graphical abstract: {E(p["title"])}" loading="lazy"></span>
        <span class="body">
          <span class="t">{E(p["title"])}</span>
          <span class="ref">{E(typeset(p["journal_ref"]))}</span>
        </span>
      </a>""")

    directions = [
        "Carbon Monoxide as reducing agent",
        "Selective reductive amination",
        "Simplified Eschweiler-Clarke",
        "Fluoride activated catalysis",
        "Simple metal salts as catalysts",
    ]
    dir_items = "".join(f'<li><a href="research.html">{E(d)}</a></li>' for d in directions)

    people = DATA["people"]
    strip = []
    for p in people[:3]:
        role = "Principal Investigator" if p["slug"] == "denis-chusov" else (p["role"] or p["group_role"])
        strip.append(f"""
      <a class="person-mini" href="people/{E(p["slug"])}.html">
        <img src="assets/{E(p["photo"])}" alt="{E(p["name"])}" loading="lazy">
        <span class="n">{E(p["name"])}</span>
        <span class="r">{E(role)}</span>
      </a>""")

    news = DATA["news"][:5]
    news_rows = []
    for n in news:
        news_rows.append(f"""
      <article class="news-item slim">
        <p class="date"><time datetime="{E((n["date"] or "")[:10])}">{E(fmt_date(n["date"]))}</time></p>
        <h3><a href="news.html#{E(n["slug"])}">{E(n["title"])}</a></h3>
      </article>""")

    media_top = [DATA["media"][6], DATA["media"][11], DATA["media"][2], DATA["media"][8]]
    media_rows = "".join(f"""
      <article class="media-item">
        <div class="thumb"><img src="assets/{E(m["thumb"])}" alt="" loading="lazy"></div>
        <h3><a href="{E(m["url"])}" rel="noopener">{E(m["title"])}</a></h3>
        <span class="go"><a href="{E(m["url"])}" rel="noopener" tabindex="-1" aria-hidden="true">Read More</a></span>
      </article>""" for m in media_top if m["thumb"])

    # photo collage from the group's own blog photos
    LAB_LIFE = [
        ("img/news/team-s-participation-in-ncocs-2022-22.jpg", "team-s-participation-in-ncocs-2022",
         "NCOCS-2022 symposium in Stavropol — group photo of the participants", "s22"),
        ("img/news/our-lab-took-part-in-the-sixth-internati-30.jpg",
         "our-lab-took-part-in-the-sixth-international-scientific-conf",
         "Denis Chusov lecturing at The Sixth International Scientific Conference", "s22"),
        ("img/news/our-group-has-successfully-participated--55.jpg",
         "our-group-has-successfully-participated-in-the-rcoc-conferen",
         "Talk at the RCOC conference", "s12"),
        ("img/news/participation-in-ix-young-scientists-con-18.jpg",
         "participation-in-ix-young-scientists-conference",
         "Award ceremony at the IX Young Scientists Conference", ""),
        ("img/news/congratulations-to-artemy-fatkulin-and-v-42.jpg",
         "congradulations-to-artemy-fatkulin-and-vladimir-ostrovskii-w",
         "PhD defense of Artemy Fatkulin and Vladimir Ostrovskii", ""),
    ]
    lablife = "".join(f"""
      <a class="ph {cls}" href="news.html#{E(anchor)}"><img src="assets/{E(img)}" alt="{E(alt)}" loading="lazy"></a>"""
                      for img, anchor, alt, cls in LAB_LIFE)

    body = f"""
<section class="hero">
  <div class="wrap">
    <div>
      <h1>The Chemistry for me</h1>
      <p class="sub">Official web page of Group of Effective Catalysis</p>
      <p class="lede">Steel is being produced in big amounts every year. Carbon monoxide is the main
      waste in this production and it should be used for industry use. Reducing without external
      source of hydrogen allows to avoid hydrogenation functional and protecting groups.</p>
      <div class="hero-actions">
        <a class="btn" href="research.html">What We Do</a>
        <a class="btn ghost" href="people.html">Learn More</a>
      </div>
    </div>
    <figure class="hero-art">
      <img src="assets/img/misc/hero-sketch.jpg" width="1600" height="1511" alt="Scheme: exhaust-pipe gases feeding a Rh/C catalytic cycle that turns aldehydes and amines into products, TON up to 2400" fetchpriority="high">
    </figure>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Publications</h2>
      <a class="more" href="publications.html">Read More</a>
    </div>
    <div class="pub-cards">{"".join(cards)}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Research</h2>
      <a class="more" href="research.html">Read More</a>
    </div>
    <div class="dir-grid">
      <div>
        <p>Steel is being produced in big amounts every year. Carbon monoxide is the main waste
        in this production and it should be used for industry use.</p>
        <p style="margin-top:10px">Reducing without external source of hydrogen allows to avoid
        hydrogenation functional and protecting groups.</p>
      </div>
      <ul class="dir-list">{dir_items}</ul>
    </div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>People</h2>
      <a class="more" href="people.html">Learn More</a>
    </div>
    <div class="people-strip">{"".join(strip)}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Life in the lab</h2>
      <a class="more" href="news.html">Read More</a>
    </div>
    <div class="lablife">{lablife}</div>
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>News</h2>
      <a class="more" href="news.html">Read More</a>
    </div>
    {"".join(news_rows)}
  </div>
</section>

<section class="section">
  <div class="wrap">
    <div class="section-head">
      <h2>Media</h2>
      <a class="more" href="media.html">Read More</a>
    </div>
    {media_rows}
  </div>
</section>

<section class="tg-band">
  <a class="tg-inner" href="https://t.me/chusov_lab" rel="noopener">
    <img class="tg-icon" src="assets/img/misc/telegram.svg" width="52" height="52" alt="" aria-hidden="true">
    <span class="tg-text">
      <span class="tg-title">Subscribe to our Telegram channel</span>
      <span class="tg-sub">Papers, talks and life in the lab — <b>@chusov_lab</b></span>
    </span>
    <span class="tg-btn">Subscribe</span>
  </a>
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
    body = f"""
{page_head("Research", sub="Revealing the Mysteries of Science")}
<div class="wrap">
  <div class="prose" style="margin-top:26px">
    <h2>Carbon Monoxide as reducing agent</h2>
    <p>Steel is being produced in big amounts every year. Carbon monoxide is the main waste
    in this production and it should be used for industry use.</p>
    <figure class="plate">
      <img src="assets/img/research/steel.jpg" alt="Steel production" loading="lazy">
    </figure>

    <h2>Selective reductive amination</h2>
    <p>Reducing without external source of hydrogen allows to avoid hydrogenation functional
    and protecting groups.</p>
    <figure class="plate">
      <img src="assets/img/research/chem.png" alt="Reaction scheme from the group's research" loading="lazy">
    </figure>

    <h2>Simplified Eschweiler-Clarke</h2>
    <h2>Fluoride activated catalysis</h2>
    <h2>Simple metal salts as catalysts</h2>
    <p style="margin-top:14px">Details on every direction are in the
    <a href="publications.html">publications</a>.</p>
  </div>
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
<div class="wrap">
  {"".join(blocks)}
</div>
"""
    write("news.html", shell(
        title="Blog | ChemCatGroup",
        desc="Blog of the Group of Effective Catalysis: publications, defenses, conferences and lab life.",
        active="news.html", body=body, page="news.html"))


# ---------------------------------------------------------------- media

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
        back = "people.html" if kind == "member" else "alumni.html"
        body = f"""
<div class="wrap">
  <div class="profile-head">
    {photo}
    <div>
      <p class="crumb"><a href="../{back}">{'Personnel' if kind == 'member' else 'Alumni'}</a> /</p>
      <h1>{E(name)}</h1>
      <p class="r">{E(role)}</p>
      {status}
      {fields_html(rec)}
      {profile_links_html(slug)}
      {stats_html(slug)}
    </div>
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
    base = "https://www.chemcatgroup.com/"
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
    write("CNAME", "www.chemcatgroup.com\n")
    nf = """
<div class="wrap" style="padding:72px 24px;text-align:center">
  <h1 style="font-size:44px">404</h1>
  <p class="sub" style="font-size:18px;color:var(--muted);margin-top:8px">Page not found.</p>
  <p style="margin-top:22px"><a class="btn" href="/index.html">Back to home</a></p>
</div>
"""
    write("404.html", shell(title="Page not found | ChemCatGroup",
                            desc="The page you are looking for does not exist.",
                            active=None, body=nf, page="404.html", prefix="/"))


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
