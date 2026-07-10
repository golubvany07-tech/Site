#!/usr/bin/env python3
"""Pull authoritative data from colab.ws for the group and its members.

Build-time only. Reads the API key from $COLAB_API_KEY or _build/colab_key.txt
(both gitignored). Writes only public, committable data — never the key.

Endpoints (base https://colab.ws/api/v0):
  GET /articles/{doi}                      single article incl. author colab_ids/orcids
  GET /researchers/{colab_id}              metrics, ids, interests, coauthors
  GET /articles/?filter=researcher:{id}    a researcher's article list (cursor paging)

Outputs (all public / committable):
  _build/colab_ids.json    {slug: colab_id}  discovered by ORCID then name; hand-editable
  _build/colab_meta.json   per-slug metrics/ids/interests + per-DOI citations + _fetched
  _build/colab_new_pubs.json  Chusov papers on colab not on the site (report; see --add-drafts)

build.py *layers* colab_meta.json over the hand-curated data (supplement, never overwrites).
Raw API responses are cached under _build/.colab_cache/ (gitignored) so re-runs cost ~0 quota.

Usage:
  python3 _build/fetch_colab.py            # use cache where possible
  python3 _build/fetch_colab.py --force    # ignore cache, refetch everything
"""
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://colab.ws/api/v0"
LAB_ID = "765"  # the group's colab.ws lab page (colab.ws/labs/765)
CACHE_DIR = os.path.join(HERE, ".colab_cache")
FORCE = "--force" in sys.argv

DATA = json.load(open(os.path.join(HERE, "site_data.json"), encoding="utf-8"))
PROFILES = json.load(open(os.path.join(HERE, "profiles.json"), encoding="utf-8"))
from match_people import PEOPLE  # {slug: (family variants, given initial)} — reuse curated name map


def load_key():
    k = os.environ.get("COLAB_API_KEY")
    if k:
        return k.strip()
    p = os.path.join(HERE, "colab_key.txt")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    sys.exit("No API key: set $COLAB_API_KEY or create _build/colab_key.txt (gitignored).")


KEY = load_key()
_quota = {"left": None, "calls": 0}
RES_CACHE = {}  # colab_id -> researcher item (this run)


def _http(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "45", url], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout:
        return None
    try:
        j = json.loads(r.stdout)
    except json.JSONDecodeError:
        return None
    if isinstance(j, dict):
        if j.get("requests-left") is not None:
            _quota["left"] = j["requests-left"]
        if j.get("success") is False:
            return None
    _quota["calls"] += 1
    return j


