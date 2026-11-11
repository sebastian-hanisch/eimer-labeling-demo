"""Kern gegen Handrechnung und gegen einen unabhängigen Rechenweg (`ref_labeling.py`, DEMO-PLAYBOOK §1b und §12).

Das Handbeispiel: Depot (5, 5), sechs Kunden, Manhattan-Abstand, Bedienzeit 2, Horizont 40, Kapazität 9. Die Zahlen unten sind die einer Handrechnung (Label für Label); sie stehen
als Rechnung da (57 + 45 = 102), nicht als einzelne abgeschriebene Summe."""

import pytest

import eml_algorithm as A
from eml_scenario import HAND_DUALS, hand_instance, make_instance, ng_masks
from ref_labeling import plain, ref_price

CONFIGS = [(None, None), (10, None), (None, 3), (10, 3), (5, None), (5, 3)]
# je Einstellung (cmp1, cmp2, Eimerschritte) bei exakten Eimergrenzen: Handrechnung, 35 erzeugte, 11 gestrichene, 24 lebende Labels in allen sechs Fällen
HAND_COUNTS = {
    (None, None): (57, 45, 57),
    (10, None): (57, 28, 174),
    (None, 3): (52, 16, 149),
    (10, 3): (52, 8, 477),
    (5, None): (57, 28, 296),
    (5, 3): (52, 8, 818),
}


def test_the_hand_table_in_conftest_equals_the_scenario_module(hand):
    inst, pi = hand
    s = hand_instance()
    assert (inst.n, inst.points, inst.d, inst.demand, inst.ready, inst.due, inst.service, inst.horizon, inst.capacity) == \
           (s.n, s.points, s.d, s.demand, s.ready, s.due, s.service, s.horizon, s.capacity)
    assert tuple(pi) == HAND_DUALS


# --- Einheiten --------------------------------------------------------------------------------------------------------------------------

def test_bucket_count_and_index():
    assert A.bucket_count(40, 10) == 5 and A.bucket_count(9, 3) == 4 and A.bucket_count(40, None) == 1
    assert [A.bucket_of(t, 10, 5) for t in (0, 9.99, 10, 19, 20, 39, 40, 99)] == [0, 0, 1, 1, 2, 3, 4, 4]   # Eimer = Zeit // 10, am letzten Eimer abgeschnitten
    assert [A.bucket_of(q, 3, 4) for q in (0, 2, 3, 5, 6, 8, 9)] == [0, 0, 1, 1, 2, 2, 3]
    assert A.bucket_of(12345, None, 1) == 0


def test_dominance_rule_each_condition_on_its_own():
    # Label als Liste [Zeit, Kosten, Last, Gedächtnis, Knoten, Vorgänger, gestrichen, Nr]
    old = [10.0, 5.0, 4, 0b0110, 3, -1, False, 1]
    assert A.dominates(old, 5.0, 10.0, 4, 0b0110)                          # alles gleich: dominiert
    assert A.dominates(old, 6.0, 12.0, 5, 0b1110)                          # alles schlechter, Gedächtnis größer
    assert not A.dominates(old, 4.9, 10.0, 4, 0b0110)                      # Kosten des neuen Labels niedriger
    assert not A.dominates(old, 5.0, 9.9, 4, 0b0110)                       # Zeit des neuen Labels früher
    assert not A.dominates(old, 5.0, 10.0, 3, 0b0110)                      # Last des neuen Labels niedriger
    assert not A.dominates(old, 5.0, 10.0, 4, 0b0010)                      # Gedächtnis von old ist keine Teilmenge
    assert A.dominates(old, 5.0 - 5e-10, 10.0 - 5e-10, 4, 0b0110)          # Toleranz EPS bei Kosten und Zeit
    # Umkehrung: das neue Label (Kosten, Zeit, Last, Gedächtnis) dominiert old
    assert A.dominated_by(old, 5.0, 10.0, 4, 0b0010) and not A.dominated_by(old, 5.0, 10.0, 4, 0b1110)
    assert not A.dominated_by(old, 5.1, 10.0, 4, 0b0110) and not A.dominated_by(old, 5.0, 10.1, 4, 0b0110) and not A.dominated_by(old, 5.0, 10.0, 5, 0b0110)


