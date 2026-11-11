"""Erzeugt die festen Messreihen (data/*.json): rechnet die 320 Läufe der Messung mit dem Kern der Demo neu und gleicht sie mit den Rohausgaben der Vormessung ab.

Zwei Schritte (im Ordner der Demo, Python des Test-venv):

1. Messen (neu gerechnet mit dem Kern der Demo: Spaltenerzeugung `eml_colgen.py` für die Dualpreise, danach `eml_algorithm.price` mit den 14 Eimer-Einstellungen):
       python tools/bands_bauen.py messen --typ zufall --Q 70 --out roh_zufall_70.jsonl
   (je Instanz-Typ und Kapazität ein Aufruf; vier Aufrufe können parallel laufen). Je Instanz (n = 30, Fensterbreite 40 und 100, Zufalls-Seeds 0 bis 9, Gedächtnis k = 5) rechnet er die
   Spaltenerzeugung mit Überdeckungs-Master, nimmt die Dualpreise der Runden 1, 3, 8 und am Ende und löst das Preisproblem je Einstellung. Eine Zeile je Instanz.
2. Bauen (liest die Rohzeilen und die Rohausgaben der Vormessung):
       python tools/bands_bauen.py bauen roh_*.jsonl --vormessung <Ordner label-setting-planung/vormessung>
   schreibt data/laeufe_v10.json (alle neu gerechneten Läufe), data/dualpreise_v10.json (die Dualpreise, mit denen gerechnet wurde) und data/vormessung_abgleich.json
   (Vergleich jeder neu gerechneten Zeile mit der Rohausgabe `out_v10_mess_*.txt`: Zeilen, die in Labels, Dominanzvergleichen und Eimerschritten übereinstimmen)."""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DATA = ROOT / "data"
CONFIGS = [(None, None), (1, None), (2, None), (5, None), (10, None), (20, None), (40, None), (80, None),
           (None, 5), (None, 10), (10, 5), (10, 10), (20, 10), (5, 5)]
WIDTHS, SEEDS, N, K = (40, 100), range(10), 30, 5


def messen(args) -> None:
    import eml_algorithm as A
    import eml_colgen as G
    from eml_scenario import make_instance

    with open(args.out, "a", encoding="utf-8") as out:
        for width in WIDTHS:
            for seed in SEEDS:
                inst = make_instance(N, seed, width, capacity=args.Q, clustered=(args.typ == "cluster"))
                t0 = time.perf_counter()
                cg = G.colgen_duals(inst, K, rounds=(1, 3, 8))
                assert not cg["aborted"]
                dual_sets = {str(r): pi for r, pi in sorted(cg["duals"].items())}
                dual_sets["ende"] = cg["ende"]
                row = {"typ": args.typ, "breite": width, "seed": seed, "Q": args.Q, "iterationen": cg["iters"], "schranke": cg["bound"],
                       "sekunden_colgen": round(time.perf_counter() - t0, 2), "dualpreise": dual_sets, "laeufe": {}}
                for rnd, pi in dual_sets.items():
                    base = None
                    runs = {}
                    for wt, wq in CONFIGS:
                        t1 = time.perf_counter()
                        res = A.price(inst, pi, K, wt, wq, max_routes=10 ** 6)
                        dt = time.perf_counter() - t1
                        if wt is None and wq is None:
                            base = res
                        same = res.routes == base.routes and res.live == base.live and res.generated == base.generated and res.dominated == base.dominated
                        runs[f"{wt or 0},{wq or 0}"] = [res.generated, res.dominated, res.cmp1, res.cmp2, res.steps, bool(same), round(dt, 3)]
                    row["laeufe"][rnd] = runs
                out.write(json.dumps(row) + "\n")
                out.flush()
                print(args.typ, args.Q, width, seed, "fertig", flush=True)


def _rohzeilen(folder: Path) -> dict:
    """Rohausgaben der Messung V10: (typ, breite, seed, Q, runde, wt, wq) -> (labels, dominiert, cmp1, cmp2, steps)."""
    raw = {}
    for f in sorted(folder.glob("out_v10_mess_*.txt")):
        for line in f.read_text(encoding="utf-8").splitlines()[1:]:
            p = line.split()
            if len(p) < 16:
                continue
            raw[(p[0], int(p[1]), int(p[2]), int(p[4]), p[5], int(p[6]), int(p[7]))] = (int(p[8]), int(p[9]), int(p[10]), int(p[11]), int(p[12]), f.name)
    return raw