def _cached(kind, ident, fetch):
    """Disk-cache a JSON response. fetch() -> dict|None."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", ident)
    path = os.path.join(CACHE_DIR, f"{kind}_{safe}.json")
    if not FORCE and os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    j = fetch()
    if j is not None:
        json.dump(j, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    return j


def get_article(doi):
    j = _cached("art", doi, lambda: _http(f"{BASE}/articles/{doi}?key={KEY}"))
    return (j or {}).get("item")


def get_researcher(cid):
    if cid in RES_CACHE:
        return RES_CACHE[cid]
    j = _cached("res", cid, lambda: _http(f"{BASE}/researchers/{cid}?key={KEY}"))
    RES_CACHE[cid] = (j or {}).get("item")
    return RES_CACHE[cid]


def researcher_articles(cid):
    """All DOIs+items for a researcher via the paged /articles filter."""
    out, cursor = [], None
    for _ in range(20):  # hard page cap
        url = f"{BASE}/articles/?filter=researcher:{cid}&key={KEY}"
        if cursor:
            url += f"&cursor={cursor}"
        j = _http(url)
        if not j or not j.get("result"):
            break
        out.extend(j["result"])
        cursor = j.get("cursor")
        if not cursor or j.get("page", 1) >= j.get("pages", 1):
            break
    return out


def norm_doi(url):
    if not url:
        return None
    m = re.search(r"(10\.\d{4,9}/[^\s?#]+?)(?:\?|#|$)", url)
    return m.group(1).rstrip("/.").lower() if m else None


def all_people():
    out = {}
    for p in DATA["people"]:
        out.setdefault(p["slug"], p["name"])
    for a in DATA["alumni"]:
        if a.get("slug"):
            out.setdefault(a["slug"], a["name"])
    for f in DATA["former"]:
        out.setdefault(f["slug"], f["name"])
    return out


def orcid_of(slug):
    for l in (PROFILES.get(slug) or {}).get("links", []):
        if l.get("type") == "orcid":
            m = re.search(r"(\d{4}-\d{4}-\d{4}-[\dX]{4})", l.get("url", ""), re.I)
            if m:
                return m.group(1).upper()
    return None


# ------------------------------------------------------------------ phase 1: discovery
def discover(article_cache):
    orcid2colab, name2colab = {}, {}

    def add(a):
        cid = a.get("colab_id")
        if not cid:
            return
        if a.get("orcid"):
            orcid2colab.setdefault(a["orcid"].upper(), cid)
        fam = (a.get("family") or "").strip().lower()
        giv = (a.get("given") or "").strip().lower()
        if fam:
            name2colab.setdefault((fam, giv[:1]), cid)

    for doi in filter(None, (norm_doi(p["doi"]) for p in DATA["pubs"])):
        item = get_article(doi)
        if item:
            article_cache[doi] = item
            for a in item.get("authors", []):
                add(a)
        sys.stdout.write("."); sys.stdout.flush()
    print()

    ids, by = {}, {}
    p = os.path.join(HERE, "colab_ids.json")
    if os.path.exists(p):
        for k, v in json.load(open(p, encoding="utf-8")).items():
            if not k.startswith("_"):
                ids[k], by[k] = v, "kept"

    def match():
        added = 0
        for slug in PEOPLE:  # canonical roster (final slugs, incl. null-slug alumni)
            if slug in ids:
                continue
            oc = orcid_of(slug)
            if oc and oc in orcid2colab:
                ids[slug], by[slug] = orcid2colab[oc], "orcid"; added += 1; continue
            fams, initial = PEOPLE.get(slug, ([], ""))
            for fam in fams:
                if (fam, initial) in name2colab:
                    ids[slug], by[slug] = name2colab[(fam, initial)], "name"; added += 1; break
        return added

    match()
    # Iteratively harvest coauthors of matched members (Chusov's ~35 coauthors carry the group).
    fetched = set()
    for _ in range(6):
        todo = [cid for cid in ids.values() if cid not in fetched]
        if not todo:
            break
        for cid in todo:
            fetched.add(cid)
            it = get_researcher(cid)
            for c in (it or {}).get("coauthors", []):
                add(c)
        if match() == 0 and not [c for c in ids.values() if c not in fetched]:
            break

    # Supplementary source: researchers registered on the group's colab lab page
    # (catches members who aren't reachable through the coauthor graph, e.g. the admin).
    r = subprocess.run(["curl", "-sL", "--max-time", "45", f"https://colab.ws/labs/{LAB_ID}"],
                       capture_output=True, text=True)
    lab_html = r.stdout if r.returncode == 0 else ""
    for rid in dict.fromkeys(re.findall(r"researchers/(R-[A-Z0-9-]{5,})", lab_html)):
        if rid in ids.values():
            continue
        it = get_researcher(rid)
        if not it:
            continue
        nm = it.get("names") or {}
        add({"colab_id": rid, "orcid": (it.get("ids") or {}).get("orcid"),
             "family": nm.get("surname_en"), "given": nm.get("name_en")})
    match()

    out = {"_comment": "slug -> colab.ws researcher id, auto-discovered by ORCID then name from "
                       "the group's papers and Chusov's coauthors. Hand-edit freely; edits are kept."}
    out.update(dict(sorted(ids.items())))
    json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tally = {m: sum(1 for s in by if by[s] == m) for m in ("orcid", "name", "kept")}
    print(f"colab_ids: {len(ids)}/{len(PEOPLE)} matched "
          f"(orcid={tally['orcid']} name={tally['name']} kept={tally['kept']})")
    return ids


# ------------------------------------------------------------------ phase 2: per-person
def fetch_people(ids, article_cache):
    people = {}
    for slug, cid in ids.items():
        it = get_researcher(cid)
        if not it:
            print(f"  ! researcher fetch failed: {slug} ({cid})")
            continue
        rids = it.get("ids") or {}
        people[slug] = {
            "colab_id": cid,
            "citations": it.get("citations_count"),
            "h_index": it.get("h_index"),
            "articles_count": it.get("articles_count"),
            "ids": {"orcid": rids.get("orcid"), "scopus": rids.get("scopus_id"),
                    "scholar": rids.get("google_scholar_id"), "wos": rids.get("rid")},
            "interests_en": [i["name_en"].strip() for i in it.get("interests", []) if i.get("name_en")],
            "interests_ru": [i["name_ru"].strip() for i in it.get("interests", []) if i.get("name_ru")],
        }
    articles = {doi: {"citations": it.get("citations_count")}
                for doi, it in article_cache.items() if it.get("citations_count") is not None}
    meta = {"_fetched": time.strftime("%Y-%m-%d"), "people": people, "articles": articles}
    json.dump(meta, open(os.path.join(HERE, "colab_meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    withstats = sum(1 for v in people.values() if v.get("citations") is not None)
    print(f"colab_meta: {len(people)} people ({withstats} with metrics), {len(articles)} article citations")
    return meta


PREPRINT = re.compile(r"10\.(26434|48550|21203|1101|31219|31224)/|chemrxiv|arxiv|biorxiv|ssrn", re.I)


def detect_new_pubs():
    """Recent group papers not yet on the site, for review / drafting.

    colab's /articles?filter=researcher endpoint currently 500s, so we enumerate
    Chusov's works via OpenAlex (already used by fetch_pub_meta.py) by ORCID and
    keep only: real journal articles (no preprints), published in the last ~2 years,
    not already listed (by DOI or title), and co-authored by >=1 other group member.
    """
    chusov = orcid_of("denis-chusov")
    if not chusov:
        return
    member_orcids = {o for s in PEOPLE if (o := orcid_of(s))}
    # ignore unpromoted auto-drafts so they stay detectable (re-placeable) on re-runs
    curated = [p for p in DATA["pubs"] if not p.get("draft")]
    site_dois = {norm_doi(p["doi"]) for p in curated}
    site_titles = {re.sub(r"[^a-z0-9]", "", (p["title"] or "").lower())[:40] for p in curated}
    max_year = max((p.get("year") or 0) for p in DATA["pubs"])

    works, cursor = [], "*"
    for _ in range(6):
        j = _http(f"https://api.openalex.org/works?filter=author.orcid:{chusov}"
                  f"&per-page=200&cursor={cursor}&mailto=fedundfed@gmail.com")
        if not j or not j.get("results"):
            break
        works += j["results"]
        cursor = (j.get("meta") or {}).get("next_cursor")
        if not cursor:
            break

    new = []
    for w in works:
        doi = norm_doi(w.get("doi"))
        if not doi or doi in site_dois:
            continue
        if PREPRINT.search(doi) or w.get("type") in ("posted-content", "preprint"):
            continue
        year = w.get("publication_year")
        if not year or year < max_year - 1:
            continue
        if re.sub(r"[^a-z0-9]", "", (w.get("title") or "").lower())[:40] in site_titles:
            continue
        au = {(a.get("author") or {}).get("orcid") for a in w.get("authorships", [])}
        au = {o.rsplit("/", 1)[-1].upper() for o in au if o}
        b = w.get("biblio") or {}
        new.append({
            "doi": "https://doi.org/" + doi, "title": w.get("title"), "year": year,
            "journal": ((w.get("primary_location") or {}).get("source") or {}).get("display_name"),
            "volume": b.get("volume"), "issue": b.get("issue"),
            "pages": f"{b['first_page']}-{b['last_page']}" if b.get("first_page") else None,
            "cited_by": w.get("cited_by_count"),
            "group_coauthors": sorted((au & member_orcids) - {chusov}),
        })
    confident = [p for p in new if p["group_coauthors"]]
    report = {"_fetched": time.strftime("%Y-%m-%d"), "_source": "OpenAlex (colab list endpoint down)",
              "confident_new_group_papers": sorted(confident, key=lambda x: -x["year"]),
              "other_new_candidates": sorted([p for p in new if not p["group_coauthors"]],
                                             key=lambda x: -x["year"])}
    json.dump(report, open(os.path.join(HERE, "colab_new_pubs.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"new-pubs: {len(confident)} confident group paper(s), "
          f"{len(new) - len(confident)} other candidates -> colab_new_pubs.json")
    return confident


def _draft_ref(p):
    j = (p.get("journal") or "").strip().rstrip(".")
    head = f"{j} {p['year']}" if p.get("year") else j
    tail = ", ".join(str(x) for x in (p.get("volume"), p.get("issue"), p.get("pages")) if x)
    return f"{head}, {tail}" if tail else head


def add_drafts(confident):
    """Insert confident new papers into site_data.json as drafts, at their
    date-appropriate position (n=1 is newest), then renumber.

    Unpromoted auto-drafts are removed and re-inserted each run, so placement stays
    correct and re-runs are idempotent. A draft the maintainer has curated (removed
    the "draft" flag) is left untouched. Regenerate pub_meta/people_pubs afterwards.
    """
    if not confident:
        print("  no confident new papers to insert."); return 0
    # drop existing auto-drafts so we can re-place them cleanly
    DATA["pubs"] = [p for p in DATA["pubs"] if not p.get("draft")]
    present = {norm_doi(p["doi"]) for p in DATA["pubs"]}
    fresh = [p for p in confident if norm_doi(p["doi"]) not in present]
    if not fresh:
        print("  new papers already curated on the site — nothing to insert.")
    drafts = [{
        "n": None, "year": p.get("year"), "title": p.get("title"), "title_link": None,
        "journal_line": _draft_ref(p), "doi": p["doi"], "toc": None, "toc_local": "",
        "journal_ref": _draft_ref(p), "impact": None, "draft": True,
    } for p in fresh]
    pubs = DATA["pubs"]
    for d in sorted(drafts, key=lambda d: -(d["year"] or 0)):  # newest draft first
        y = d["year"] or 0
        idx = next((i for i, p in enumerate(pubs) if (p.get("year") or 0) <= y), len(pubs))
        pubs.insert(idx, d)  # becomes the newest paper of its year
    for i, p in enumerate(pubs, 1):
        p["n"] = i
    assert [p["n"] for p in pubs] == list(range(1, len(pubs) + 1))
    json.dump(DATA, open(os.path.join(HERE, "site_data.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for d in drafts:
        print(f"  + draft #{d['n']}: {d['year']} {d['journal_ref']} — {(d['title'] or '')[:48]}")
    print(f"  pubs now {len(pubs)}. REGENERATE next:")
    print("    python3 _build/fetch_pub_meta.py && python3 _build/match_people.py && python3 _build/build.py")
    return len(drafts)


def main():
    cache = {}
    print("phase 1: discovering colab_ids (articles + Chusov's coauthors + lab page)...")
    ids = discover(cache)
    print("phase 2: assembling per-researcher metrics/interests...")
    fetch_people(ids, cache)
    print("phase 3: detecting new group publications...")
    confident = detect_new_pubs()
    if "--add-drafts" in sys.argv:
        print("phase 4: inserting drafts into site_data.json...")
        add_drafts(confident or [])
    print(f"colab API calls this run: {_quota['calls']}"
          + (f", quota left: {_quota['left']}" if _quota["left"] is not None else ""))


if __name__ == "__main__":
    main()