def test_ng_masks_hand_example(hand):
    inst, _ = hand
    masks = ng_masks(inst, 1)
    assert all(masks[j] == 1 << j for j in range(1, 7))                    # k = 1: nur der Kunde selbst
    full = ng_masks(inst, 6)
    assert all(full[j] == 0b1111110 for j in range(1, 7))                  # k = n: alle Kunden (elementar)
    near = ng_masks(inst, 2)
    # Kunde 5 (7, 1): nächster anderer Kunde nach Manhattan-Abstand ist Kunde 4 (6, 2) mit Abstand 2
    assert near[5] == (1 << 5) | (1 << 4)


def test_check_route_by_hand(hand):
    inst, pi = hand
    # Route 5-6-3: Weg 6 + 7 + 4 + 7 = 24, Dualpreise 7,5 + 10,5 + 9 = 27, also 24 - 27 = -3; Zeiten 9 (Warten), 18, 24, zurück 33 <= 40; Last 2 + 3 + 2 = 7 <= 9
    assert A.check_route(inst, pi, (5, 6, 3)) == pytest.approx(24 - 27)
    assert A.check_route(inst, pi, (1, 2)) is None        # Kunde 2 ist nach Kunde 1 nicht mehr im Fenster
    assert A.check_route(inst, pi, (1, 4, 3, 2)) is None  # Last 4 + 4 + 2 + 3 = 13 > 9


# --- Handbeispiel -----------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("wt,wq", CONFIGS)
def test_hand_counts_equal_the_hand_calculation(hand, wt, wq):
    inst, pi = hand
    r = A.price(inst, pi, 6, wt, wq, rand=0.0, max_routes=10 ** 6)
    c1, c2, steps = HAND_COUNTS[(wt, wq)]
    assert (r.generated, r.dominated, len(r.live)) == (35, 11, 24)
    assert (r.cmp1, r.cmp2, r.steps) == (c1, c2, steps)
    assert r.best[1] == (5, 6, 3) and r.best[0] == pytest.approx(-3)


def test_hand_totals_as_sums(hand):
    inst, pi = hand
    base = A.price(inst, pi, 6, None, None, rand=0.0)
    assert base.comparisons == 57 + 45 == 102
    z10 = A.price(inst, pi, 6, 10, None, rand=0.0)
    assert z10.comparisons == 57 + 28 == 85 and z10.comparisons / base.comparisons == pytest.approx(85 / 102)
    both = A.price(inst, pi, 6, 10, 3, rand=0.0)
    assert both.comparisons == 52 + 8 == 60
    # Zeit-Eimer sparen hier nur cmp2, Last-Eimer auch cmp1
    assert z10.cmp1 == base.cmp1 and z10.cmp2 < base.cmp2
    last = A.price(inst, pi, 6, None, 3, rand=0.0)
    assert last.cmp1 < base.cmp1 and last.cmp2 < base.cmp2


def test_hand_weighted_effort_with_weight_one_tenth(hand):
    inst, pi = hand
    effort = {c: (lambda r: r.comparisons + 0.1 * r.steps)(A.price(inst, pi, 6, *c, rand=0.0)) for c in CONFIGS}
    base = 102 + 0.1 * 57
    assert effort[(None, None)] == pytest.approx(base)
    assert effort[(10, None)] == pytest.approx(85 + 0.1 * 174) and effort[(10, None)] / base == pytest.approx(102.4 / 107.7, abs=1e-3)
    assert effort[(None, 3)] / base < 0.8 and effort[(5, 3)] / base > 1.3     # Last 3 lohnt sich, Zeit 5 x Last 3 nicht (Annahme: Gewicht 0,1)


