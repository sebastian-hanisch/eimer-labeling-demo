"""Auswertung: Live-Läufe, Handbeispiel, feste Messreihen, Zahlenformate und die Verdikte der App (reine Funktionen: Art, Text; DEMO-PLAYBOOK §12)."""

import hashlib
import json
import statistics
from dataclasses import dataclass
from pathlib import Path

import eml_algorithm as A
import eml_colgen as G
import eml_constants as C
from eml_scenario import HAND_DUALS, Instance, hand_instance, make_instance

DATA = Path(__file__).resolve().parent / "data"


# --- Formate --------------------------------------------------------------------------------------------------------------------------------

def fmt_int(n) -> str:
    """Ganze Zahl mit Leerzeichen als Tausendertrenner (4 424 statt 4424)."""
    return f"{int(round(n)):,}".replace(",", " ")


def fmt_dec(x: float, digits: int = 1) -> str:
    """Dezimalzahl mit deutschem Komma und immer gleich vielen Nachkommastellen (echtes Minuszeichen)."""
    return f"{x:.{digits}f}".replace(".", ",").replace("-", "−")


def fmt_pct(x: float, digits: int = 1) -> str:
    """Prozentwert (x ist schon in Prozent) mit deutschem Komma."""
    return f"{fmt_dec(x, digits)} %"


def fmt_ratio(x: float) -> str:
    """Verhältnis mit drei Nachkommastellen und deutschem Komma (0,809)."""
    return fmt_dec(x, 3)


def config_name(wt: int, wq: int) -> str:
    """Name einer Eimer-Einstellung: 'ohne Eimer', 'Zeit 10', 'Last 5', 'Zeit 10 × Last 5' (0 heißt kein Eimer dieser Art)."""
    if not wt and not wq:
        return "ohne Eimer"
    if not wq:
        return f"Zeit {wt}"
    if not wt:
        return f"Last {wq}"
    return f"Zeit {wt} × Last {wq}"


def route_text(route) -> str:
    return "–".join(str(j) for j in route) if route else "keine"


# --- Live-Instanz ---------------------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Die Live-Instanz: Größe, Fensterbreite, Typ ('zufall' oder 'cluster'), Kapazität, Zufalls-Seed (Gedächtnis immer k = 5, Dualpreise am Ende der Spaltenerzeugung)."""

    n: int
    width: int
    typ: str
    q: int
    seed: int


@dataclass(frozen=True)
class Run:
    """Zähler eines Laufs mit einer Eimer-Einstellung (0 = kein Eimer dieser Art) und ein Fingerabdruck des Ergebnisses (Routen, lebende Labels, erzeugte und gestrichene Labels)."""

    wt: int
    wq: int
    generated: int
    dominated: int
    cmp1: int
    cmp2: int
    steps: int
    aborted: bool
    digest: str
    n_routes: int
    best_rc: float | None
    best_route: tuple | None
    live: int

    @property
    def comparisons(self) -> int:
        return self.cmp1 + self.cmp2


def instance_of(s: Settings) -> Instance:
    return make_instance(s.n, s.seed, s.width, capacity=s.q, clustered=(s.typ == "cluster"))


def live_duals(s: Settings) -> dict:
    """Spaltenerzeugung der Live-Instanz (Überdeckungs-Master, k = 5): Dualpreise der letzten Runde, Runden, Schranke; bei Abbruch am Labelbudget ende = None."""
    return G.colgen_duals(instance_of(s), C.MEMORY_K, rounds=(), max_labels_per_call=C.MAX_LABELS_CALL, max_labels_total=C.MAX_LABELS_COLGEN)


def fingerprint(res: A.PricingResult) -> str:
    return hashlib.sha1(repr((res.routes, res.live, res.generated, res.dominated)).encode()).hexdigest()


