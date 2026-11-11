"""Plotly-Abbildungen. Alle Achsen fest (`fixedrange`), damit Touch-Scrollen auf der Seite nicht am Diagramm hängen bleibt; keine Log-Achsen mit Nullwerten,
feste Wertebereiche aus den Daten (nie leer, nie unendlich)."""

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import eml_constants as C
import eml_evaluation as ev


def _layout(fig, height, title=None, legend_bottom=False):
    """Einheitliches Layout; die Legende steht oben (ohne Titel) oder unter dem Diagramm (bei Titeln und Teildiagrammen, damit nichts überlappt)."""
    legend = dict(orientation="h", yanchor="top", y=-0.18, x=0) if legend_bottom else dict(orientation="h", yanchor="bottom", y=1.02, x=0)
    fig.update_layout(height=height, margin=dict(l=55, r=20, t=40 if title else 15, b=95 if legend_bottom else 45), title=title, legend=legend, dragmode=False)
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _zeit_label(w: int) -> str:
    return "ohne Eimer" if w == 0 else f"Zeit {w}"


def build_hand_map(inst, route, depot_label="Depot") -> go.Figure:
    """Das Handbeispiel: Depot und sechs Kunden auf dem Gitter, die beste Route (falls vorhanden) als Linie (erst waagerecht, dann senkrecht)."""
    fig = go.Figure()
    if route:
        seq = (0,) + tuple(route) + (0,)
        xs, ys = [], []
        for a, b in zip(seq, seq[1:]):
            (x0, y0), (x1, y1) = inst.points[a], inst.points[b]
            xs += [x0, x1, x1]
            ys += [y0, y0, y1]
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=C.COLOR_OK, width=3), name="beste Route", hoverinfo="skip"))
    xs = [p[0] for p in inst.points]
    ys = [p[1] for p in inst.points]
    fig.add_trace(go.Scatter(x=xs[1:], y=ys[1:], mode="markers", marker=dict(size=22, color=C.COLOR_LINE), name="Kunde", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=xs[:1], y=ys[:1], mode="markers", marker=dict(size=22, color=C.COLOR_LINE2, symbol="square"), name=depot_label, hoverinfo="skip"))
    for i in range(1, inst.n + 1):
        fig.add_annotation(x=xs[i], y=ys[i], text=f"<b>{i}</b>", showarrow=False, font=dict(color="white", size=12))
        fig.add_annotation(x=xs[i], y=ys[i] - 0.75, text=f"[{inst.ready[i]}, {inst.due[i]}] · Last {inst.demand[i]}", showarrow=False, font=dict(size=10), bgcolor="rgba(255,255,255,0.80)",
                           font_color="#333")
    fig.add_annotation(x=xs[0], y=ys[0], text="<b>D</b>", showarrow=False, font=dict(color="white", size=12))
    fig.update_xaxes(range=[-1, 9], showgrid=True, zeroline=False, dtick=1)
    fig.update_yaxes(range=[-1.7, 8.5], showgrid=True, zeroline=False, dtick=1)
    return _layout(fig, 380)


