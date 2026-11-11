"""End-to-end-Tests über Streamlits AppTest: lädt app.py mit den Standardeinstellungen, klickt jeden Knopf, fährt jeden Regler an seine Grenzen, wählt jede Option,
prüft den Permalink und je Schnellstart-Szenario die erwartete Verdikt-Zeile. Expander werden nie per Index angesprochen (DEMO-PLAYBOOK §2 Punkt 7)."""

import os
import re

import pytest
from streamlit.testing.v1 import AppTest

import eml_constants as C
import eml_evaluation as ev
import eml_presets as P

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
TIMEOUT = int(os.environ.get("APPTEST_TIMEOUT", "300"))  # unter Last (parallele Läufe) reichen 180 s nicht immer; Umgebungsvariable zum Anpassen
AUTOPLAY_MARKER = "▶"  # Auto-Play-Buttons (Animation mit sleep) im Smoke-Test auslassen
SLIDER_KEYS = [k for k, spec in P.SETTING_SPECS.items() if spec.choices is None and spec.hi is not None and k != "seed_input"]
CHOICE_KEYS = {"hand_wt_radio": ("radio", C.HAND_WT_OPTIONS), "hand_wq_radio": ("radio", C.HAND_WQ_OPTIONS), "width_radio": ("radio", C.WIDTH_OPTIONS), "typ_radio": ("radio", C.TYP_OPTIONS),
               "q_radio": ("radio", C.Q_OPTIONS), "wt_select": ("selectbox", C.WT_OPTIONS), "wq_select": ("selectbox", C.WQ_OPTIONS)}


def _fresh_app(query=None) -> AppTest:
    at = AppTest.from_file(APP_PATH, default_timeout=TIMEOUT)
    if query:
        at.query_params.update(query)
    at.run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _texts(at, kind):
    return [e.value for e in getattr(at, kind)]


def _widget(at, kind, key):
    return getattr(at.sidebar, kind)(key=key)


def test_app_loads_without_exception():
    at = _fresh_app()
    assert at.title[0].value.endswith("Eimer im Labeling: wie viel sparen sie wirklich?")


def test_the_buttons_are_the_presets_and_the_new_instance_button():
    labels = [b.label for b in _fresh_app().sidebar.button]
    assert labels[: len(C.PRESETS)] == list(C.PRESETS) and labels[len(C.PRESETS):] == ["🎲 Neue Instanz generieren"]


@pytest.mark.parametrize("index", range(len(C.PRESETS) + 1))
def test_every_button_click_does_not_raise(index):
    at = _fresh_app()
    label = at.sidebar.button[index].label
    if AUTOPLAY_MARKER in label:
        pytest.skip("Auto-Play")
    at.sidebar.button[index].click().run(timeout=TIMEOUT)
    assert not at.exception, (label, [str(e) for e in at.exception])


@pytest.mark.parametrize("state_key", SLIDER_KEYS)
@pytest.mark.parametrize("edge", ["min", "max"])
def test_every_slider_at_its_min_and_max_does_not_raise(state_key, edge):
    at = _fresh_app()
    spec = P.SETTING_SPECS[state_key]
    value = spec.lo if edge == "min" else spec.hi
    at.sidebar.slider(key=state_key).set_value(value if isinstance(spec.default, float) else int(value)).run(timeout=TIMEOUT)
    assert not at.exception, (state_key, edge, [str(e) for e in at.exception])


@pytest.mark.parametrize("key", list(CHOICE_KEYS))
def test_every_option_of_every_choice_widget_does_not_raise(key):
    kind, options = CHOICE_KEYS[key]
    for option in options:
        at = _fresh_app()
        _widget(at, kind, key).set_value(option).run(timeout=TIMEOUT)
        assert not at.exception, (key, option, [str(e) for e in at.exception])


@pytest.mark.parametrize("n,width,typ,q,seed", [(C.N_MIN, 40, "zufall", 70, 0), (C.N_MIN, 100, "cluster", 120, C.SEED_MAX), (C.N_MAX, 40, "zufall", 70, 0), (C.N_MAX, 100, "zufall", 70, C.SEED_MAX)])
def test_corner_matrix_at_the_widget_edges(n, width, typ, q, seed):
    """Eckfall-Matrix (DEMO-PLAYBOOK §1d): Kundenzahl, Fensterbreite, Verteilung, Kapazität und Zufalls-Seed an den Rändern gemeinsam."""
    at = _fresh_app()
    at.sidebar.slider(key="n_slider").set_value(n)
    at.sidebar.radio(key="width_radio").set_value(width)
    at.sidebar.radio(key="typ_radio").set_value(typ)
    at.sidebar.radio(key="q_radio").set_value(q)
    at.sidebar.number_input(key="seed_input").set_value(seed)
    at.run(timeout=TIMEOUT)
    assert not at.exception, ((n, width, typ, q, seed), [str(e) for e in at.exception])
    assert at.sidebar.slider(key="n_slider").value == n


