#!/usr/bin/env python3
"""Attribute publications to group members by Crossref author names.

Match rule: family-name variant AND given name compatible (first letter),
so that e.g. Dmitry Muratov (INEOS colleague) is not attributed to alumnus Karim Muratov.

Writes _build/people_pubs.json: {slug: {pubs: [n...], citations, h_index}}
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
META = json.load(open(os.path.join(HERE, "pub_meta.json"), encoding="utf-8"))

# slug -> (family variants (lowercase), given-name first letter(s) accepted)
PEOPLE = {
    # current members
    "denis-chusov": (["chusov"], "d"),
    "oleg-afanasyev": (["afanasyev", "afanas'ev"], "o"),
    "evgeniya-podyacheva": (["podyacheva"], "e"),
    "artemy-fatkulin": (["fatkulin"], "a"),
    "andrey-kozlov": (["kozlov"], "a"),
    "klim-birukov": (["biriukov", "birukov"], "k"),
    "alexandra-balalaeva": (["balalaeva"], "a"),
    "ilya-aniskin": (["aniskin"], "i"),
    "fedor-kluev": (["kliuev", "kluev"], "f"),
    "olesya-zvereva": (["zvereva"], "o"),
    "mikhail-losev": (["losev"], "m"),
    "taisiya-brylova": (["brylova"], "t"),
    "vasilii-korochancev": (["korochantsev", "korochancev"], "v"),
    "ivan-golub": (["golub"], "i"),
    "ivan-smirnov": (["smirnov"], "i"),
    "danil-rakitianskii": (["rakitianskii", "rakityanskii", "rakityansky"], "d"),
    "dmitrii-pozdniakov": (["pozdniakov", "pozdnyakov"], "d"),
    "alexander-modin": (["modin"], "a"),
    # alumni
    "alexei-moskovets": (["moskovets", "moskovez"], "a"),
    "niyaz-yagafarov": (["yagafarov"], "n"),
    "pavel-kolesnikov": (["kolesnikov"], "p"),
    "vasilii-fastovskiy": (["fastovskiy", "fastovsky", "fastovskii"], "v"),
    "mariya-makarova": (["makarova"], "m"),
    "karim-muratov": (["muratov"], "k"),
    "ekaterina-kuchuk": (["kuchuk"], "e"),
    "sofiya-runikhina": (["runikhina"], "s"),
    "alexey-tsygankov": (["tsygankov"], "a"),
    "vladimir-ostrovskii": (["ostrovskii", "ostrovsky"], "v"),
    "max-shandybo": (["shandybo"], "m"),
    "natalya-lebedeva": (["lebedeva"], "n"),
    # former (archived pages)
    "vsevolod-bondarenko": (["bondarenko"], "v"),
    "alexander-prokhorov": (["prokhorov"], "a"),
    "alexander-boldyrev": (["boldyrev"], "a"),
    "alexander-khailuk": (["khailuk", "hayluk"], "a"),
    "anastasiya-kamalova": (["kamalova"], "a"),
    "dmitry-malikov": (["malikov"], "d"),
}


def h_index(cites):
    cites = sorted((c for c in cites if c is not None), reverse=True)
    h = 0
    for i, c in enumerate(cites, 1):
        if c >= i:
            h = i
    return h


def main():
    result = {}
    for slug, (fams, initial) in PEOPLE.items():
        pubs = []
        for k, rec in META.items():
            if k == "_fetched":
                continue
            for a in rec["authors"]:
                fam = a["family"].lower().strip()
                giv = (a["given"] or "").strip().lower()
                if fam in fams and (not giv or giv[0] == initial):
                    pubs.append(int(k))
                    break
        pubs = sorted(set(pubs))
        cites = [META[str(n)]["cited_by"] for n in pubs]
        result[slug] = {
            "pubs": pubs,
            "n_pubs": len(pubs),
            "citations": sum(c for c in cites if c),
            "h_index": h_index(cites),
        }
    result["_fetched"] = META.get("_fetched")
    with open(os.path.join(HERE, "people_pubs.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    for slug, r in sorted(result.items(), key=lambda x: -x[1]["n_pubs"] if isinstance(x[1], dict) else 0):
        if isinstance(r, dict):
            print(f"{slug:26s} pubs={r['n_pubs']:3d} cites={r['citations']:5d} h={r['h_index']}")


if __name__ == "__main__":
    main()
