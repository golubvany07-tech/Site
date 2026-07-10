#!/usr/bin/env python3
"""Fetch authors + citation counts for every publication via Crossref (fallback: OpenAlex).

Usage: python3 _build/fetch_pub_meta.py
Writes _build/pub_meta.json  {pub_n: {doi, authors:[{given,family}], cited_by, source, fetched}}
Re-run any time to refresh citation counts.
"""
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = json.load(open(os.path.join(HERE, "site_data.json"), encoding="utf-8"))
UA = "ChusovGroupSite/1.0 (mailto:Chden@ya.ru)"


def extract_doi(url):
    if not url:
        return None
    m = re.search(r"pubs\.rsc\.org/en/content/articlelanding/\d+/\w+/(C\w+|D\w+)", url, re.I)
    if m:
        return "10.1039/" + m.group(1)
    m = re.search(r"(10\.\d{4,9}/[^\s?#]+?)(?:\?|#|$)", url)
    if m:
        return m.group(1).rstrip("/.")
    return None


def get_json(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA,
                        "-H", "Accept: application/json", url],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"curl failed for {url}")
    return json.loads(r.stdout)


def fetch_one(pub):
    doi = extract_doi(pub["doi"])
    rec = {"doi": doi, "authors": [], "cited_by": None, "source": None}
    if not doi:
        return pub["n"], rec
    # Crossref
    try:
        j = get_json(f"https://api.crossref.org/works/{doi}")["message"]
        rec["authors"] = [{"given": a.get("given", ""), "family": a.get("family", "")}
                          for a in j.get("author", [])]
        rec["cited_by"] = j.get("is-referenced-by-count")
        rec["source"] = "crossref"
    except Exception:
        pass
    # OpenAlex fallback / enrich
    if not rec["authors"] or rec["cited_by"] is None:
        try:
            j = get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
            if not rec["authors"]:
                for au in j.get("authorships", []):
                    name = au.get("author", {}).get("display_name", "")
                    parts = name.rsplit(" ", 1)
                    rec["authors"].append({"given": parts[0] if len(parts) > 1 else "",
                                           "family": parts[-1]})
            if rec["cited_by"] is None:
                rec["cited_by"] = j.get("cited_by_count")
            rec["source"] = (rec["source"] or "") + "+openalex"
        except Exception:
            pass
    return pub["n"], rec


def main():
    out = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for n, rec in ex.map(fetch_one, DATA["pubs"]):
            out[str(n)] = rec
            sys.stdout.write(".")
            sys.stdout.flush()
    print()
    out["_fetched"] = time.strftime("%Y-%m-%d")
    with open(os.path.join(HERE, "pub_meta.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    ok = sum(1 for k, v in out.items() if k != "_fetched" and v["authors"])
    cited = sum(1 for k, v in out.items() if k != "_fetched" and v["cited_by"] is not None)
    miss = [k for k, v in out.items() if k != "_fetched" and not v["authors"]]
    print(f"authors: {ok}/{len(DATA['pubs'])}, citations: {cited}/{len(DATA['pubs'])}, missing authors: {miss}")


if __name__ == "__main__":
    main()
