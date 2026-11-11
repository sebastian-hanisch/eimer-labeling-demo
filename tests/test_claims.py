"""Jede Zahl der README an festen Zufalls-Seeds (DEMO-PLAYBOOK §4, §11a): Handbeispiel exakt, Messreihen aus ihren Läufen abgeleitet (die Tabellen der README müssen zeichengleich aus
`data/laeufe_v10.json` entstehen), Zählungen statt Urteilswörter.

Zeiten werden nie festgeschrieben. Der Abgleich der Messreihe mit den Rohausgaben der früheren Messung steht in `data/vormessung_abgleich.json` (nicht in der Suite wiederholbar).
Zahl-zu-Test-Tabelle: README, Abschnitt „Befunde“."""

from pathlib import Path

import pytest

import eml_algorithm as A
import eml_constants as C
import eml_evaluation as ev
import readme_tables as T
from eml_scenario import HAND_DUALS, hand_instance

ROOT = Path(__file__).resolve().parent.parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
BANDS = ev.load_bands()


def _t(q, runde="ende"):
    return {r["cfg"]: r for r in ev.band_table(BANDS, q, runde, 0.1)}


# --- Handbeispiel ---------------------------------------------------------------------------------------------------------------------------

def test_hand_example_numbers_of_the_readme():
    rows = {(r["wt"], r["wq"]): r for r in ev.hand_overview()}
    base = rows[(0, 0)]
    assert (base["generated"], base["dominated"], base["cmp1"], base["cmp2"], base["steps"]) == (35, 11, 57, 45, 57)
    res = ev.hand_run(0, 0)
    assert len(res.live) == 24 and res.best[1] == (5, 6, 3) and res.best[0] == pytest.approx(-3)
    expected = {(10, 0): (57, 28, 174, 0.83), (0, 3): (52, 16, 149, 0.67), (10, 3): (52, 8, 477, 0.59), (5, 0): (57, 28, 296, 0.83), (5, 3): (52, 8, 818, 0.59)}
    for cfg, (c1, c2, steps, ratio) in expected.items():
        r = rows[cfg]
        assert (r["cmp1"], r["cmp2"], r["steps"]) == (c1, c2, steps) and r["comparisons"] / base["comparisons"] == pytest.approx(ratio, abs=0.005) and r["same"]
    for text in ("Ohne Eimer 57 + 45 = 102", "Zeit-Eimer 10: 57 + 28 = 85 (Anteil 0,83)", "Last-Eimer 3: 52 + 16 = 68 (0,67)", "Zeit 10 × Last 3: 52 + 8 = 60 (0,59)", "Zeit-Eimer 5: 57 + 28 = 85",
                 "Zeit 5 × Last 3: 52 + 8 = 60", "Eimerschritte: 57, 174, 149, 477, 296 und 818", "35 erzeugte Labels (das Start-Label mitgezählt), 11 gestrichen, 24 lebend am Ende",
                 "beste Route 5-6-3 mit reduzierten Kosten −3", "39 zulässige elementare Routen, 3 davon mit negativen Kosten"):
        assert text in README, text
    # Aufwand bei Gewicht 0,1 (Annahme): Vergleiche + 0,1 x Eimerschritte, Anteil am Aufwand ohne Eimer
    net = {cfg: r["net"] for cfg, r in rows.items()}
    assert net[(0, 0)] == pytest.approx(107.7)
    for cfg, value, ratio in [((10, 0), 102.4, 0.95), ((0, 3), 82.9, 0.77), ((10, 3), 107.7, 1.00), ((5, 0), 114.6, 1.06), ((5, 3), 141.8, 1.32)]:
        assert net[cfg] == pytest.approx(value, abs=0.05) and net[cfg] / net[(0, 0)] == pytest.approx(ratio, abs=0.005)
    for text in ("Aufwand ohne Eimer 107,7; mit Zeit-Eimer 10 102,4 (Anteil 0,95); mit Last-Eimer 3 82,9 (0,77); mit Zeit 10 × Last 3 107,7 (1,00); mit Zeit-Eimer 5 114,6 (1,06); mit Zeit 5 × Last 3 141,8 (1,32)",):
        assert text in README, text
    assert 1 - rows[(10, 0)]["comparisons"] / base["comparisons"] == pytest.approx(0.167, abs=0.0005) and "16,7 % weniger Vergleiche mit Zeit-Eimer 10" in README