def live_run(inst: Instance, pi, wt: int, wq: int, max_labels=C.MAX_LABELS) -> Run:
    """Ein Lauf mit Zeit-Eimerbreite `wt` und Last-Eimerbreite `wq` (0 = keiner) auf der Instanz mit den Dualpreisen `pi` (alle negativen Routen, Gedächtnis k = 5)."""
    res = A.price(inst, pi, C.MEMORY_K, wt or None, wq or None, max_routes=10 ** 6, max_labels=max_labels)
    best_rc = res.best[0] if res.best else None
    best_route = res.best[1] if res.best else None
    return Run(wt, wq, res.generated, res.dominated, res.cmp1, res.cmp2, res.steps, res.aborted, fingerprint(res), len(res.routes), best_rc, best_route, len(res.live))


def same_result(a: Run, b: Run) -> bool:
    """Gleiches Ergebnis: dieselben negativen Routen, dieselbe Menge lebender Labels, dieselbe Zahl erzeugter und gestrichener Labels (Fingerabdruck)."""
    return a.digest == b.digest


def net_cost(run: Run, weight: float) -> float:
    """Aufwand = Vergleiche + Gewicht x Eimerschritte. Das Gewicht ist eine Annahme (Voreinstellung 0,1), keine Messung."""
    return run.comparisons + weight * run.steps


def saved_share(base: Run, run: Run) -> float | None:
    """Anteil der gesparten Vergleiche (0 bis 1; negativ, wenn mehr nötig waren), None ohne Vergleiche im Bezug."""
    return None if base.comparisons == 0 else 1.0 - run.comparisons / base.comparisons


def net_ratio(base: Run, run: Run, weight: float) -> float | None:
    """Aufwand mit Eimern geteilt durch Aufwand ohne Eimer (bei Gewicht `weight`); None, wenn der Bezug 0 ist."""
    b = net_cost(base, weight)
    return None if b == 0 else net_cost(run, weight) / b


def split_ratios(base: Run, run: Run) -> tuple:
    """(Anteil cmp1, Anteil cmp2) der Vergleiche mit Eimern an denen ohne Eimer; None, wo der Bezug 0 ist."""
    return (None if base.cmp1 == 0 else run.cmp1 / base.cmp1, None if base.cmp2 == 0 else run.cmp2 / base.cmp2)


def best_zeit_width(runs: dict, weight: float) -> int:
    """Zeit-Breite (0 = ohne Eimer) mit dem kleinsten Aufwand bei diesem Gewicht; bei Gleichstand die erste in der Reihenfolge von C.SWEEP_WT (ohne Eimer zuerst)."""
    return min((w for w in C.SWEEP_WT if (w, 0) in runs), key=lambda w: net_cost(runs[(w, 0)], weight))


# --- Verdikte -------------------------------------------------------------------------------------------------------------------------------

def verdict_identical(same: bool) -> tuple:
    """Die Eimer dürfen das Ergebnis nie ändern."""
    if same:
        return ("success", "Dieselbe Menge lebender Labels wie ohne Eimer: ja. Gleich sind auch die Zahl der erzeugten und der gestrichenen Labels und die Liste der negativen Routen; "
                           "nur die Zahl der Vergleiche ändert sich.")
    return ("error", "Die Eimer ändern das Ergebnis (lebende Labels, Zahl der Labels oder Routen weichen vom Lauf ohne Eimer ab): Der Kern ist fehlerhaft.")


