"""Unabhängiger Rechenweg für die Tests (kein Import aus dem Kern): Label-Verfahren mit Eimern in Mengen und Listen statt Bitmasken, Heap und Dictionary-Eimern,
dazu die Aufzählung aller zulässigen elementaren Routen.

`ref_price` rechnet wie das Handbeispiel von Hand: neue Labels in der Reihenfolge (Zeit, Entstehung), je neues Label die Kandidatenliste der lebenden Labels des Kunden,
sortiert nach (Zeit-Eimer, Last-Eimer, Entstehung), gefiltert nach den Eimerbedingungen. Die Zähler (cmp1, cmp2, Eimerschritte) entstehen aus dieser Liste, nicht aus dem Eimer-Dictionary des Kerns."""

import math

EPS = 1e-9


def plain(inst) -> dict:
    """Eine eml_scenario.Instance als einfache Listen (der Kern wird nicht benutzt)."""
    return dict(n=inst.n, d=[list(r) for r in inst.d], svc=inst.service, H=inst.horizon, Q=inst.capacity, ready=list(inst.ready), due=list(inst.due), dem=list(inst.demand))


def neighbours(p: dict, k: int) -> list:
    """NG(j): die k nächsten Kunden von j (Entfernung, bei Gleichstand kleinere Nummer) und j selbst."""
    n, d = p["n"], p["d"]
    out = [set()]
    for j in range(1, n + 1):
        near = sorted(range(1, n + 1), key=lambda i: (d[j][i], i))[:k]
        out.append(set(near) | {j})
    return out


def ref_price(p: dict, pi, k: int, wt=None, wq=None, safe: bool = False) -> dict:
    """Label-Verfahren mit Eimern (wt, wq; None = keiner). safe=True: Sicherheitsrand 1e-9 an den Eimergrenzen wie der Kern (Standard der Live-Rechnung), safe=False: exakte Grenzen."""
    n, d, svc, H, Q = p["n"], p["d"], p["svc"], p["H"], p["Q"]
    ng = neighbours(p, k)
    nt = 1 if wt is None else int(H / wt) + 1
    nq = 1 if wq is None else int(Q / wq) + 1

    def bt(t):
        return 0 if wt is None else min(math.floor(t / wt), nt - 1)

    def bq(q):
        return 0 if wq is None else min(math.floor(q / wq), nq - 1)

    rand = EPS if safe else 0.0
    labels = [dict(t=0.0, c=0.0, q=0, mem=frozenset(), node=0, parent=-1, dead=False)]
    queue = [(0.0, 0)]
    alive = [[] for _ in range(n + 1)]
    gen, dom, c1, c2, steps = 1, 0, 0, 0, 0
    ended = []
    while queue:
        queue.sort()
        _, li = queue.pop(0)
        L = labels[li]
        if L["dead"]:
            continue
        i = L["node"]
        if i != 0 and L["t"] + svc + d[i][0] <= H:
            ended.append((L["c"] + d[i][0], li))
        for j in range(1, n + 1):
            if j == i or j in L["mem"] or L["q"] + p["dem"][j] > Q:
                continue
            arr = L["t"] + (svc if i != 0 else 0.0) + d[i][j]
            if arr > p["due"][j] + EPS:
                continue
            t2 = max(arr, p["ready"][j])
            c2_ = L["c"] + d[i][j] - pi[j]
            q2 = L["q"] + p["dem"][j]
            m2 = frozenset((L["mem"] & ng[j]) | {j})
            gen += 1
            own_t, own_q = bt(t2), bq(q2)
            hi_t, lo_t = bt(t2 + rand), bt(max(0.0, t2 - rand))
            live = [x for x in alive[j]]
            order = lambda x: (bt(labels[x]["t"]), bq(labels[x]["q"]), x)   # noqa: E731
            # cmp1: Eimer mit Zeit-Index <= hi_t und Last-Index <= own_q, in Eimerreihenfolge, Abbruch beim ersten dominierenden Label
            steps += (hi_t + 1) * (own_q + 1)
            cand1 = sorted((x for x in live if bt(labels[x]["t"]) <= hi_t and bq(labels[x]["q"]) <= own_q), key=order)
            killed_new = False
            for x in cand1:
                c1 += 1
                O = labels[x]
                if O["c"] <= c2_ + EPS and O["t"] <= t2 + EPS and O["q"] <= q2 and O["mem"] <= m2:
                    killed_new = True
                    break
            if killed_new:
                dom += 1
                labels.append(dict(t=t2, c=c2_, q=q2, mem=m2, node=j, parent=li, dead=True))
                continue
            # cmp2: Eimer mit Zeit-Index >= lo_t und Last-Index >= own_q
            steps += (nt - lo_t) * (nq - own_q)
            cand2 = sorted((x for x in live if bt(labels[x]["t"]) >= lo_t and bq(labels[x]["q"]) >= own_q), key=order)
            dead_now = set()
            for x in cand2:
                c2 += 1
                O = labels[x]
                if c2_ <= O["c"] + EPS and t2 <= O["t"] + EPS and q2 <= O["q"] and m2 <= O["mem"]:
                    O["dead"] = True
                    dead_now.add(x)
                    dom += 1
            alive[j] = [x for x in live if x not in dead_now]
            labels.append(dict(t=t2, c=c2_, q=q2, mem=m2, node=j, parent=li, dead=False))
            alive[j].append(len(labels) - 1)
            queue.append((t2, len(labels) - 1))
    routes = {}
    for rc, li in ended:
        r, x = [], li
        while x != -1:
            r.append(labels[x]["node"])
            x = labels[x]["parent"]
        route = tuple(reversed(r))[1:]
        if rc < -1e-7 and route not in routes:
            routes[route] = rc
    live_set = sorted((x["node"], x["t"], x["c"], x["q"], tuple(sorted(x["mem"]))) for x in labels if not x["dead"])
    return dict(gen=gen, dom=dom, c1=c1, c2=c2, steps=steps, live=live_set, routes=routes, nlive=len(live_set))


