"""Eimer im Labeling: wie viele Dominanzvergleiche spart es, die Labels eines Knotens nach Zeit und Last in Eimer zu sortieren? - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Label-Verfahren für das Preisproblem der Spaltenerzeugung mit Eimern je Knoten („Bucket-Graph light“): Handbeispiel Schritt für Schritt, Live-Rechnung auf einer Zufallsinstanz mit
30 Kunden, Eimerbreite und Verwaltungsgewicht, Aufteilung der Vergleiche und die 320 festen Läufe der Messreihe. Der echte Bucket-Graph ist nicht Teil der Demo.

Lauffähig mit: streamlit run app.py
"""

import pandas as pd
import streamlit as st

import eml_algorithm as A
import eml_constants as C
import eml_evaluation as ev
from eml_layout import dunkles_design, kopf_css
from eml_presets import (
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sidebar_presets,
    sync_query_params,
)
from eml_scenario import HAND_DUALS, hand_instance
from eml_visualization import (
    build_band_chart,
    build_hand_map,
    build_hand_split_chart,
    build_optimum_bars,
    build_optimum_chart,
    build_split_chart,
    build_sweep_chart,
)

st.set_page_config(page_title="Eimer im Labeling – Sebastian Hanisch", layout="wide")

TYP_NAMES = {"zufall": "zufällig verteilt", "cluster": "gruppiert"}


@st.cache_data(show_spinner=False)
def _duals(n, width, typ, q, seed):
    return ev.live_duals(ev.Settings(n, width, typ, q, seed))


@st.cache_data(show_spinner=False)
def _run(n, width, typ, q, seed, wt, wq):
    s = ev.Settings(n, width, typ, q, seed)
    pi = _duals(n, width, typ, q, seed)["ende"]
    return ev.live_run(ev.instance_of(s), pi, wt, wq)


@st.cache_data(show_spinner=False)
def _hand_overview():
    return ev.hand_overview()


@st.cache_data(show_spinner=False)
def _hand_detail(nr, wt, wq):
    return ev.hand_step_detail(nr, wt, wq)


@st.cache_data(show_spinner=False)
def _hand_rows(wt, wq):
    return ev.hand_step_rows(wt, wq)


@st.cache_data(show_spinner=False)
def _rounding():
    return ev.rounding_difference()


@st.cache_data(show_spinner=False)
def _bands():
    return ev.load_bands()


def _delta(x) -> str:
    """Differenz „mein Wert minus Bezug“ mit Vorzeichen. Streamlit erkennt die Richtung am ASCII-Zeichen „-“ am Anfang (ein echtes Minuszeichen „−“ zeigte einen Pfeil nach oben und die falsche Farbe)."""
    return ("+" if x > 0 else "-") + ev.fmt_int(abs(x))


def _pct(part, whole) -> str:
    return ev.fmt_pct(100 * part / whole) if whole else "–"


# Fester Kopf: nur der Titel bleibt beim Scrollen oben (Stylesheet in eml_layout.py).
st.html(kopf_css(dunkles_design()))
with st.container(key="kopf"):
    st.title("🪣 Eimer im Labeling: wie viel sparen sie wirklich?")
st.markdown(
    """
Beim **Preisproblem der Spaltenerzeugung** wird ein Weg mit negativen **reduzierten Kosten** gesucht (Weglänge minus die **Dualpreise** der besuchten Kunden; der Dualpreis ist der Betrag, den die übergeordnete Planung
einem Kunden zurechnet). Das **Label-Verfahren** verlängert Teilwege (**Labels**) und streicht dominierte; jedes neue Label wird dafür mit den lebenden Labels seines Kunden verglichen. Diese Demo fragt:
**Spart es Vergleiche, die Labels eines Kunden nach Zeit und Last in Fächer, sogenannte Eimer (englisch Buckets), zu sortieren, und was kostet die Verwaltung der Eimer?** Gemessen werden **Dominanzvergleiche** und
**angesehene Eimer** (keine Sekunden): am Handbeispiel Schritt für Schritt, auf einer Zufallsinstanz mit bis zu 30 Kunden und in 320 festen Läufen.

**Eimer ändern das Ergebnis nicht** (dasselbe Ergebnis wie ohne Eimer, in jedem Lauf geprüft). Wie viele Vergleiche sie sparen, und ob das nach Abzug der Verwaltung bleibt, zeigen die Experimente. **Das ist der einfache Teil
des Bucket-Graphs der Literatur (Eimer je Kunde); der echte Bucket-Graph mit Sprungkanten ist nicht gebaut und nicht gemessen.**

Weiter unten: der Expander **So funktionieren Eimer** (zuerst), fünf Experimente (**🔬**), **🚧 Wo die Annahmen enden**, **📐 Mathematische Formulierung** und **⚠️ Annahmen, Grenzen und bekannte Probleme**.
Die Anwendung dieses Verfahrens in einem Fall (Besatzungsplanung im Zugverkehr) zeigt [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo). Nicht zu verwechseln mit
[hub-labeling-demo](https://github.com/sebastian-hanisch/hub-labeling-demo): Dort sind Labels vorberechnete Listen für schnelle Abfragen kürzester Wege, hier sind es Teilwege im Preisproblem.
"""
)