def test_hand_single_decisions_and_rounding_margin_of_the_readme():
    with_b = {e["nr"]: e for e in ev.hand_run(10, 3, trace=True).events}
    without = {e["nr"]: e for e in ev.hand_run(0, 0, trace=True).events}
    pairs = {20: (3, 0, 3, 3), 32: (5, 0, 5, 5), 34: (3, 1, 6, 6), 15: (1, 1, 2, 2)}
    for nr, (a1, a2, b1, b2) in pairs.items():
        assert (len(with_b[nr]["ex1"]), len(with_b[nr]["ex2"]), len(without[nr]["ex1"]), len(without[nr]["ex2"])) == (a1, a2, b1, b2)
    assert [with_b[nr]["node"] for nr in (20, 32, 34, 15)] == [3, 1, 1, 6]
    for text in ("F20 (Kunde 3) drei Labels bei cmp1 und keines bei cmp2 (ohne Eimer 3 und 3)", "F32 (Kunde 1): 5 und 0 (ohne Eimer 5 und 5)", "F34 (Kunde 1): 3 und 1 (ohne Eimer 6 und 6)",
                 "F15 (Kunde 6): 1 und 1 (ohne Eimer 2 und 2)"):
        assert text in README, text
    rd = ev.rounding_difference()
    assert rd == {(10, 0): (28, 33), (10, 3): (8, 12)}
    assert "cmp2 bei Zeit-Eimer 10 gleich 33 statt 28 und bei Zeit 10 × Last 3 gleich 12 statt 8" in README and "bei Zeit-Eimer 10 gleich 33 statt 28" in README
    assert (ev.hand_run(10, 0, A.RAND_MESSCODE).cmp1, ev.hand_run(10, 0).cmp1) == (57, 57)


# --- Messreihen: Kopfzahlen -------------------------------------------------------------------------------------------------------------------

def test_headline_numbers_of_the_readme():
    import statistics
    base_labels = [x["einstellungen"][(0, 0)][0] for x in BANDS]
    assert statistics.median(base_labels) == 5141.5 and max(base_labels) == 293469
    share = statistics.median(x["einstellungen"][(0, 0)][1] / x["einstellungen"][(0, 0)][0] for x in BANDS)
    assert round(100 * share, 1) == 85.1
    assert len(BANDS) == 320 and ev.all_identical(BANDS) == (4480, 4480)
    for text in ("im Median 5 141,5 Labels je Lauf (höchstens 293 469) und streicht davon im Median 85,1 %", "320 Läufe (Instanz × Kapazität × Runde), je 14 Eimer-Einstellungen, 4 480 Zeilen",
                 "stimmen in 4 480 von 4 480 Zeilen überein", "In allen 4 480 Zeilen (320 Läufe × 14 Einstellungen, 30 Kunden, k = 5)"):
        assert text in README, text
    assert "im Median 5,9 Vergleiche je Label bei unter 2 000 Labels und 112,1 bei 50 000 Labels und mehr" in README
    classes = ev.label_class_table(BANDS)
    assert (round(classes[0]["per_label"], 1), round(classes[-1]["per_label"], 1)) == (5.9, 112.1)


def test_where_buckets_cost_more_comparisons_than_no_buckets():
    """Korrektur gegenüber dem Plan: cmp2 nie mehr als ohne Eimer; cmp1 in 1 025 von 4 160 Zeilen höher; die Summe in 9 von 4 160 Zeilen höher, nur Last-Eimer, nur gruppierte Kunden, größtes Verhältnis 1,102."""
    with_buckets = [(x, c) for x in BANDS for c in C.BAND_CONFIGS if c != (0, 0)]
    assert len(with_buckets) == 4160
    assert all(ev.band_ratio(x, c, "cmp2") <= 1.0 for x, c in with_buckets)
    assert sum(1 for x, c in with_buckets if ev.band_ratio(x, c, "cmp1") > 1.0) == 1025
    over = [(ev.band_ratio(x, c), x, c) for x, c in with_buckets if ev.band_ratio(x, c) > 1.0]
    assert len(over) == 9 and all(c in ((0, 5), (0, 10)) and x["typ"] == "cluster" for _, x, c in over)
    assert sorted(c for _, _, c in over).count((0, 5)) == 4 and sorted(c for _, _, c in over).count((0, 10)) == 5
    top = max(over, key=lambda o: o[0])
    assert round(top[0], 3) == 1.102 and (top[2], top[1]["Q"], top[1]["breite"], top[1]["seed"], top[1]["runde"]) == ((0, 5), 120, 100, 7, "8")
    for text in ("in allen 4 160 Zeilen mit Eimern gilt cmp2 mit Eimern ≤ cmp2 ohne Eimer", "cmp1 ist in 1 025 von 4 160 Zeilen höher als ohne Eimer", "Die Summe beider ist in 9 von 4 160 Zeilen höher als ohne Eimer, jeweils bei Last-Eimern (4-mal Last 5, 5-mal Last 10)",
                 "bei gruppiert verteilten Kunden, am stärksten mit dem Faktor 1,102", "(Last 5, Kapazität 120, Fensterbreite 100, Zufalls-Seed 7, Dualpreise der Runde 8)"):
        assert text in README, text