def test_hand_single_decisions_zeit10_last3(hand):
    """Vier von Hand nachgerechnete Einzelfälle: Label Nr. 20 (3 / 0), 32 (5 / 0), 34 (3 / 1) und 15 (1 / 1) (cmp1 / cmp2 mit Eimern Zeit 10 x Last 3)."""
    inst, pi = hand
    with_b = {e["nr"]: e for e in A.price(inst, pi, 6, 10, 3, rand=0.0, trace=True).events}
    without = {e["nr"]: e for e in A.price(inst, pi, 6, None, None, rand=0.0, trace=True).events}
    for nr, (b1, b2, w1, w2) in {20: (3, 3, 3, 0), 32: (5, 5, 5, 0), 34: (6, 6, 3, 1), 15: (2, 2, 1, 1)}.items():
        assert (len(without[nr]["ex1"]), len(without[nr]["ex2"]), len(with_b[nr]["ex1"]), len(with_b[nr]["ex2"])) == (b1, b2, w1, w2), nr
    # F20: Kunde 3, Zeit 23, Last 8, Eimer (2, 2); alle drei lebenden Labels haben Last-Eimer 0 oder 1 < 2: cmp2 überspringt sie (ein Label mit kleinerer Last wird nicht dominiert)
    e = with_b[20]
    assert (e["node"], e["time"], e["load"], e["bucket"]) == (3, 23, 8, (2, 2)) and len(e["live_before"]) == 3
    # F32: Kunde 1, Zeit 32 (Eimer 3); die fünf lebenden Labels haben Zeit <= 24 (Eimer 2 < 3)
    e = with_b[32]
    assert (e["node"], e["time"], e["bucket"][0]) == (1, 32, 3) and len(e["live_before"]) == 5


def test_hand_same_labels_in_every_configuration(hand):
    inst, pi = hand
    ref = A.price(inst, pi, 6, None, None, rand=0.0, max_routes=10 ** 6, trace=True)
    for wt, wq in CONFIGS[1:]:
        r = A.price(inst, pi, 6, wt, wq, rand=0.0, max_routes=10 ** 6, trace=True)
        assert (r.live, r.routes, r.generated, r.dominated) == (ref.live, ref.routes, ref.generated, ref.dominated)
        assert [(e["nr"], e["node"], e["time"], e["load"], e["status"]) for e in r.events] == [(e["nr"], e["node"], e["time"], e["load"], e["status"]) for e in ref.events]


def test_hand_rounding_margin_of_the_measurement_version(hand):
    """E12.5: Mit dem Sicherheitsrand der Messreihen (rand = 1e-9) sieht cmp2 bei ganzzahligen Zeiten auf einer Eimergrenze einen Eimer mehr an; Ergebnis und cmp1 bleiben."""
    inst, pi = hand
    exact = A.price(inst, pi, 6, 10, None, rand=0.0)
    safe = A.price(inst, pi, 6, 10, None, rand=A.EPS)
    assert (exact.cmp1, exact.cmp2, exact.steps) == (57, 28, 174) and (safe.cmp1, safe.cmp2, safe.steps) == (57, 33, 175)
    assert (safe.live, safe.routes) == (exact.live, exact.routes)
    both_exact, both_safe = A.price(inst, pi, 6, 10, 3, rand=0.0), A.price(inst, pi, 6, 10, 3, rand=A.EPS)
    assert (both_exact.cmp2, both_safe.cmp2, both_safe.steps) == (8, 12, 479)
    base = A.price(inst, pi, 6, None, None, rand=A.EPS)
    for r in (safe, both_safe):
        assert r.comparisons <= base.comparisons          # nie mehr als ohne Eimer


def test_default_rand_is_the_measurement_version(hand):
    inst, pi = hand
    d = A.price(inst, pi, 6, 10, None)
    assert A.RAND_MESSCODE == A.EPS == 1e-9 and (d.cmp1, d.cmp2) == (57, 33)


