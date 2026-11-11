"""Tabellen der README aus den Daten (zeichengleich); die Tests in `test_claims.py` verlangen, dass genau diese Zeilen in der README stehen. Aufruf zum Erzeugen: python tests/readme_tables.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import eml_constants as C  # noqa: E402
import eml_evaluation as ev  # noqa: E402

BAND_HEADER = ("| Einstellung | Läufe | Median | Mittel | Maximum | Median cmp1 | Median cmp2 | Median Eimerschritte | Median Aufwand (Gewicht 0,1) |\n"
               "|---|---|---|---|---|---|---|---|---|")


def band_rows(bands, q, runde="ende", weight=0.1) -> list:
    return [f"| {r['name']} | {r['n']} | {ev.fmt_ratio(r['median'])} | {ev.fmt_ratio(r['mean'])} | {ev.fmt_ratio(r['max'])} | {ev.fmt_ratio(r['cmp1'])} | {ev.fmt_ratio(r['cmp2'])} | "
            f"{ev.fmt_int(r['steps'])} | {ev.fmt_ratio(r['net'])} |" for r in ev.band_table(bands, q, runde, weight)]


def class_rows(bands) -> list:
    rows = []
    for r in ev.label_class_table(bands):
        label = f"{ev.fmt_int(r['lo'])} bis unter {ev.fmt_int(r['hi'])}" if r["hi"] < 10 ** 9 else f"ab {ev.fmt_int(r['lo'])}"
        rows.append(f"| {label} | {r['n']} | {ev.fmt_dec(r['per_label'], 1)} | {ev.fmt_ratio(r[(10, 0)])} | {ev.fmt_ratio(r[(1, 0)])} | {ev.fmt_ratio(r[(0, 5)])} | {ev.fmt_ratio(r[(10, 5)])} |")
    return rows


CLASS_HEADER = ("| Labels ohne Eimer | Läufe | Vergleiche je Label ohne Eimer (Median) | Zeit 10 | Zeit 1 | Last 5 | Zeit 10 × Last 5 |\n|---|---|---|---|---|---|---|")


def optimum_rows(bands) -> list:
    rows = []
    for q in (70, 120):
        for g in C.BAND_WEIGHTS:
            o = ev.optimum_counts(bands, q, g)
            best = max(o["counts"], key=lambda c: (o["counts"][c], -ev.ZEIT_CFGS.index(c)))
            none = o["counts"][(0, 0)]
            rows.append(f"| {q} | {ev.fmt_dec(g, 1)} | {ev.config_name(*best)}: {o['counts'][best]} von {o['n']} | ohne Eimer: {none} von {o['n']} |")
    return rows


OPTIMUM_HEADER = "| Kapazität | Gewicht je Eimerschritt | am häufigsten die beste Wahl | ohne Eimer die beste Wahl |\n|---|---|---|---|"

if __name__ == "__main__":
    b = ev.load_bands()
    for q in (70, 120):
        print(f"Kapazität {q}, Dualpreise am Ende\n" + BAND_HEADER)
        print("\n".join(band_rows(b, q)))
        print()
    print(CLASS_HEADER)
    print("\n".join(class_rows(b)))
    print()
    print(OPTIMUM_HEADER)
    print("\n".join(optimum_rows(b)))
