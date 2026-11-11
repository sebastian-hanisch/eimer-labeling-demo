"""Spaltenerzeugung mit Überdeckungs-Master: liefert die Dualpreise, mit denen die Eimer-Experimente das Preisproblem lösen.

Master: kleinste Kosten, jeder Kunde mindestens einmal überdeckt (Überdeckung, >= 1), Spalten = Routen. Start: eine Einzelfahrt je Kunde. In jeder Runde löst HiGHS (scipy) den Master;
die Dualpreise sind die Schattenpreise der Überdeckungsbedingungen. Das Preisproblem (`eml_algorithm.price`, ohne Eimer, Gedächtnis k) liefert bis zu 15 neue Routen mit negativen
reduzierten Kosten; findet es keine neue, endet die Spaltenerzeugung. Die Dualpreise einzelner Runden und die der letzten Runde („Ende“) werden zurückgegeben."""

import numpy as np
from scipy.optimize import linprog

import eml_algorithm as A
from eml_scenario import Instance


def route_cost(inst: Instance, route) -> float:
    """Länge der Route Depot - Kunden - Depot (Entfernung = Kosten)."""
    seq = (0,) + tuple(route) + (0,)
    return sum(inst.d[a][b] for a, b in zip(seq, seq[1:]))


def master_duals(inst: Instance, columns) -> tuple:
    """Löst den Überdeckungs-Master über den gegebenen Spalten (Routen) und gibt (Zielwert, Dualpreise mit pi[0] = 0) zurück."""
    n = inst.n
    costs = [route_cost(inst, r) for r in columns]
    A_mat = np.zeros((n, len(columns)))
    for c, r in enumerate(columns):
        for i in r:
            A_mat[i - 1, c] += 1
    res = linprog(costs, A_ub=-A_mat, b_ub=-np.ones(n), bounds=(0, None), method="highs")
    return float(res.fun), [0.0] + [float(x) for x in -res.ineqlin.marginals]


def colgen_duals(inst: Instance, k: int, rounds=(1, 3, 8), max_iter: int = 200, max_labels_per_call=None, max_labels_total=None) -> dict:
    """Spaltenerzeugung. Rückgabe: dict(duals={Runde: Dualpreise}, ende=Dualpreise der letzten Runde, iters, bound=Zielwert der letzten Runde, aborted, labels).

    `max_labels_per_call`: Labelbudget je Preisproblem, `max_labels_total`: Labelbudget über alle Runden zusammen (None = unbegrenzt); bei Überschreitung ist aborted True und `ende` None.
    `labels` ist die Zahl der erzeugten Labels über alle Runden."""
    n = inst.n
    cols = [(i,) for i in range(1, n + 1)]
    duals = {}
    it = 0
    pi = None
    obj = None
    total = 0
    while it < max_iter:
        it += 1
        obj, pi = master_duals(inst, cols)
        if it in rounds:
            duals[it] = list(pi)
        res = A.price(inst, pi, k, max_labels=max_labels_per_call)
        total += res.generated
        if res.aborted or (max_labels_total is not None and total > max_labels_total):
            return dict(duals=duals, ende=None, iters=it, bound=None, aborted=True, labels=total)
        known = set(cols)
        fresh = [r for rc, r in res.routes if r not in known]
        if not fresh:
            break
        cols.extend(fresh)
    return dict(duals=duals, ende=list(pi), iters=it, bound=obj, aborted=False, labels=total)