def test_counts_named_in_the_scenario_help_texts():
    zeit = [c for c in C.BAND_CONFIGS if c[0] and not c[1]]
    feinste = sum(1 for x in BANDS if ev.band_comparisons(x, (1, 0)) == min(ev.band_comparisons(x, c) for c in zeit))
    beide = sum(1 for x in BANDS if ev.band_comparisons(x, (10, 5)) < min(ev.band_comparisons(x, (10, 0)), ev.band_comparisons(x, (0, 5))))
    assert (feinste, beide) == (297, 316)
    assert "in der Messreihe in 297 von 320 Läufen" in C.PRESET_HELP["Sehr feine Zeit-Eimer (Breite 1)"] and "bei Zeit 10 × Last 5 in 316 von 320 Läufen" in C.PRESET_HELP["Zeit- und Last-Eimer zusammen"]
    assert "Unter den sieben Zeit-Breiten hat Breite 1 in 297 von 320 Läufen die wenigsten Vergleiche" in README and "als Zeit 10 und als Last 5 in 316 von 320 Läufen" in README


# --- Tabellen der README ----------------------------------------------------------------------------------------------------------------------

def test_the_band_tables_of_the_readme_are_derived_from_the_data():
    for q in (70, 120):
        rows = T.band_rows(BANDS, q)
        assert len(rows) == 14
        block = "\n".join(rows)
        assert block in README, f"Tabelle Kapazität {q} weicht von den Daten ab"
        assert T.BAND_HEADER in README
    assert "Median der Vergleiche ohne Eimer in dieser Zelle: 30 744." in README and "42 690,5 (ganzzahlig gerundet 42 690)" in README
    assert (_t(70)[(0, 0)]["comparisons_base"], _t(120)[(0, 0)]["comparisons_base"]) == (30744, 42690.5)


def test_label_class_and_optimum_tables_of_the_readme_are_derived_from_the_data():
    assert T.CLASS_HEADER in README and "\n".join(T.class_rows(BANDS)) in README
    assert T.OPTIMUM_HEADER in README and "\n".join(T.optimum_rows(BANDS)) in README


# --- Spannen und Aufteilungen ------------------------------------------------------------------------------------------------------------------

def test_median_ranges_of_the_readme():
    t70, t120 = _t(70), _t(120)
    saved = {cfg: (1 - t70[cfg]["median"], 1 - t120[cfg]["median"]) for cfg in C.BAND_CONFIGS if cfg != (0, 0)}
    zeit = [v for w in (1, 2, 5, 10, 20, 40, 80) for v in saved[(w, 0)]]
    last = [v for q in (5, 10) for v in saved[(0, q)]]
    assert (round(100 * min(zeit), 1), round(100 * max(zeit), 1)) == (6.8, 19.2)
    assert (round(100 * min(last), 1), round(100 * max(last), 1)) == (26.9, 30.9)
    assert [round(100 * v, 1) for v in saved[(5, 5)]] == [37.8, 38.6] and max(100 * v for cfg, vs in saved.items() for v in vs) == pytest.approx(100 * max(max(saved[(5, 5)]), max(saved[(10, 5)])))
    assert (round(t70[(1, 0)]["median"], 3), round(t70[(80, 0)]["median"], 3), round(t120[(1, 0)]["median"], 3), round(t120[(80, 0)]["median"], 3)) == (0.809, 0.928, 0.808, 0.932)
    for text in ("fällt das Verhältnis von 0,809 (Zeit 1) bis 0,928 (Zeit 80) bei Kapazität 70 und von 0,808 bis 0,932 bei Kapazität 120, also 6,8 bis 19,2 % weniger Vergleiche",
                 "Im Median 26,9 % (Last 10, Kapazität 70) bis 30,9 % (Last 5, Kapazität 120) weniger Vergleiche", "Zeit 5 × Last 5 im Median 37,8 % (Kapazität 70) und 38,6 % (Kapazität 120) weniger Vergleiche",
                 "Die Ersparnis liegt im Median bei 6,8 bis 19,2 % mit Zeit-Eimern, 26,9 bis 30,9 % mit Last-Eimern und bis zu 38,6 % mit beiden"):
        assert text in README, text
    assert saved[(0, 10)][0] == min(last) and saved[(0, 5)][1] == max(last)


