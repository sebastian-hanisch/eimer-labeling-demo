"""Kern: Label-Verfahren für den Weg mit den kleinsten reduzierten Kosten (Preisproblem der Spaltenerzeugung), Dominanzprüfung wahlweise mit Eimern je Knoten.

Ein Label ist ein Teilweg: (Zeit, Kosten, Last, Gedächtnis, Knoten). Das Verfahren verlängert Labels in Zeitreihenfolge und streicht dominierte Labels
(Kosten, Zeit, Last und Gedächtnis des anderen Labels sind alle höchstens so groß, das Gedächtnis als Teilmenge). **Eimer** ordnen die lebenden Labels eines Knotens nach
Zeit und Last in Fächer; die beiden Prüfungen sehen nur die Fächer an, in denen ein dominierendes bzw. dominiertes Label überhaupt liegen kann. Das Ergebnis ändert sich dadurch nicht,
nur die Zahl der Dominanzvergleiche (und der Fächer, die dafür angesehen werden).

Einheiten (je eine Regel, DEMO-PLAYBOOK §1b): `bucket_of`, `bucket_count`, `dominates`, `price` (Komposition), `check_route` (unabhängiger Routenprüfer).
Gezählt werden Vergleiche, keine Sekunden. Zufall kommt nur in `eml_scenario.make_instance` vor (Generator `random.Random(seed)`).

Eimerrand (Entscheidung E12.5): Die Dominanzprüfung selbst vergleicht mit der Toleranz `EPS` (Kosten, Zeit). Damit ein Label, dessen Zeit nur um Rundung neben einer Eimergrenze liegt,
nie im falschen Eimer gesucht wird, beginnt die Suche mit dem Eimer von `t ± rand`. Die festen Messreihen und die Live-Rechnung nehmen `rand = EPS` (die Fassung der Messung); liegt die
Zeit genau auf einer Eimergrenze, sieht die Prüfung „dominiert das neue Label alte?“ dann einen Eimer mehr an: unnötig, aber nie falsch. Das Handbeispiel (ganze Zahlen) rechnet mit
`rand = 0` (exakte Grenzen); `tests/test_algorithm.py` zeigt beide Fassungen und ihren Unterschied."""

import heapq
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass, field

from eml_scenario import Instance, ng_masks

EPS = 1e-9
RAND_MESSCODE = EPS        # Sicherheitsrand der Eimersuche in den Messreihen und in der Live-Rechnung (siehe Modul-Docstring)
_BIG = 10 ** 9

# Positionen im Label (Liste, damit „gestrichen“ in place gesetzt werden kann)
T, COST, LOAD, MEM, NODE, PARENT, DEAD, NR = range(8)


@dataclass
class PricingResult:
    """Ergebnis eines Laufs: negative Routen, Zähler, Menge der lebenden Labels; bei `trace` die Entscheidung je neuem Label."""

    routes: list                    # [(reduzierte Kosten, Route)], aufsteigend, höchstens max_routes
    generated: int                  # erzeugte Labels, Start im Depot und sofort verworfene mitgezählt
    dominated: int                  # gestrichene Labels (sofort verworfene und später entfernte)
    cmp1: int                       # Vergleiche „wird das neue Label dominiert?“
    cmp2: int                       # Vergleiche „dominiert das neue Label alte?“
    steps: int                      # angesehene Eimerindizes (auch leere), nach Formel gezählt
    aborted: bool                   # Abbruch am Labelbudget
    live: tuple                     # sortierte (Knoten, Zeit, Kosten, Last, Gedächtnis) aller lebenden Labels
    events: list = field(default_factory=list)   # nur bei trace=True

    @property
    def comparisons(self) -> int:
        return self.cmp1 + self.cmp2

    @property
    def best(self):
        """Beste Route (reduzierte Kosten, Route) oder None, wenn keine Route negative Kosten hat."""
        return self.routes[0] if self.routes else None


def bucket_count(limit, width) -> int:
    """Zahl der Eimerindizes für Werte von 0 bis `limit` bei Eimerbreite `width` (None = ein einziger Eimer): int(limit / width) + 1."""
    return 1 if width is None else int(limit / width) + 1


