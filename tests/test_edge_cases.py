"""Randfälle, an denen Kernroutinen erfahrungsgemäß brechen (DEMO-PLAYBOOK §12): Label genau auf der Eimergrenze, Breite 1, Eimer so breit wie der Horizont, t = H, ein Label am Kunden,
leerer Kunde, n = 1 und n = 2, Gleichstände, Dualpreise 0, Kapazität unter jeder Last, Gedächtnis k = 0."""

import pytest

import eml_algorithm as A
import eml_evaluation as ev
from eml_scenario import Instance, make_instance, ng_masks


def _inst(d, dem, ready=None, due=None, svc=0.0, H=100.0, Q=10):
    n = len(d) - 1
    return Instance(n, ((0, 0),) * (n + 1), tuple(tuple(float(x) for x in r) for r in d), tuple(dem), tuple(ready or [0.0] * (n + 1)), tuple(due or [H] * (n + 1)), float(svc), float(H), Q)


# Depot 0, Kunden 1, 2, 3: das Label über Kunde 1 erreicht Kunde 3 zur Zeit 15, das über Kunde 2 zur Zeit 20 (genau auf der Grenze des Zeit-Eimers 2 bei Breite 10)
BOUNDARY = _inst([[0, 5, 10, 50], [5, 0, 100, 10], [10, 100, 0, 10], [50, 10, 10, 0]], (0, 3, 3, 3))
BOUNDARY_PI = [0.0, 0.0, 20.0, 0.0]


def test_label_exactly_on_a_bucket_border():
    """t = 20 bei Breite 10: das neue Label liegt im Eimer 2; cmp2 sieht mit Sicherheitsrand auch Eimer 1 an (ein Vergleich mehr), Ergebnis gleich, nie mehr als ohne Eimer."""
    exact = A.price(BOUNDARY, BOUNDARY_PI, 3, 10, None, rand=0.0, trace=True)
    safe = A.price(BOUNDARY, BOUNDARY_PI, 3, 10, None, rand=A.EPS, trace=True)
    base = A.price(BOUNDARY, BOUNDARY_PI, 3, None, None, rand=0.0)
    e = next(x for x in exact.events if x["time"] == 20.0 and x["node"] == 3)
    s = next(x for x in safe.events if x["time"] == 20.0 and x["node"] == 3)
    assert e["bucket"] == s["bucket"] == (2, 0)
    assert len(e["ex2"]) == 1 and len(s["ex2"]) == 2        # das Label mit Zeit 15 (Eimer 1) liegt unter der Grenze; es kann nicht dominiert werden, wird aber mit Sicherheitsrand angesehen
    assert (exact.live, exact.routes) == (safe.live, safe.routes) == (base.live, base.routes)
    assert safe.cmp1 == exact.cmp1 and safe.cmp2 == exact.cmp2 + 1 and safe.comparisons <= base.comparisons


def test_time_just_below_the_border_is_in_the_lower_bucket():
    assert A.bucket_of(19.999999999, 10, 11) == 1 and A.bucket_of(20.0, 10, 11) == 2


def test_width_one_and_width_equal_to_the_horizon():
    base = A.price(BOUNDARY, BOUNDARY_PI, 3, None, None, rand=0.0)
    fine = A.price(BOUNDARY, BOUNDARY_PI, 3, 1, None, rand=0.0)
    assert (fine.live, fine.routes, fine.generated) == (base.live, base.routes, base.generated) and fine.steps > base.steps
    assert A.bucket_count(100.0, 1) == 101
    h = A.price(BOUNDARY, BOUNDARY_PI, 3, 100, None, rand=0.0)       # Breite = Horizont: zwei Eimer (0 bis 99 und 100)
    assert A.bucket_count(100.0, 100) == 2 and (h.live, h.routes) == (base.live, base.routes)