def test_split_between_cmp1_and_cmp2():
    t70, t120 = _t(70), _t(120)
    zeit_c1 = [t[(w, 0)]["cmp1"] for t in (t70, t120) for w in (1, 2, 5, 10, 20, 40, 80)]
    zeit_c2 = [t[(w, 0)]["cmp2"] for t in (t70, t120) for w in (1, 2, 5, 10, 20, 40, 80)]
    last_c1 = [t[(0, q)]["cmp1"] for t in (t70, t120) for q in (5, 10)]
    last_c2 = [t[(0, q)]["cmp2"] for t in (t70, t120) for q in (5, 10)]
    assert [round(x, 3) for x in (min(zeit_c1), max(zeit_c1), min(zeit_c2), max(zeit_c2))] == [0.991, 0.999, 0.381, 0.807]
    assert [round(x, 3) for x in (min(last_c1), max(last_c1), min(last_c2), max(last_c2))] == [0.870, 0.885, 0.326, 0.437]
    assert round(100 * ev.cmp1_share(BANDS), 1) == 68.9
    assert "Zeit-Eimer lassen cmp1 im Median bei 0,991 bis 0,999 und cmp2 bei 0,381 bis 0,807" in README and "Last-Eimer lassen cmp1 bei 0,870 bis 0,885 und cmp2 bei 0,326 bis 0,437" in README
    assert "cmp1 macht ohne Eimer im Median 68,9 % aller Vergleiche aus" in README


def test_label_classes_of_the_readme():
    classes = ev.label_class_table(BANDS)
    assert [c["n"] for c in classes] == [59, 172, 79, 10] and sum(c["n"] for c in classes) == 320
    assert [round(c[(10, 0)], 3) for c in classes] == [0.858, 0.832, 0.824, 0.828] and [round(c[(0, 5)], 3) for c in classes] == [0.716, 0.750, 0.811, 0.693]
    for text in ("Zeit-Eimer 10 liegt im Median bei 0,858, 0,832, 0,824 und 0,828 in den Klassen unter 2 000, 2 000 bis 10 000, 10 000 bis 50 000 und ab 50 000 Labels (59, 172, 79 und 10 Läufe); Last 5 bei 0,716, 0,750, 0,811 und 0,693",):
        assert text in README, text


def test_net_effort_of_the_readme():
    t70, t120 = _t(70), _t(120)
    nets = {(q, w): t[(w, 0)]["net"] for q, t in ((70, t70), (120, t120)) for w in (1, 2, 5, 10, 20, 40, 80)}
    assert [round(nets[(70, w)], 3) for w in (20, 40, 80)] == [0.970, 0.951, 0.959] and [round(nets[(120, w)], 3) for w in (20, 40, 80)] == [0.939, 0.934, 0.956]
    saved = [100 * (1 - nets[(q, w)]) for q in (70, 120) for w in (20, 40, 80)]
    assert (round(min(saved), 1), round(max(saved), 1)) == (3.0, 6.6)
    fine = [nets[(q, w)] for q in (70, 120) for w in (1, 2, 5, 10)]
    assert (round(min(fine), 3), round(max(fine), 3)) == (1.033, 3.276) and all(x > 1 for x in fine)
    assert [round(t[(0, 10)]["net"], 3) for t in (t70, t120)] == [0.800, 0.799] and [round(t[(0, 5)]["net"], 3) for t in (t70, t120)] == [0.839, 0.865]
    for text in ("bei 0,970, 0,951 und 0,959 des Aufwands ohne Eimer bei Kapazität 70 und bei 0,939, 0,934 und 0,956 bei Kapazität 120, also 3,0 bis 6,6 % gespart; mit Zeit 1 bis 10 bei 1,033 bis 3,276, also mehr als ohne Eimer",
                 "Last 10 liegt bei 0,800 bzw. 0,799, also rund 20 % gespart; Last 5 bei 0,839 bzw. 0,865", "bleiben mit Zeit-Eimern höchstens 6,6 % (bei Breite 20, 40 oder 80), mit Last-Eimern rund 20 % (Breite 10)"):
        assert text in README, text