def verdict_saving(base: Run, run: Run, weight: float) -> tuple:
    """Wie viel sparen die Eimer dieser Einstellung, vor und nach Abzug der Verwaltung (Gewicht je Eimerschritt)?"""
    if base.aborted:
        return ("warning", f"Die Rechnung ist nach {fmt_int(C.MAX_LABELS)} erzeugten Labels abgebrochen (Labelbudget der Live-Rechnung); die Zähler sind unvollständig. "
                           "Kleinere Instanz wählen oder die festen Messreihen in Experiment 5 ansehen.")
    if not run.wt and not run.wq:
        return ("info", f"Kein Eimer gewählt: Das ist die Bezugsrechnung mit {fmt_int(base.comparisons)} Vergleichen. Eine Zeit- oder Lastbreite in der Seitenleiste wählen.")
    share = saved_share(base, run)
    ratio = net_ratio(base, run, weight)
    if share is None or ratio is None:
        return ("info", "Ohne Eimer gibt es auf dieser Instanz keinen Vergleich: Hier ist nichts zu sparen.")
    head = f"{config_name(run.wt, run.wq)}: {fmt_int(run.comparisons)} statt {fmt_int(base.comparisons)} Vergleichen"
    if share > 0:
        head += f", also {fmt_pct(share * 100)} weniger."
    elif share == 0:
        head += ": keine Ersparnis."
    else:
        head += f", also {fmt_pct(-share * 100)} mehr."
    tail = (f" Zusammen mit {fmt_int(run.steps)} angesehenen Eimern (Bezug: {fmt_int(base.steps)}) und einem Gewicht von {fmt_dec(weight, 2)} je Eimerschritt "
            f"(Annahme, keine Messung) liegt der Aufwand bei {fmt_pct(ratio * 100)} des Aufwands ohne Eimer")
    if ratio < 1:
        return ("success", head + tail + f": netto werden {fmt_pct((1 - ratio) * 100)} gespart.")
    return ("warning", head + tail + f": bei diesem Gewicht lohnt sich diese Eimerbreite nicht (netto {fmt_pct((ratio - 1) * 100)} mehr).")


def verdict_split(base: Run, zeit: Run, last: Run) -> tuple:
    """Zeit-Eimer sparen fast nur die Prüfung „dominiert das neue Label alte?“ (cmp2), Last-Eimer auch „wird das neue Label dominiert?“ (cmp1)."""
    if base.aborted:
        return ("warning", "Die Rechnung ist am Labelbudget abgebrochen; die Aufteilung ist unvollständig.")
    z1, z2 = split_ratios(base, zeit)
    l1, l2 = split_ratios(base, last)
    if None in (z1, z2, l1, l2):
        return ("info", "Ohne Vergleiche in einer der beiden Prüfungen gibt es keine Aufteilung zu zeigen.")
    text = (f"{config_name(zeit.wt, zeit.wq)} lässt cmp1 bei {fmt_pct(z1 * 100)} und cmp2 bei {fmt_pct(z2 * 100)} der Vergleiche ohne Eimer; "
            f"{config_name(last.wt, last.wq)} lässt cmp1 bei {fmt_pct(l1 * 100)} und cmp2 bei {fmt_pct(l2 * 100)}.")
    if z1 > 0.95 and z2 < 0.95 and l1 < z1:
        return ("success", text + " Die Zeit-Eimer sparen hier nur cmp2; die Last-Eimer sparen auch cmp1.")
    return ("info", text + " Auf dieser Instanz zeigt sich das Muster „Zeit-Eimer sparen nur cmp2, Last-Eimer auch cmp1“ nicht in dieser Deutlichkeit.")


def verdict_optimum(runs: dict, weights=C.BAND_WEIGHTS) -> tuple:
    """Beste Zeit-Breite je Gewicht auf der Live-Instanz."""
    if any(r.aborted for r in runs.values()):
        return ("warning", "Mindestens ein Lauf ist am Labelbudget abgebrochen; die Kurven sind unvollständig.")

    def name(w):
        return "ohne Eimer" if w == 0 else f"Zeit-Breite {w}"
    parts = [f"Gewicht {fmt_dec(g, 1)}: {name(best_zeit_width(runs, g))}" for g in weights]
    return ("info", "Beste Wahl auf dieser Instanz (kleinster Aufwand aus Vergleichen und Eimerschritten): " + "; ".join(parts) + ".")