def bucket_of(value, width, count) -> int:
    """Eimerindex eines Werts: int(value / width), am letzten Eimer abgeschnitten; ohne Breite immer 0."""
    if width is None:
        return 0
    b = int(value / width)
    return b if b < count else count - 1


def dominates(old, cost, time, load, mem) -> bool:
    """Regel der Dominanz: Das Label `old` (Liste mit T, COST, LOAD, MEM) dominiert ein neues Label (cost, time, load, mem) am selben Knoten,
    wenn Kosten, Zeit und Last nicht höher sind und das Gedächtnis von `old` eine Teilmenge ist (Toleranz EPS bei Kosten und Zeit)."""
    return old[COST] <= cost + EPS and old[T] <= time + EPS and old[LOAD] <= load and (old[MEM] & ~mem) == 0


def dominated_by(old, cost, time, load, mem) -> bool:
    """Umkehrung: das neue Label (cost, time, load, mem) dominiert das alte `old`."""
    return cost <= old[COST] + EPS and time <= old[T] + EPS and load <= old[LOAD] and (mem & ~old[MEM]) == 0


def _route_of(labels, li) -> tuple:
    route = []
    x = li
    while x != -1:
        route.append(labels[x][NODE])
        x = labels[x][PARENT]
    return tuple(reversed(route))[1:]