def test_arrival_exactly_at_the_horizon_lands_in_the_last_bucket():
    inst = _inst([[0, 50], [50, 0]], (0, 3), due=[100.0, 50.0], svc=0.0, H=100.0)       # Kunde 1 zur Zeit 50, zurück zur Zeit 100 = H
    r = A.price(inst, [0.0, 150.0], 1, 50, None, rand=0.0, trace=True)
    assert r.best[1] == (1,) and r.best[0] == pytest.approx(100 - 150)
    # eine Fahrt, die genau zur Zeit H zurückkehrt, ist zulässig; eine, die später käme, nicht
    late = _inst([[0, 51], [51, 0]], (0, 3), due=[100.0, 51.0])
    assert A.price(late, [0.0, 200.0], 1, 50, None, rand=0.0).routes == []
    assert A.bucket_of(100.0, 50, A.bucket_count(100.0, 50)) == 2    # t = H im letzten Eimer


def test_one_label_at_a_node_and_an_empty_node():
    r = A.price(BOUNDARY, BOUNDARY_PI, 3, 10, 5, rand=0.0, trace=True)
    firsts = [e for e in r.events if not e["live_before"]]           # erstes Label an einem Kunden: kein lebendes Label, keine Vergleiche
    assert firsts and all(e["ex1"] == [] and e["ex2"] == [] for e in firsts)
    one = next(e for e in r.events if len(e["live_before"]) == 1)
    assert len(one["ex1"]) <= 1 and len(one["ex2"]) <= 1


def test_single_customer_and_two_customers():
    one = make_instance(1, 0, 100)
    r = A.price(one, [0.0, 500.0], 1, 10, 5)
    assert r.generated == 2 and r.comparisons == 0 and r.best[1] == (1,) and len(r.live) == 2      # Start-Label im Depot und das Label an Kunde 1
    two = make_instance(2, 0, 100)
    r2 = A.price(two, [0.0, 500.0, 500.0], 2, 10, None, max_routes=10 ** 6)
    base2 = A.price(two, [0.0, 500.0, 500.0], 2, None, None, max_routes=10 ** 6)
    assert (r2.live, r2.routes, r2.generated) == (base2.live, base2.routes, base2.generated) and len(r2.routes) >= 3      # (1), (2), (1, 2) und/oder (2, 1)


def test_ties_keep_the_older_label():
    """Zwei gleiche Kunden (Ort, Fenster, Last): die beiden Wege zu einem dritten Kunden sind gleich gut; das ältere Label bleibt, das neue wird gestrichen (cmp1 findet den Treffer)."""
    d = [[0, 5, 5, 20], [5, 0, 0, 10], [5, 0, 0, 10], [20, 10, 10, 0]]
    inst = _inst(d, (0, 3, 3, 3))
    r = A.price(inst, [0.0, 1.0, 1.0, 0.0], 3, 10, None, rand=0.0, trace=True)
    e3 = [e for e in r.events if e["node"] == 3]
    killed = [e for e in e3 if e["status"] == "dominiert" and e["killer"] is not None]
    assert killed and all(e["killer"] < e["nr"] for e in killed)


def test_all_dual_prices_zero_means_no_negative_route():
    inst = make_instance(10, 4, 100)
    for wt, wq in [(None, None), (10, 5)]:
        r = A.price(inst, [0.0] * 11, 5, wt, wq)
        assert r.routes == [] and r.best is None and r.generated > 1


def test_capacity_below_every_demand_leaves_only_the_start_label():
    inst = _inst([[0, 5, 5], [5, 0, 5], [5, 5, 0]], (0, 30, 30), Q=10)
    r = A.price(inst, [0.0, 100.0, 100.0], 2, 10, 5)
    assert r.generated == 1 and r.comparisons == 0 and r.routes == []


def test_memory_zero_equals_memory_one():
    inst = make_instance(8, 2, 100)
    assert ng_masks(inst, 0) == ng_masks(inst, 1) == [1 << j if j else 0 for j in range(9)]


def test_weight_zero_and_empty_baseline_in_the_effort_functions():
    run = ev.Run(10, 0, 5, 3, 7, 4, 99, False, "x", 0, None, None, 2)
    empty = ev.Run(0, 0, 1, 0, 0, 0, 0, False, "y", 0, None, None, 1)
    assert ev.net_cost(run, 0.0) == 11 and ev.net_cost(run, 1.0) == 110
    assert ev.saved_share(empty, run) is None and ev.net_ratio(empty, run, 0.1) is None
    assert ev.verdict_saving(empty, run, 0.1)[0] == "info"
    assert ev.split_ratios(empty, run) == (None, None)