def verdict_monotone(runs: dict) -> tuple:
    """Die Vergleiche sinken mit feineren Zeit-Eimern, solange nichts anderes dazwischenkommt; steigen sie bei einem Schritt der Reihe von C.SWEEP_WT, steht der Schritt im Text."""
    order = [w for w in C.SWEEP_WT if (w, 0) in runs]
    cmps = [runs[(w, 0)].comparisons for w in order]
    up = [(order[i], order[i + 1]) for i in range(len(order) - 1) if cmps[i + 1] > cmps[i]]
    steps = [runs[(w, 0)].steps for w in order]
    if any(runs[(w, 0)].aborted for w in order):
        return ("warning", "Mindestens ein Lauf ist am Labelbudget abgebrochen; die Reihe ist unvollständig.")
    if up:
        return ("info", "Bei diesem Schritt der Reihe steigen die Vergleiche mit dem feineren Eimer: " + ", ".join(f"{_zeit_name(a)} → {_zeit_name(b)}" for a, b in up)
                + ". Deutung (nicht eigens gemessen): Mit Eimern wird in anderer Reihenfolge geprüft (nach Eimern statt nach Einfügen), und cmp1 bricht beim ersten dominierenden Label ab; dadurch kann cmp1 im Einzelfall leicht steigen.")
    return ("info", f"Die Vergleiche steigen bei keinem Schritt der Reihe, von {fmt_int(cmps[0])} ohne Eimer auf {fmt_int(cmps[-1])} bei Breite {order[-1]}; "
                    f"die angesehenen Eimer steigen dabei von {fmt_int(steps[0])} auf {fmt_int(steps[-1])}.")


def _zeit_name(w: int) -> str:
    return "ohne Eimer" if w == 0 else f"Zeit {w}"


# --- Handbeispiel ---------------------------------------------------------------------------------------------------------------------------

HAND_CONFIGS = ((0, 0), (10, 0), (0, 3), (10, 3), (5, 0), (5, 3))


def hand_run(wt: int, wq: int, rand: float = 0.0, trace: bool = False) -> A.PricingResult:
    """Das Handbeispiel mit Eimerbreiten (0 = keine); `rand = 0`: exakte Eimergrenzen (ganze Zahlen), `rand = A.EPS`: Fassung der Messreihen."""
    return A.price(hand_instance(), HAND_DUALS, hand_instance().n, wt or None, wq or None, rand=rand, max_routes=10 ** 6, trace=trace)


def hand_overview(rand: float = 0.0) -> list:
    """Eine Zeile je Einstellung des Handbeispiels: Zähler und Vergleich mit dem Lauf ohne Eimer."""
    base = hand_run(0, 0, rand)
    rows = []
    for wt, wq in HAND_CONFIGS:
        r = hand_run(wt, wq, rand)
        rows.append({"wt": wt, "wq": wq, "name": config_name(wt, wq), "generated": r.generated, "dominated": r.dominated, "cmp1": r.cmp1, "cmp2": r.cmp2, "comparisons": r.comparisons,
                     "steps": r.steps, "net": r.comparisons + 0.1 * r.steps, "same": (r.live, r.routes, r.generated, r.dominated) == (base.live, base.routes, base.generated, base.dominated)})
    return rows


def hand_label_info(events: list) -> dict:
    """Nummer des Labels -> (Knoten, Zeit, Last, Eimer (Zeit-Index, Last-Index)) für alle neuen Labels eines Laufs mit trace."""
    return {e["nr"]: (e["node"], e["time"], e["load"], e["bucket"]) for e in events}


def hand_bucket_of(nr: int, info: dict, wt: int, wq: int) -> tuple:
    node, t, q, _ = info[nr]
    inst = hand_instance()
    return (A.bucket_of(t, wt or None, A.bucket_count(inst.horizon, wt or None)), A.bucket_of(q, wq or None, A.bucket_count(inst.capacity, wq or None)))


def skip_reason(kind: str, o_bucket: tuple, own: tuple) -> str:
    """Warum ein lebendes Label an diesem Knoten bei der Prüfung `kind` ('cmp1' oder 'cmp2') nicht angesehen wird (aus den Eimerindizes)."""
    (ot, oq), (nt_, nq_) = o_bucket, own
    if kind == "cmp1":
        if ot > nt_:
            return f"Zeit-Eimer {ot} > {nt_}"
        if oq > nq_:
            return f"Last-Eimer {oq} > {nq_}"
    else:
        if ot < nt_:
            return f"Zeit-Eimer {ot} < {nt_}"
        if oq < nq_:
            return f"Last-Eimer {oq} < {nq_}"
    return ""