# --- Zufallsinstanzen -------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("wt,wq", [(None, None), (10, None), (None, 5), (10, 5), (1, None), (80, 10)])
def test_matches_the_independent_reference_on_random_instances(wt, wq):
    for seed in range(6):
        inst = make_instance(7, seed, 80, capacity=30, clustered=bool(seed % 2))
        pi = [0.0] + [12.0 + 3.1 * ((j * 7 + seed) % 5) for j in range(1, 8)]
        r = A.price(inst, pi, 4, wt, wq, max_routes=10 ** 6)
        ref = ref_price(plain(inst), pi, 4, wt, wq, safe=True)
        assert (r.generated, r.dominated, r.cmp1, r.cmp2, r.steps) == (ref["gen"], ref["dom"], ref["c1"], ref["c2"], ref["steps"]), (seed, wt, wq)
        assert len(r.live) == ref["nlive"] and set(r.routes[i][1] for i in range(len(r.routes))) == set(ref["routes"])


def test_live_set_and_routes_do_not_depend_on_the_bucket_widths():
    for seed in range(5):
        inst = make_instance(12, seed, 100, capacity=70)
        pi = [0.0] + [20.0 + 2.0 * ((j * 3 + seed) % 7) for j in range(1, 13)]
        base = A.price(inst, pi, 5, None, None, max_routes=10 ** 6, trace=True)
        full_scan = sum(len(e["live_before"]) for e in base.events)       # cmp1 ohne Abbruch beim ersten dominierenden Label: jedes lebende Label des Kunden
        for wt, wq in [(1, None), (10, None), (40, None), (None, 5), (10, 5), (5, 5)]:
            r = A.price(inst, pi, 5, wt, wq, max_routes=10 ** 6)
            assert (r.live, r.routes, r.generated, r.dominated) == (base.live, base.routes, base.generated, base.dominated), (seed, wt, wq)
            # cmp2 hat keinen Abbruch: die angesehenen Labels sind eine Teilmenge der lebenden, also nie mehr als ohne Eimer. cmp1 bricht beim ersten dominierenden Label ab; mit Eimern
            # ist die Reihenfolge eine andere (nach Eimern statt nach Einfügen), also ist nur die Obergrenze „alle lebenden Labels“ sicher (Einzelfälle: 232 gegen 231 Vergleiche).
            assert r.cmp2 <= base.cmp2 and r.cmp1 <= full_scan


def test_label_budget_aborts_and_reports_it():
    inst = make_instance(15, 0, 100, capacity=120, clustered=True)
    pi = [0.0] + [30.0] * 15
    r = A.price(inst, pi, 5, None, None, max_labels=50)
    assert r.aborted and r.generated >= 50
    assert not A.price(inst, pi, 5, None, None, max_labels=10 ** 9).aborted


def test_worst_case_at_the_widget_maximum_finishes_with_every_bucket_setting():
    """n = 30, Fensterbreite 100, Kapazität 70, gruppiert (Regler-Maximum der Instanz, noch unter dem Rechenbudget): alle vierzehn Einstellungen der Messreihen laufen durch."""
    import eml_colgen as G
    inst = make_instance(30, 1, 100, capacity=70, clustered=True)
    cg = G.colgen_duals(inst, 5, rounds=(), max_labels_per_call=150_000, max_labels_total=400_000)
    assert not cg["aborted"]
    pi = cg["ende"]
    base = A.price(inst, pi, 5, None, None, max_routes=10 ** 6, max_labels=150_000)
    assert not base.aborted
    for wt, wq in [(1, None), (5, 5), (10, None), (80, None), (None, 5), (None, 10), (20, 10)]:
        r = A.price(inst, pi, 5, wt, wq, max_routes=10 ** 6, max_labels=150_000)
        assert (r.live, r.routes) == (base.live, base.routes)