def test_optimum_of_the_readme():
    o = {(q, g): ev.optimum_counts(BANDS, q, g) for q in (70, 120) for g in C.BAND_WEIGHTS}
    assert o[(70, 0.0)]["counts"][(1, 0)] == 151 and o[(120, 0.0)]["counts"][(1, 0)] == 146
    assert o[(70, 0.1)]["counts"][(40, 0)] == 74 and o[(120, 0.1)]["counts"][(20, 0)] == 65 and (o[(70, 0.1)]["counts"][(0, 0)], o[(120, 0.1)]["counts"][(0, 0)]) == (24, 22)
    assert (o[(70, 1.0)]["counts"][(0, 0)], o[(120, 1.0)]["counts"][(0, 0)]) == (140, 126) and (o[(70, 0.0)]["counts"][(0, 0)], o[(120, 0.0)]["counts"][(0, 0)]) == (0, 0)
    assert [round(100 * x / 160) for x in (74, 65, 140, 126)] == [46, 41, 88, 79]
    for text in ("Bei Gewicht 0 ist Zeit 1 in 151 von 160 Läufen (Kapazität 70) und 146 von 160 (Kapazität 120) die beste Wahl; bei Gewicht 0,1 Zeit 40 in 74 von 160 (46 %) bei Kapazität 70 und Zeit 20 in 65 von 160 (41 %) bei Kapazität 120, ohne Eimer in 24 und 22 von 160; "
                 "bei Gewicht 1 ohne Eimer in 140 und 126 von 160 (88 % und 79 %)", "ist „ohne Eimer“ in 88 % (Kapazität 70) und 79 % (Kapazität 120) der Läufe die beste Wahl, bei Gewicht 0 nie"):
        assert text in README, text


def test_scenario_numbers_of_the_readme():
    from test_presets import EXPECTED
    for name, (kind, piece) in EXPECTED.items():
        numbers = piece.split(" Vergleichen")[0]                       # „5 106 statt 5 522“ bzw. mit Prozent
        before, after = numbers.split(" statt ")
        assert f"{after} → {before}" in README, name
    for text in ("Zeit 10: 5 522 → 5 106 (7,5 % weniger, netto mehr Aufwand)", "Last 5: 5 522 → 3 724 (32,6 %, netto weniger)", "Zeit 10 × Last 5: 5 522 → 3 586 (35,1 %, netto mehr)", "Zeit 1: 5 522 → 5 055 (8,5 %, netto mehr)",
                 "Zeit 40 bei Gewicht 1: 5 522 → 5 310 (3,8 %, netto mehr)", "gruppiert, Kapazität 120, Breite 100: 50 135 → 36 862 (26,5 %, netto weniger)"):
        assert text in README, text
    assert {n: EXPECTED[n][0] for n in EXPECTED} == {"Zeit-Eimer 10 (Voreinstellung)": "warning", "Last-Eimer 5": "success", "Zeit- und Last-Eimer zusammen": "warning", "Sehr feine Zeit-Eimer (Breite 1)": "warning",
                                                       "Verwaltung gleich teuer wie ein Vergleich (Gewicht 1)": "warning", "Gruppierte Kunden, Kapazität 120, Breite 100": "success"}


# --- Rechenbudget und Verweise ----------------------------------------------------------------------------------------------------------------

def test_budget_numbers_of_the_readme():
    assert (C.MAX_LABELS_COLGEN, C.MAX_LABELS_CALL, C.MAX_LABELS) == (400_000, 150_000, 60_000)
    assert "mehr als 400 000 erzeugten Labels in der Spaltenerzeugung oder mehr als 150 000 in einer Runde, bei mehr als 60 000 Labels im Lauf mit den gewählten Eimern" in README


def test_linked_demos_of_the_readme_exist_in_the_portfolio():
    """Verweise nur auf Demos, deren Ordner im Projektordner existiert (DEMO-PLAYBOOK §11 Punkt 1); ohne Projektordner (CI) entfällt die Prüfung."""
    import re
    portfolio = ROOT.parent
    names = set(re.findall(r"github\.com/sebastian-hanisch/([a-z0-9-]+)\)", README))
    assert {"crew-pairing-demo", "dominanz-labels-demo", "mehrere-grenzen-demo", "elementar-pricing-demo", "hub-labeling-demo"} <= names
    if (portfolio / "crew-pairing-demo").exists():
        assert all((portfolio / n).exists() for n in names), [n for n in names if not (portfolio / n).exists()]


def test_the_abgleich_record_is_stated_in_the_readme():
    assert "stimmen in 4 480 von 4 480 Zeilen überein, ebenso die 320 Dualpreis-Sätze (größte Abweichung 0,0)" in README and "data/vormessung_abgleich.json" in README
    assert HAND_DUALS[1:] == (5, 4.5, 9, 4.5, 7.5, 10.5) and hand_instance().n == 6
    assert "Dualpreise 5; 4,5; 9; 4,5; 7,5; 10,5" in README