def hand_step_rows(wt: int, wq: int) -> list:
    """Eine Zeile je neues Label des Handbeispiels: Eimer, Vergleiche ohne und mit Eimern, Entscheidung."""
    base = hand_run(0, 0, trace=True).events
    bucketed = hand_run(wt, wq, trace=True).events
    rows = []
    for b, e in zip(base, bucketed):
        assert (b["nr"], b["node"], b["time"], b["load"], b["status"]) == (e["nr"], e["node"], e["time"], e["load"], e["status"])
        rows.append({"nr": e["nr"], "node": e["node"], "time": e["time"], "load": e["load"], "bucket": e["bucket"], "status": e["status"],
                     "base1": len(b["ex1"]), "base2": len(b["ex2"]), "cmp1": len(e["ex1"]), "cmp2": len(e["ex2"]), "live_before": len(e["live_before"])})
    return rows


def hand_step_detail(nr: int, wt: int, wq: int) -> dict:
    """Die Prüfung des neuen Labels Nummer `nr` (1 bis 34) mit Eimern: Eimertabelle des Knotens vor dem Einfügen, angesehene und übersprungene Labels mit Grund."""
    res = hand_run(wt, wq, trace=True)
    base = hand_run(0, 0, trace=True)
    info = hand_label_info(res.events)
    e = next(x for x in res.events if x["nr"] == nr)
    b = next(x for x in base.events if x["nr"] == nr)
    own = e["bucket"]
    inst = hand_instance()
    nt = A.bucket_count(inst.horizon, wt or None)
    nq = A.bucket_count(inst.capacity, wq or None)
    cells = {}
    for o in e["live_before"]:
        cells.setdefault(hand_bucket_of(o, info, wt, wq), []).append(o)
    skipped1, skipped2 = [], []
    for o in e["live_before"]:
        ob = hand_bucket_of(o, info, wt, wq)
        if o not in e["ex1"]:
            skipped1.append((o, skip_reason("cmp1", ob, own) or "nach dem ersten dominierenden Label nicht mehr angesehen"))
        if e["status"] == "behalten" and o not in e["ex2"]:
            skipped2.append((o, skip_reason("cmp2", ob, own)))
    return {"event": e, "base": b, "info": info, "nt": nt, "nq": nq, "cells": cells, "own": own, "skipped1": skipped1, "skipped2": skipped2,
            "wt": wt, "wq": wq, "horizon": inst.horizon, "capacity": inst.capacity}


def bucket_axis_labels(limit: int, width: int, count: int, unit: str) -> list:
    """Beschriftung der Eimerindizes: '0–9', '10–19', …, letzter Eimer '40 und mehr'; ohne Breite ein einziger Eimer."""
    if not width:
        return [f"alle {unit}"]
    labels = [f"{i * width}–{(i + 1) * width - 1}" for i in range(count - 1)]
    labels.append(f"{(count - 1) * width} und mehr")
    return labels


def rounding_difference() -> dict:
    """E12.5: dasselbe Handbeispiel mit exakten Eimergrenzen und mit dem Sicherheitsrand der Messreihen (cmp2 bei Zeit-Eimer 10 und bei Zeit 10 × Last 3)."""
    out = {}
    for wt, wq in ((10, 0), (10, 3)):
        out[(wt, wq)] = (hand_run(wt, wq, 0.0).cmp2, hand_run(wt, wq, A.RAND_MESSCODE).cmp2)
    return out


def verdict_hand(rows: list, wt: int, wq: int) -> tuple:
    """Verdikt des Handbeispiels für die gewählte Einstellung (Zähler aus `hand_overview`-Zeilen)."""
    base = rows[0]
    sel = next(r for r in rows if (r["wt"], r["wq"]) == (wt, wq))   # HAND_CONFIGS enthält jede Kombination der Handbeispiel-Regler
    if not sel["same"]:
        return ("error", "Die Eimer ändern am Handbeispiel das Ergebnis: Der Kern ist fehlerhaft.")
    if not wt and not wq:
        return ("info", f"Ohne Eimer prüft das Verfahren jedes neue Label gegen alle lebenden Labels des Knotens: {base['cmp1']} Vergleiche für „wird das neue Label dominiert?“ und {base['cmp2']} für „dominiert das neue Label alte?“.")
    return ("success", f"{sel['name']}: dieselben {base['generated']} erzeugten Labels, dieselben {base['dominated']} gestrichenen, dieselbe beste Route. {sel['cmp1']} + {sel['cmp2']} = {sel['comparisons']} Vergleiche statt "
                       f"{base['cmp1']} + {base['cmp2']} = {base['comparisons']}; angesehene Eimer: {sel['steps']} statt {base['steps']}.")


