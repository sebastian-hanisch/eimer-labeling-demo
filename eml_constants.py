"""Konstanten: Regler-Grenzen, feste Annahmen, Farben, Schnellstart-Szenarien und Texte, die App und README gemeinsam haben."""

# --- Regler ---------------------------------------------------------------------------------------------------------------------------------
# Komplexität am Regler-Maximum (n = 30, Fensterbreite 100, Kapazität 120, gruppiert): Die Spaltenerzeugung erzeugt über alle Runden mehrere Hunderttausend Labels (bei vier gemessenen
# Zufalls-Seeds 0,47 bis 0,84 Millionen), und das Verfahren prüft je neues Label alle lebenden Labels des Kunden. MAX_LABELS_COLGEN, MAX_LABELS_CALL und MAX_LABELS fangen das ab: Die Rechnung bricht nach so vielen
# erzeugten Labels ab (einige Sekunden in Python) und die App zeigt den Abbruch als Befund; die festen Messreihen (Experiment 5) bleiben davon unberührt.
N_MIN, N_MAX, DEFAULT_N = 8, 30, 20
WIDTH_OPTIONS, DEFAULT_WIDTH = (40, 100), 40
TYP_OPTIONS, DEFAULT_TYP = ("zufall", "cluster"), "zufall"
Q_OPTIONS, DEFAULT_Q = (70, 120), 70
SEED_MAX, DEFAULT_SEED = 999999, 0
WT_OPTIONS, DEFAULT_WT = (0, 1, 2, 5, 10, 20, 40, 80), 10     # Zeit-Eimerbreite in Zeiteinheiten; 0 = kein Zeit-Eimer
WQ_OPTIONS, DEFAULT_WQ = (0, 5, 10), 0                        # Last-Eimerbreite in Lasteinheiten; 0 = kein Last-Eimer
WEIGHT_MIN, WEIGHT_MAX, DEFAULT_WEIGHT, WEIGHT_STEP = 0.0, 1.0, 0.1, 0.05   # Gewicht je Eimerschritt: eine ANNAHME, keine Messung
MAX_LABELS = 60_000                                           # Abbruch eines Live-Laufs (und damit der Reihe der Experimente 2 bis 4) bei so vielen erzeugten Labels
MAX_LABELS_CALL = 150_000                                     # Abbruch eines einzelnen Preisproblems in der Spaltenerzeugung der Live-Instanz
MAX_LABELS_COLGEN = 400_000                                   # Abbruch der Spaltenerzeugung der Live-Instanz bei so vielen erzeugten Labels über alle Runden zusammen
MEMORY_K = 5                                                  # Gedächtnis (ng-Nachbarschaft) aller Rechnungen mit Zufallsinstanzen
HORIZON, SERVICE = 300, 10
SWEEP_WT = (0, 80, 40, 20, 10, 5, 2, 1)                       # Zeit-Eimerbreiten in Experiment 2 und 3 (grob nach fein; 0 = ohne)
SPLIT_CONFIGS = ((0, 0), (10, 0), (0, 5), (10, 5))            # Einstellungen der Aufteilung in Experiment 4: ohne, Zeit 10, Last 5, beide
# Handbeispiel
HAND_WT_OPTIONS, DEFAULT_HAND_WT = (0, 5, 10), 10
HAND_WQ_OPTIONS, DEFAULT_HAND_WQ = (0, 3), 0
HAND_STEP_MIN, HAND_STEP_MAX, DEFAULT_HAND_STEP = 1, 34, 32   # Nummer des neuen Labels, dessen Prüfung gezeigt wird (F01 bis F34)

# Messreihen (data/laeufe_v10.json): 2 Typen x 2 Fensterbreiten x 10 Zufalls-Seeds x 2 Kapazitäten x 4 Runden = 320 Läufe, je 14 Einstellungen
BAND_CONFIGS = ((0, 0), (1, 0), (2, 0), (5, 0), (10, 0), (20, 0), (40, 0), (80, 0), (0, 5), (0, 10), (10, 5), (10, 10), (20, 10), (5, 5))
BAND_ROUNDS = ("1", "3", "8", "ende")
BAND_WEIGHTS = (0.0, 0.1, 1.0)

