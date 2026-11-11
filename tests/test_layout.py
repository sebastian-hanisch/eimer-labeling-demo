"""Layout (DEMO-PLAYBOOK §2): fester Kopf, Schnellstart oben in der Seitenleiste, aktives Preset hervorgehoben.

Die Hervorhebung ist zustandslos (`aktives_preset` vergleicht jeden Regler aus SETTING_SPECS mit dem Preset). Der Test unten stellt
sicher, dass wirklich JEDER Regler der Seitenleiste dort steht: sonst bliebe das Preset trotz Änderung markiert."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import eml_constants as C
import eml_presets as P

APP = str(Path(__file__).resolve().parent.parent / "app.py")
REGLER_ARTEN = ("slider", "number_input", "select_slider", "selectbox", "radio", "toggle", "checkbox", "text_input")


def _app() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=180)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]
    return at


def _typen(at) -> dict:
    """Button-Typ je Preset-Name (die Preset-Buttons der Seitenleiste)."""
    return {b.label: b.proto.type for b in at.sidebar.button if b.label in C.PRESETS}


def _regler(at, key):
    for art in REGLER_ARTEN:
        try:
            return getattr(at.sidebar, art)(key=key)
        except KeyError:
            continue
    raise AssertionError(f"Regler {key} steht nicht in der Seitenleiste")


def test_presets_stehen_in_der_seitenleiste_und_nicht_im_hauptbereich():
    at = _app()
    assert [b.label for b in at.sidebar.button][: len(C.PRESETS)] == list(C.PRESETS)  # die ersten Buttons der Seitenleiste
    assert not [b for b in at.main.button if b.label in C.PRESETS]


def test_titel_steht_im_festen_kopf():
    at = _app()
    assert "st-key-kopf" in " ".join(h.proto.body for h in at.get("html"))  # das Stylesheet setzt an der Klasse des Containers an
    assert at.title[0].value


def test_beim_start_ist_genau_das_standard_preset_hervorgehoben():
    typen = _typen(_app())
    assert [name for name, typ in typen.items() if typ == "primary"] == [next(iter(C.PRESETS))]


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_angeklicktes_preset_ist_hervorgehoben_und_bleibt_es_im_naechsten_lauf(name):
    at = _app()
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]
    at.run()
    assert [n for n, typ in _typen(at).items() if typ == "primary"] == [name]


def test_jeder_regler_der_seitenleiste_steht_in_setting_specs():
    at = _app()
    schluessel = {w.key for art in REGLER_ARTEN for w in getattr(at.sidebar, art) if w.key}
    fehlt = schluessel - set(P.SETTING_SPECS)
    assert not fehlt, f"Regler {sorted(fehlt)} fehlen in SETTING_SPECS: ihre Änderung hebt das aktive Preset nicht auf"


@pytest.mark.parametrize("state_key", list(P.SETTING_SPECS))
def test_jede_aenderung_eines_reglers_hebt_die_hervorhebung_auf(state_key):
    """Der Regler wird auf einen Wert gestellt, bei dem die Einstellungen KEINEM Szenario entsprechen: dann ist nichts hervorgehoben. Gibt es einen solchen Wert nicht
    (ein einzeln geänderter Regler ergibt genau ein anderes Szenario, etwa k = 1 oder Breite 40), ist nach der Änderung genau dieses andere Szenario hervorgehoben,
    nicht mehr das alte."""
    at = _app()
    spec = P.SETTING_SPECS[state_key]
    regler = _regler(at, state_key)
    kandidaten = list(spec.choices) if spec.choices else [spec.hi, spec.lo, (spec.lo + spec.hi) // 2]

    def passende_szenarien(wert):
        zustand = {sk: s.default for sk, s in P.SETTING_SPECS.items()}
        zustand[state_key] = wert
        return [name for name, preset in C.PRESETS.items() if all(zustand[sk] == preset[k] for k, sk in P.PRESET_KEYS.items())]

    kandidaten = [w for w in kandidaten if w != regler.value]
    ohne = [w for w in kandidaten if not passende_szenarien(w)]
    neu = ohne[0] if ohne else kandidaten[0]
    regler.set_value(neu).run()
    assert not at.exception
    hervorgehoben = [n for n, typ in _typen(at).items() if typ == "primary"]
    assert hervorgehoben == passende_szenarien(neu)
    assert next(iter(C.PRESETS)) not in hervorgehoben or passende_szenarien(neu) == [next(iter(C.PRESETS))]
    # erneutes Anklicken markiert wieder
    name = next(iter(C.PRESETS))
    at.sidebar.button(key=f"preset_{name}").click().run()
    assert _typen(at)[name] == "primary"


def test_breite_tabellen_scrollen_im_telefon_fenster_innerhalb_der_spalte():
    """Markdown-Tabellen (Messreihen, Symboltabelle, Annahmen) laufen unter 640 px nicht über den Rand: Das Stylesheet macht sie zum scrollbaren Block."""
    from eml_layout import kopf_css
    css = kopf_css(False)
    media = css[css.index("@media (max-width: 640px)"):]
    assert '[data-testid="stMarkdownContainer"] table { display: block; overflow-x: auto; }' in media