# --- Feste Messreihen -----------------------------------------------------------------------------------------------------------------------

def load_bands(path=None) -> list:
    """Die 320 Läufe der festen Messreihen (data/laeufe_v10.json); je Lauf `einstellungen` mit Schlüssel (Zeitbreite, Lastbreite) -> [Labels, gestrichen, cmp1, cmp2, Schritte, gleich, Sekunden]."""
    raw = json.loads(Path(path or DATA / "laeufe_v10.json").read_text(encoding="utf-8"))
    out = []
    for lauf in raw["laeufe"]:
        cfgs = {tuple(int(x) for x in k.split(",")): v for k, v in lauf["einstellungen"].items()}
        out.append({**lauf, "einstellungen": cfgs})
    return out


def band_comparisons(lauf: dict, cfg: tuple) -> int:
    v = lauf["einstellungen"][cfg]
    return v[2] + v[3]


def band_ratio(lauf: dict, cfg: tuple, part: str = "all", weight: float = 0.0) -> float:
    """Verhältnis (Aufwand mit Eimern) / (Aufwand ohne Eimer) eines Laufs; part 'all' (cmp1 + cmp2), 'cmp1' oder 'cmp2'; Aufwand = Vergleiche + weight x Eimerschritte (nur bei 'all')."""
    v, b = lauf["einstellungen"][cfg], lauf["einstellungen"][(0, 0)]
    if part == "cmp1":
        return v[2] / b[2]
    if part == "cmp2":
        return v[3] / b[3]
    return (v[2] + v[3] + weight * v[4]) / (b[2] + b[3] + weight * b[4])


def stats_of(values) -> dict:
    """Median, Mittel, Maximum und Zahl der Werte."""
    values = list(values)
    return {"median": statistics.median(values), "mean": statistics.fmean(values), "max": max(values), "min": min(values), "n": len(values)}


def select(laeufe: list, q=None, runde=None, typ=None) -> list:
    return [x for x in laeufe if (q is None or x["Q"] == q) and (runde is None or x["runde"] == runde) and (typ is None or x["typ"] == typ)]


def band_time_ratio(sel: list, cfg: tuple):
    """Median des Verhältnisses der gemessenen Sekunden (Einstellung / ohne Eimer) über die Läufe, deren Lauf ohne Eimer länger als 0,02 s dauerte; nur Information (parallele Läufe)."""
    ratios = [x["einstellungen"][cfg][6] / x["einstellungen"][(0, 0)][6] for x in sel if x["einstellungen"][(0, 0)][6] > 0.02]
    return statistics.median(ratios) if ratios else None


def band_table(laeufe: list, q: int, runde: str, weight: float = 0.1) -> list:
    """Eine Zeile je Einstellung für eine Zelle (Kapazität, Runde): Median, Mittel, Maximum des Vergleichs-Verhältnisses, Median von cmp1 und cmp2, Median der Eimerschritte, Aufwand mit Gewicht."""
    sel = select(laeufe, q, runde)
    rows = []
    for cfg in C.BAND_CONFIGS:
        s = stats_of(band_ratio(x, cfg) for x in sel)
        rows.append({"cfg": cfg, "name": config_name(*cfg), "n": s["n"], "median": s["median"], "mean": s["mean"], "max": s["max"],
                     "cmp1": statistics.median(band_ratio(x, cfg, "cmp1") for x in sel), "cmp2": statistics.median(band_ratio(x, cfg, "cmp2") for x in sel),
                     "steps": statistics.median(x["einstellungen"][cfg][4] for x in sel), "net": statistics.median(band_ratio(x, cfg, weight=weight) for x in sel),
                     "comparisons_base": statistics.median(band_comparisons(x, (0, 0)) for x in sel), "time": band_time_ratio(sel, cfg)})
    return rows