def build_sweep_chart(runs: dict) -> go.Figure:
    """Experiment 2: Vergleiche (Anteil an denen ohne Eimer) und angesehene Eimer je Zeit-Breite (grob nach fein; 'ohne Eimer' links); dazu Last 5 und Last 10 als Punkte."""
    order = [w for w in C.SWEEP_WT if (w, 0) in runs]
    base = runs[(0, 0)].comparisons
    xs = [_zeit_label(w) for w in order]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=False, vertical_spacing=0.18, subplot_titles=("Vergleiche (Anteil an den Vergleichen ohne Eimer)", "angesehene Eimer (nach Formel gezählt)"))
    fig.add_trace(go.Scatter(x=xs, y=[runs[(w, 0)].comparisons / base for w in order], mode="lines+markers", name="Zeit-Eimer", line=dict(color=C.COLOR_LINE)), row=1, col=1)
    lasts = [(q, runs[(0, q)]) for q in (5, 10) if (0, q) in runs]
    if lasts:
        fig.add_trace(go.Scatter(x=[f"Last {q}" for q, _ in lasts], y=[r.comparisons / base for _, r in lasts], mode="markers", name="Last-Eimer",
                                 marker=dict(color=C.COLOR_LINE2, size=11, symbol="diamond")), row=1, col=1)
    fig.add_trace(go.Bar(x=xs, y=[runs[(w, 0)].steps for w in order], name="Eimerschritte (Zeit)", marker_color=C.COLOR_LINE, showlegend=False), row=2, col=1)
    if lasts:
        fig.add_trace(go.Bar(x=[f"Last {q}" for q, _ in lasts], y=[r.steps for _, r in lasts], name="Eimerschritte (Last)", marker_color=C.COLOR_LINE2, showlegend=False), row=2, col=1)
    top = max(max(r.steps for r in runs.values()), 1)
    fig.update_yaxes(range=[0, 1.1], row=1, col=1)
    fig.update_yaxes(range=[0, top * 1.12], row=2, col=1)
    fig.update_xaxes(categoryorder="array", categoryarray=xs + [f"Last {q}" for q, _ in lasts], row=1, col=1)
    fig.update_xaxes(categoryorder="array", categoryarray=xs + [f"Last {q}" for q, _ in lasts], row=2, col=1)
    return _layout(fig, 600, legend_bottom=True)


def build_optimum_chart(runs: dict, weights=C.BAND_WEIGHTS) -> go.Figure | None:
    """Experiment 3: Aufwand (Vergleiche + Gewicht x Eimerschritte) je Zeit-Breite im Verhältnis zum Aufwand ohne Eimer, für jedes Gewicht; logarithmische Achse (alle Werte > 0).
    Gibt None zurück, wenn der Bezug 0 ist (nichts zu zeigen)."""
    order = [w for w in C.SWEEP_WT if (w, 0) in runs]
    fig = go.Figure()
    colors = [C.COLOR_LINE, C.COLOR_LINE2, C.COLOR_LINE3]
    values = []
    for g, col in zip(weights, colors):
        b = ev.net_cost(runs[(0, 0)], g)
        if b <= 0:
            return None
        ys = [ev.net_cost(runs[(w, 0)], g) / b for w in order]
        values += ys
        fig.add_trace(go.Scatter(x=[_zeit_label(w) for w in order], y=ys, mode="lines+markers", name=f"Gewicht {ev.fmt_dec(g, 1)}", line=dict(color=col)))
    lo = min(min(values), 1.0)
    hi = max(max(values), 1.0)
    fig.update_yaxes(type="log", range=[math.log10(lo * 0.9), math.log10(hi * 1.15)], title="Aufwand / Aufwand ohne Eimer", tickvals=[v for v in (0.5, 1, 2, 5, 10, 20, 50, 100) if lo * 0.9 <= v <= hi * 1.15],
                     ticktext=[ev.fmt_dec(v, 1).replace(",0", "") if v >= 1 else ev.fmt_dec(v, 1) for v in (0.5, 1, 2, 5, 10, 20, 50, 100) if lo * 0.9 <= v <= hi * 1.15])
    fig.add_hline(y=1.0, line_dash="dot", line_color="rgba(120,120,120,0.8)")
    fig.update_xaxes(categoryorder="array", categoryarray=[_zeit_label(w) for w in order])
    return _layout(fig, 380)


