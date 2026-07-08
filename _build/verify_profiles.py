#!/usr/bin/env python3
"""Find ORCID iDs for group members via OpenAlex + ORCID public APIs.

Verification: an OpenAlex author candidate counts as OUR person only if they are
listed as an author on one of the person's anchor papers (group publications).
People without publications are matched via ORCID affiliation (INEOS/HSE/MSU) only.

Writes /tmp candidates for review; final assembly is manual in profiles.json.
"""
import json
import subprocess
import time
import urllib.parse

SCRATCH = "/private/tmp/claude-501/-Users-kliuev-Documents-Proga-ChusovLab-site/972d4426-ca7f-4373-9fc0-c3ec485d4d5b/scratchpad"
DOSSIERS = json.load(open(f"{SCRATCH}/dossiers.json", encoding="utf-8"))

DONE = {"denis-chusov", "ilya-aniskin", "olesya-zvereva"}
AFFIL_OK = ("nesmeyanov", "organoelement", "higher school of economics",
            "lomonosov", "moscow state university", "ineos", "mendeleev university",
            "higher chemical college")


def get_json(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "40",
                        "-A", "ChusovGroupSite/1.0 (mailto:Chden@ya.ru)",
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {}


def openalex_verified(person):
    """Return verified OpenAlex author dict or None."""
    name = person["name"]
    anchors = [a["doi"] for a in person["anchor_papers"] if a.get("doi")]
    if not anchors:
        return None
    j = get_json(f"https://api.openalex.org/authors?search={urllib.parse.quote(name)}&per-page=8")
    for cand in j.get("results", []):
        aid = cand["id"].rsplit("/", 1)[-1]
        for doi in anchors[:2]:
            w = get_json(f"https://api.openalex.org/works?filter=author.id:{aid},doi:{doi}&per-page=1")
            if w.get("meta", {}).get("count", 0) > 0:
                return {"openalex_id": aid, "display_name": cand.get("display_name"),
                        "orcid": cand.get("orcid"),
                        "affil": [a["institution"]["display_name"] for a in cand.get("affiliations", [])][:4],
                        "verified_by": doi}
    # try family-name-only search as fallback
    fam = name.split()[-1]
    j = get_json(f"https://api.openalex.org/authors?search={urllib.parse.quote(fam)}&per-page=15")
    for cand in j.get("results", []):
        aid = cand["id"].rsplit("/", 1)[-1]
        for doi in anchors[:1]:
            w = get_json(f"https://api.openalex.org/works?filter=author.id:{aid},doi:{doi}&per-page=1")
            if w.get("meta", {}).get("count", 0) > 0:
                return {"openalex_id": aid, "display_name": cand.get("display_name"),
                        "orcid": cand.get("orcid"),
                        "affil": [a["institution"]["display_name"] for a in cand.get("affiliations", [])][:4],
                        "verified_by": doi}
    return None


def orcid_by_affiliation(person):
    """For people without anchor papers: ORCID search + affiliation filter."""
    parts = person["name"].split()
    given, family = parts[0], parts[-1]
    q = urllib.parse.quote(f'family-name:{family} AND given-names:{given}')
    j = get_json(f"https://pub.orcid.org/v3.0/expanded-search/?q={q}&rows=10")
    hits = []
    for r in (j.get("expanded-result") or []):
        insts = [i.lower() for i in (r.get("institution-name") or [])]
        if any(k in i for k in AFFIL_OK for i in insts):
            hits.append({"orcid": r["orcid-id"],
                         "name": f'{r.get("given-names","")} {r.get("family-names","")}',
                         "insts": (r.get("institution-name") or [])[:4]})
    return hits


results = {}
for p in DOSSIERS:
    if p["slug"] in DONE:
        continue
    entry = {"name": p["name"], "n_pubs": p["n_pubs"]}
    if p["anchor_papers"]:
        v = openalex_verified(p)
        entry["openalex"] = v
        if v and not v.get("orcid"):
            entry["orcid_affil_hits"] = orcid_by_affiliation(p)
    else:
        entry["orcid_affil_hits"] = orcid_by_affiliation(p)
    results[p["slug"]] = entry
    status = "OA✓" if entry.get("openalex") else ("orcid?" if entry.get("orcid_affil_hits") else "—")
    print(f'{p["slug"]:26s} {status}')
    time.sleep(0.15)

with open(f"{SCRATCH}/profile_candidates.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1, ensure_ascii=False)
print("saved profile_candidates.json")