with st.expander("So funktionieren Eimer", expanded=True):
    st.markdown(
        """
1. **Ein Label ist ein Teilweg** in vier Zahlen und einer Menge: **reduzierte Kosten**, **Zeit** (Beginn der Bedienung; wer zu früh kommt, wartet kostenlos), verbrauchte **Last** und das **Gedächtnis** (die Kunden, die der Weg nicht noch einmal besuchen darf).
2. **Ein Label O dominiert ein neues Label N** am selben Kunden, wenn O Kosten, Zeit und Last **nicht höher** hat und das Gedächtnis von O in dem von N enthalten ist; N wird dann gestrichen. Umgekehrt streicht ein neues Label N die alten, die es so dominiert.
   Ohne Eimer vergleicht das Verfahren N mit **allen** lebenden Labels des Kunden: zuerst „wird N dominiert?“ (**cmp1**), dann, wenn N bleibt, „dominiert N alte Labels?“ (**cmp2**).
3. **Eimer ordnen die lebenden Labels eines Kunden nach Zeit und Last.** Zeit-Eimer der Breite 10 heißt: Zeit 0 bis 9 liegt in Eimer 0, 10 bis 19 in Eimer 1 und so weiter; Last-Eimer ebenso. Ein Label liegt in genau einem Eimer (Zeit-Index, Last-Index).
4. **Viele Eimer können übersprungen werden.** Ein O, das N dominiert, hat Zeit und Last nicht höher, liegt also in einem Eimer mit Zeit-Index und Last-Index **höchstens** denen von N: nur diese Eimer braucht cmp1 anzusehen. Ein O, das von N dominiert wird, hat Zeit und Last nicht niedriger:
   cmp2 sieht nur Eimer mit Zeit-Index und Last-Index **mindestens** denen von N an. Das Ergebnis bleibt gleich, nur die Zahl der Vergleiche sinkt.
5. **Die Verwaltung kostet etwas:** Je feiner die Eimer, desto mehr Eimerindizes muss die Suche durchlaufen. Die Demo zählt sie als **Eimerschritte** und rechnet sie mit einem **Gewicht** in den Aufwand ein (**Annahme, keine Messung**).

Merksatz: **Eimer sparen nur einen Teil der Vergleiche, und der Teil schrumpft, sobald die Verwaltung etwas kostet.** Wie groß der Teil ist, steht in den Messungen (Experimente 2 bis 5), nicht im Handbeispiel.
"""
    )

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    sidebar_presets()  # Schnellstart oben, das aktive Szenario ist hervorgehoben
    st.header("⚙️ Einstellungen")
    st.markdown("**Handbeispiel** (Experiment 1)")
    hand_wt = st.radio("Zeit-Eimerbreite", C.HAND_WT_OPTIONS, key="hand_wt_radio", horizontal=True, format_func=lambda w: "keine" if w == 0 else str(w),
                       help="Breite der Zeit-Eimer im Handbeispiel (Zeiten 0 bis 40); „keine“ heißt ein einziger Zeit-Eimer.")
    hand_wq = st.radio("Last-Eimerbreite", C.HAND_WQ_OPTIONS, key="hand_wq_radio", horizontal=True, format_func=lambda w: "keine" if w == 0 else str(w),
                       help="Breite der Last-Eimer im Handbeispiel (Lasten 0 bis 9); „keine“ heißt ein einziger Last-Eimer.")
    step = st.slider("Neues Label Nr.", *bounds("step_slider"), key="step_slider", help="Welches der 34 neuen Labels des Handbeispiels Experiment 1 im Einzelnen zeigt (F01 bis F34, in der Reihenfolge ihrer Entstehung).")
    st.markdown("**Zufallsinstanz** (Ergebnis und Experimente 2 bis 4)")
    n = st.slider("Kunden n", *bounds("n_slider"), key="n_slider", help="Zahl der Kunden der Zufallsinstanz (8 bis 30).")
    width = st.radio("Fensterbreite", C.WIDTH_OPTIONS, key="width_radio", horizontal=True, help="Breite der Zeitfenster der Kunden in Zeiteinheiten (Horizont 300).")
    typ = st.radio("Verteilung der Kunden", C.TYP_OPTIONS, key="typ_radio", horizontal=True, format_func=TYP_NAMES.get, help="Zufällig im Quadrat verteilt oder in fünf Gruppen.")
    q = st.radio("Kapazität", C.Q_OPTIONS, key="q_radio", horizontal=True, help="Kapazität des Fahrzeugs (die Last der Kunden liegt zwischen 5 und 25).")
    seed = st.number_input("Zufalls-Seed der Instanz", *bounds("seed_input"), key="seed_input", step=1)
    st.button("🎲 Neue Instanz generieren", width="stretch", on_click=randomize_seed)
    st.markdown("**Eimer und Verwaltung** (Ergebnis und Experimente 2 bis 4)")
    wt = st.selectbox("Zeit-Eimerbreite (Zufallsinstanz)", C.WT_OPTIONS, key="wt_select", format_func=lambda w: "keine" if w == 0 else str(w), help="Breite der Zeit-Eimer in Zeiteinheiten.")
    wq = st.selectbox("Last-Eimerbreite (Zufallsinstanz)", C.WQ_OPTIONS, key="wq_select", format_func=lambda w: "keine" if w == 0 else str(w), help="Breite der Last-Eimer in Lasteinheiten.")
    weight = st.slider("Gewicht je Eimerschritt (Annahme, keine Messung)", *bounds("weight_slider"), key="weight_slider", step=C.WEIGHT_STEP,
                       help="Wie viele Vergleiche ein angesehener Eimer kosten soll, wenn man die Verwaltung der Eimer einrechnet. 0: Verwaltung kostet nichts; 1: ein Eimerschritt kostet so viel wie ein Vergleich. Voreinstellung 0,1.")

sync_query_params({"hand_wt_radio": int(hand_wt), "hand_wq_radio": int(hand_wq), "step_slider": int(step), "n_slider": int(n), "width_radio": int(width), "typ_radio": typ, "q_radio": int(q),
                   "seed_input": int(seed), "wt_select": int(wt), "wq_select": int(wq), "weight_slider": float(weight)})

inst_args = (int(n), int(width), typ, int(q), int(seed))
settings = ev.Settings(*inst_args)
instance_text = f"{n} Kunden, {TYP_NAMES[typ]}, Fensterbreite {width}, Kapazität {q}, Zufalls-Seed {seed}"

# --- Ergebnis: Zufallsinstanz ---------------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Ergebnis: Eimer auf einer Zufallsinstanz")
with st.spinner("Spaltenerzeugung und Label-Verfahren rechnen …"):
    duals = _duals(*inst_args)
    ok = duals["ende"] is not None
    if ok:
        base = _run(*inst_args, 0, 0)
        run = _run(*inst_args, int(wt), int(wq))
if not ok:
    st.warning(f"Die Spaltenerzeugung dieser Instanz ({instance_text}) ist abgebrochen: Sie hätte mehr als {ev.fmt_int(C.MAX_LABELS_COLGEN)} Labels über alle Runden (oder mehr als {ev.fmt_int(C.MAX_LABELS_CALL)} in einer Runde) erzeugt, das Rechenbudget der Live-Rechnung. Eine kleinere Instanz, schmalere Fenster oder die Kapazität 70 wählen; die festen Messreihen (Experiment 5) und das Handbeispiel (Experiment 1) bleiben davon unberührt.")