def enum_routes(p: dict, pi) -> dict:
    """Alle zulässigen elementaren Routen (Tiefensuche über Besuchsreihenfolgen, ohne Labels) mit negativen reduzierten Kosten: {Route: reduzierte Kosten}; dazu `all` aller zulässigen Routen."""
    n, d, svc, H, Q = p["n"], p["d"], p["svc"], p["H"], p["Q"]
    found = {}

    def rec(i, t, q, visited, cost, path):
        if i != 0 and t + svc + d[i][0] <= H:
            found[tuple(path)] = cost + d[i][0]
        for j in range(1, n + 1):
            if j in visited or q + p["dem"][j] > Q:
                continue
            arr = t + (svc if i != 0 else 0.0) + d[i][j]
            if arr > p["due"][j] + EPS:
                continue
            rec(j, max(arr, p["ready"][j]), q + p["dem"][j], visited | {j}, cost + d[i][j] - pi[j], path + [j])

    rec(0, 0.0, 0, frozenset(), 0.0, [])
    return found


def permuted(p: dict, pi, perm) -> tuple:
    """Dieselbe Instanz mit umnummerierten Kunden: Kunde j wird zu perm[j - 1] (perm ist eine Permutation von 1..n)."""
    n = p["n"]
    new_of = [0] + list(perm)
    old_of = [0] * (n + 1)
    for old, new in enumerate(new_of):
        old_of[new] = old
    q = dict(p)
    q["d"] = [[p["d"][old_of[a]][old_of[b]] for b in range(n + 1)] for a in range(n + 1)]
    for key in ("ready", "due", "dem"):
        q[key] = [p[key][old_of[a]] for a in range(n + 1)]
    return q, [pi[old_of[a]] for a in range(n + 1)]


__all__ = ["plain", "ref_price", "enum_routes", "permuted", "neighbours"]