def price(inst: Instance, pi, k: int, wt=None, wq=None, rand: float = RAND_MESSCODE, max_routes: int = 15, max_labels=None, trace: bool = False) -> PricingResult:
    """Bestes Label-Verfahren mit Eimern je Knoten (Zeit-Eimer der Breite `wt`, Last-Eimer der Breite `wq`; None = kein Eimer dieser Art).

    `pi[0] = 0`, `pi[j]` Dualpreis des Kunden j; `k` Größe des Gedächtnisses (k = n elementar). Die Eimer je Knoten stehen in einem Dictionary (Schlüssel (Zeit-Index, Last-Index)),
    ihre belegten Schlüssel in einer sortierten Liste: durchlaufen werden nur belegte Eimer, in der Reihenfolge Zeit-Index, Last-Index, im Eimer Einfügereihenfolge.
    Ohne Eimer (wt = wq = None) gibt es einen Eimer je Knoten: die Prüfung läuft in Einfügereihenfolge über alle lebenden Labels des Knotens.

    cmp1: ein dominierendes Label hat Zeit <= t und Last <= q, liegt also in einem Eimer mit Zeit-Index <= dem von t und Last-Index <= dem von q (Abbruch beim ersten Treffer).
    cmp2: ein vom neuen Label dominiertes Label hat Zeit >= t und Last >= q (Eimer mit Zeit-Index >= und Last-Index >=). Eimerschritte: alle Indizes im Suchbereich, auch leere.
    `max_labels`: Abbruch (aborted = True), sobald so viele Labels erzeugt sind. `trace`: je neues Label eine Entscheidung in `events`."""
    n = inst.n
    ng = ng_masks(inst, k)
    d, svc, H, Q = inst.d, inst.service, inst.horizon, inst.capacity
    nt = bucket_count(H, wt)
    nq = bucket_count(Q, wq)
    bks = [dict() for _ in range(n + 1)]       # Schlüssel (Zeit-Index, Last-Index) -> Liste von Label-Indizes
    keys = [[] for _ in range(n + 1)]          # sortierte belegte Schlüssel je Knoten
    labels = [[0.0, 0.0, 0, 0, 0, -1, False, 0]]
    heap = [(0.0, 0)]
    generated = 1
    dominated = 0
    cmp1 = cmp2 = steps = 0
    ended = []
    events = []
    aborted = False
    while heap:
        _, li = heapq.heappop(heap)
        L = labels[li]
        if L[DEAD]:
            continue
        if max_labels is not None and generated > max_labels:
            aborted = True
            break
        t, c, q, mem, i = L[T], L[COST], L[LOAD], L[MEM], L[NODE]
        if i != 0 and t + svc + d[i][0] <= H:
            ended.append((c + d[i][0], li))
        for j in range(1, n + 1):
            if j == i or (mem >> j) & 1:
                continue
            q2 = q + inst.demand[j]
            if q2 > Q:
                continue
            arr = t + (svc if i != 0 else 0.0) + d[i][j]
            if arr > inst.due[j] + EPS:
                continue
            t2 = max(arr, inst.ready[j])
            c2 = c + d[i][j] - pi[j]
            m2 = (mem & ng[j]) | (1 << j)
            generated += 1
            bj = bks[j]
            kj = keys[j]
            hi_t = bucket_of(t2 + rand, wt, nt)
            lo_t = bucket_of(max(0.0, t2 - rand), wt, nt)
            own_t = bucket_of(t2, wt, nt)
            own_q = bq2 = bucket_of(q2, wq, nq)
            if trace:
                before = [labels[oi][NR] for key in kj for oi in bj[key]]
                ev = dict(nr=generated - 1, node=j, time=t2, cost=c2, load=q2, bucket=(own_t, own_q), live_before=before, ex1=[], ex2=[], killer=None, killed=[])
            # (1) wird das neue Label dominiert? Suche in Eimern mit Zeit-Index <= hi_t und Last-Index <= bq2
            steps += (hi_t + 1) * (bq2 + 1)
            keep = True
            for x in range(bisect_right(kj, (hi_t, _BIG))):
                key = kj[x]
                if key[1] > bq2:
                    continue
                for oi in bj[key]:
                    cmp1 += 1
                    if trace:
                        ev["ex1"].append(labels[oi][NR])
                    if dominates(labels[oi], c2, t2, q2, m2):
                        keep = False
                        if trace:
                            ev["killer"] = labels[oi][NR]
                        break
                if not keep:
                    break
            if not keep:
                dominated += 1
                if trace:
                    ev["status"] = "dominiert"
                    events.append(ev)
                continue
            # (2) dominiert das neue Label alte? Suche in Eimern mit Zeit-Index >= lo_t und Last-Index >= bq2
            steps += (nt - lo_t) * (nq - bq2)
            for x in range(bisect_left(kj, (lo_t, -1)), len(kj)):
                key = kj[x]
                if key[1] < bq2:
                    continue
                lst = bj[key]
                surv = []
                for oi in lst:
                    cmp2 += 1
                    O = labels[oi]
                    if trace:
                        ev["ex2"].append(O[NR])
                    if dominated_by(O, c2, t2, q2, m2):
                        O[DEAD] = True
                        dominated += 1
                        if trace:
                            ev["killed"].append(O[NR])
                    else:
                        surv.append(oi)
                if len(surv) != len(lst):
                    bj[key] = surv
            labels.append([t2, c2, q2, m2, j, li, False, generated - 1])
            idx = len(labels) - 1
            nk = (own_t, own_q)
            if nk not in bj:
                bj[nk] = []
                insort(kj, nk)
            bj[nk].append(idx)
            heapq.heappush(heap, (t2, idx))
            if trace:
                ev["status"] = "behalten"
                events.append(ev)
    res = {}
    for rc, li in ended:
        route = _route_of(labels, li)
        if rc < -1e-7 and route not in res:
            res[route] = rc
    routes = sorted(((rc, r) for r, rc in res.items()))[:max_routes]
    live = tuple(sorted((L[NODE], L[T], L[COST], L[LOAD], L[MEM]) for L in labels if not L[DEAD]))
    return PricingResult(routes, generated, dominated, cmp1, cmp2, steps, aborted, live, events)


def check_route(inst: Instance, pi, route):
    """Unabhängige Prüfung einer Route (ohne Labels): Fenster, Last und Horizont eingehalten? Gibt die reduzierten Kosten zurück, sonst None."""
    seq = (0,) + tuple(route) + (0,)
    t = 0.0
    q = 0
    cost = 0.0
    for a, b in zip(seq, seq[1:]):
        t += (inst.service if a != 0 else 0.0) + inst.d[a][b]
        cost += inst.d[a][b]
        if b != 0:
            if t > inst.due[b] + 1e-7:
                return None
            t = max(t, inst.ready[b])
            q += inst.demand[b]
            cost -= pi[b]
    if q > inst.capacity or t > inst.horizon + 1e-7:
        return None
    return cost
