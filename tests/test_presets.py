"""Schnellstart-Szenarien: Vollständigkeit, gültige Werte, Standard-Szenario = Standardeinstellungen, und die erwartete Verdikt-Zeile je Szenario (DEMO-PLAYBOOK §11a Punkt 7)."""

import pytest

import eml_constants as C
import eml_evaluation as ev
import eml_presets as P

DEFAULT = "Zeit-Eimer 10 (Voreinstellung)"
# Erwartung je Szenario: Art des Verdikts der Ersparnis (Zufallsinstanz) und ein Textstück daraus; die Art des Handbeispiel-Verdikts ist immer "success" (andere Einstellung als „keine“)
EXPECTED = {
    "Zeit-Eimer 10 (Voreinstellung)": ("warning", "5 106 statt 5 522 Vergleichen, also 7,5 % weniger"),
    "Last-Eimer 5": ("success", "3 724 statt 5 522 Vergleichen, also 32,6 % weniger"),
    "Zeit- und Last-Eimer zusammen": ("warning", "3 586 statt 5 522 Vergleichen, also 35,1 % weniger"),
    "Sehr feine Zeit-Eimer (Breite 1)": ("warning", "5 055 statt 5 522 Vergleichen, also 8,5 % weniger"),
    "Verwaltung gleich teuer wie ein Vergleich (Gewicht 1)": ("warning", "5 310 statt 5 522 Vergleichen, also 3,8 % weniger"),
    "Gruppierte Kunden, Kapazität 120, Breite 100": ("success", "36 862 statt 50 135 Vergleichen, also 26,5 % weniger"),
}


def _live(p):
    s = ev.Settings(p["n"], p["width"], p["typ"], p["q"], p["seed"])
    cg = ev.live_duals(s)
    assert cg["ende"] is not None
    inst = ev.instance_of(s)
    return ev.live_run(inst, cg["ende"], 0, 0), ev.live_run(inst, cg["ende"], p["wt"], p["wq"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) == set(EXPECTED)
    for name, preset in C.PRESETS.items():
        assert set(preset) == set(P.PRESET_KEYS), name
        assert C.PRESET_HELP[name]


def test_preset_values_are_inside_the_widget_bounds():
    for name, p in C.PRESETS.items():
        assert p["hand_wt"] in C.HAND_WT_OPTIONS and p["hand_wq"] in C.HAND_WQ_OPTIONS and C.HAND_STEP_MIN <= p["step"] <= C.HAND_STEP_MAX, name
        assert C.N_MIN <= p["n"] <= C.N_MAX and p["width"] in C.WIDTH_OPTIONS and p["typ"] in C.TYP_OPTIONS and p["q"] in C.Q_OPTIONS, name
        assert 0 <= p["seed"] <= C.SEED_MAX and p["wt"] in C.WT_OPTIONS and p["wq"] in C.WQ_OPTIONS and C.WEIGHT_MIN <= p["weight"] <= C.WEIGHT_MAX, name


def test_default_preset_equals_the_default_settings():
    preset = C.PRESETS[DEFAULT]
    assert next(iter(C.PRESETS)) == DEFAULT
    for state_key, spec in P.SETTING_SPECS.items():
        key = next(k for k, v in P.PRESET_KEYS.items() if v == state_key)
        assert preset[key] == spec.default, state_key


def test_setting_specs_cover_every_preset_key_and_choices_are_the_constants():
    assert set(P.PRESET_KEYS.values()) == set(P.SETTING_SPECS)
    s = P.SETTING_SPECS
    assert (s["hand_wt_radio"].choices, s["hand_wq_radio"].choices, s["width_radio"].choices, s["typ_radio"].choices, s["q_radio"].choices, s["wt_select"].choices, s["wq_select"].choices) == \
           (C.HAND_WT_OPTIONS, C.HAND_WQ_OPTIONS, C.WIDTH_OPTIONS, C.TYP_OPTIONS, C.Q_OPTIONS, C.WT_OPTIONS, C.WQ_OPTIONS)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_expected_verdict_lines_of_every_preset(name):
    kind_expected, piece = EXPECTED[name]
    p = C.PRESETS[name]
    base, run = _live(p)
    assert ev.verdict_identical(ev.same_result(base, run))[0] == "success"
    kind, text = ev.verdict_saving(base, run, p["weight"])
    assert kind == kind_expected and piece in text, text
    rows = ev.hand_overview()
    assert ev.verdict_hand(rows, p["hand_wt"], p["hand_wq"])[0] == "success"


def test_the_help_texts_state_what_the_scenarios_show():
    """Hilfetexte sind Behauptungen: gemessen an der Instanz des Szenarios."""
    base, last = _live(C.PRESETS["Last-Eimer 5"])
    assert last.cmp1 < base.cmp1 and "auch Vergleiche der Prüfung „wird das neue Label dominiert?“" in C.PRESET_HELP["Last-Eimer 5"]
    p = C.PRESETS["Zeit- und Last-Eimer zusammen"]
    base, both = _live(p)
    _, last5 = _live(C.PRESETS["Last-Eimer 5"])
    _, zeit10 = _live(C.PRESETS[DEFAULT])
    assert both.comparisons < min(last5.comparisons, zeit10.comparisons) and both.steps > max(last5.steps, zeit10.steps)
    assert "weniger Vergleiche als mit einer Eimerart allein, aber auch viel mehr angesehene Eimer" in C.PRESET_HELP["Zeit- und Last-Eimer zusammen"]
    # feinste Zeit-Breite: die wenigsten Vergleiche unter allen Zeit-Eimern, die meisten Eimerschritte
    p = C.PRESETS["Sehr feine Zeit-Eimer (Breite 1)"]
    s = ev.Settings(p["n"], p["width"], p["typ"], p["q"], p["seed"])
    pi = ev.live_duals(s)["ende"]
    runs = {w: ev.live_run(ev.instance_of(s), pi, w, 0) for w in C.WT_OPTIONS if w}
    assert runs[1].comparisons == min(r.comparisons for r in runs.values()) and runs[1].steps == max(r.steps for r in runs.values())
    # Gewicht 1: mit Zeit-Eimer 40 ist der Aufwand höher als ohne Eimer
    p = C.PRESETS["Verwaltung gleich teuer wie ein Vergleich (Gewicht 1)"]
    base, run = _live(p)
    assert p["weight"] == 1.0 and ev.net_ratio(base, run, 1.0) > 1 and "lohnt sich diese Eimerbreite auf dieser Instanz nicht" in C.PRESET_HELP["Verwaltung gleich teuer wie ein Vergleich (Gewicht 1)"]
    # die letzte Instanz ist größer als die Voreinstellung
    big_base, _ = _live(C.PRESETS["Gruppierte Kunden, Kapazität 120, Breite 100"])
    default_base, _ = _live(C.PRESETS[DEFAULT])
    assert big_base.generated > default_base.generated and "eine größere Rechnung als die Voreinstellung" in C.PRESET_HELP["Gruppierte Kunden, Kapazität 120, Breite 100"]


def test_hand_step_of_each_preset_shows_a_saving_where_the_help_text_says_so():
    """Das gezeigte neue Label spart in jedem Szenario mit Eimern im Handbeispiel Vergleiche (Label 32 bzw. 34)."""
    for name, p in C.PRESETS.items():
        rows = ev.hand_step_rows(p["hand_wt"], p["hand_wq"])
        row = rows[p["step"] - 1]
        assert row["nr"] == p["step"] and row["cmp1"] + row["cmp2"] < row["base1"] + row["base2"], name

