"""Szenario: Instanzen für das Label-Verfahren (ein Depot, Kunden mit Last, Zeitfenster und Dualpreis).

Zwei Arten von Instanzen:
- das **Handbeispiel** (6 Kunden, Manhattan-Abstand, ganze Zahlen und halbzahlige Dualpreise; von Hand nachrechenbar),
- **Zufallsinstanzen** im Stil der Solomon-Instanzen (Quadrat 100 x 100, Fahrzeit = Entfernung, Bedienzeit 10, Kapazität 70 oder 120, Horizont 300; nicht die
  Originalinstanzen), Kunden zufällig verteilt oder in fünf Gruppen. `make_instance` zieht die Zahlen in derselben Reihenfolge wie die Messreihe der Planung, damit die
  festen Zufalls-Seeds dieselben Instanzen ergeben."""

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Instance:
    """Knoten 0 ist das Depot, die Kunden sind 1..n. Alle Tupel haben die Länge n + 1."""

    n: int
    points: tuple[tuple[float, float], ...]
    d: tuple[tuple[float, ...], ...]   # Entfernung = Fahrzeit = Kosten
    demand: tuple[int, ...]
    ready: tuple[float, ...]           # frühester Beginn der Bedienung (früher ankommen heißt warten, kostenlos)
    due: tuple[float, ...]             # spätester Beginn der Bedienung
    service: float                     # Bedienzeit je Kunde
    horizon: float                     # spätestmögliche Rückkehr ins Depot
    capacity: int


def make_instance(n: int, seed: int, width: float, horizon: float = 300.0, capacity: int = 70, service: float = 10.0, clustered: bool = False) -> Instance:
    """Zufallsinstanz aus (n, seed, Fensterbreite, Typ): gleiche Eingabe, gleiche Instanz (Zufallsgenerator `random.Random(seed)`).

    Zufällig verteilt: Kunden gleichverteilt im Quadrat. Gruppiert: fünf Mittelpunkte, jeder Kunde gehört zu einem davon (Normalverteilung mit Streuung 6, am Rand des Quadrats begrenzt)."""
    rng = random.Random(seed)
    if clustered:
        centres = [(rng.uniform(15, 85), rng.uniform(15, 85)) for _ in range(5)]
        customers = []
        for _ in range(n):
            cx, cy = rng.choice(centres)
            customers.append((min(100.0, max(0.0, rng.gauss(cx, 6))), min(100.0, max(0.0, rng.gauss(cy, 6)))))
    else:
        customers = [(rng.uniform(0, 100), rng.uniform(0, 100)) for _ in range(n)]
    points = [(50.0, 50.0)] + customers
    d = tuple(tuple(math.dist(a, b) for b in points) for a in points)
    demand = [0] + [rng.randint(5, 25) for _ in range(n)]
    ready = [0.0] * (n + 1)
    due = [horizon] * (n + 1)
    for i in range(1, n + 1):
        lo = d[0][i]
        hi = horizon - service - d[0][i]
        center = rng.uniform(lo, hi)
        ready[i] = max(lo, center - width / 2)
        due[i] = min(hi, center + width / 2)
    return Instance(n, tuple(points), d, tuple(demand), tuple(ready), tuple(due), service, horizon, capacity)


def ng_masks(inst: Instance, k: int) -> list[int]:
    """Nachbarschaft NG(j) als Bitmaske: die k nächsten Kunden von j, j selbst eingeschlossen (k = n heißt elementar)."""
    masks = [0] * (inst.n + 1)
    for j in range(1, inst.n + 1):
        order = sorted(range(1, inst.n + 1), key=lambda i: inst.d[j][i])
        m = 0
        for i in order[:k]:
            m |= 1 << i
        masks[j] = m | (1 << j)
    return masks


# --- Handbeispiel ---------------------------------------------------------------------------------------------------------------------------

HAND_POINTS = ((5, 5), (5, 0), (4, 7), (0, 3), (6, 2), (7, 1), (1, 0))    # Depot, dann Kunde 1 bis 6
HAND_DEMAND = (0, 4, 3, 2, 4, 2, 3)
HAND_READY = (0, 22, 5, 22, 25, 9, 9)
HAND_DUE = (40, 33, 17, 31, 34, 19, 19)
HAND_DUALS = (0, 5, 4.5, 9, 4.5, 7.5, 10.5)
HAND_SERVICE, HAND_HORIZON, HAND_CAPACITY = 2, 40, 9


def _manhattan(points) -> tuple:
    return tuple(tuple(abs(a[0] - b[0]) + abs(a[1] - b[1]) for b in points) for a in points)


def hand_instance() -> Instance:
    """Das Handbeispiel: Manhattan-Abstand, alle Zahlen ganz; Dualpreise halbzahlig (`HAND_DUALS`)."""
    return Instance(6, HAND_POINTS, _manhattan(HAND_POINTS), HAND_DEMAND, HAND_READY, HAND_DUE, HAND_SERVICE, HAND_HORIZON, HAND_CAPACITY)