def test_worst_case_at_the_widget_maximum_stays_inside_the_budget():
    """Worst-Case (DEMO-PLAYBOOK §1c): n = 30, Fensterbreite 100, gruppiert, Kapazität 120, Zufalls-Seed 0 würde über 400 000 Labels in der Spaltenerzeugung erzeugen. Die App bricht ab,
    zeigt den Abbruch als Warnung statt als Fehler, und die festen Messreihen und das Handbeispiel erscheinen trotzdem."""
    at = _fresh_app({"n": "30", "breite": "100", "typ": "cluster", "q": "120", "seed": "0"})
    warnings = _texts(at, "warning")
    assert any("Die Spaltenerzeugung dieser Instanz" in w and "abgebrochen" in w for w in warnings)
    subheaders = [s.value for s in at.subheader]
    assert any(s.startswith("🔬 Experiment 1:") for s in subheaders) and any(s.startswith("🔬 Experiment 5:") for s in subheaders)
    assert not any(s.startswith("🔬 Experiment 2:") for s in subheaders)
    assert not at.error


def test_largest_instance_inside_the_budget_shows_every_experiment():
    at = _fresh_app({"n": "30", "breite": "100", "typ": "cluster", "q": "70", "seed": "3"})
    subheaders = [s.value for s in at.subheader]
    for number in range(1, 6):
        assert any(s.startswith(f"🔬 Experiment {number}:") for s in subheaders), number
    assert not at.error and not at.exception


def test_permalink_sets_the_widgets_and_clamps_invalid_values():
    at = _fresh_app({"hzeit": "5", "hlast": "3", "label": "7", "n": "14", "breite": "100", "typ": "cluster", "q": "120", "seed": "7", "zeit": "20", "last": "10", "gewicht": "0.55"})
    assert at.sidebar.radio(key="hand_wt_radio").value == 5 and at.sidebar.radio(key="hand_wq_radio").value == 3 and at.sidebar.slider(key="step_slider").value == 7
    assert at.sidebar.slider(key="n_slider").value == 14 and at.sidebar.radio(key="width_radio").value == 100 and at.sidebar.radio(key="typ_radio").value == "cluster"
    assert at.sidebar.radio(key="q_radio").value == 120 and at.sidebar.number_input(key="seed_input").value == 7
    assert at.sidebar.selectbox(key="wt_select").value == 20 and at.sidebar.selectbox(key="wq_select").value == 10
    assert at.sidebar.slider(key="weight_slider").value == pytest.approx(0.55)
    bad = _fresh_app({"label": "999", "n": "999", "breite": "123", "typ": "x", "q": "99", "seed": "-5", "zeit": "3", "last": "7", "gewicht": "9"})
    assert bad.sidebar.slider(key="step_slider").value == C.HAND_STEP_MAX and bad.sidebar.slider(key="n_slider").value == C.N_MAX
    assert bad.sidebar.radio(key="width_radio").value == C.DEFAULT_WIDTH and bad.sidebar.radio(key="typ_radio").value == C.DEFAULT_TYP and bad.sidebar.radio(key="q_radio").value == C.DEFAULT_Q
    assert bad.sidebar.number_input(key="seed_input").value == 0 and bad.sidebar.selectbox(key="wt_select").value == C.DEFAULT_WT and bad.sidebar.selectbox(key="wq_select").value == C.DEFAULT_WQ
    assert bad.sidebar.slider(key="weight_slider").value == C.WEIGHT_MAX
    garbage = _fresh_app({"n": "abc", "seed": "1.5", "gewicht": "nan", "hzeit": "x"})
    assert garbage.sidebar.slider(key="n_slider").value == C.DEFAULT_N and garbage.sidebar.number_input(key="seed_input").value == C.DEFAULT_SEED
    assert garbage.sidebar.radio(key="hand_wt_radio").value == C.DEFAULT_HAND_WT and not garbage.exception


def test_query_params_follow_the_settings():
    at = _fresh_app()
    at.sidebar.selectbox(key="wt_select").set_value(20).run(timeout=TIMEOUT)
    assert at.query_params["zeit"] in (["20"], "20")


def test_settings_in_the_url_match_the_setting_specs():
    assert {spec.url_param for spec in P.SETTING_SPECS.values()} == {"hzeit", "hlast", "label", "n", "breite", "typ", "q", "seed", "zeit", "last", "gewicht"}
    assert re.fullmatch(r"[a-z0-9]+", "".join(spec.url_param for spec in P.SETTING_SPECS.values()))