def build_optimum_bars(counts_by_weight: dict, q: int) -> go.Figure:
    """Experiment 3: Häufigkeit (Anteil der 160 Läufe einer Kapazität), mit der jede Zeit-Breite (oder keine) bei dem Gewicht den kleinsten Aufwand hat."""
    fig = go.Figure()
    colors = [C.COLOR_LINE, C.COLOR_LINE2, C.COLOR_LINE3]
    xs = [_zeit_label(c[0]) for c in ev.ZEIT_CFGS]
    top = 1.0
    for (g, res), col in zip(counts_by_weight.items(), colors):
        ys = [100 * res["counts"][c] / res["n"] for c in ev.ZEIT_CFGS]
        top = max(top, max(ys))
        fig.add_trace(go.Bar(x=xs, y=ys, name=f"Gewicht {ev.fmt_dec(g, 1)}", marker_color=col))
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, min(100, top * 1.15 + 2)], title="Anteil der Läufe in %")
    fig.update_xaxes(categoryorder="array", categoryarray=xs)
    return _layout(fig, 400, title=f"Kapazität {q}", legend_bottom=True)


def build_split_chart(runs: dict, configs=C.SPLIT_CONFIGS) -> go.Figure:
    """Experiment 4: Vergleiche je Einstellung, aufgeteilt in cmp1 (wird das neue Label dominiert?) und cmp2 (dominiert das neue Label alte?)."""
    names = [ev.config_name(*c) for c in configs]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=[runs[c].cmp1 for c in configs], name="cmp1: wird das neue Label dominiert?", marker_color=C.COLOR_LINE))
    fig.add_trace(go.Bar(x=names, y=[runs[c].cmp2 for c in configs], name="cmp2: dominiert das neue Label alte?", marker_color=C.COLOR_LINE2))
    fig.update_layout(barmode="stack")
    top = max(max(runs[c].comparisons for c in configs), 1)
    fig.update_yaxes(range=[0, top * 1.12], title="Vergleiche")
    fig.update_xaxes(categoryorder="array", categoryarray=names)
    return _layout(fig, 430, legend_bottom=True)


def build_hand_split_chart(rows: list) -> go.Figure:
    """Experiment 4, Handbeispiel: cmp1 und cmp2 je Einstellung (Zeit-Eimer 10, Last-Eimer 3, beide, ohne)."""
    sel = [r for r in rows if (r["wt"], r["wq"]) in ((0, 0), (10, 0), (0, 3), (10, 3))]
    names = [r["name"] for r in sel]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=names, y=[r["cmp1"] for r in sel], name="cmp1", marker_color=C.COLOR_LINE))
    fig.add_trace(go.Bar(x=names, y=[r["cmp2"] for r in sel], name="cmp2", marker_color=C.COLOR_LINE2))
    fig.update_layout(barmode="stack")
    fig.update_yaxes(range=[0, max(r["comparisons"] for r in sel) * 1.12], title="Vergleiche")
    fig.update_xaxes(categoryorder="array", categoryarray=names)
    return _layout(fig, 390, legend_bottom=True)


def build_band_chart(rows: list) -> go.Figure:
    """Experiment 5: je Einstellung Median (Balken), Mittel (Raute) und Maximum (Strich) des Verhältnisses 'Vergleiche mit Eimern / ohne Eimer' über die Läufe einer Zelle."""
    sel = [r for r in rows if r["cfg"] != (0, 0)]
    names = [r["name"] for r in sel]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=names, x=[r["median"] for r in sel], orientation="h", name="Median", marker_color=C.COLOR_LINE))
    fig.add_trace(go.Scatter(y=names, x=[r["mean"] for r in sel], mode="markers", name="Mittel", marker=dict(symbol="diamond", size=9, color=C.COLOR_LINE2)))
    fig.add_trace(go.Scatter(y=names, x=[r["max"] for r in sel], mode="markers", name="Maximum", marker=dict(symbol="line-ns-open", size=14, color=C.COLOR_BAD, line=dict(width=2))))
    top = max([1.0] + [r["max"] for r in sel])
    fig.update_xaxes(range=[0, top * 1.05], title="Vergleiche mit Eimern / Vergleiche ohne Eimer")
    fig.update_yaxes(categoryorder="array", categoryarray=names[::-1])
    return _layout(fig, 120 + 28 * len(sel))
