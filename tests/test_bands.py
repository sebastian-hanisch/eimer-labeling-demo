"""Die festen Messreihen (data/laeufe_v10.json, data/dualpreise_v10.json): Aufbau, Quellenangaben, Stichprobe neu gerechnet mit dem Kern.

Die Zahlen sind mit dem Kern dieser Demo neu gerechnet (tools/bands_bauen.py) und beim Bau mit den Rohausgaben der Vormessung abgeglichen (data/vormessung_abgleich.json); der Abgleich selbst
läuft nicht in der Testsuite (die Rohausgaben liegen nicht im Repo). Hier wird geprüft, dass die Datei vollständig ist und dass eine Stichprobe der Läufe mit den gespeicherten Dualpreisen und dem
Kern dieselben Zahlen ergibt."""

import json
from pathlib import Path

import pytest

import eml_algorithm as A
import eml_colgen as G
import eml_constants as C
import eml_evaluation as ev
from eml_scenario import make_instance

DATA = Path(__file__).resolve().parent.parent / "data"
BANDS = ev.load_bands()
DUALS = json.loads((DATA / "dualpreise_v10.json").read_text(encoding="utf-8"))["instanzen"]


def _instance_of(lauf):
    return make_instance(30, lauf["seed"], lauf["breite"], capacity=lauf["Q"], clustered=(lauf["typ"] == "cluster"))


def test_the_bands_have_the_documented_shape():
    assert len(BANDS) == 320
    cells = {}
    for x in BANDS:
        cells.setdefault((x["Q"], x["runde"]), []).append(x)
        assert set(x["einstellungen"]) == set(C.BAND_CONFIGS) and len(C.BAND_CONFIGS) == 14
        assert all(len(v) == 7 for v in x["einstellungen"].values())
    assert sorted(cells) == [(q, r) for q in (70, 120) for r in ("1", "3", "8", "ende")]
    assert all(len(v) == 40 for v in cells.values())                        # 2 Typen x 2 Breiten x 10 Zufalls-Seeds je Zelle
    for x_list in cells.values():
        assert {(x["typ"], x["breite"], x["seed"]) for x in x_list} == {(t, b, s) for t in ("zufall", "cluster") for b in (40, 100) for s in range(10)}
    # Kapazität 70 und 120 benutzen dieselben Zufalls-Seeds
    assert {(x["typ"], x["breite"], x["seed"]) for x in ev.select(BANDS, 70)} == {(x["typ"], x["breite"], x["seed"]) for x in ev.select(BANDS, 120)}


def test_every_run_names_its_source_and_its_duals():
    for x in BANDS:
        assert "tools/bands_bauen.py" in x["quelle"] and "out_v10_mess_" in x["quelle"]
        key = f"{x['typ']}|{x['breite']}|{x['seed']}|{x['Q']}"
        assert x["dualpreise"] == key and x["runde"] in DUALS[key]["dualpreise"] and "tools/bands_bauen.py" in DUALS[key]["quelle"]
    assert len(DUALS) == 80 and all("ende" in v["dualpreise"] and len(v["dualpreise"]["ende"]) == 31 for v in DUALS.values())


def test_every_setting_has_the_result_of_the_run_without_buckets():
    rows = [v for x in BANDS for v in x["einstellungen"].values()]
    assert len(rows) == 4480 and all(v[5] is True for v in rows)
    for x in BANDS:
        base = x["einstellungen"][(0, 0)]
        assert all(v[0] == base[0] and v[1] == base[1] for v in x["einstellungen"].values())          # gleiche Zahl erzeugter und gestrichener Labels
        assert all(v[3] <= base[3] for v in x["einstellungen"].values())                              # cmp2 nie mehr als ohne Eimer


def test_a_sample_of_runs_recomputes_to_the_stored_counters():
    small = sorted(BANDS, key=lambda x: x["einstellungen"][(0, 0)][0])
    sample = small[:6] + [small[160]] + [small[250]]
    for x in sample:
        inst = _instance_of(x)
        pi = DUALS[x["dualpreise"]]["dualpreise"][x["runde"]]
        for cfg, stored in x["einstellungen"].items():
            r = A.price(inst, pi, 5, cfg[0] or None, cfg[1] or None, max_routes=10 ** 6)
            assert [r.generated, r.dominated, r.cmp1, r.cmp2, r.steps] == stored[:5], (x["typ"], x["breite"], x["seed"], x["Q"], x["runde"], cfg)


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_the_column_generation_reproduces_the_stored_bound(seed):
    """Die Schranke der Spaltenerzeugung ist eindeutig (die Dualpreise bei Entartung nicht): sie muss mit der gespeicherten übereinstimmen."""
    inst = make_instance(30, seed, 40, capacity=70)
    cg = G.colgen_duals(inst, 5, rounds=())
    stored = DUALS[f"zufall|40|{seed}|70"]
    assert cg["bound"] == pytest.approx(stored["schranke"], rel=1e-9) and not cg["aborted"]
    assert abs(cg["iters"] - stored["iterationen"]) <= 3


def test_the_comparison_with_the_raw_output_of_the_earlier_measurement_is_recorded():
    rec = json.loads((DATA / "vormessung_abgleich.json").read_text(encoding="utf-8"))
    assert rec["zeilen_neu"] == rec["zeilen_gleich"] == 4480 and rec["zeilen_abweichend"] == 0 and rec["zeilen_ohne_rohzeile"] == 0
    assert rec["dualpreise_verglichen"] == 320 and rec["dualpreise_groesste_abweichung"] < 1e-9


def test_the_evaluation_helpers_on_the_bands():
    table = ev.band_table(BANDS, 70, "ende", 0.1)
    assert [r["cfg"] for r in table] == list(C.BAND_CONFIGS) and all(r["n"] == 40 for r in table)
    assert table[0]["median"] == table[0]["mean"] == table[0]["max"] == 1.0
    # Mittel liegt zwischen kleinstem und größtem Wert; der Median ebenfalls
    for r in table[1:]:
        lo = min(ev.band_ratio(x, r["cfg"]) for x in ev.select(BANDS, 70, "ende"))
        assert lo <= r["median"] <= r["max"] and lo <= r["mean"] <= r["max"]
    counts = ev.optimum_counts(BANDS, 70, 0.1)
    assert sum(counts["counts"].values()) == counts["n"] == 160
    assert sum(r["n"] for r in ev.label_class_table(BANDS)) == 320