if ok:
    st.markdown(
        f"Instanz: **{instance_text}**. Die **Dualpreise** stammen aus einer Spaltenerzeugung mit Überdeckungs-Master ({duals['iters']} Runden; es wird mit den Dualpreisen der letzten Runde gerechnet), das Gedächtnis ist k = {C.MEMORY_K} "
        f"(die {C.MEMORY_K} nächsten Kunden). Das Label-Verfahren erzeugt **{ev.fmt_int(base.generated)} Labels**, davon werden {ev.fmt_int(base.dominated)} gestrichen; am Ende leben {ev.fmt_int(base.live)}. "
        f"Es gibt {ev.fmt_int(base.n_routes)} Routen mit negativen reduzierten Kosten" + (f", die beste hat {ev.fmt_dec(base.best_rc, 2)}." if base.best_rc is not None
                                                                                       else " (mit den Dualpreisen der letzten Runde zu erwarten: Die Spaltenerzeugung endet, wenn das Preisproblem keine neue Route mehr findet). Das Verfahren muss dafür trotzdem alle Labels erzeugen und prüfen.")
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Vergleiche ohne Eimer", ev.fmt_int(base.comparisons), help=f"cmp1 {ev.fmt_int(base.cmp1)} + cmp2 {ev.fmt_int(base.cmp2)}.")
    m2.metric(f"Vergleiche, {ev.config_name(run.wt, run.wq)}", ev.fmt_int(run.comparisons), delta=_delta(run.comparisons - base.comparisons) if run.comparisons != base.comparisons else "wie ohne Eimer",
              delta_color="inverse" if run.comparisons != base.comparisons else "off", help=f"cmp1 {ev.fmt_int(run.cmp1)} + cmp2 {ev.fmt_int(run.cmp2)}.")
    m3.metric("Angesehene Eimer", ev.fmt_int(run.steps), delta=_delta(run.steps - base.steps) if run.steps != base.steps else "wie ohne Eimer", delta_color="inverse" if run.steps != base.steps else "off",
              help="Alle Eimerindizes im durchsuchten Bereich, auch leere (nach Formel gezählt). Ohne Eimer ist es ein Eimer je Prüfung.")
    net_base, net_run = ev.net_cost(base, float(weight)), ev.net_cost(run, float(weight))
    m4.metric(f"Aufwand mit Gewicht {ev.fmt_dec(float(weight), 2)}", ev.fmt_int(round(net_run)), delta=_delta(round(net_run - net_base)) if round(net_run) != round(net_base) else "wie ohne Eimer",
              delta_color="inverse" if round(net_run) != round(net_base) else "off", help="Vergleiche plus Gewicht mal angesehene Eimer; das Gewicht ist eine Annahme, keine Messung.")

    # --- Kernfrage -----------------------------------------------------------------------------------------------------------------------------

    st.markdown("## ❓ Kernfrage: Wie viele Vergleiche sparen Eimer, und lohnt sich das nach Abzug der Verwaltung?")
    if not base.aborted:
        kind, text = ev.verdict_identical(ev.same_result(base, run))
        getattr(st, kind)(text)
    if base.best_route is not None and not base.aborted:   # unabhängiger Routenprüfer (ohne Labels): bewertet die beste Route des Verfahrens neu
        check = A.check_route(ev.instance_of(settings), duals["ende"], base.best_route)
        if check is None or abs(check - base.best_rc) > 1e-6:
            st.error("Der unabhängige Routenprüfer bewertet die beste gefundene Route anders als das Verfahren: Der Kern ist fehlerhaft.")
    kind, text = ev.verdict_saving(base, run, float(weight))
    getattr(st, kind)(text)
    st.caption("Das ist eine einzelne Instanz. Wie stark die Ersparnis über viele Instanzen streut, zeigt Experiment 5 (320 feste Läufe mit Median, Mittel und Maximum).")

st.markdown("---")

# --- Experiment 1 --------------------------------------------------------------------------------------------------------------------------

inst_h = hand_instance()
st.subheader("🔬 Experiment 1: Die Eimer Schritt für Schritt (Handbeispiel)")
st.markdown(
    f"Ein Fahrzeug startet im Depot D (Gitterpunkt {inst_h.points[0]}) und besucht Kunden. **Entfernung = Fahrzeit = Kosten = Manhattan-Abstand**, Bedienzeit {inst_h.service}, Rückkehr spätestens zur Zeit {inst_h.horizon}, "
    f"Last höchstens {inst_h.capacity}; wer vor Beginn seines Fensters ankommt, wartet kostenlos. Reduzierte Kosten einer Route = Summe der Entfernungen minus Summe der Dualpreise der besuchten Kunden. "
    "Das Gedächtnis ist elementar: jeder Kunde höchstens einmal."
)
hand_table = pd.DataFrame({
    "Kunde": list(range(1, inst_h.n + 1)),
    "Punkt": [f"({inst_h.points[i][0]}, {inst_h.points[i][1]})" for i in range(1, inst_h.n + 1)],
    "Zeitfenster [früh, spät]": [f"[{inst_h.ready[i]}, {inst_h.due[i]}]" for i in range(1, inst_h.n + 1)],
    "Last": [inst_h.demand[i] for i in range(1, inst_h.n + 1)],
    "Dualpreis": [ev.fmt_dec(HAND_DUALS[i], 1) for i in range(1, inst_h.n + 1)],
})
st.dataframe(hand_table, hide_index=True, width="stretch")
hand_rows = _hand_overview()
hsel = next(r for r in hand_rows if (r["wt"], r["wq"]) == (int(hand_wt), int(hand_wq)))
hbase = hand_rows[0]
hres = ev.hand_run(int(hand_wt), int(hand_wq))
h1, h2, h3, h4 = st.columns(4)
h1.metric("Erzeugte Labels", hbase["generated"], help="Das Start-Label im Depot eingeschlossen; sofort verworfene Labels zählen mit.")
h2.metric("Vergleiche ohne Eimer", hbase["comparisons"], help=f"cmp1 {hbase['cmp1']} + cmp2 {hbase['cmp2']}.")
h3.metric(f"Vergleiche, {hsel['name']}", hsel["comparisons"], delta=f"{_delta(hsel['comparisons'] - hbase['comparisons'])}" if hsel["comparisons"] != hbase["comparisons"] else "wie ohne Eimer",
          delta_color="inverse" if hsel["comparisons"] != hbase["comparisons"] else "off", help=f"cmp1 {hsel['cmp1']} + cmp2 {hsel['cmp2']}.")
h4.metric("Angesehene Eimer", hsel["steps"], delta=_delta(hsel["steps"] - hbase["steps"]) if hsel["steps"] != hbase["steps"] else "wie ohne Eimer", delta_color="inverse" if hsel["steps"] != hbase["steps"] else "off")
kind, text = ev.verdict_hand(hand_rows, int(hand_wt), int(hand_wq))
getattr(st, kind)(text)
best = hres.best
if best is None or A.check_route(inst_h, HAND_DUALS, best[1]) is None or abs(A.check_route(inst_h, HAND_DUALS, best[1]) - best[0]) > 1e-9:
    st.error("Der unabhängige Routenprüfer bewertet die gefundene Route des Handbeispiels anders als das Verfahren: Der Kern ist fehlerhaft.")
st.plotly_chart(build_hand_map(inst_h, best[1] if best else None), width="stretch", key="hand_map")
st.caption(f"Die beste Route des Handbeispiels ist {ev.route_text(best[1]) if best else 'keine'} mit reduzierten Kosten {ev.fmt_dec(best[0], 0) if best else '–'} (unabhängig durch Aufzählung aller zulässigen elementaren Routen bestätigt, siehe Tests). "
           "Unter den Kunden stehen Zeitfenster und Last.")

det = _hand_detail(int(step), int(hand_wt), int(hand_wq))
ev1, evb = det["event"], det["base"]
st.markdown(f"**Das neue Label F{int(step):02d} im Einzelnen** (Regler „Neues Label Nr.“ in der Seitenleiste)")
nt_, nq_ = det["own"]
st.markdown(
    f"F{ev1['nr']:02d} entsteht am Kunden {ev1['node']} mit Zeit {ev.fmt_dec(ev1['time'], 0)}, Last {ev1['load']} und reduzierten Kosten {ev.fmt_dec(ev1['cost'], 1)}; es liegt im Eimer (Zeit-Index {nt_}, Last-Index {nq_}). "
    f"Am Kunden leben vor ihm {len(ev1['live_before'])} Labels. Entscheidung: **{ev1['status']}**"
    + (f" (von F{ev1['killer']:02d})" if ev1["killer"] is not None else "")
    + (f"; es streicht {len(ev1['killed'])} alte Label(s)" + (": " + ", ".join(f"F{k:02d}" for k in ev1["killed"]) if ev1["killed"] else "") if ev1["status"] == "behalten" and ev1["killed"] else "")
    + f". **Vergleiche ohne Eimer:** cmp1 {len(evb['ex1'])}, cmp2 {len(evb['ex2'])}. **Mit {hsel['name']}:** cmp1 {len(ev1['ex1'])}, cmp2 {len(ev1['ex2'])}."
)
rows_labels = ev.bucket_axis_labels(det["horizon"], det["wt"], det["nt"], "Zeiten")
cols_labels = ev.bucket_axis_labels(det["capacity"], det["wq"], det["nq"], "Lasten")
grid = pd.DataFrame([["" for _ in cols_labels] for _ in rows_labels], index=rows_labels, columns=cols_labels)
for (it, iq), lst in det["cells"].items():
    grid.iloc[it, iq] = ", ".join(f"F{o:02d}" for o in lst)
grid.iloc[det["own"][0], det["own"][1]] = (grid.iloc[det["own"][0], det["own"][1]] + " ▶ neu F" + f"{ev1['nr']:02d}").strip()


def _style_grid(df):
    css = pd.DataFrame("", index=df.index, columns=df.columns)
    for it in range(det["nt"]):
        for iq in range(det["nq"]):
            in1 = it <= det["own"][0] and iq <= det["own"][1]
            in2 = ev1["status"] == "behalten" and it >= det["own"][0] and iq >= det["own"][1]
            css.iloc[it, iq] = C.CELL_BOTH if in1 and in2 else C.CELL_CMP1 if in1 else C.CELL_CMP2 if in2 else ""
    css.iloc[det["own"][0], det["own"][1]] = C.CELL_NEW
    return css


st.dataframe(grid.style.apply(_style_grid, axis=None), width="stretch")
st.caption("Zeilen: Zeit-Eimer, Spalten: Last-Eimer; in den Feldern stehen die lebenden Labels des Kunden vor dem Einfügen. **Blau:** Eimer, die cmp1 („wird das neue Label dominiert?“) ansieht (Zeit-Index und Last-Index höchstens die des neuen Labels). "
           "**Orange:** Eimer, die cmp2 („dominiert das neue Label alte?“) ansieht (Zeit-Index und Last-Index mindestens die des neuen Labels; nur, wenn das neue Label bleibt). **Violett:** Eimer des neuen Labels. Alle anderen Felder werden übersprungen.")
info = det["info"]


def _skip_lines(items):
    return [f"F{o:02d} (Kunde {info[o][0]}, Zeit {ev.fmt_dec(info[o][1], 0)}, Last {info[o][2]}): {why}" for o, why in items]


if ev1["status"] == "dominiert":
    st.markdown("cmp2 entfällt: Das neue Label wurde schon bei cmp1 gestrichen.")
if det["skipped1"] or det["skipped2"]:
    if det["skipped1"]:
        st.markdown("**Bei cmp1 nicht angesehen:**\n" + "\n".join(f"- {line}" for line in _skip_lines(det["skipped1"])))
    if det["skipped2"]:
        st.markdown("**Bei cmp2 nicht angesehen:**\n" + "\n".join(f"- {line}" for line in _skip_lines(det["skipped2"])))
else:
    st.markdown("Bei diesem Label und dieser Einstellung wird kein Label übersprungen.")

st.markdown("**Alle sechs Einstellungen im Handbeispiel** (Zeit-Eimerbreite × Last-Eimerbreite; dieselben Labels, dieselbe Menge lebender Labels, dieselbe beste Route):")
df_over = pd.DataFrame({
    "Einstellung": [r["name"] for r in hand_rows],
    "Erzeugte Labels": [r["generated"] for r in hand_rows],
    "Gestrichen": [r["dominated"] for r in hand_rows],
    "cmp1": [r["cmp1"] for r in hand_rows],
    "cmp2": [r["cmp2"] for r in hand_rows],
    "Vergleiche": [r["comparisons"] for r in hand_rows],
    "Eimerschritte": [r["steps"] for r in hand_rows],
    "Vergleiche + 0,1 × Schritte": [ev.fmt_dec(r["net"], 1) for r in hand_rows],
    "Ergebnis gleich": ["ja" if r["same"] else "NEIN" for r in hand_rows],
})
st.dataframe(df_over, hide_index=True, width="stretch")
rd = _rounding()
st.caption(
    "Das Gewicht 0,1 je Eimerschritt ist eine Annahme. Mit ihm lohnt sich im kleinen Handbeispiel nur der Last-Eimer (der Zeit-Eimer 10 kaum, beide Eimer zusammen und feine Eimer nicht); die Zahlen stehen in der Tabelle. "
    f"**Eimerrand:** Die Handbeispiel-Zahlen rechnen mit exakten Eimergrenzen. Die festen Messreihen und die Live-Rechnung beginnen die Suche für cmp2 beim Eimer von „Zeit minus 10⁻⁹“ (Rundungssicherheit bei Fließkommazeiten); "
    f"liegt die Zeit genau auf einer Eimergrenze, sieht cmp2 dann einen Eimer mehr an (unnötig, nie falsch). Im Handbeispiel, mit ganzen Zeiten, ergibt das bei Zeit-Eimer 10 cmp2 = {rd[(10, 0)][1]} statt {rd[(10, 0)][0]} "
    f"und bei Zeit 10 × Last 3 cmp2 = {rd[(10, 3)][1]} statt {rd[(10, 3)][0]}."
)
if st.checkbox("Alle 34 neuen Labels mit ihren Vergleichen zeigen", key="show_all_labels"):
    srows = _hand_rows(int(hand_wt), int(hand_wq))
    st.dataframe(pd.DataFrame({
        "Label": [f"F{r['nr']:02d}" for r in srows],
        "Kunde": [r["node"] for r in srows],
        "Zeit": [int(r["time"]) for r in srows],
        "Last": [r["load"] for r in srows],
        "Eimer (Zeit, Last)": [f"({r['bucket'][0]}, {r['bucket'][1]})" for r in srows],
        "Lebende Labels am Kunden": [r["live_before"] for r in srows],
        "Entscheidung": [r["status"] for r in srows],
        "ohne Eimer cmp1": [r["base1"] for r in srows],
        "ohne Eimer cmp2": [r["base2"] for r in srows],
        "mit Eimern cmp1": [r["cmp1"] for r in srows],
        "mit Eimern cmp2": [r["cmp2"] for r in srows],
    }), hide_index=True, width="stretch", height=420)

st.markdown("---")

# --- Experimente 2 bis 4: eine Reihe von Läufen auf der Zufallsinstanz -------------------------------------------------------------------------

SERIES_CONFIGS = [(w, 0) for w in C.SWEEP_WT] + [(0, 5), (0, 10), (10, 5)]
series = None
if ok:
    if base.aborted:
        st.info(f"Diese Instanz erzeugt mehr als {ev.fmt_int(C.MAX_LABELS)} Labels (Labelbudget der Live-Rechnung): Die Reihe von Läufen für die Experimente 2 bis 4 wird nicht gerechnet. Eine kleinere Instanz oder schmalere Fenster wählen.")
    else:
        with st.spinner(f"{len(SERIES_CONFIGS)} Läufe mit verschiedenen Eimerbreiten rechnen …"):
            series = {cfg: _run(*inst_args, *cfg) for cfg in SERIES_CONFIGS}

    if series is not None:
        # --- Experiment 2 ---------------------------------------------------------------------------------------------------------------------
        st.subheader("🔬 Experiment 2: Die Eimerbreite verstellen")
        st.caption(
            f"Dieselbe Instanz ({instance_text}) mit jeder Zeit-Eimerbreite von grob (80) bis fein (1) und mit Last-Eimern. Oben: wie viele Vergleiche übrig bleiben, im Verhältnis zu den Vergleichen ohne Eimer; unten: wie viele Eimer dafür angesehen werden. "
            "Die gewählte Einstellung der Seitenleiste steht in der Tabelle fett."
        )
        st.plotly_chart(build_sweep_chart(series), width="stretch", key="sweep_chart")
        sbase = series[(0, 0)]
        order = [(w, 0) for w in C.SWEEP_WT] + [(0, 5), (0, 10), (10, 5)]
        st.dataframe(pd.DataFrame({
            "Einstellung": [("► " if cfg == (int(wt), int(wq)) else "") + ev.config_name(*cfg) for cfg in order],
            "Vergleiche": [series[cfg].comparisons for cfg in order],
            "cmp1": [series[cfg].cmp1 for cfg in order],
            "cmp2": [series[cfg].cmp2 for cfg in order],
            "Anteil der Vergleiche ohne Eimer (%)": [100 * series[cfg].comparisons / sbase.comparisons if sbase.comparisons else 100.0 for cfg in order],
            "Eimerschritte": [series[cfg].steps for cfg in order],
            "Ergebnis gleich": ["ja" if ev.same_result(sbase, series[cfg]) else "NEIN" for cfg in order],
        }), hide_index=True, width="stretch", column_config={"Anteil der Vergleiche ohne Eimer (%)": st.column_config.NumberColumn(format="%.1f %%")})
        kind, text = ev.verdict_monotone(series)
        getattr(st, kind)(text)

        st.markdown("---")

        # --- Experiment 3 ---------------------------------------------------------------------------------------------------------------------
        st.subheader("🔬 Experiment 3: Wo liegt das Optimum?")
        st.caption(
            "Aufwand = Vergleiche + Gewicht × angesehene Eimer, im Verhältnis zum Aufwand ohne Eimer (Linie bei 1; darunter lohnt sich der Eimer). Das Gewicht ist eine **Annahme**: 0 heißt, die Verwaltung kostet nichts, 1, ein Eimerschritt kostet so viel wie ein Vergleich. "
            "Logarithmische Achse."
        )
        fig_opt = build_optimum_chart(series)
        if fig_opt is None:
            st.info("Ohne Eimer gibt es auf dieser Instanz keinen Aufwand; es gibt nichts zu vergleichen.")
        else:
            st.plotly_chart(fig_opt, width="stretch", key="optimum_chart")
        kind, text = ev.verdict_optimum(series)
        getattr(st, kind)(text)
        bands = _bands()
        st.markdown("**Und in den 320 festen Läufen?** Wie oft hat welche Zeit-Breite den kleinsten Aufwand (je Kapazität 160 Läufe: 2 Verteilungen × 2 Fensterbreiten × 10 Zufalls-Seeds × 4 Runden der Spaltenerzeugung)?")
        cq1, cq2 = st.columns(2)
        for col, qq in ((cq1, 70), (cq2, 120)):
            with col:
                counts = {g: ev.optimum_counts(bands, qq, g) for g in C.BAND_WEIGHTS}
                st.plotly_chart(build_optimum_bars(counts, qq), width="stretch", key=f"optimum_bars_{qq}")
        o70 = {g: ev.optimum_counts(bands, 70, g) for g in C.BAND_WEIGHTS}
        o120 = {g: ev.optimum_counts(bands, 120, g) for g in C.BAND_WEIGHTS}
        best1_70 = o70[0.0]["counts"][(1, 0)]
        best1_120 = o120[0.0]["counts"][(1, 0)]
        none_w1_70, none_w1_120 = o70[1.0]["counts"][(0, 0)], o120[1.0]["counts"][(0, 0)]
        st.info(
            f"Ohne Verwaltungskosten (Gewicht 0) ist die feinste Breite (Zeit 1) in {best1_70} von {o70[0.0]['n']} Läufen bei Kapazität 70 und in {best1_120} von {o120[0.0]['n']} bei Kapazität 120 die beste; "
            f"bei Gewicht 1 ist „ohne Eimer“ die beste Wahl in {none_w1_70} bzw. {none_w1_120} Läufen. Ein Optimum der Eimerbreite gibt es also nur unter einem angenommenen Gewicht."
        )

        st.markdown("---")

        # --- Experiment 4 ---------------------------------------------------------------------------------------------------------------------
        st.subheader("🔬 Experiment 4: Warum sparen Zeit-Eimer nur die zweite Prüfung?")
        st.caption(
            "Die Vergleiche zerfallen in cmp1 („wird das neue Label dominiert?“) und cmp2 („dominiert das neue Label alte?“). Links die Zufallsinstanz mit vier Einstellungen, rechts das Handbeispiel. "
            "**Deutung (nicht eigens gemessen):** Die Labels werden nach Zeit geordnet abgearbeitet, ein neues Label hat daher meist eine spätere Zeit als die lebenden Labels seines Kunden; cmp1 muss dann fast alle Zeit-Eimer ansehen, cmp2 nur die wenigen mit gleicher oder späterer Zeit."
        )
        cs1, cs2 = st.columns(2)
        with cs1:
            st.plotly_chart(build_split_chart(series), width="stretch", key="split_chart")
        with cs2:
            st.plotly_chart(build_hand_split_chart(hand_rows), width="stretch", key="hand_split_chart")
        kind, text = ev.verdict_split(sbase, series[(10, 0)], series[(0, 5)])
        getattr(st, kind)(text)
        share = ev.cmp1_share(bands)
        st.caption(
            f"In den 320 festen Läufen macht cmp1 ohne Eimer im Median {ev.fmt_pct(100 * share)} aller Vergleiche aus. Handbeispiel: ohne Eimer {hbase['cmp1']} und {hbase['cmp2']} Vergleiche (cmp1, cmp2), mit Zeit-Eimern der Breite 10 "
            f"{next(r for r in hand_rows if (r['wt'], r['wq']) == (10, 0))['cmp1']} und {next(r for r in hand_rows if (r['wt'], r['wq']) == (10, 0))['cmp2']}."
        )

        st.markdown("---")
else:
    st.info("Die Experimente 2 bis 4 brauchen die Live-Rechnung dieser Instanz, die hier nicht fertig wurde (siehe oben); mit einer kleineren Instanz rechnen sie.")


# --- Experiment 5 --------------------------------------------------------------------------------------------------------------------------

bands = _bands()
st.subheader("🔬 Experiment 5: Die festen Messreihen (320 Läufe)")
st.caption(
    "Fest gemessen, mit dem Kern dieser Demo neu gerechnet (nicht aus einer Messdatei übernommen): **30 Kunden**, Fensterbreite 40 und 100, zufällig verteilt und gruppiert, Kapazität 70 und 120, je 10 Zufalls-Seeds (0 bis 9), Gedächtnis k = 5, "
    "Dualpreise der Spaltenerzeugung in den Runden 1, 3, 8 und am Ende. **Kapazität 70 und 120 benutzen dieselben Zufalls-Seeds und sind daher nicht unabhängig.** Je Zelle (Kapazität, Runde) stehen 40 Läufe; in jedem hat jede der 14 Einstellungen dasselbe Ergebnis wie ohne Eimer."
)
b1, b2 = st.columns(2)
bq = b1.radio("Kapazität", C.Q_OPTIONS, key="band_q", horizontal=True)
brunde = b2.selectbox("Dualpreise der Runde", C.BAND_ROUNDS, key="band_round", index=len(C.BAND_ROUNDS) - 1, format_func=lambda r: "Ende" if r == "ende" else r)
btable = ev.band_table(bands, int(bq), brunde, float(weight))
st.dataframe(pd.DataFrame({
    "Einstellung": [r["name"] for r in btable],
    "Läufe": [r["n"] for r in btable],
    "Median": [ev.fmt_ratio(r["median"]) for r in btable],
    "Mittel": [ev.fmt_ratio(r["mean"]) for r in btable],
    "Maximum": [ev.fmt_ratio(r["max"]) for r in btable],
    "Median cmp1": [ev.fmt_ratio(r["cmp1"]) for r in btable],
    "Median cmp2": [ev.fmt_ratio(r["cmp2"]) for r in btable],
    "Median Eimerschritte": [ev.fmt_int(r["steps"]) for r in btable],
    f"Median Aufwand (Gewicht {ev.fmt_dec(float(weight), 2)})": [ev.fmt_ratio(r["net"]) for r in btable],
    "Median Laufzeit (nur Information)": [ev.fmt_ratio(r["time"]) if r["time"] is not None else "–" for r in btable],
}), hide_index=True, width="stretch")
st.caption(
    f"Alle Verhältnisse beziehen sich auf den Lauf ohne Eimer derselben Instanz und derselben Dualpreise (Median ohne Eimer in dieser Zelle: {ev.fmt_int(btable[0]['comparisons_base'])} Vergleiche). "
    "**Median, Mittel und Maximum** sind das Verhältnis „Vergleiche mit Eimern / Vergleiche ohne Eimer“; der Aufwand rechnet das Gewicht der Seitenleiste je Eimerschritt ein (Annahme). "
    "Die Laufzeitspalte ist das Verhältnis der gemessenen Sekunden (parallele Läufe auf einem Rechner, nur Größenordnung; in der Python-Fassung bleibt die Laufzeit mit Eimern in derselben Größenordnung wie ohne Eimer)."
)
st.plotly_chart(build_band_chart(btable), width="stretch", key="band_chart")
band_options = [c for c in C.BAND_CONFIGS if c != (0, 0)]
default_band = (int(wt), int(wq)) if (int(wt), int(wq)) in band_options else (10, 0)
band_cfg = st.selectbox("Einstellung für das Verdikt", band_options, key="band_cfg", index=band_options.index(default_band), format_func=lambda c: ev.config_name(*c))
kind, text = ev.verdict_bands(bands, int(bq), brunde, band_cfg, float(weight))
getattr(st, kind)(text)
st.markdown("**Abhängigkeit von der Zahl der Labels** (alle 320 Läufe beider Kapazitäten; Median des Verhältnisses der Vergleiche je Klasse der Labelzahl ohne Eimer):")
lc = ev.label_class_table(bands)
st.dataframe(pd.DataFrame({
    "Labels ohne Eimer": [f"{ev.fmt_int(r['lo'])} bis unter {ev.fmt_int(r['hi'])}" if r["hi"] < 10 ** 9 else f"ab {ev.fmt_int(r['lo'])}" for r in lc],
    "Läufe": [r["n"] for r in lc],
    "Vergleiche je Label ohne Eimer (Median)": [ev.fmt_dec(r["per_label"], 1) for r in lc],
    "Zeit 10": [ev.fmt_ratio(r[(10, 0)]) for r in lc],
    "Zeit 1": [ev.fmt_ratio(r[(1, 0)]) for r in lc],
    "Last 5": [ev.fmt_ratio(r[(0, 5)]) for r in lc],
    "Zeit 10 × Last 5": [ev.fmt_ratio(r[(10, 5)]) for r in lc],
}), hide_index=True, width="stretch")
rows_total, rows_same = ev.all_identical(bands)
st.caption(f"In {rows_same} von {rows_total} Zeilen (320 Läufe × 14 Einstellungen) stimmen Menge der lebenden Labels, Zahl der erzeugten und gestrichenen Labels und die Liste der negativen Routen mit dem Lauf ohne Eimer überein.")

st.markdown("---")

# --- Grenzen -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was gilt, wenn sie nicht stimmt | Belegt durch |
|---|---|---|
| **Eimer je Kunde, kein Bucket-Graph** | Der echte Bucket-Graph (Eimer als Knoten mit Sprungkanten, ganze Eimer werden auf einmal verlängert) ist weder gebaut noch gemessen; was hier steht, gilt nur für die einfache Ablage. | Aufbau der Demo |
| **Gewicht je Eimerschritt (Voreinstellung 0,1)** | Das Gewicht ist angenommen. Bei Gewicht 0 sind die feinsten Eimer am besten, bei Gewicht 1 meist gar keine; die Netto-Aussagen der Demo hängen daran. | Experiment 3 |
| **30 Kunden, k = 5, Kapazität 70 und 120, eigene Instanzen** | Für 50 und 100 Kunden, andere Kapazitäten, ein anderes Gedächtnis und die Originalinstanzen ist nichts gemessen. | Experiment 5 |
| **Python-Fassung** | Die Laufzeit bleibt mit Eimern in dieser Fassung in derselben Größenordnung (je nach Zellenbildung etwa das 0,7- bis 1,4-Fache); gezählt werden Vergleiche und Eimerschritte, nicht Sekunden. Über schnellere Fassungen sagt die Demo nichts. | Experiment 5 |
| **Eimer allein, ohne beidseitiges Labeling** | Wie Eimer und beidseitiges Suchen zusammenwirken, ist nicht gemessen. | – |
"""
)

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Lesehilfe.** *Gegeben:* ein Depot $0$ und Kunden $1,\dots,n$ mit Entfernungen $d_{ij}$, Lasten $q_j$, Zeitfenstern $[e_j, l_j]$ und Dualpreisen $\pi_j$. *Gesucht:* Routen ab und bis zum Depot mit negativen
reduzierten Kosten (die beste zuerst). Das Label-Verfahren verlängert Teilwege Kunde für Kunde und streicht dominierte Labels. *Neu hier:* wie die lebenden Labels eines Kunden abgelegt werden, damit die Dominanzprüfung nur
einen Teil von ihnen ansehen muss.

| Symbol | Bedeutung |
|---|---|
| $i, j$ | Knoten; $0$ ist das Depot, $1,\dots,n$ sind Kunden |
| $d_{ij}$ | Entfernung von $i$ nach $j$; gleich der Fahrzeit und den Kosten |
| $\pi_j$ | Dualpreis des Kunden $j$ ($\pi_0 = 0$) |
| $q_j$, $Q$ | Last des Kunden $j$; Kapazität des Fahrzeugs |
| $e_j$, $l_j$ | frühester und spätester Beginn der Bedienung bei $j$ |
| $s$, $H$ | Bedienzeit je Kunde; Horizont (späteste Rückkehr ins Depot) |
| $(T, C, R, M)$ | Label: Zeit, reduzierte Kosten, verbrauchte Last, Gedächtnis (Menge) |
| $O \preceq N$ | Label $O$ dominiert Label $N$ (am selben Kunden) |
| $w_T$, $w_R$ | Breite der Zeit-Eimer und der Last-Eimer (Zeiteinheiten, Lasteinheiten) |
| $\beta_T(T)$, $\beta_R(R)$ | Zeit-Index und Last-Index eines Labels |
| $K_T$, $K_R$ | Zahl der Zeit-Eimer und der Last-Eimer |
| $\mathrm{cmp}_1$, $\mathrm{cmp}_2$ | Zahl der Vergleiche „wird $N$ dominiert?“ und „dominiert $N$ alte Labels?“ |
| $\lambda$ | Gewicht je Eimerschritt (eine Annahme) |

**Fortsetzung** eines Labels $(T, C, R, M)$ am Knoten $i$ zum Kunden $j \notin M$ (mit $s\,[i \ne 0]$: im Depot entfällt die Bedienzeit):

$$T' = \max\bigl(e_j,\; T + s\,[i \ne 0] + d_{ij}\bigr), \quad C' = C + d_{ij} - \pi_j, \quad R' = R + q_j, \quad M' = (M \cap NG(j)) \cup \{j\}$$

Zulässig ist sie, wenn $T + s\,[i \ne 0] + d_{ij} \le l_j$ und $R' \le Q$ gelten; $NG(j)$ sind die $k$ nächsten Kunden von $j$ (einschließlich $j$), $k = n$ heißt elementar.

**Dominanz:**

$$O \preceq N \iff C_O \le C_N, \quad T_O \le T_N, \quad R_O \le R_N, \quad M_O \subseteq M_N$$

**Eimer.** Ein Label mit Zeit $T$ und Last $R$ liegt im Eimer $(\beta_T(T), \beta_R(R))$ seines Kunden mit

$$\beta_T(T) = \min\bigl(\lfloor T / w_T \rfloor,\; K_T - 1\bigr), \quad \beta_R(R) = \min\bigl(\lfloor R / w_R \rfloor,\; K_R - 1\bigr), \quad K_T = \lfloor H / w_T \rfloor + 1, \quad K_R = \lfloor Q / w_R \rfloor + 1$$

Ohne Eimer einer Art ist $K = 1$ (ein einziger Eimer). Weil $\lfloor \cdot \rfloor$ monoton ist, gilt für zwei Labels $O$ und $N$ am selben Kunden:

$$O \preceq N \;\Rightarrow\; \beta_T(T_O) \le \beta_T(T_N) \ \text{und}\ \beta_R(R_O) \le \beta_R(R_N), \qquad N \preceq O \;\Rightarrow\; \beta_T(T_O) \ge \beta_T(T_N) \ \text{und}\ \beta_R(R_O) \ge \beta_R(R_N)$$

**Suchbereiche.** $\mathrm{cmp}_1$ prüft $N$ nur gegen Labels in Eimern mit $\beta_T \le \beta_T(T_N)$ und $\beta_R \le \beta_R(R_N)$ (mit Abbruch beim ersten dominierenden Label), $\mathrm{cmp}_2$ nur gegen Labels in Eimern mit
$\beta_T \ge \beta_T(T_N)$ und $\beta_R \ge \beta_R(R_N)$. Kein übersprungenes Label kann in der jeweiligen Richtung dominieren, die Menge der lebenden Labels ist also dieselbe wie ohne Eimer (die Tests prüfen es an 408 Fällen gegen einen unabhängigen
Rechenweg). **Eimerschritte** (nach Formel gezählt, auch leere Eimer): $(\beta_T(T_N)+1)(\beta_R(R_N)+1)$ für $\mathrm{cmp}_1$ und $(K_T-\beta_T(T_N))(K_R-\beta_R(R_N))$ für $\mathrm{cmp}_2$. **Aufwand:**
$\mathrm{cmp}_1 + \mathrm{cmp}_2 + \lambda \cdot \text{Eimerschritte}$.

**Eimerrand.** Die Dominanzprüfung vergleicht Kosten und Zeit mit der Toleranz $\varepsilon = 10^{-9}$. Die Suche beginnt deshalb bei $\beta_T(T_N - \varepsilon)$ (cmp2) bzw. endet bei $\beta_T(T_N + \varepsilon)$ (cmp1). Liegt $T_N$ genau auf einer Eimergrenze, sieht cmp2 einen Eimer mehr an
(unnötig, nie falsch). Das Handbeispiel rechnet mit $\varepsilon = 0$.

**Zählgrößen.** *Labels:* jedes erzeugte Label, auch ein sofort verworfenes, plus das Start-Label. *Dominanzvergleiche:* jedes tatsächlich ausgeführte Paar (neues Label, vorhandenes Label). Dass die Zahl der Vergleiche mit feineren Eimern fällt, ist in den Läufen
gezählt, kein Satz; dass sie nicht über die ohne Eimer steigt, folgt aus den Suchbereichen und wird in den Tests geprüft.

**Literatur** (Prüfstand: was gelesen wurde, steht dabei; die Demo übernimmt keine Zahl daraus, und gemessen ist nur die einfache Ablage je Kunde, nicht der Bucket-Graph):
- Sadykov, Uchoa, Pessoa (2021): A bucket graph–based labeling algorithm with application to vehicle routing, Transportation Science 55(1), 4–28 (Eimer nach Ressourcenbereich, weniger Dominanzprüfungen, bidirektional; nur die Zusammenfassung gelesen).
- Pessoa, Sadykov, Uchoa, Vanderbeck (2020): A generic exact solver for vehicle routing and related problems, Mathematical Programming 183, 483–523 (Umsetzung des Bucket-Graphen im Löser; Volltext gelesen, aber hier nicht gemessen).
- Pecin, Pessoa, Poggi, Uchoa (2017): Improved branch-cut-and-price for capacitated vehicle routing, Mathematical Programming Computation 9(1), 61–100 (Eimer in einem Branch-Cut-and-Price; nur als Suchtreffer gesehen, nicht nachgelesen).
        """
    )

st.markdown("---")

with st.expander("⚠️ Annahmen, Grenzen und bekannte Probleme"):
    st.markdown(C.ASSUMPTIONS_MARKDOWN)

st.markdown("---")
st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html)."
)
