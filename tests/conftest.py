"""Gemeinsame Fixtures: die Mini-Instanz, an der jede Einheit von Hand geprüft wird (DEMO-PLAYBOOK §1b).

Die Mini-Instanz ist das Handbeispiel: Depot bei (5, 5) und sechs Kunden auf einem Gitter, Entfernung = Fahrzeit = Kosten = Manhattan-Abstand, Bedienzeit 2, Horizont 40,
Kapazität 9, Zeitfenster [früh, spät], halbzahlige Dualpreise. Die Zahlen stehen hier **noch einmal von Hand** (nicht aus eml_scenario); `test_algorithm.py` vergleicht beide Fassungen.
Die Handrechnung steht als Rechnung in den Tests, nicht als abgeschriebenes Ergebnis."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from eml_scenario import Instance  # noqa: E402

# Kunde: (Punkt, Last, früh, spät, Dualpreis); Index 0 ist das Depot
HAND_TABLE = {
    0: ((5, 5), 0, 0, 40, 0),
    1: ((5, 0), 4, 22, 33, 5),
    2: ((4, 7), 3, 5, 17, 4.5),
    3: ((0, 3), 2, 22, 31, 9),
    4: ((6, 2), 4, 25, 34, 4.5),
    5: ((7, 1), 2, 9, 19, 7.5),
    6: ((1, 0), 3, 9, 19, 10.5),
}
SERVICE, HORIZON, CAPACITY = 2, 40, 9


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def build_hand():
    pts = tuple(HAND_TABLE[i][0] for i in range(7))
    d = tuple(tuple(manhattan(a, b) for b in pts) for a in pts)
    inst = Instance(6, pts, d, tuple(HAND_TABLE[i][1] for i in range(7)), tuple(HAND_TABLE[i][2] for i in range(7)), tuple(HAND_TABLE[i][3] for i in range(7)), SERVICE, HORIZON, CAPACITY)
    pi = tuple(HAND_TABLE[i][4] for i in range(7))
    return inst, pi


@pytest.fixture
def hand():
    """(Instanz, Dualpreise) des Handbeispiels aus der Tabelle oben."""
    return build_hand()
