"""Verdikte an von Hand gesetzten Werten (DEMO-PLAYBOOK §12): jede Schwelle der Art und jede Zahl im Text steht hier.

Ein Verdikt ist eine reine Funktion (Art, Text) und bekommt Zahlen, keine Seeds."""

import eml_constants as C
import eml_evaluation as ev


def run(wt, wq, cmp1, cmp2, steps, generated=100, aborted=False, digest="a"):
    return ev.Run(wt, wq, generated, 60, cmp1, cmp2, steps, aborted, digest, 3, -5.0, (1,), 40)


BASE = run(0, 0, 700, 300, 100)          # 1000 Vergleiche, 100 angesehene Eimer


def test_formats():
    assert ev.fmt_int(30744) == "30 744" and ev.fmt_dec(0.809, 3) == "0,809" and ev.fmt_dec(-1.5, 1) == "−1,5" and ev.fmt_pct(7.5) == "7,5 %"
    assert ev.config_name(0, 0) == "ohne Eimer" and ev.config_name(10, 0) == "Zeit 10" and ev.config_name(0, 5) == "Last 5" and ev.config_name(10, 5) == "Zeit 10 × Last 5"


def test_verdict_identical_both_branches():
    assert ev.verdict_identical(True)[0] == "success" and "Dieselbe Menge lebender Labels wie ohne Eimer: ja" in ev.verdict_identical(True)[1]
    kind, text = ev.verdict_identical(False)
    assert kind == "error" and "Der Kern ist fehlerhaft" in text
    assert ev.same_result(BASE, run(10, 0, 1, 1, 1)) and not ev.same_result(BASE, run(10, 0, 1, 1, 1, digest="b"))


def test_verdict_saving_net_gain():
    """Zeit 10: 800 + 100 = 900... hier 600 + 100 = 700 Vergleiche (30 % weniger), 120 Eimerschritte: Aufwand 700 + 0,1 * 120 = 712 gegen 1000 + 0,1 * 100 = 1010: 70,5 %, netto 29,5 % gespart."""
    kind, text = ev.verdict_saving(BASE, run(10, 0, 450, 250, 120), 0.1)
    assert kind == "success"
    assert "Zeit 10: 700 statt 1 000 Vergleichen, also 30,0 % weniger" in text
    assert "120 angesehenen Eimern (Bezug: 100)" in text and "Gewicht von 0,10 je Eimerschritt (Annahme, keine Messung)" in text
    assert "70,5 % des Aufwands ohne Eimer" in text and "netto werden 29,5 % gespart" in text


def test_verdict_saving_threshold_is_the_effort_without_buckets():
    # Aufwand genau gleich (1010): keine Ersparnis nach Abzug; knapp darunter: success
    equal = run(10, 0, 500, 300, 110)          # 800 + 0,1 * 110 = 811 < 1010: gespart
    assert ev.verdict_saving(BASE, equal, 0.1)[0] == "success"
    kind, text = ev.verdict_saving(BASE, run(10, 0, 500, 300, 2100), 0.1)      # 800 + 210 = 1010 = Aufwand ohne Eimer
    assert kind == "warning" and "lohnt sich diese Eimerbreite nicht (netto 0,0 % mehr)" in text
    kind, text = ev.verdict_saving(BASE, run(10, 0, 500, 300, 5000), 0.1)      # 800 + 500 = 1300
    assert kind == "warning" and "netto 28,7 % mehr" in text and "also 20,0 % weniger" in text
    assert ev.verdict_saving(BASE, run(10, 0, 500, 300, 5000), 0.0)[0] == "success"      # Gewicht 0: nur die Vergleiche zählen


def test_verdict_saving_more_comparisons_and_no_saving_and_no_bucket():
    kind, text = ev.verdict_saving(BASE, run(0, 5, 800, 300, 10), 0.0)
    assert "also 10,0 % mehr" in text and kind == "warning"
    assert "keine Ersparnis" in ev.verdict_saving(BASE, run(10, 0, 700, 300, 100), 0.1)[1]
    kind, text = ev.verdict_saving(BASE, run(0, 0, 700, 300, 100), 0.1)
    assert kind == "info" and "Kein Eimer gewählt" in text and "1 000 Vergleichen" in text


def test_verdict_saving_aborted_baseline():
    kind, text = ev.verdict_saving(run(0, 0, 700, 300, 100, aborted=True), run(10, 0, 1, 1, 1, aborted=True), 0.1)
    assert kind == "warning" and f"{ev.fmt_int(C.MAX_LABELS)} erzeugten Labels abgebrochen" in text


