# Eimer im Labeling: wie viel sparen sie wirklich? – Streamlit-Demo

<!-- Nach dem Deploy hier direkt den Live-Link einsetzen (Leerzeile davor und danach):
**[→ Demo live ausprobieren](https://sebastianhanisch-eimer-labeling-demo.streamlit.app/)** -->

Demo der Linie „Ressourcenwege und Spaltenerzeugung“ in der „Konzepte“-Reihe für die Website „Sebastian Hanisch – Operations Research und Machine Learning“. Das **Label-Verfahren** sucht den Weg mit den kleinsten **reduzierten Kosten**
(Weglänge minus die Dualpreise der besuchten Kunden), mit Zeitfenstern und Last; es ist das Preisproblem der Spaltenerzeugung. Jeder Teilweg ist ein **Label**, und jedes neue Label wird gegen die lebenden Labels seines Kunden auf **Dominanz** geprüft.
Diese Demo fragt nur eines: **Spart es Vergleiche, die lebenden Labels eines Kunden nach Zeit und Last in Fächer, sogenannte Eimer (englisch Buckets), zu sortieren, und was kostet die Verwaltung der Eimer?** Gezählt werden Dominanzvergleiche und angesehene Eimer, keine Sekunden.
**Der echte Bucket-Graph der Literatur (Eimer als Knoten mit Sprungkanten, ganze Eimer werden auf einmal verlängert) ist nicht gebaut und nicht gemessen;** die Demo misst nur die einfache Ablage der Eimer je Kunde („Bucket-Graph light“).

Die Anwendung in einem Fall zeigt [crew-pairing-demo](https://github.com/sebastian-hanisch/crew-pairing-demo) (Besatzungsplanung im Zugverkehr: Preisproblem als Label-Verfahren, nicht gemessen). Aus derselben Linie:
[dominanz-labels-demo](https://github.com/sebastian-hanisch/dominanz-labels-demo) (wann ein Label gestrichen werden darf), [mehrere-grenzen-demo](https://github.com/sebastian-hanisch/mehrere-grenzen-demo) (was jede zusätzliche Grenze kostet) und
[elementar-pricing-demo](https://github.com/sebastian-hanisch/elementar-pricing-demo) (was es kostet, jeden Kunden höchstens einmal zu besuchen). **Abgrenzung:** [hub-labeling-demo](https://github.com/sebastian-hanisch/hub-labeling-demo) meint etwas anderes
(vorberechnete Listen für schnelle Abfragen kürzester Wege); hier sind Labels Teilwege im Preisproblem, und die Eimer ordnen die lebenden Labels eines Kunden.

## Warum dieses Problem

Das Label-Verfahren verbringt einen großen Teil seiner Rechnung mit Dominanzvergleichen: In den 320 festen Läufen dieser Demo (30 Kunden, siehe unten) braucht es ohne Eimer im Median 5,9 Vergleiche je Label bei unter 2 000 Labels und 112,1 bei 50 000 Labels und mehr. Eimer versprechen,
dass die Prüfung nur noch die Labels ansieht, die überhaupt dominieren oder dominiert werden können. Das Ergebnis des Verfahrens bleibt dabei dasselbe; die Frage ist nur, wie viel die Ablage spart und was sie kostet. Die Demo beantwortet sie am Handbeispiel mit sechs Kunden,
an einer Zufallsinstanz mit bis zu 30 Kunden und in 320 festen Läufen, und sie nennt das Ergebnis, auch wenn es bescheiden ist.

**Kurz:** Eimer ändern das Ergebnis nicht, sparen aber nur einen Teil der Dominanzvergleiche, und der Teil schrumpft, sobald die Verwaltung der Eimer etwas kostet (Zahlen mit ihren Voraussetzungen im Abschnitt „Befunde“).

## Befunde und Korrekturen gegenüber dem Plan

- **Neu gerechnet statt übernommen:** Die 320 Läufe der Messreihe sind mit dem Kern dieser Demo neu gerechnet (`tools/bands_bauen.py`), einschließlich der Spaltenerzeugung, aus der die Dualpreise stammen. Beim Bau wurde jede der 4 480 Zeilen (320 Läufe × 14 Einstellungen) mit der Rohausgabe der früheren Messung
  verglichen: Labels, gestrichene Labels, beide Vergleichszahlen und Eimerschritte stimmen in 4 480 von 4 480 Zeilen überein, ebenso die 320 Dualpreis-Sätze (größte Abweichung 0,0). Dieser Abgleich ist nicht Teil der Testsuite (die Rohausgaben liegen nicht im Repo); `data/vormessung_abgleich.json` hält sein Ergebnis fest, und ein Test prüft,
  dass die Datei es nennt. In der Testsuite wird eine Stichprobe der Läufe mit den gespeicherten Dualpreisen neu gerechnet.
- **Korrektur: Eimer sparen nicht in jedem Lauf Vergleiche.** Die Prüfung „dominiert das neue Label alte?“ (cmp2) sieht mit Eimern nie mehr Labels an als ohne (in allen 4 160 Zeilen mit Eimern gilt cmp2 mit Eimern ≤ cmp2 ohne Eimer). Die Prüfung „wird das neue Label dominiert?“ (cmp1) bricht beim ersten dominierenden Label ab; mit Eimern
  ist die Reihenfolge eine andere (nach Eimern statt nach dem Einfügen), und cmp1 ist in 1 025 von 4 160 Zeilen höher als ohne Eimer. Die Summe beider ist in 9 von 4 160 Zeilen höher als ohne Eimer, jeweils bei Last-Eimern (4-mal Last 5, 5-mal Last 10) und bei gruppiert verteilten Kunden, am stärksten mit dem Faktor 1,102
  (Last 5, Kapazität 120, Fensterbreite 100, Zufalls-Seed 7, Dualpreise der Runde 8). Die Deutung (Reihenfolge der Prüfung) ist nicht eigens gemessen.
- **Eimerrand:** Die Dominanzprüfung vergleicht mit der Toleranz 10⁻⁹. Die Messreihen und die Live-Rechnung der App beginnen die Suche für cmp2 deshalb beim Eimer von „Zeit minus 10⁻⁹“ (Rundungssicherheit bei Fließkommazeiten); liegt die Zeit genau auf einer Eimergrenze, sieht cmp2 dann einen Eimer mehr an (unnötig, nie falsch).
  Das Handbeispiel rechnet mit ganzen Zahlen und exakten Grenzen; mit dem Sicherheitsrand wäre cmp2 bei Zeit-Eimer 10 gleich 33 statt 28 und bei Zeit 10 × Last 3 gleich 12 statt 8.
- **Das Gewicht je Eimerschritt ist eine Annahme, keine Messung.** Wo die Demo „netto“ sagt, steht das Gewicht (Voreinstellung 0,1) dabei.

## Modell

Ein Depot und Kunden mit Last, Zeitfenster und Dualpreis; Entfernung = Fahrzeit = Kosten; Warten vor einem Fenster ist kostenlos; Kapazität, Horizont (späteste Rückkehr) und Bedienzeit je Kunde. Ein Label am Kunden $i$ ist $(T, C, R, M)$: Zeit, reduzierte Kosten, verbrauchte Last, Gedächtnis (Menge). **Dominanz:** $O$ dominiert $N$, wenn
$C_O \le C_N$, $T_O \le T_N$, $R_O \le R_N$ und $M_O \subseteq M_N$; bei Gleichstand bleibt das ältere Label. Das Gedächtnis ist bei den Zufallsinstanzen die ng-Nachbarschaft mit $k = 5$ (die fünf nächsten Kunden), beim Handbeispiel elementar (jeder Kunde höchstens einmal).

**Eimer:** Ein Label mit Zeit $T$ und Last $R$ liegt im Eimer $(\lfloor T / w_T \rfloor, \lfloor R / w_R \rfloor)$ seines Kunden (am letzten Eimer abgeschnitten; $w_T$ Zeit-Eimerbreite, $w_R$ Last-Eimerbreite; ohne Breite ein einziger Eimer). Ein dominierendes Label hat Zeit und Last nicht höher, liegt also in einem Eimer mit
Zeit-Index und Last-Index höchstens denen des neuen Labels: nur diese Eimer sieht cmp1 an. Ein dominiertes Label hat Zeit und Last nicht niedriger: nur Eimer mit Zeit-Index und Last-Index mindestens denen des neuen Labels sieht cmp2 an. **Eimerschritte** sind die angesehenen Eimerindizes, auch leere, nach Formel gezählt
(die Rechnung springt über leere Eimer; ihre Sekunden sind daher kein Maß). **Aufwand** = cmp1 + cmp2 + Gewicht × Eimerschritte. Die Formeln stehen im Expander **📐 Mathematische Formulierung** der App (`app.py`), mit Lesehilfe.

Zwei Arten von Instanzen: das **Handbeispiel** (6 Kunden, Manhattan-Abstand, alle Zahlen ganz, halbzahlige Dualpreise, Bedienzeit 2, Horizont 40, Kapazität 9) und **Zufallsinstanzen im Stil der Solomon-Instanzen** (Quadrat 100 × 100, Fahrzeit gleich Entfernung, Bedienzeit 10, Horizont 300, Kapazität 70 oder 120,
Fensterbreite 40 oder 100, Kunden zufällig verteilt oder in fünf Gruppen; **nicht die Originalinstanzen**). Die Dualpreise der Zufallsinstanzen stammen aus einer Spaltenerzeugung mit Überdeckungs-Master (Runden 1, 3, 8 und Ende in den festen Läufen, nur Ende in der Live-Rechnung).

## Methodik

Der Kern (`eml_algorithm.py`, `price`) verlängert Labels in Zeitreihenfolge um je einen Kunden; die Eimer je Kunde stehen in einem Dictionary mit sortierter Schlüsselliste. Je Regel eine Funktion (`bucket_of`, `bucket_count`, `dominates`, `dominated_by`, `check_route`); der Kern zählt Vergleiche, Eimerschritte, erzeugte und gestrichene Labels.
Ein unabhängiger Routenprüfer (ohne Labels) bewertet die beste Route in der App neu. Die **Experimente** der App: (1) das Handbeispiel Schritt für Schritt: zu jedem neuen Label die Eimertabelle des Kunden, die angesehenen und die übersprungenen Labels mit Grund; (2) die Eimerbreite verstellen: dieselbe Zufallsinstanz mit allen Zeit-Eimerbreiten
und zwei Last-Eimerbreiten; (3) das Optimum: Aufwand je Zeit-Breite bei Gewicht 0, 0,1 und 1, dazu die Häufigkeit der besten Breite in den 320 festen Läufen; (4) die Aufteilung der Vergleiche in cmp1 und cmp2; (5) die festen Messreihen mit Median, Mittel und Maximum.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen sind Zählungen (Vergleiche, Eimerschritte, Labels) in Python an den genannten Instanzen und Dualpreisen; Zeiten sind nie ein Befund. Die feste Messreihe: 30 Kunden, Gedächtnis k = 5, Fensterbreite 40 und 100, Kunden zufällig verteilt und gruppiert, Kapazität 70 und 120, je 10 Zufalls-Seeds (0 bis 9), Dualpreise der Spaltenerzeugung
in den Runden 1, 3, 8 und am Ende: 320 Läufe (Instanz × Kapazität × Runde), je 14 Eimer-Einstellungen, 4 480 Zeilen, alle vollständig gerechnet (die Läufe der Messreihe haben kein Labelbudget); **Kapazität 70 und 120 benutzen dieselben Zufalls-Seeds und sind daher nicht unabhängig.** Ohne Eimer erzeugt das Verfahren im Median 5 141,5 Labels je Lauf (höchstens 293 469) und streicht davon im Median 85,1 %.
„Verhältnis“ heißt Vergleiche mit Eimern geteilt durch Vergleiche ohne Eimer, im selben Lauf. Die Spalte „Test“ nennt die Prüfung in `tests/test_claims.py` bzw. `tests/test_algorithm.py` (Zahl-zu-Test-Tabelle).

| Frage | Befund (Voraussetzung im Satz) | Test |
|---|---|---|
| Ändern Eimer das Ergebnis? | In allen 4 480 Zeilen (320 Läufe × 14 Einstellungen, 30 Kunden, k = 5) stimmen die Menge der lebenden Labels, die Zahl der erzeugten und der gestrichenen Labels und die Liste der negativen Routen mit dem Lauf ohne Eimer überein; ebenso an kleinen Instanzen gegen einen unabhängigen Rechenweg (siehe Verifikation). | `test_bands.py::test_every_setting_has_the_result_of_the_run_without_buckets`, `test_oracle_eimer_labeling.py` |
| Handbeispiel (6 Kunden, elementar, Dualpreise 5; 4,5; 9; 4,5; 7,5; 10,5): Labels? | 35 erzeugte Labels (das Start-Label mitgezählt), 11 gestrichen, 24 lebend am Ende; beste Route 5-6-3 mit reduzierten Kosten −3; die Aufzählung findet 39 zulässige elementare Routen, 3 davon mit negativen Kosten. | `test_algorithm.py::test_hand_counts_equal_the_hand_calculation`, `test_oracle_eimer_labeling.py::test_hand_example_against_the_enumeration` |
| Handbeispiel: Vergleiche (cmp1 + cmp2)? | Ohne Eimer 57 + 45 = 102. Zeit-Eimer 10: 57 + 28 = 85 (Anteil 0,83); Last-Eimer 3: 52 + 16 = 68 (0,67); Zeit 10 × Last 3: 52 + 8 = 60 (0,59); Zeit-Eimer 5: 57 + 28 = 85; Zeit 5 × Last 3: 52 + 8 = 60. Eimerschritte: 57, 174, 149, 477, 296 und 818. | `test_algorithm.py::test_hand_totals_as_sums`, `test_claims.py::test_hand_example_numbers_of_the_readme` |
| Handbeispiel: Aufwand bei Gewicht 0,1 (Annahme)? | Aufwand ohne Eimer 107,7; mit Zeit-Eimer 10 102,4 (Anteil 0,95); mit Last-Eimer 3 82,9 (0,77); mit Zeit 10 × Last 3 107,7 (1,00); mit Zeit-Eimer 5 114,6 (1,06); mit Zeit 5 × Last 3 141,8 (1,32). | `test_claims.py::test_hand_example_numbers_of_the_readme` |
| Handbeispiel: einzelne Entscheidungen? | Mit Zeit 10 × Last 3 prüft das neue Label F20 (Kunde 3) drei Labels bei cmp1 und keines bei cmp2 (ohne Eimer 3 und 3); F32 (Kunde 1): 5 und 0 (ohne Eimer 5 und 5); F34 (Kunde 1): 3 und 1 (ohne Eimer 6 und 6); F15 (Kunde 6): 1 und 1 (ohne Eimer 2 und 2). | `test_algorithm.py::test_hand_single_decisions_zeit10_last3` |
| Handbeispiel: Eimerrand? | Mit dem Sicherheitsrand der Messreihen ist cmp2 bei Zeit-Eimer 10 gleich 33 statt 28 und bei Zeit 10 × Last 3 gleich 12 statt 8; Ergebnis und cmp1 bleiben gleich. | `test_algorithm.py::test_hand_rounding_margin_of_the_measurement_version` |
| Wie viele Vergleiche sparen Zeit-Eimer? | Im Median über 40 Läufe (Dualpreise am Ende) fällt das Verhältnis von 0,809 (Zeit 1) bis 0,928 (Zeit 80) bei Kapazität 70 und von 0,808 bis 0,932 bei Kapazität 120, also 6,8 bis 19,2 % weniger Vergleiche (Tabellen unten). | `test_claims.py::test_median_ranges_of_the_readme` |
| … Last-Eimer? | Im Median 26,9 % (Last 10, Kapazität 70) bis 30,9 % (Last 5, Kapazität 120) weniger Vergleiche. | `test_claims.py::test_median_ranges_of_the_readme` |
| … beide Eimerarten? | Zeit 5 × Last 5 im Median 37,8 % (Kapazität 70) und 38,6 % (Kapazität 120) weniger Vergleiche. | `test_claims.py::test_median_ranges_of_the_readme` |
| Welche Prüfung spart Zeit-Eimer? | Zeit-Eimer lassen cmp1 im Median bei 0,991 bis 0,999 und cmp2 bei 0,381 bis 0,807 (je Einstellung und Kapazität); Last-Eimer lassen cmp1 bei 0,870 bis 0,885 und cmp2 bei 0,326 bis 0,437. cmp1 macht ohne Eimer im Median 68,9 % aller Vergleiche aus. | `test_claims.py::test_split_between_cmp1_and_cmp2` |
| Hängt die Ersparnis von der Zahl der Labels ab? | Zeit-Eimer 10 liegt im Median bei 0,858, 0,832, 0,824 und 0,828 in den Klassen unter 2 000, 2 000 bis 10 000, 10 000 bis 50 000 und ab 50 000 Labels (59, 172, 79 und 10 Läufe); Last 5 bei 0,716, 0,750, 0,811 und 0,693 (Tabelle unten). | `test_claims.py::test_label_classes_of_the_readme` |
| Was bleibt nach Abzug der Verwaltung (Gewicht 0,1, Annahme)? | Im Median (Dualpreise am Ende) liegt der Aufwand mit Zeit-Eimern der Breite 20, 40 und 80 bei 0,970, 0,951 und 0,959 des Aufwands ohne Eimer bei Kapazität 70 und bei 0,939, 0,934 und 0,956 bei Kapazität 120, also 3,0 bis 6,6 % gespart; mit Zeit 1 bis 10 bei 1,033 bis 3,276, also mehr als ohne Eimer. Last 10 liegt bei 0,800 bzw. 0,799, also rund 20 % gespart; Last 5 bei 0,839 bzw. 0,865. | `test_claims.py::test_net_effort_of_the_readme` |
| Gibt es ein Optimum der Zeit-Eimerbreite? | Nur unter einem angenommenen Gewicht: Bei Gewicht 0 ist Zeit 1 in 151 von 160 Läufen (Kapazität 70) und 146 von 160 (Kapazität 120) die beste Wahl; bei Gewicht 0,1 Zeit 40 in 74 von 160 (46 %) bei Kapazität 70 und Zeit 20 in 65 von 160 (41 %) bei Kapazität 120, ohne Eimer in 24 und 22 von 160; bei Gewicht 1 ohne Eimer in 140 und 126 von 160 (88 % und 79 %). | `test_claims.py::test_optimum_of_the_readme` |
| Schnellstart-Szenarien (eine Zufallsinstanz, Gewicht 0,1 außer bei „Gewicht 1“) | Vergleiche ohne → mit Eimern: Zeit 10: 5 522 → 5 106 (7,5 % weniger, netto mehr Aufwand); Last 5: 5 522 → 3 724 (32,6 %, netto weniger); Zeit 10 × Last 5: 5 522 → 3 586 (35,1 %, netto mehr); Zeit 1: 5 522 → 5 055 (8,5 %, netto mehr); Zeit 40 bei Gewicht 1: 5 522 → 5 310 (3,8 %, netto mehr); gruppiert, Kapazität 120, Breite 100: 50 135 → 36 862 (26,5 %, netto weniger). | `test_presets.py::test_expected_verdict_lines_of_every_preset` |
| Wie oft haben feine Zeit-Eimer und beide Eimerarten zusammen die wenigsten Vergleiche? | Unter den sieben Zeit-Breiten hat Breite 1 in 297 von 320 Läufen die wenigsten Vergleiche; Zeit 10 × Last 5 hat weniger Vergleiche als Zeit 10 und als Last 5 in 316 von 320 Läufen. | `test_claims.py::test_counts_named_in_the_scenario_help_texts` |
| Laufzeit | In diesem Python-Gerüst bleibt sie mit Eimern in derselben Größenordnung: Die Median-Verhältnisse der gemessenen Sekunden liegen je Kapazität und Runde zwischen 0,86 und 1,10, in feineren Zellen (Instanztyp, Fensterbreite und Runde, je 10 Läufe) zwischen etwa 0,7 und 1,4 (parallele Läufe auf einem Rechner, nur Größenordnung). | Messung dieser README, nicht im Test (Zeiten werden nie festgeschrieben) |

**Kapazität 70, Dualpreise am Ende (40 Läufe):**

| Einstellung | Läufe | Median | Mittel | Maximum | Median cmp1 | Median cmp2 | Median Eimerschritte | Median Aufwand (Gewicht 0,1) |
|---|---|---|---|---|---|---|---|---|
| ohne Eimer | 40 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 4 407 | 1,000 |
| Zeit 1 | 40 | 0,809 | 0,806 | 0,904 | 0,992 | 0,415 | 802 465 | 3,276 |
| Zeit 2 | 40 | 0,812 | 0,808 | 0,905 | 0,992 | 0,419 | 402 696 | 2,044 |
| Zeit 5 | 40 | 0,817 | 0,815 | 0,908 | 0,993 | 0,450 | 162 792 | 1,306 |
| Zeit 10 | 40 | 0,828 | 0,825 | 0,912 | 0,996 | 0,484 | 82 884 | 1,050 |
| Zeit 20 | 40 | 0,848 | 0,850 | 0,936 | 0,997 | 0,561 | 42 940 | 0,970 |
| Zeit 40 | 40 | 0,882 | 0,886 | 0,971 | 0,999 | 0,653 | 22 552 | 0,951 |
| Zeit 80 | 40 | 0,928 | 0,935 | 0,997 | 0,999 | 0,786 | 12 283 | 0,959 |
| Last 5 | 40 | 0,698 | 0,715 | 1,028 | 0,870 | 0,381 | 42 869 | 0,839 |
| Last 10 | 40 | 0,731 | 0,746 | 1,026 | 0,885 | 0,437 | 22 824 | 0,800 |
| Zeit 10 × Last 5 | 40 | 0,627 | 0,627 | 0,841 | 0,845 | 0,179 | 824 588 | 3,096 |
| Zeit 10 × Last 10 | 40 | 0,652 | 0,651 | 0,844 | 0,868 | 0,201 | 437 164 | 1,954 |
| Zeit 20 × Last 10 | 40 | 0,664 | 0,666 | 0,871 | 0,874 | 0,239 | 225 862 | 1,340 |
| Zeit 5 × Last 5 | 40 | 0,622 | 0,620 | 0,827 | 0,841 | 0,169 | 1 623 890 | 5,515 |

Median der Vergleiche ohne Eimer in dieser Zelle: 30 744.

**Kapazität 120, Dualpreise am Ende (40 Läufe):**

| Einstellung | Läufe | Median | Mittel | Maximum | Median cmp1 | Median cmp2 | Median Eimerschritte | Median Aufwand (Gewicht 0,1) |
|---|---|---|---|---|---|---|---|---|
| ohne Eimer | 40 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 5 260 | 1,000 |
| Zeit 1 | 40 | 0,808 | 0,796 | 0,922 | 0,991 | 0,381 | 946 611 | 3,078 |
| Zeit 2 | 40 | 0,809 | 0,799 | 0,923 | 0,991 | 0,396 | 475 132 | 1,936 |
| Zeit 5 | 40 | 0,813 | 0,807 | 0,929 | 0,993 | 0,416 | 192 000 | 1,259 |
| Zeit 10 | 40 | 0,824 | 0,818 | 0,934 | 0,996 | 0,454 | 97 652 | 1,033 |
| Zeit 20 | 40 | 0,852 | 0,843 | 0,953 | 0,997 | 0,509 | 50 650 | 0,939 |
| Zeit 40 | 40 | 0,885 | 0,886 | 0,974 | 0,999 | 0,626 | 26 536 | 0,934 |
| Zeit 80 | 40 | 0,932 | 0,934 | 0,997 | 0,999 | 0,807 | 14 441 | 0,956 |
| Last 5 | 40 | 0,691 | 0,697 | 1,014 | 0,875 | 0,326 | 66 216 | 0,865 |
| Last 10 | 40 | 0,715 | 0,718 | 1,016 | 0,885 | 0,361 | 34 802 | 0,799 |
| Zeit 10 × Last 5 | 40 | 0,621 | 0,624 | 0,781 | 0,858 | 0,144 | 1 294 908 | 3,874 |
| Zeit 10 × Last 10 | 40 | 0,633 | 0,640 | 0,787 | 0,872 | 0,164 | 677 361 | 2,343 |
| Zeit 20 × Last 10 | 40 | 0,645 | 0,654 | 0,829 | 0,877 | 0,188 | 351 137 | 1,535 |
| Zeit 5 × Last 5 | 40 | 0,614 | 0,618 | 0,754 | 0,856 | 0,130 | 2 545 827 | 6,994 |

Median der Vergleiche ohne Eimer in dieser Zelle: 42 690,5 (ganzzahlig gerundet 42 690).

**Abhängigkeit von der Zahl der Labels** (alle 320 Läufe beider Kapazitäten, Median des Verhältnisses der Vergleiche je Klasse der Labelzahl ohne Eimer):

| Labels ohne Eimer | Läufe | Vergleiche je Label ohne Eimer (Median) | Zeit 10 | Zeit 1 | Last 5 | Zeit 10 × Last 5 |
|---|---|---|---|---|---|---|
| 0 bis unter 2 000 | 59 | 5,9 | 0,858 | 0,834 | 0,716 | 0,656 |
| 2 000 bis unter 10 000 | 172 | 11,1 | 0,832 | 0,812 | 0,750 | 0,670 |
| 10 000 bis unter 50 000 | 79 | 29,8 | 0,824 | 0,809 | 0,811 | 0,694 |
| ab 50 000 | 10 | 112,1 | 0,828 | 0,821 | 0,693 | 0,628 |

**Häufigkeit der besten Zeit-Eimerbreite** (je Kapazität 160 Läufe: 2 Verteilungen × 2 Fensterbreiten × 10 Zufalls-Seeds × 4 Runden; beste Wahl = kleinster Aufwand aus Vergleichen und Eimerschritten unter den Zeit-Breiten 1, 2, 5, 10, 20, 40, 80 und „ohne Eimer“; bei Gleichstand die erste in dieser Reihenfolge von „ohne Eimer“ an):

| Kapazität | Gewicht je Eimerschritt | am häufigsten die beste Wahl | ohne Eimer die beste Wahl |
|---|---|---|---|
| 70 | 0,0 | Zeit 1: 151 von 160 | ohne Eimer: 0 von 160 |
| 70 | 0,1 | Zeit 40: 74 von 160 | ohne Eimer: 24 von 160 |
| 70 | 1,0 | ohne Eimer: 140 von 160 | ohne Eimer: 140 von 160 |
| 120 | 0,0 | Zeit 1: 146 von 160 | ohne Eimer: 0 von 160 |
| 120 | 0,1 | Zeit 20: 65 von 160 | ohne Eimer: 22 von 160 |
| 120 | 1,0 | ohne Eimer: 126 von 160 | ohne Eimer: 126 von 160 |

## Ehrliche Grenzen

- **Gemessen sind Eimer je Kunde, nicht der Bucket-Graph.** Wie sich Eimer als Knoten mit Sprungkanten verhalten, sagt die Demo nicht; die Zahlen dieser Demo gelten nur für die einfache Ablage.
- Der Befund ist bescheiden: Die Ersparnis liegt im Median bei 6,8 bis 19,2 % mit Zeit-Eimern, 26,9 bis 30,9 % mit Last-Eimern und bis zu 38,6 % mit beiden, und nach Abzug einer angenommenen Verwaltung von 0,1 Vergleichen je Eimerschritt bleiben mit Zeit-Eimern höchstens 6,6 % (bei Breite 20, 40 oder 80), mit Last-Eimern rund 20 % (Breite 10). Die Demo sagt nicht, dass Eimer das Labeling schneller machen.
- Das Gewicht je Eimerschritt ist angenommen. Bei Gewicht 1 ist „ohne Eimer“ in 88 % (Kapazität 70) und 79 % (Kapazität 120) der Läufe die beste Wahl, bei Gewicht 0 nie; ein Optimum der Eimerbreite gibt es nur unter dem angenommenen Gewicht.
- Die feste Messreihe hat nur 30 Kunden, Kapazität 70 und 120, Gedächtnis k = 5 und eigene Instanzen (nicht die Solomon-Originale); 50 und 100 Kunden, andere Kapazitäten, ein anderes Gedächtnis und Eimer zusammen mit beidseitigem Labeling sind nicht gemessen. Kapazität 70 und 120 benutzen dieselben Zufalls-Seeds und sind nicht unabhängig.
- Eimerschritte sind nach Formel gezählt (alle Indizes im durchsuchten Bereich, auch leere); die Rechnung selbst springt über leere Eimer, ihre Laufzeit ist daher kein Maß.
- Die Live-Rechnung der App hat ein Rechenbudget (Abbruch bei mehr als 400 000 erzeugten Labels in der Spaltenerzeugung oder mehr als 150 000 in einer Runde, bei mehr als 60 000 Labels im Lauf mit den gewählten Eimern); darüber zeigt die App den Abbruch als Warnung. Die festen Messreihen und das Handbeispiel sind davon unberührt.
- Das Handbeispiel (6 Kunden) ist zum Nachrechnen gebaut: Seine Zahlen (zum Beispiel 16,7 % weniger Vergleiche mit Zeit-Eimer 10) sind ein einzelnes Beispiel und kein Beleg für die Größenordnung in den Messreihen.
- Ursachen („weil …“) sind Deutungen, wo es dasteht; gemessen sind die Zählungen.
- Literatur (Prüfstand: Sadykov, Uchoa, Pessoa 2021, Transportation Science, nur die Zusammenfassung gelesen; Pessoa, Sadykov, Uchoa, Vanderbeck 2020, Mathematical Programming, Volltext gelesen, aber hier nicht gemessen; Pecin, Pessoa, Poggi, Uchoa 2017, Mathematical Programming Computation, nur als Suchtreffer gesehen). Keine Zahl daraus übernommen.

Annahmen, Grenzen und bekannte Probleme, wie sie auch in der App stehen (ein Test prüft, dass beide Fassungen gleich sind):

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

## Verifikation

- **Kern** (`tests/conftest.py`, `tests/test_algorithm.py`): je Einheit gegen Handrechnung am Handbeispiel: Eimerindex und Eimerzahl, Dominanzregel (jede Bedingung einzeln, Toleranz), Gedächtnis, Routenprüfer, die Zähler aller sechs Einstellungen des Handbeispiels als Summen, vier Einzelentscheidungen, Eimerrand mit und ohne Sicherheitsrand, Labelbudget, Worst-Case der größten Instanz im Budget.
- **Orakel** (`tests/test_oracle_eimer_labeling.py`, `tests/ref_labeling.py`): ein anders geschriebener Rechenweg (Mengen und Listen statt Bitmasken und Dictionary-Eimern) liefert dieselben Zähler (erzeugte, gestrichene Labels, cmp1, cmp2, Eimerschritte), dieselbe Menge lebender Labels und dieselben Routen an 90 kleinen Instanzen (7 Kunden, Gedächtnis 7 und 3, 8 Einstellungen, mit und ohne Sicherheitsrand) und an 8 Instanzen mit 14 Kunden;
  die Aufzählung aller elementaren Routen bestätigt die gemeldeten Routen und die beste Route (Handbeispiel: 39 Routen). Beim Bau lief außerdem eine große Fassung außerhalb des Repos (Messung dieser README, nicht im Test): 300 Zufallsinstanzen mit 4 bis 9 Kunden, 14 Einstellungen, beide Eimerränder, 8 400 Vergleiche mit dem unabhängigen Rechenweg, 0 Abweichungen.
- **Eigenschaften** (`tests/test_eigenschaften_eimer_labeling.py`): Eimer ändern nie das Ergebnis; cmp2 nie mehr als ohne Eimer; Eimerbreite über Horizont oder Kapazität gleich ohne Eimer; alle Zeiten verdoppelt, dieselben Zähler; Umnummerieren der Kunden; gleiche Zähler in einem zweiten Prozess mit anderem Hash-Zufall.
- **Randfälle** (`tests/test_edge_cases.py`): Label genau auf der Eimergrenze, Breite 1, Breite gleich dem Horizont, Ankunft genau zur Zeit H, ein Label am Kunden, leerer Kunde, ein und zwei Kunden, Gleichstand, alle Dualpreise 0, Kapazität unter jeder Last, Gedächtnis 0.
- **Messreihen** (`tests/test_bands.py`): Aufbau, Quelle je Lauf, eine Stichprobe von 8 Läufen mit den gespeicherten Dualpreisen neu gerechnet (alle 14 Einstellungen gleich), die Spaltenerzeugung reproduziert drei gespeicherte Schranken.
- **Zahlen der README** (`tests/test_claims.py`): jede Tabelle der README entsteht zeichengleich aus den Daten; die Handbeispiel-Zahlen, Spannen, Aufteilungen und Häufigkeiten werden aus den Läufen berechnet.
- **Verdikte** (`tests/test_verdicts.py`) und **je Schnellstart-Szenario die erwartete Verdikt-Zeile** (`tests/test_presets.py`, `tests/test_app.py`).
- **Oberfläche:** AppTest-Rauchtest (jeder Knopf, jeder Regler am Minimum und Maximum, jede Option, Eckfälle, Worst-Case am Regler-Maximum, Permalink mit ungültigen Werten), Layout (fester Kopf, Schnellstart in der Seitenleiste, Hervorhebung), Footer, Laufzeit-Importe.
- **Testzahl:** 164 Tests (`pytest --collect-only -q tests`).

## Dateistruktur

| Datei | Zweck |
|---|---|
| `.github/workflows/tests.yml` | CI: Push, Pull Request, wöchentlicher Canary |
| `.gitignore` | venv, Caches, Streamlit-Secrets |
| `.streamlit/config.toml` | Streamlit-Einstellungen (keine Nutzungsstatistik) |
| `app.py` | Streamlit-App: Kopf, Ergebnis, Kernfrage, fünf Experimente, Grenzen, Formeln, Fußzeile |
| `eml_algorithm.py` | Kern: Label-Verfahren mit Eimern je Kunde (Vergleiche und Eimerschritte gezählt), Dominanzregel, Routenprüfer |
| `eml_colgen.py` | Spaltenerzeugung (scipy, Überdeckungs-Master) für die Dualpreise der Live-Instanz und der Messreihen |
| `eml_constants.py` | Regler-Grenzen, Rechenbudget, Farben, Schnellstart-Szenarien, gemeinsamer Text der Annahmen |
| `eml_evaluation.py` | Live-Läufe, Handbeispiel-Auswertung, Auswertung der Messreihen, Zahlenformate, Verdikte (reine Funktionen) |
| `eml_layout.py` | Fester Kopf (Stylesheet) |
| `eml_presets.py` | Permalink (Begrenzen), Schnellstart in der Seitenleiste, aktives Szenario hervorgehoben, Zufalls-Seed-Knopf |
| `eml_scenario.py` | Handbeispiel, Zufallsinstanzen im Solomon-Stil, Nachbarschaft des Gedächtnisses |
| `eml_visualization.py` | Plotly-Abbildungen (Achsen gesperrt) |
| `data/laeufe_v10.json`, `data/dualpreise_v10.json`, `data/vormessung_abgleich.json` | feste Messreihen (neu gerechnete Läufe mit Quelle je Lauf), die zugehörigen Dualpreise, Ergebnis des Abgleichs mit den Rohausgaben der früheren Messung |
| `tools/bands_bauen.py` | rechnet die 320 Läufe mit dem Kern der Demo (`messen`) und baut `data/*.json` samt Abgleich (`bauen`) |
| `requirements-dev.txt` | Laufzeit plus pytest |
| `requirements.txt` | Laufzeit-Bibliotheken (ungepinnt) |
| `tests/` | siehe Verifikation; `tests/ref_labeling.py` ist der unabhängige Rechenweg, `tests/readme_tables.py` erzeugt die Tabellen der README aus den Daten |

## Bewusst nicht umgesetzt

- **Der echte Bucket-Graph** (Eimer als Knoten mit Sprungkanten, ganze Eimer werden auf einmal verlängert) ist nicht gebaut und nicht gemessen; die Demo zeigt nur die einfache Ablage je Kunde.
- Keine Aussage über Rechenzeit und keine Zeitmessung in der App; die Sekunden der Messreihe stehen nur in `data/laeufe_v10.json`.
- Keine Eimer zusammen mit beidseitigem Labeling, keine Filter über reduzierte Kosten, keine Zeitfenster-Eimer anderer Art.
- Keine Instanzen mit mehr als 30 Kunden, keine Originalinstanzen, kein anderes Gedächtnis als k = 5 bei den Zufallsinstanzen.
- Kein PDF-Export.

## Lokal ausführen

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Python 3.12 oder neuer (die CI läuft mit 3.12). Die in der Streamlit Cloud eingestellte Python-Version ist beim ersten Deploy einzutragen. <!-- lint-ok: dezimalpunkt -->

## Tests ausführen

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Gebaut mit Streamlit, Plotly, pandas, NumPy und SciPy.

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Ressourcenwege: von der Grenze zur Verfahrenswahl](https://sebastianhanisch.net/konzepte-ressourcenwege.html).
