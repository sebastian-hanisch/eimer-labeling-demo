"""Eigenschaftstests (ORACLE-PLAYBOOK §5.2): Aussagen über das Verfahren, die ohne bekanntes Ergebnis prüfbar sind. Je Eigenschaft 20 bis 30 Instanzen mit festem Zufalls-Seed.

1. Eimer ändern nie die Menge der lebenden Labels, die Zahl der erzeugten und der gestrichenen Labels und die Liste der Routen.
2. cmp2 sieht nur lebende Labels an, die auch ohne Eimer angesehen würden: nie mehr als ohne Eimer. cmp1 bricht beim ersten dominierenden Label ab; mit Eimern ist die Reihenfolge eine andere,
   also gilt nur die Obergrenze „jedes lebende Label des Kunden“ (und das ist keine Ersparnis-Aussage).
3. Eine Eimerbreite über dem Horizont (Zeit) oder über der Kapazität (Last) ist ein einziger Eimer: dieselben Zähler wie ohne Eimer.
4. Alle Zeiten, Kosten und die Zeit-Eimerbreite mit 2 multipliziert (Potenz von 2, exakt in Fließkomma): dieselben Zähler.
5. Umnummerieren der Kunden ändert Ergebnis, Zahl der erzeugten und gestrichenen Labels und die Menge der lebenden Labels (bis auf die Umbenennung), nicht aber notwendig die Zahl der Vergleiche
   (die Reihenfolge der Labels im Eimer hängt von der Reihenfolge der Erzeugung ab, und cmp1 bricht beim ersten Treffer ab).
6. Gleiche Eingabe, gleiche Zähler, auch in einem zweiten Prozess mit anderem Hash-Zufall (PYTHONHASHSEED)."""

import json
import os
import random
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

import eml_algorithm as A
from eml_scenario import make_instance
from ref_labeling import permuted, plain

ROOT = Path(__file__).resolve().parent.parent
CONFIGS = [(1, None), (10, None), (40, None), (None, 5), (None, 10), (10, 5), (20, 10)]


def _cases(count=20):
    for seed in range(count):
        n = 8 + seed % 5
        inst = make_instance(n, 50 + seed, 100 if seed % 2 else 40, capacity=70 if seed % 3 else 120, clustered=bool(seed % 4 == 0))
        rng = random.Random(9000 + seed)
        yield inst, [0.0] + [rng.uniform(18, 48) for _ in range(inst.n)]


def test_buckets_never_change_the_result_and_cmp2_never_grows():
    for inst, pi in _cases():
        base = A.price(inst, pi, 5, None, None, max_routes=10 ** 6, trace=True)
        full_scan = sum(len(e["live_before"]) for e in base.events)
        for wt, wq in CONFIGS:
            r = A.price(inst, pi, 5, wt, wq, max_routes=10 ** 6)
            assert (r.live, r.routes, r.generated, r.dominated) == (base.live, base.routes, base.generated, base.dominated), (wt, wq)
            assert r.cmp2 <= base.cmp2 and r.cmp1 <= full_scan


def test_bucket_width_above_horizon_or_capacity_is_one_bucket():
    for inst, pi in _cases(12):
        base = A.price(inst, pi, 5, None, None)
        for wt, wq in [(1000, None), (None, 1000), (1000, 1000), (int(inst.horizon) + 1, None), (None, inst.capacity + 1)]:
            r = A.price(inst, pi, 5, wt, wq)
            assert (r.cmp1, r.cmp2, r.steps, r.generated, r.dominated) == (base.cmp1, base.cmp2, base.steps, base.generated, base.dominated), (wt, wq)


def test_scaling_all_times_by_two_keeps_every_counter():
    for inst, pi in _cases(12):
        s2 = replace(inst, d=tuple(tuple(2 * x for x in row) for row in inst.d), ready=tuple(2 * x for x in inst.ready), due=tuple(2 * x for x in inst.due),
                     service=2 * inst.service, horizon=2 * inst.horizon)
        pi2 = [2 * x for x in pi]
        for wt, wq in [(None, None), (10, None), (None, 5), (10, 5)]:
            a = A.price(inst, pi, 5, wt, wq)
            b = A.price(s2, pi2, 5, None if wt is None else 2 * wt, wq)
            assert (a.generated, a.dominated, a.cmp1, a.cmp2, a.steps) == (b.generated, b.dominated, b.cmp1, b.cmp2, b.steps), (wt, wq)


def test_renumbering_the_customers_keeps_the_result():
    rng = random.Random(77)
    for inst, pi in _cases(15):
        n = inst.n
        perm = list(range(1, n + 1))
        rng.shuffle(perm)
        p2, pi2 = permuted(plain(inst), pi, perm)
        inst2 = replace(inst, d=tuple(tuple(r) for r in p2["d"]), demand=tuple(p2["dem"]), ready=tuple(p2["ready"]), due=tuple(p2["due"]))   # die Koordinaten kommen im Kern nicht vor
        # k = n: das Gedächtnis hängt nicht an der Nummerierung (bei k < n entscheidet bei gleichen Abständen die Nummer über die k nächsten Kunden)
        a = A.price(inst, pi, n, 10, None, max_routes=10 ** 6)
        b = A.price(inst2, pi2, n, 10, None, max_routes=10 ** 6)
        assert (a.generated, a.dominated, len(a.live)) == (b.generated, b.dominated, len(b.live))
        assert a.best is None and b.best is None or a.best[0] == pytest.approx(b.best[0])
        new_of = [0] + perm
        mapped = sorted((new_of[node], t, c, q, sum(1 << new_of[j] for j in range(1, n + 1) if (mem >> j) & 1)) for node, t, c, q, mem in a.live)
        assert [(x[0], x[1], x[2], x[3], x[4]) for x in mapped] == [(x[0], x[1], x[2], x[3], x[4]) for x in sorted(b.live)]


def test_same_input_same_counters():
    inst, pi = next(_cases(1))
    first = A.price(inst, pi, 5, 10, 5)
    second = A.price(inst, pi, 5, 10, 5)
    assert (first.cmp1, first.cmp2, first.steps, first.live) == (second.cmp1, second.cmp2, second.steps, second.live)


_SCRIPT = """
import json, random, sys
sys.path.insert(0, {root!r})
import eml_algorithm as A
from eml_scenario import make_instance
inst = make_instance(12, 3, 100, capacity=120, clustered=True)
rng = random.Random(5)
pi = [0.0] + [rng.uniform(18, 48) for _ in range(inst.n)]
out = []
for wt, wq in [(None, None), (10, None), (None, 5), (10, 5)]:
    r = A.price(inst, pi, 5, wt, wq)
    out.append([r.generated, r.dominated, r.cmp1, r.cmp2, r.steps, len(r.live)])
print(json.dumps(out))
"""


def test_counters_do_not_depend_on_the_hash_seed():
    results = []
    for hash_seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=hash_seed)
        out = subprocess.run([sys.executable, "-c", _SCRIPT.format(root=str(ROOT))], capture_output=True, text=True, env=env, timeout=120, check=True).stdout
        results.append(json.loads(out))
    assert results[0] == results[1] and results[0][0][2] > 0