# --- Farben ---------------------------------------------------------------------------------------------------------------------------------
COLOR_OK = "#2F6B65"
COLOR_BAD = "#C0392B"
COLOR_OTHER = "rgba(150,150,150,0.55)"
COLOR_LINE = "#4c78a8"
COLOR_LINE2 = "#e08a2c"
COLOR_LINE3 = "#7a5195"
CELL_NEW = "background-color: rgba(128, 90, 213, 0.35)"       # Eimer des neuen Labels
CELL_CMP1 = "background-color: rgba(76, 120, 168, 0.30)"      # von der Prüfung „wird das neue Label dominiert?“ angesehen
CELL_CMP2 = "background-color: rgba(224, 138, 44, 0.30)"      # von der Prüfung „dominiert das neue Label alte?“ angesehen
CELL_BOTH = "background-color: rgba(128, 90, 213, 0.35)"

# --- Schnellstart-Szenarien -----------------------------------------------------------------------------------------------------------------
# Jedes Szenario setzt alle Regler: Handbeispiel (Eimerbreiten, Nummer des gezeigten Labels) und Live-Instanz (Größe, Fensterbreite, Typ, Kapazität, Zufalls-Seed, Eimerbreiten, Gewicht).


def _scenario(hand_wt, hand_wq, step, n, width, typ, q, seed, wt, wq, weight):
    return {"hand_wt": hand_wt, "hand_wq": hand_wq, "step": step, "n": n, "width": width, "typ": typ, "q": q, "seed": seed, "wt": wt, "wq": wq, "weight": weight}


PRESETS = {
    "Zeit-Eimer 10 (Voreinstellung)": _scenario(DEFAULT_HAND_WT, DEFAULT_HAND_WQ, DEFAULT_HAND_STEP, DEFAULT_N, DEFAULT_WIDTH, DEFAULT_TYP, DEFAULT_Q, DEFAULT_SEED, DEFAULT_WT, DEFAULT_WQ, DEFAULT_WEIGHT),
    "Last-Eimer 5": _scenario(0, 3, 34, DEFAULT_N, DEFAULT_WIDTH, DEFAULT_TYP, DEFAULT_Q, DEFAULT_SEED, 0, 5, DEFAULT_WEIGHT),
    "Zeit- und Last-Eimer zusammen": _scenario(10, 3, 34, DEFAULT_N, DEFAULT_WIDTH, DEFAULT_TYP, DEFAULT_Q, DEFAULT_SEED, 10, 5, DEFAULT_WEIGHT),
    "Sehr feine Zeit-Eimer (Breite 1)": _scenario(5, 0, 34, DEFAULT_N, DEFAULT_WIDTH, DEFAULT_TYP, DEFAULT_Q, DEFAULT_SEED, 1, 0, DEFAULT_WEIGHT),
    "Verwaltung gleich teuer wie ein Vergleich (Gewicht 1)": _scenario(DEFAULT_HAND_WT, DEFAULT_HAND_WQ, DEFAULT_HAND_STEP, DEFAULT_N, DEFAULT_WIDTH, DEFAULT_TYP, DEFAULT_Q, DEFAULT_SEED, 40, 0, 1.0),
    "Gruppierte Kunden, Kapazität 120, Breite 100": _scenario(DEFAULT_HAND_WT, DEFAULT_HAND_WQ, DEFAULT_HAND_STEP, DEFAULT_N, 100, "cluster", 120, DEFAULT_SEED, 10, 0, DEFAULT_WEIGHT),
}
PRESET_HELP = {
    "Zeit-Eimer 10 (Voreinstellung)": "Handbeispiel mit Zeit-Eimern der Breite 10 (Label 32); Zufallsinstanz mit 20 Kunden, Fensterbreite 40, Kapazität 70, Zufalls-Seed 0, Zeit-Eimern der Breite 10 und Gewicht 0,1 je Eimerschritt.",
    "Last-Eimer 5": "Handbeispiel mit Last-Eimern der Breite 3 (Label 34), Zufallsinstanz mit Last-Eimern der Breite 5 statt Zeit-Eimern: Last-Eimer sparen auch Vergleiche der Prüfung „wird das neue Label dominiert?“ (Experiment 4).",
    "Zeit- und Last-Eimer zusammen": "Zeit-Eimer 10 und Last-Eimer (Handbeispiel 3, Zufallsinstanz 5) zusammen: weniger Vergleiche als mit einer Eimerart allein, aber auch viel mehr angesehene Eimer; in der Messreihe gilt das bei Zeit 10 × Last 5 in 316 von 320 Läufen.",
    "Sehr feine Zeit-Eimer (Breite 1)": "Zeit-Eimer der Breite 1 (Handbeispiel: Breite 5): auf dieser Instanz die wenigsten Vergleiche unter den Zeit-Eimern (in der Messreihe in 297 von 320 Läufen), aber sehr viele angesehene Eimer (Experiment 3).",
    "Verwaltung gleich teuer wie ein Vergleich (Gewicht 1)": "Zeit-Eimer 40 und Gewicht 1 je Eimerschritt: Wenn ein angesehener Eimer so viel kostet wie ein Vergleich, lohnt sich diese Eimerbreite auf dieser Instanz nicht (Experiment 3).",
    "Gruppierte Kunden, Kapazität 120, Breite 100": "Gruppiert verteilte Kunden, Kapazität 120, Fensterbreite 100: eine größere Rechnung als die Voreinstellung (20 Kunden, Zufalls-Seed 0, Zeit-Eimer 10).",
}

