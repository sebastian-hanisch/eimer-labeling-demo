"""Orakel-Test eimer-labeling-demo: der Kern (Bitmasken, Heap, Eimer als Dictionary mit sortierter Schlüsselliste) gegen zwei andere Rechenwege.

1. `ref_labeling.ref_price`: dasselbe Verfahren in Mengen und Listen, die Eimerkandidaten je neuem Label als gefilterte, sortierte Liste. Verglichen werden erzeugte und gestrichene Labels,
   cmp1, cmp2, Eimerschritte, die Menge der lebenden Labels und die negativen Routen, in jeder Eimer-Einstellung, bei exakten Grenzen und mit dem Sicherheitsrand der Messreihen.
2. Aufzählung aller zulässigen elementaren Routen (`ref_labeling.enum_routes`, keine Labels): jede vom Labeling gemeldete Route steht in ihr mit denselben reduzierten Kosten, und die beste Route
   des Labelings (k = n) hat die kleinsten reduzierten Kosten aller Routen.
Das Handbeispiel steht als Handrechnung in `test_algorithm.py`; hier wird es zusätzlich gegen die Aufzählung (39 zulässige Routen) geprüft.
Die große Fassung lief beim Bau im Scratch-Lauf, nicht im Repo (DEMO-PLAYBOOK §12): 300 Zufallsinstanzen (4 bis 9 Kunden, Kapazität 20 bis 120, Gedächtnis n, 3 und 2) × 14 Einstellungen × zwei Eimerränder = 8 400 Vergleiche, 0 Abweichungen;
bei Gedächtnis n zusätzlich die beste Route gegen die Aufzählung."""

import random

import pytest

import eml_algorithm as A
from eml_scenario import make_instance
from ref_labeling import enum_routes, plain, ref_price

CONFIGS = [(None, None), (1, None), (5, None), (10, None), (40, None), (None, 5), (5, 5), (10, 10)]


def _live_as_sets(live):
    """Lebende Labels des Kerns mit dem Gedächtnis als Tupel statt Bitmaske (zum Vergleich mit der Referenz)."""
    return [(node, t, c, q, tuple(j for j in range(1, 40) if (mem >> j) & 1)) for node, t, c, q, mem in live]


def _small_cases():
    for seed in range(30):
        for width in (30, 80, 200):
            inst = make_instance(7, seed, width)
            rng = random.Random(1000 + seed)
            yield inst, [0.0] + [rng.uniform(20, 70) for _ in range(inst.n)], seed, width


def test_core_equals_the_reference_on_small_instances_in_every_bucket_setting():
    cases = checked = 0
    for inst, pi, seed, width in _small_cases():
        p = plain(inst)
        for k in (7, 3):
            for wt, wq in CONFIGS:
                for rand, safe in ((A.EPS, True), (0.0, False)):
                    r = A.price(inst, pi, k, wt, wq, rand=rand, max_routes=10 ** 6)
                    ref = ref_price(p, pi, k, wt, wq, safe=safe)
                    ctx = (seed, width, k, wt, wq, safe)
                    assert (r.generated, r.dominated, r.cmp1, r.cmp2, r.steps) == (ref["gen"], ref["dom"], ref["c1"], ref["c2"], ref["steps"]), ctx
                    assert _live_as_sets(r.live) == ref["live"], ctx
                    assert {route: rc for rc, route in r.routes} == pytest.approx(ref["routes"]), ctx
                    checked += 1
        cases += 1
    assert cases == 90 and checked == 90 * 2 * len(CONFIGS) * 2


def test_reported_routes_are_enumerated_routes_and_the_best_route_is_the_best():
    """Das Labeling meldet nur Routen, die bei lebenden Labels enden (dominierte Teilwege fallen weg): jede gemeldete Route steht in der Aufzählung mit denselben reduzierten Kosten,
    und die beste Route hat die kleinsten reduzierten Kosten aller zulässigen elementaren Routen (bei k = n)."""
    for inst, pi, seed, width in _small_cases():
        found = enum_routes(plain(inst), pi)
        best = min(found.values(), default=0.0)
        for wt, wq in [(None, None), (10, None), (None, 5), (10, 5)]:
            r = A.price(inst, pi, 7, wt, wq, max_routes=10 ** 6)
            for rc, route in r.routes:
                assert route in found and found[route] == pytest.approx(rc), (seed, width, wt, wq, route)
            if best < -1e-7:
                assert r.best[0] == pytest.approx(best), (seed, width, wt, wq)
            else:
                assert not r.routes


def test_hand_example_against_the_enumeration(hand):
    inst, pi = hand
    found = enum_routes(plain(inst), pi)
    assert len(found) == 39                                  # zulässige elementare Routen des Handbeispiels
    best_route, best_rc = min(found.items(), key=lambda kv: kv[1])
    assert best_route == (5, 6, 3) and best_rc == pytest.approx(-3)
    negative = {r: rc for r, rc in found.items() if rc < -1e-7}
    assert len(negative) == 3
    for wt, wq in [(None, None), (10, None), (None, 3), (10, 3), (5, None), (5, 3)]:
        r = A.price(inst, pi, 6, wt, wq, rand=0.0, max_routes=10 ** 6)
        assert {route: rc for rc, route in r.routes} == pytest.approx(negative)   # im Handbeispiel meldet das Labeling alle drei negativen Routen


def test_core_equals_the_reference_on_medium_instances():
    """n = 14, Gedächtnis k = 5 (zufällig und gruppiert, beide Kapazitäten): Zähler und lebende Labels in vier Einstellungen."""
    for seed in range(2):
        for clustered in (False, True):
            for q in (70, 120):
                inst = make_instance(14, 300 + seed, 100, capacity=q, clustered=clustered)
                rng = random.Random(3000 + seed)
                pi = [0.0] + [rng.uniform(15, 45) for _ in range(inst.n)]
                p = plain(inst)
                for wt, wq in [(None, None), (10, None), (None, 5), (20, 10)]:
                    r = A.price(inst, pi, 5, wt, wq, max_routes=10 ** 6)
                    ref = ref_price(p, pi, 5, wt, wq, safe=True)
                    assert (r.generated, r.dominated, r.cmp1, r.cmp2, r.steps) == (ref["gen"], ref["dom"], ref["c1"], ref["c2"], ref["steps"]), (seed, clustered, q, wt, wq)
                    assert _live_as_sets(r.live) == ref["live"]


def test_the_reference_itself_agrees_with_the_hand_example(hand):
    """Das Orakel vorher am Handbeispiel prüfen (ORACLE-PLAYBOOK): dieselben Zahlen wie die Handrechnung."""
    inst, pi = hand
    p = plain(inst)
    for (wt, wq), counts in {(None, None): (57, 45, 57), (10, None): (57, 28, 174), (None, 3): (52, 16, 149), (10, 3): (52, 8, 477)}.items():
        ref = ref_price(p, list(pi), 6, wt, wq, safe=False)
        assert (ref["gen"], ref["dom"], ref["nlive"]) == (35, 11, 24) and (ref["c1"], ref["c2"], ref["steps"]) == counts
    assert ref_price(p, list(pi), 6, 10, None, safe=True)["c2"] == 33