def test_sections_are_present_by_title_not_by_index():
    at = _fresh_app()
    expanders = {e.label: e for e in at.expander}
    assert "So funktionieren Eimer" in expanders and expanders["So funktionieren Eimer"].proto.expanded
    assert "📐 Mathematische Formulierung" in expanders and "⚠️ Annahmen, Grenzen und bekannte Probleme" in expanders
    subheaders = [s.value for s in at.subheader]
    for number in range(1, 6):
        assert any(s.startswith(f"🔬 Experiment {number}:") for s in subheaders), number
    assert any(s.startswith("🚧 Wo die Annahmen enden") for s in subheaders)
    math = expanders["📐 Mathematische Formulierung"].markdown[0].value
    assert math.startswith("**Lesehilfe.**") and "| Symbol | Bedeutung |" in math
    assert "Prüfstand" in math and "weder gebaut noch gemessen" not in math and "nicht der Bucket-Graph" in math


def test_assumptions_expander_text_equals_the_constant_and_the_readme():
    at = _fresh_app()
    box = next(e for e in at.expander if e.label == "⚠️ Annahmen, Grenzen und bekannte Probleme")
    assert box.markdown[0].value.strip() == C.ASSUMPTIONS_MARKDOWN.strip()
    readme = open(os.path.join(os.path.dirname(APP_PATH), "README.md"), encoding="utf-8").read()
    assert C.ASSUMPTIONS_MARKDOWN.strip() in readme


def _first_frame(at, column):
    frames = [d.value for d in at.dataframe if hasattr(d.value, "columns") and column in d.value.columns]
    assert frames, column
    return frames[0]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_shows_its_expected_verdict_lines(name):
    from test_presets import EXPECTED
    at = _fresh_app()
    at.sidebar.button(key=f"preset_{name}").click().run(timeout=TIMEOUT)
    assert not at.exception, [str(e) for e in at.exception]
    kind, piece = EXPECTED[name]
    p = C.PRESETS[name]
    shown = _texts(at, kind)
    assert any(piece in t for t in shown), (name, shown)
    assert any(t.startswith("Dieselbe Menge lebender Labels wie ohne Eimer: ja") for t in _texts(at, "success"))
    assert any("dieselben 35 erzeugten Labels" in t and t.startswith(ev.config_name(p["hand_wt"], p["hand_wq"])) for t in _texts(at, "success")), name


def test_the_label_table_checkbox_shows_34_labels_and_the_hand_overview_has_six_rows():
    at = _fresh_app()
    over = _first_frame(at, "Eimerschritte")
    assert list(over["cmp1"])[:1] == [57] and list(over["cmp2"])[:1] == [45] and len(over) == 6 and set(over["Ergebnis gleich"]) == {"ja"}
    at.checkbox(key="show_all_labels").set_value(True).run(timeout=TIMEOUT)
    assert not at.exception
    labels = _first_frame(at, "Eimer (Zeit, Last)")
    assert len(labels) == 34 and labels["Label"][0] == "F01" and labels["Label"][33] == "F34"
    assert sum(labels["ohne Eimer cmp1"]) == 57 and sum(labels["ohne Eimer cmp2"]) == 45 and sum(labels["mit Eimern cmp1"]) == 57 and sum(labels["mit Eimern cmp2"]) == 28


def test_the_step_slider_shows_the_chosen_label_and_its_skipped_labels():
    at = _fresh_app({"hzeit": "10", "hlast": "3", "label": "20"})
    text = " ".join(m.value for m in at.markdown)
    assert "F20 entsteht am Kunden 3 mit Zeit 23, Last 8" in text and "**Mit Zeit 10 × Last 3:** cmp1 3, cmp2 0" in text and "**Vergleiche ohne Eimer:** cmp1 3, cmp2 3" in text
    assert "F03 (Kunde 3, Zeit 22, Last 2): Last-Eimer 0 < 2" in text
    at.sidebar.slider(key="step_slider").set_value(1).run(timeout=TIMEOUT)
    assert not at.exception and "Bei diesem Label und dieser Einstellung wird kein Label übersprungen." in " ".join(m.value for m in at.markdown)


def test_the_hand_example_shows_the_rounding_sentence_with_the_measured_numbers():
    text = " ".join(c.value for c in _fresh_app().caption)
    assert "cmp2 = 33 statt 28" in text and "cmp2 = 12 statt 8" in text


def test_the_band_table_follows_the_capacity_and_round_widgets():
    at = _fresh_app()
    table = _first_frame(at, "Median Eimerschritte")
    assert list(table["Läufe"]) == [40] * 14 and table["Einstellung"][0] == "ohne Eimer" and table["Median"][4] == "0,828"
    at.radio(key="band_q").set_value(120).run(timeout=TIMEOUT)
    at.selectbox(key="band_round").set_value("1").run(timeout=TIMEOUT)
    assert not at.exception
    t2 = _first_frame(at, "Median Eimerschritte")
    assert list(t2["Läufe"]) == [40] * 14 and t2["Median"][4] != "0,828"