# --- Text, den App und README gleich führen -------------------------------------------------------------------------------------------------
ASSUMPTIONS_MARKDOWN = """\
**Annahmen**
- Eigene Instanzen im Stil der Solomon-Instanzen (Quadrat 100 × 100, Fahrzeit gleich Entfernung, Bedienzeit 10, Horizont 300, Kapazität 70 oder 120), **nicht die Originalinstanzen**; das Handbeispiel rechnet mit dem Manhattan-Abstand auf einem Gitter.
- Die Dualpreise der Messreihen und der Live-Rechnung sind die der Spaltenerzeugung mit Überdeckungs-Master (Runden 1, 3, 8 und Ende bzw. nur Ende), Gedächtnis k = 5 (die fünf nächsten Kunden).
- Warten vor einem Zeitfenster ist erlaubt und kostenlos.
- Gezählt werden Dominanzvergleiche und angesehene Eimer, nicht Sekunden. **Das Gewicht je Eimerschritt (Voreinstellung 0,1) ist eine Annahme, keine Messung.** Eimerschritte sind nach Formel gezählt (alle Eimerindizes im durchsuchten Bereich, auch leere); die Rechnung selbst springt über leere Eimer.

**Grenzen**
- Gemessen sind Eimer je Knoten (einfache Ablage). **Der echte Bucket-Graph der Literatur (Eimer als Knoten mit Sprungkanten, ganze Eimer werden auf einmal verlängert) ist weder gebaut noch gemessen.**
- Die festen Messreihen haben 30 Kunden, Kapazität 70 und 120, Fensterbreite 40 und 100, je 10 Zufalls-Seeds und zwei Instanztypen; Kapazität 70 und 120 benutzen dieselben Zufalls-Seeds und sind daher nicht unabhängig.
- Nicht gemessen: 50 und 100 Kunden, andere Kapazitäten, Eimer zusammen mit beidseitigem Labeling, Gedächtnis k ungleich 5.
- Die Laufzeit in Python bleibt mit Eimern in derselben Größenordnung wie ohne Eimer (je nach Zellenbildung etwa das 0,7- bis 1,4-Fache); Sekunden sind hier nur Information (parallele Läufe).

**Bekannte Probleme und Unsicherheiten**
- Ursachen („weil …“) sind Deutungen, wo es dasteht; gemessen sind die Zählungen.
- Die Dualpreise hängen vom Löser des Master-Problems ab und können mit einer anderen Version der Bibliothek abweichen; die festen Messreihen enthalten die Dualpreise, mit denen gerechnet wurde.
- Die Darstellung der Tabellen und Diagramme ist im Browser am Computer und in einem 375 Pixel breiten Fenster durchgesehen, nicht auf anderen Geräten oder in anderen Browsern. Die Diagramme haben keine Auswahl per Mausklick.
"""