def bauen(args) -> None:
    rows = []
    for path in args.rohdateien:
        rows += [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    rows.sort(key=lambda r: (r["typ"], r["Q"], r["breite"], r["seed"]))
    folder = Path(args.vormessung)
    raw = _rohzeilen(folder)
    heute = date.today().isoformat()
    laeufe, duals, gleich, ungleich, fehlend = [], {}, 0, 0, 0
    dual_diff = []
    for r in rows:
        key = f"{r['typ']}|{r['breite']}|{r['seed']}|{r['Q']}"
        v9 = json.loads((folder / f"v9_duale_{r['typ']}_Q{r['Q']}.json").read_text(encoding="utf-8"))[f"{r['typ']}|{r['breite']}|{r['seed']}|{K}"]
        duals[key] = {"quelle": f"tools/bands_bauen.py messen (Kern der Demo, eml_colgen.py, Überdeckungs-Master, k = {K}), Lauf vom {heute}", "iterationen": r["iterationen"],
                      "schranke": r["schranke"], "dualpreise": r["dualpreise"]}
        for rnd, pi in r["dualpreise"].items():
            ref = v9["ende"] if rnd == "ende" else v9["duals"].get(rnd)
            if ref is not None:
                dual_diff.append(max(abs(a - b) for a, b in zip(pi, ref)))
        for rnd, runs in r["laeufe"].items():
            src = None
            zeilen = {}
            for cfg, v in runs.items():
                wt, wq = (int(x) for x in cfg.split(","))
                ref = raw.get((r["typ"], r["breite"], r["seed"], r["Q"], rnd, wt, wq))
                if ref is None:
                    fehlend += 1
                else:
                    src = ref[5]
                    if tuple(v[:5]) == ref[:5]:
                        gleich += 1
                    else:
                        ungleich += 1
                zeilen[cfg] = v
            laeufe.append({"typ": r["typ"], "breite": r["breite"], "seed": r["seed"], "Q": r["Q"], "runde": rnd, "dualpreise": key,
                           "quelle": f"neu gerechnet mit dem Kern der Demo (tools/bands_bauen.py, Lauf vom {heute}); verglichen mit {src or 'keiner Rohausgabe'} (Vormessung)",
                           "einstellungen": zeilen})
    DATA.mkdir(exist_ok=True)
    (DATA / "laeufe_v10.json").write_text(json.dumps({
        "hinweis": "Je Lauf (Instanz x Dualpreise einer Runde) die 14 Eimer-Einstellungen 'Zeitbreite,Lastbreite' (0 = kein Eimer): [erzeugte Labels, gestrichene Labels, Vergleiche cmp1, "
                   "Vergleiche cmp2, Eimerschritte, Ergebnis gleich dem Lauf ohne Eimer, Sekunden (nur Information, parallele Läufe)]. n = 30, Gedächtnis k = 5.",
        "laeufe": laeufe}, ensure_ascii=False, indent=0), encoding="utf-8")
    (DATA / "dualpreise_v10.json").write_text(json.dumps({
        "hinweis": "Dualpreise der Spaltenerzeugung (Überdeckungs-Master) je Instanz (Typ|Breite|Zufalls-Seed|Kapazität): Runden 1, 3, 8 und Ende; Index 0 ist das Depot.",
        "instanzen": duals}, ensure_ascii=False, indent=0), encoding="utf-8")
    (DATA / "vormessung_abgleich.json").write_text(json.dumps({
        "hinweis": "Abgleich der neu gerechneten Läufe mit den Rohausgaben der Vormessung (out_v10_mess_*.txt) beim Bau der Daten; nicht Teil der Testsuite.",
        "zeilen_neu": gleich + ungleich + fehlend, "zeilen_gleich": gleich, "zeilen_abweichend": ungleich, "zeilen_ohne_rohzeile": fehlend,
        "dualpreise_verglichen": len(dual_diff), "dualpreise_groesste_abweichung": max(dual_diff) if dual_diff else None,
        "quelle": "tools/bands_bauen.py bauen, Rohausgaben out_v10_mess_*.txt und v9_duale_*.json"}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(laeufe)} Läufe, Zeilen gleich {gleich}, abweichend {ungleich}, ohne Rohzeile {fehlend}; Dualpreise: größte Abweichung {max(dual_diff) if dual_diff else None}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("messen")
    m.add_argument("--typ", choices=("zufall", "cluster"), required=True)
    m.add_argument("--Q", type=int, choices=(70, 120), required=True)
    m.add_argument("--out", required=True)
    b = sub.add_parser("bauen")
    b.add_argument("rohdateien", nargs="+")
    b.add_argument("--vormessung", required=True)
    args = ap.parse_args()
    {"messen": messen, "bauen": bauen}[args.cmd](args)


if __name__ == "__main__":
    main()