LABEL_CLASSES = ((0, 2000), (2000, 10000), (10000, 50000), (50000, 10 ** 9))


def label_class_table(laeufe: list, cfgs=((10, 0), (1, 0), (0, 5), (10, 5))) -> list:
    """Median des Vergleichs-Verhältnisses je Klasse der Labelzahl ohne Eimer (alle Läufe beider Kapazitäten) und Vergleiche je Label ohne Eimer (Median)."""
    rows = []
    for lo, hi in LABEL_CLASSES:
        sel = [x for x in laeufe if lo <= x["einstellungen"][(0, 0)][0] < hi]
        if not sel:
            continue
        row = {"lo": lo, "hi": hi, "n": len(sel), "per_label": statistics.median(band_comparisons(x, (0, 0)) / x["einstellungen"][(0, 0)][0] for x in sel)}
        for cfg in cfgs:
            row[cfg] = statistics.median(band_ratio(x, cfg) for x in sel)
        rows.append(row)
    return rows


ZEIT_CFGS = ((0, 0), (1, 0), (2, 0), (5, 0), (10, 0), (20, 0), (40, 0), (80, 0))


def optimum_counts(laeufe: list, q: int, weight: float) -> dict:
    """Wie oft ist jede Zeit-Breite (oder keine) in den Läufen der Kapazität q die mit dem kleinsten Aufwand (Vergleiche + weight x Schritte)? Gleichstand: die erste in ZEIT_CFGS."""
    sel = select(laeufe, q)
    counts = {cfg: 0 for cfg in ZEIT_CFGS}
    for x in sel:
        best = min(ZEIT_CFGS, key=lambda c: x["einstellungen"][c][2] + x["einstellungen"][c][3] + weight * x["einstellungen"][c][4])
        counts[best] += 1
    return {"counts": counts, "n": len(sel)}


def cmp1_share(laeufe: list) -> float:
    """Median des Anteils von cmp1 an allen Vergleichen ohne Eimer."""
    return statistics.median(x["einstellungen"][(0, 0)][2] / band_comparisons(x, (0, 0)) for x in laeufe)


def all_identical(laeufe: list) -> tuple:
    """(Zahl der Zeilen, davon mit gleichem Ergebnis wie ohne Eimer, davon abgebrochen: es gibt keine Abbruch-Spalte, die Läufe haben kein Labelbudget)."""
    rows = [v for x in laeufe for v in x["einstellungen"].values()]
    return len(rows), sum(1 for v in rows if v[5])


def verdict_bands(laeufe: list, q: int, runde: str, cfg: tuple, weight: float) -> tuple:
    """Verdikt einer Band-Zelle: in wie vielen der Läufe spart die Einstellung Vergleiche, Median und Maximum des Verhältnisses; Aufwand mit Gewicht."""
    sel = select(laeufe, q, runde)
    ratios = [band_ratio(x, cfg) for x in sel]
    nets = [band_ratio(x, cfg, weight=weight) for x in sel]
    fewer = sum(1 for r in ratios if r < 1)
    below = sum(1 for r in nets if r < 1)
    s = stats_of(ratios)
    n = stats_of(nets)
    text = (f"Kapazität {q}, Dualpreise {'der letzten Runde' if runde == 'ende' else f'der Runde {runde}'}, {config_name(*cfg)}: weniger Vergleiche als ohne Eimer in {fewer} von {s['n']} Läufen "
            f"(Median des Verhältnisses {fmt_ratio(s['median'])}, Maximum {fmt_ratio(s['max'])}); mit Gewicht {fmt_dec(weight, 2)} je Eimerschritt (Annahme) weniger Aufwand in {below} von {n['n']} Läufen "
            f"(Median {fmt_ratio(n['median'])}).")
    return ("success" if n["median"] < 1 else "warning", text)