def test_verdict_split_pattern_and_exception():
    zeit = run(10, 0, 697, 160, 500)            # cmp1 99,6 %, cmp2 53,3 %
    last = run(0, 5, 600, 120, 300)             # cmp1 85,7 %, cmp2 40 %
    kind, text = ev.verdict_split(BASE, zeit, last)
    assert kind == "success" and "Zeit 10 lässt cmp1 bei 99,6 % und cmp2 bei 53,3 % der Vergleiche ohne Eimer" in text and "Last 5 lässt cmp1 bei 85,7 % und cmp2 bei 40,0 %" in text
    assert "Die Zeit-Eimer sparen hier nur cmp2; die Last-Eimer sparen auch cmp1." in text
    kind, text = ev.verdict_split(BASE, run(10, 0, 500, 160, 500), last)              # Zeit-Eimer sparen auch cmp1: Muster gilt nicht
    assert kind == "info" and "nicht in dieser Deutlichkeit" in text
    kind, text = ev.verdict_split(BASE, run(10, 0, 697, 290, 500), run(0, 5, 698, 120, 300))      # Last spart cmp1 nicht mehr als Zeit
    assert kind == "info"
    assert ev.verdict_split(run(0, 0, 0, 300, 10), zeit, last)[0] == "info"


def test_verdict_optimum_and_best_width():
    # Aufwand je Zeit-Breite: ohne 1000 + 0,1*100; 80: 900 + 0,1*250; 10: 800 + 0,1*2000; 1: 700 + 0,1*20000
    runs = {(0, 0): run(0, 0, 700, 300, 100), (80, 0): run(80, 0, 650, 250, 250), (10, 0): run(10, 0, 600, 200, 2000), (1, 0): run(1, 0, 500, 200, 20000)}
    assert ev.best_zeit_width(runs, 0.0) == 1 and ev.best_zeit_width(runs, 0.1) == 80 and ev.best_zeit_width(runs, 1.0) == 0
    kind, text = ev.verdict_optimum(runs)
    assert kind == "info" and "Gewicht 0,0: Zeit-Breite 1; Gewicht 0,1: Zeit-Breite 80; Gewicht 1,0: ohne Eimer" in text
    runs[(1, 0)] = run(1, 0, 500, 200, 20000, aborted=True)
    assert ev.verdict_optimum(runs)[0] == "warning"


def test_verdict_monotone():
    runs = {(w, 0): run(w, 0, 700 - 10 * i, 200, 100 * (i + 1)) for i, w in enumerate(C.SWEEP_WT)}
    kind, text = ev.verdict_monotone(runs)
    assert kind == "info" and "steigen bei keinem Schritt der Reihe, von 900 ohne Eimer auf 830 bei Breite 1" in text and "von 100 auf 800" in text
    runs[(10, 0)] = run(10, 0, 900, 200, 500)
    kind, text = ev.verdict_monotone(runs)
    assert "steigen die Vergleiche mit dem feineren Eimer" in text and "Deutung (nicht eigens gemessen)" in text


def test_verdict_hand_each_branch():
    rows = ev.hand_overview()
    base = rows[0]
    assert (base["cmp1"], base["cmp2"], base["steps"]) == (57, 45, 57)
    kind, text = ev.verdict_hand(rows, 0, 0)
    assert kind == "info" and "57 Vergleiche für „wird das neue Label dominiert?“ und 45 für „dominiert das neue Label alte?“" in text
    kind, text = ev.verdict_hand(rows, 10, 3)
    assert kind == "success" and "dieselben 35 erzeugten Labels, dieselben 11 gestrichenen" in text and "52 + 8 = 60 Vergleiche statt 57 + 45 = 102" in text and "angesehene Eimer: 477 statt 57" in text
    broken = [dict(r, same=False) if (r["wt"], r["wq"]) == (10, 0) else r for r in rows]
    assert ev.verdict_hand(broken, 10, 0)[0] == "error"


def test_verdict_bands_counts_and_threshold():
    bands = ev.load_bands()
    kind, text = ev.verdict_bands(bands, 70, "ende", (10, 0), 0.1)
    assert kind == "warning" and "weniger Vergleiche als ohne Eimer in 40 von 40 Läufen (Median des Verhältnisses 0,828, Maximum 0,912)" in text and "weniger Aufwand in 12 von 40 Läufen (Median 1,050)" in text
    kind, _ = ev.verdict_bands(bands, 70, "ende", (0, 10), 0.1)          # Last 10: Median des Aufwands 0,800 < 1
    assert kind == "success"
