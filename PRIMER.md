# Primer — alligator-py

Arbeitsplan für die Portierung des Java-Werkzeugs `alligator` (Allen
Transformer) nach Python, als Teil des Alpaka-Frameworks aus Alligator und
Academic Meta Tool.

**Ort.** <https://github.com/n4o-rse/alligator-py/blob/main/PRIMER.md>

**So wird es benutzt.** Es wird in jedem Chat vollständig hochgeladen (oder aus
dem öffentlichen Repo gelesen, siehe A5). Danach
genügt ein Satz: „Wir machen S2." Teil A gilt immer, Teil B ist die Übersicht,
Teil C beschreibt den einzelnen Schritt. Die Statusspalte in Teil B und die
Beschlusslage in A4 werden nach jedem Chat nachgeführt, damit spätere Chats den
aktuellen Stand sehen.

---

# Teil A — Immer gültig

## A1. Ausgangslage

**Vier Vorläufer-Repositorien, ein Werkzeug.**

| Repo | Sprache | Was daraus übernommen wird |
|---|---|---|
| `leiza-rse/alligator` | Java, MIT | der Algorithmus, der AGT-Parser, alle sechs Ausgabeformate, der AMT-Ontologieblock, `ontology/alligator.ttl` (Triceratops Edition) |
| `leiza-rse/alligator-app` | JS, MIT | die vis.js-Ansichten Timeline, Graph und Matrix — werden zur statischen GitHub-Pages-Seite |
| `leiza-rse/alligator-ca` | R | die Korrespondenzanalyse, die das AGT-File erzeugt; läuft als ADP auf <https://www4.leiza.de/adp/> |
| `leiza-rse/alligator-format` | — | die Formatbeschreibung, gespiegelt in `alligator-ca/data/_format/agt.md` |

**Das laufende Java-Werkzeug** steht unter <https://tools.leiza.de/alligator/>.
Es ist die Referenz, gegen die portiert wird, und die Quelle der Golden Files.
Sein Quelltext liegt seit dem 2026-08-28 unter `reference/alligator-java/` im
Repo; nachzuschlagen ist also nichts mehr hochzuladen.

**Der Ort.** alligator-py liegt unter `n4o-rse`, also in derselben Organisation
wie `amt-engine` und `amt-runner`. Die drei Alpaka-Bausteine sind damit
benachbart; die Vorläufer `alligator`, `alligator-app` und `alligator-ca`
bleiben unter `leiza-rse`.

**Die AMT-Seite ist bereits Python.** Das ist die wichtigste Änderung der
Ausgangslage gegenüber der Zeit, in der der Java-Alligator entstand:

| Repo | Rolle |
|---|---|
| `n4o-rse/amt-engine` | reiner Python-Reasoner für die AMT-Ontologie: SHACL-Vorvalidierung, n-äre RoleChain-Inferenz, sechs Fuzzy-Operatoren, Export nach TTL/Cypher/CSV/HTML, Markdown-Report |
| `n4o-rse/amt-runner` | schmales Wrapper-Skript `run_amt.py`, das die Engine holt und die Pipeline auf einer TTL-Datei laufen lässt |
| `leiza-scit/CAA2026-amt` | die JS-Visualisierung, die dasselbe TTL-Format liest |

Damit ist Alpaka zum ersten Mal durchgängig in einer Sprache erreichbar:
`Zähltabelle → CA → AGT → alligator-py → AMT-TTL → amt-engine → Viewer`.

**Was der Java-Code tatsächlich ist.** 3 886 Zeilen in 19 Klassen, davon:

| Bereich | Zeilen | Charakter |
|---|---|---|
| `Alligator.java` | 322 | Kern: Parsing, Distanzen, Nachbarschaft, Allen-Zeichen |
| `AllenInttervalAlgebra.java` | 343 | 13 Relationen plus Freksas Semi-Intervalle (letztere nie aufgerufen) |
| `Timeline`, `Graph`, `MatrixAllen`, `MatrixDist`, `Cypher`, `RDFEvents` | 420 | Ausgabeschreiber, trivial |
| `AMTEvents.java` | 1 992 | **davon rund 980 Zeilen hartkodiertes Turtle** |
| REST, Tomcat, GZIP, CORS, POM, Logging | ~800 | entfällt vollständig |

Echte Logik sind rund 700 Zeilen.

**Der AMT-Block ist Daten, kein Code.** Gemessen an
`v1/alligator_re_results_amt.ttl`: 31 `amt:Role`, 28 `amt:InverseAxiom`, 126
`amt:RoleChainAxiom`, 31 `amt:SelfDisjointAxiom`, 6 `amt:DisjointAxiom` — die
Kompositionstafel der Allen-Algebra, für jede Eingabe identisch. Sie wird eine
statische `.ttl`-Datei.

**Testdaten.** `romanempire.agt`: 12 Ereignisse, elf davon fixiert, eines
(`DomitianConsulate2`) beidseitig floating, Gewichte `1.0|1.0|1.0`.
`alligator-ca/data/ca_3Dcoordinates_4_2.agt`: acht Ereignisse, Gewichte
`0.365|0.149|0.145`, darunter `NoordzeeKust` mit fixiertem Anfang und
floating Ende. Dazu die sechs Referenzausgaben in `v1/`.

## A2. Zielbild

**alligator-py ist ein Dateiwerkzeug, kein Dienst.** Der Java-Alligator ist eine
Web-Anwendung: Eingabe per POST, Ausgabe im Antwortkörper, nichts bleibt liegen.
alligator-py liest ein AGT-File und schreibt Dateien, die versioniert, zitiert
und wieder gelesen werden können.

- Eine Pipeline, ein Einstiegspunkt: `python py/main.py`.
- Erzeugte Ergebnisse werden **mitversioniert**. Das geht nur, weil A3 die
  Byte-Gleichheit erzwingt und A4 die zufälligen IDs abschafft.
- Die Timeline läuft ohne Server: GitHub Pages liest die erzeugte JSON-Datei,
  es gibt keine API mehr.
- Die Grenze zu AMT bleibt scharf. alligator-py **schreibt** eine AMT-Datei und
  ruft optional `amt-engine` auf; es reimplementiert kein Reasoning.
- Was AMT.engine bereits leistet, wird nicht nachgebaut: die Vokabulardatei
  `ontology/amt.ttl` lädt die Engine selbst, unsere Ausgabe muss sie nicht
  mitschreiben.

**Verhältnis zu den Vorlagen.** `alligator` (Java) und `alligator-app` bleiben
stehen und werden nicht angefasst. `alligator-ca` wird durch die CA-Phase
abgelöst, bleibt aber als Referenzimplementierung erhalten, solange die ADP-Seite
darauf läuft.

## A3. Querschnittsregeln

- **Zweimal laufen lassen, `git status` muss sauber bleiben.** Identische
  Eingaben ergeben byte-identische Ausgaben. Tripel sortiert ausgeben, keine
  zufälligen Blank-Node-Labels, keine zufälligen IDs, feste Zahlenformate.
- **Keine Uhr im Output.** Kein Generator liest `datetime.now()`. Der Java-Code
  schreibt einen Zeitstempel auf die Konsole; im Ergebnis steht keiner, und das
  bleibt so.
- **Faithful port first.** Jede bewusste Abweichung vom Java-Verhalten bekommt
  eine Zeile in A8. Was dort nicht steht, ist ein Fehler und kein Feature.
- **Der Kern kennt keine Dateien.** Funktionen nehmen und liefern Objekte; nur
  die CLI schreibt. Das ist die Bedingung dafür, dass später eine FastAPI-Schicht
  ohne Umbau daraufpasst.
- Kopierter Code trägt seine Prüfungen mit.
- Ein Thema pro Chat, ein Schritt pro Chat.
- **Offene Entscheidungen werden als interaktives Formular gestellt**, nicht als
  Aufzählung im Fliesstext, und jedes Formular hat ein freies Kommentarfeld.
- Sprache: Konversation deutsch, Code, Kommentare, README und Ontologie
  englisch. Ausnahme: dieses `PRIMER.md` bleibt deutsch — internes
  Arbeitsdokument.

## A4. Beschlusslage

| Frage | Beschluss | seit |
|---|---|---|
| Repo-Name | `alligator-py` | 2026-08-28 |
| Einstiegspunkt | ein einziger: `python py/main.py`, phasenbewusst | 2026-08-28 |
| Ort der portierten Logik | Paket `py/alligator/` | 2026-08-28 |
| Ort der Ergebnisse | `output/<dataset>/`, versioniert — nicht neben dem Code | 2026-08-28 |
| Schnittstelle v1 | nur Terminal. FastAPI ist Ausblick, kein Lieferbestandteil | 2026-08-28 |
| Ereignis-IDs | **deterministisch**, aus dem Inhalt der AGT-Zeile. `--random-ids` stellt das Java-Verhalten für A/B-Vergleiche wieder her | 2026-08-28 |
| RDF-Erzeugung | **`rdflib`**, keine String-Verkettung | 2026-08-28 |
| Basis-URI der Ontologie | `http://archaeology.link/ontology#` (Triceratops Edition). Die beiden abweichenden URIs im Java-Code werden aufgegeben | 2026-08-28 |
| Python-Version | ≥ 3.10 | 2026-08-28 |
| Abhängigkeiten | `rdflib`, `numpy`, `pandas`, `matplotlib`, `pillow` in `requirements.txt`; `pytest` und `ruff` in `requirements-dev.txt`; `pyshacl` nur im optionalen Extra `[amt]`. Ein reiner Pipelinelauf zieht keinen Testrunner nach. `pillow` ist eigens gepinnt: das SVG ist über Versionen hinweg byte-stabil, das JPEG nicht | 2026-08-28 |
| AMT-Ausgabe | zielt auf **AMT.engine**, nicht auf den Java-Block: Gewichte als `xsd:decimal`, Validierung gegen `amt-shapes.ttl` | 2026-08-28 |
| AMT-Vokabular in der Ausgabe | nein. Die Engine lädt `ontology/amt.ttl` selbst; wir schreiben nur die Allen-Rollen und -Axiome | 2026-08-28 |
| Ort der Allen-Axiome | statische Datei `py/alligator/vocab/amt_allen_axioms.ttl`, aus dem Java-Block extrahiert: 921 Tripel, 1 `amt:Concept`, 31 `amt:Role`, 28 `amt:InverseAxiom`, 126 `amt:RoleChainAxiom`, 31 `amt:SelfDisjointAxiom`, 6 `amt:DisjointAxiom`. Die Zahlen, die hier bis S3 standen, waren um eins bis zwei zu hoch: der Block steht **zweimal** in `AMTEvents.java` und wurde offenbar über beide Kopien gezählt. Beide sind identisch und stimmen tripelgenau mit dem Block in den Referenzdateien überein | 2026-08-28, korrigiert in S3 |
| Namensraum der Ereignisse | `http://data.archaeology.link/data/ae/` — was das laufende Werkzeug heute schreibt, belegt in `potterlimes.ttl`. `http://example.net/event#` aus dem Java-Quelltext wird aufgegeben | 2026-08-28 |
| Klasse eines Ereignisses | `alligator:Alligator_Event`, die einzige, die das Vokabular deklariert. `alligator:event` aus dem Java-String war nie erklärt — siehe A8/D-15 | 2026-08-28 |
| Ereignisse in der AMT-Datei | unter `ae:`, nicht unter `rgzm:`. `rgzm:` trägt danach nur noch Vokabular, und die beiden Turtle-Dateien eines Laufs beschreiben dieselben IRIs — siehe A8/D-17 | 2026-08-28 |
| Kanonisches Turtle | **eigener Schreiber**, `outputs/turtle.py`. Der Graph wird mit rdflib gebaut, das Byte-Layout kommt von uns: ein Tripel pro Zeile, Reihenfolge der AGT-Datei, deterministische Blank-Node-Labels. `rdflib.Graph.serialize` scheidet aus, gemessen — siehe S3 | 2026-08-28 |
| Timeline auf GitHub Pages | statisch, liest `docs/data/<dataset>/*.json`. Kein Upload-Formular, kein API-Aufruf | 2026-08-28 |
| Statische Abbildungen | **zusätzlich** zur interaktiven Seite, nicht statt ihrer: jede der vier Ansichten als SVG und als JPEG mit 300 dpi. Die Seite bleibt vis.js, die Bilder sind für Paper, Poster und Zenodo | 2026-08-28 |
| Ort der Abbildungen | `output/<dataset>/img/`, Dateinamen mit demselben Stamm wie die Datendatei: `<ds>_graph.json` und `<ds>_graph.svg` sind dieselbe Sache zweimal | 2026-08-28 |
| Erzeugt werden sie in | **S2**, nicht in S4. Sie lesen den `Result`, nicht die JSON-Dateien, und hängen damit nicht an der Pages-Phase | 2026-08-28 |
| Rendering | matplotlib. Kein networkx: das Graph-Layout ist ein fester Kreis, weil ein kraftbasiertes Layout mit festem Seed nur so aussieht, als wäre es reproduzierbar | 2026-08-28 |
| Farbpalette der Abbildungen | die aus `leiza-scit/CAA2026-alligator`, `py/viz/_prelude.py`: nach Relationsfamilie eingefärbt (blau sequenziell, orange überlappend, rot enthaltend, grün gleich), Abkürzungen wie dort. Eine Relation hat in der ganzen Familie dieselbe Farbe | 2026-08-28 |
| Byte-Reproduzierbarkeit von matplotlib | `py/wd_repro.py`, wortgleiche Kopie aus `CAA2026-alligator` samt Salt `wdttest`. Setzt `svg.hashsalt` auf `rcParamsDefault`, damit ein späteres `plt.rcdefaults()` es nicht wegwirft, und `SOURCE_DATE_EPOCH=0`. Änderungen gehören zuerst nach oben | 2026-08-28 |
| CA-Implementierung | numpy, Algorithmus im README ausgeschrieben — kein `prince` | 2026-08-28 |
| Zeilenenden | LF beim Schreiben, CRLF und LF beim Lesen. `.gitattributes` mit `eol=lf` | 2026-08-28 |
| Kodierung | UTF-8 ohne BOM (`RätischeLimes`, `fruehkaiserzeitlich`) | 2026-08-28 |
| Dezimaltrenner in den Matrizen | Punkt. Java schreibt Komma, weil `DecimalFormat` die Locale zieht — siehe A8/D-10 | 2026-08-28 |
| Selbstrelationen | **werden überall ausgeschlossen**, auch in Matrix, Graph und Cypher. Java schreibt sie dort — siehe A8/D-13 | 2026-08-28 |
| Ziel der CA-Phase | dem ADP-Ergebnis nahekommen, nicht es byte-genau nachbilden. Ein eigenständiges Skript mit Parametern auf der Kommandozeile | 2026-08-28 |
| Golden Files | `tests/reference/`, aus <https://tools.leiza.de/alligator/> gezogen. Vergleich **namensbasiert**, nicht ID-basiert | 2026-08-28 |
| Lizenz | MIT, Fortschreibung von Florian Thiery / LEIZA | 2026-08-28 |
| Grundlage der IDs | die **geparsten Zahlen** der AGT-Zeile, je in kanonischer Schreibweise (`repr(float(...))`), plus der Name. `0.0810`, `0.081` und ` 0.081 ` ergeben dieselbe ID, `0.0811` nicht. Damit überlebt eine ID das Neuschreiben der Datei mit anderer Nachkommastellenzahl. Spalte 7 und die Zeilennummer gehen nicht ein | 2026-08-28 |
| Datumsvergleich | **exakt**, wie Java. Ein nicht ganzzahliges Datum ist eine Warnung, kein Fehler | 2026-08-28 |
| Spalte 7 gegen den Floating-Wert | Widerspruch ist eine Warnung; unter `--strict` bricht der Lauf ab. Entschieden wird in jedem Fall nach dem Floating-Wert (A7) | 2026-08-28 |
| Umgedrehte Intervalle | `b < a` nach der Datierung wird **nicht** in den Zustand geschrieben. `a` und `b` bleiben stehen, `start`, `end` und `reversed` sind abgeleitete Eigenschaften — siehe A8/D-05 | 2026-08-28 |
| `--random-ids` | stellt die *Eigenschaft* des Java-Verhaltens wieder her (IDs, die zwischen zwei Läufen wechseln), nicht dessen Hashid-Algorithmus. Für A/B-Vergleiche reicht das, byte-gleich wird ein Zufallslauf ohnehin nie | 2026-08-28 |

## A5. Wie der Stand in den Chat kommt

Die Zeile **Uploads** bei jedem Schritt in Teil C nennt, was zusätzlich gebraucht
wird. Für den Regelfall gilt: **gar nichts.**

**Das Repo ist öffentlich.** <https://github.com/n4o-rse/alligator-py> lässt sich
im Chat direkt klonen; ein Upload ist nur nötig, wenn ungepushte Arbeit im Spiel
ist. Der Satz „Wir machen S1" genügt also, sofern der Stand auf `main` liegt.

Was das mitbringt und damit nie mehr hochgeladen werden muss: der Java-Quelltext
unter `reference/alligator-java/`, die Testdaten unter `data/`, die Golden Files
unter `tests/reference/` und dieser PRIMER.

**Wenn doch ein Bundle gebraucht wird** — ungepushte Änderungen, oder GitHub ist
gerade nicht erreichbar. Ein Befehl, **eine** Zeile; `&` statt `&&`, weil
robocopy bei Erfolg Exitcode 1 liefert und `&&` daran abbräche:

```cmd
cd /d C:\git & rmdir /s /q bundle 2>nul & robocopy alligator-py bundle\alligator-py /E /MAX:2000000 /NFL /NDL /XD .git .venv __pycache__ .pytest_cache vendor & powershell -NoProfile -Command "Compress-Archive -Path 'bundle\alligator-py' -DestinationPath 'alligator-py_bundle.zip' -Force"
```

Ergebnis: `C:\git\alligator-py_bundle.zip`, derzeit rund 700 KB. `/XD vendor`
greift erst ab S4, wenn `docs/vendor/` mit vis.js und den Cairo-Fonts dazukommt.

**Rückweg.** Änderungen aus dem Chat kommen als Patch-ZIP zurück: nur neue und
geänderte Dateien, in der Ordnerstruktur des Repos, mit einer `PATCH-README.md`
an der Wurzel. Über dem Repo-Wurzelverzeichnis entpacken, die dort genannten
Befehle laufen lassen, `git status` prüfen, committen. Erzeugte Dateien reisen
nicht mit — sie werden vor Ort neu gebaut.

## A6. IRI-Landkarte

| Präfix | Namensraum | Rolle | Status |
|---|---|---|---|
| `alligator` | `http://archaeology.link/ontology#` | Klassen und Properties des Alligator-Vokabulars | beschlossen |
| `ae` | `http://data.archaeology.link/data/ae/` | Instanzdaten: die Ereignisse, in beiden Turtle-Dateien | beschlossen in S3 |
| `time` | `http://www.w3.org/2006/time#` | die 13 Allen-Relationen | aktiv |
| `amt` | `http://academic-meta-tool.xyz/vocab#` | AMT-Vokabular | aktiv, extern |
| `rgzm` | `http://rgzm.de/datingmechanism#` | AMT-Rollen und -Axiome der Allen-Algebra, **nur Vokabular** | beschlossen in S3 |
| `rdf`, `rdfs`, `dc`, `xsd` | Standard | | aktiv |

**Geklärt in S3.** Der `rgzm:`-Namensraum trug in der Java-AMT-Ausgabe zwei
verschiedene Dinge: die Ereignisknoten (`rgzm:jNEOv3`) und die Allen-Rollen
(`rgzm:di`, `rgzm:mi`). Instanzdaten und Vokabular flach in einem Namensraum ist
genau das Muster, das anderswo als Fehler geführt wird. Umgesetzt wie
vorgeschlagen: Rollen und Axiome bleiben unter `rgzm:`, die Ereignisse ziehen
nach `ae:` (D-17). Die Kompatibilität mit AMT.engine hängt nicht daran — die
Engine erreicht ein Ereignis über `amt:instanceOf rgzm:Event`, nie über die Form
seiner IRI.

**Ebenfalls geklärt.** Die beiden Golden Files widersprechen sich im
`ae:`-Namensraum: `romanempire.ttl` trägt `http://example.net/event#`,
`potterlimes.ttl` dagegen `http://data.archaeology.link/data/ae/` und
`alligator:` bereits auf `archaeology.link`. Die zweite Datei ist die jüngere
und zeigt, was der laufende Dienst heute schreibt; sie gilt. Der
PRIMER-Vorschlag `http://archaeology.link/event#` war eine Vermutung und wird
zurückgezogen.

Die Java-Ausgabe schreibt in `alligator_re_results_rdf.ttl` den Präfix
`alligator:` auf `http://rgzm.github.io/alligator/ontology#`, `RDFEvents.writeRDF`
dagegen auf `https://rgzm.github.io/alligator/vocab#`, und die aktuelle
`ontology/alligator.ttl` auf `http://archaeology.link/ontology#`. Drei URIs für
eine Sache; nach A4 gilt die dritte.

## A7. Das AGT-Format

Verbindliche Beschreibung, abgeglichen zwischen `alligator-ca/data/_format/agt.md`
und dem tatsächlichen Parserverhalten in `AlligatorAPI` und
`Alligator.writeToAlligatorEventList`.

```
#9999                                        Zeile 1: Wert, der ein floating date markiert
#true                                        Zeile 2: CA-Dimensionsgewichte benutzen?
#1.0|1.0|1.0                                 Zeile 3: Gewichte x|y|z
#data                                        Trenner
name	x	y	z	von	bis	fixed        Kopfzeile, genau 7 TAB-getrennte Spalten
Vespasian	0.0810	-0.1420	-0.1450	69	79	fixed
DomitianConsulate2	-0.2646	-0.8560	1.0336	9999	9999	floating
```

**Was der Parser wirklich tut:**

- Der Text wird am Literal `#data` geteilt. Aus dem vorderen Teil werden die
  Zeilenumbrüche entfernt, dann wird an `#` geteilt: `meta[1]` ist der
  Floating-Wert, `meta[2]` das Flag, `meta[3]` die Gewichte.
- Ist `meta[2] == "false"`, werden die Gewichte auf `1.0|1.0|1.0` gesetzt und
  Zeile 3 ignoriert.
- Die Kopfzeile muss **genau 7** Spalten haben; die Spaltennamen werden nie
  gelesen. Beide Schreibweisen kommen vor (`von`/`bis`/`fixed` in den Testdaten,
  `from`/`to`/`floating` in `agt.md`). Geparst wird strikt nach Position.
- Zahlenfelder können führende Leerzeichen tragen (`" 0.109"` in
  `ca_3Dcoordinates_4_2.agt`) — vor dem Parsen abschneiden.
- CRLF und LF kommen beide vor.
- **Spalte 7 entscheidet nicht.** Über den Metadatenweg — und das ist der
  einzige Weg, den die API benutzt — entscheidet der Floating-Wert:
  `von == Floating-Wert` heisst Anfang floating, `bis == Floating-Wert` heisst
  Ende floating. Beide Enden werden **unabhängig** beurteilt; `120 … 9999` ist
  gültig und kommt vor.
- Java setzt `startFixedValue` und `endFixedValue` beide auf `meta[1]`. Es gibt
  also nur einen Floating-Wert, nicht zwei.

## A8. Abweichungen vom Java-Original

Jede beabsichtigte Abweichung steht hier. Alle Befunde sind an
`v1/`-Referenzausgaben oder am Java-Quelltext belegt.

| ID | Java | alligator-py | Warum |
|---|---|---|---|
| D-01 | pro Ereignis ein Hashid aus einer frischen Zufalls-UUID | deterministische ID aus dem Zeileninhalt | In `v1/` trägt **jede der sechs Dateien andere IDs**, weil jede aus einem eigenen API-Aufruf stammt. Ergebnisse sind so weder vergleichbar noch versionierbar. `--random-ids` bringt zufällige IDs zurück, aber nicht die Hashid-Bibliothek |
| D-02 | `Cypher` baut die Relationsnamen mit einer Kette von `replace()` | Dictionary | Belegt in `alligator_re_results_cypther.cql`: dort stehen `DURINGi`, `MEETSi`, `OVERLAPSi` statt `CONTAINS`, `MET_BY`, `OVERLAPPED_BY`. `di` wurde zu `DURING`+`i`, weil `d` zuerst ersetzt wird. Betrifft `mi`, `oi`, `si`, `fi`, `di` |
| D-03 | Startwert der Minimalsuche ist `200.0`; findet sich kein Nachbar, folgt eine `NullPointerException` | `--max-neighbour-distance`, Vorgabe `200.0`, sonst klarer Fehler | undokumentierte magische Zahl, unbrauchbarer Abbruch |
| D-04 | `String.valueOf(x) != "null"` filtert leere Relationen | expliziter `is None`-Test | funktioniert in Java nur über String-Interning |
| D-05 | `b < a` nach der Datierung → `Timeline.writeTimeline` tauscht `a` und `b` **im Ereignisobjekt**, Eintrag wird rot | `a` und `b` bleiben, wie sie berechnet wurden; `start`, `end` und `reversed` leiten das Getauschte ab, dazu eine Warnung | Gleiches Ergebnis in der Timeline, aber kein Schreiber verändert mehr den Zustand, den die anderen fünf lesen (A3). In Java hängt es an der Aufrufreihenfolge, ob ein Format das getauschte Intervall sieht |
| D-06 | alle RDF-Literale sind untypisierte Strings (`amt:weight "0.99"`) | typisierte Literale (`"0.99"^^xsd:decimal`) | AMT.engine schreibt und erwartet `xsd:decimal`; ihre SHACL-Shapes prüfen darauf. Untypisierte Zahlen sind für SPARQL ohnehin unbrauchbar |
| D-07 | die Relations-IRI wird ohne spitze Klammern in den String geschrieben und danach per `replace()` zu `time:…` repariert | echte IRIs über rdflib | das Zwischenergebnis war kein gültiges Turtle |
| D-08 | `/amtrepo` lädt per curl in ein RDF4J-Repository | entfällt | ausserhalb des Umfangs |
| D-09 | `minDistanceNorm`, `maxDistanceNorm`, `AllenObject`, Freksas Semi-Intervall-Relationen | entfallen | toter Code; die Semi-Intervalle werden nie aufgerufen |
| D-10 | die Distanzmatrix nutzt `DecimalFormat("0.0000")` ohne Locale | Punkt als Dezimaltrenner | belegt in `alligator_re_results_distancesmatrix.json`: dort steht `"0,7690"`. Auf einem englischen Server käme `"0.7690"` heraus — dieselbe Rechnung, andere Datei |
| D-11 | der AMT-Ontologieblock wird bei jedem Aufruf neu in den String geschrieben | statische `.ttl`, per rdflib gemischt | 980 Zeilen Vokabular sind Daten. AMT.engine lädt `amt.ttl` ohnehin selbst |
| D-12 | Blank Nodes der AMT-Reifikation sind Zufalls-Hashids (`_:p60nn4bO03`) | deterministische Labels aus Subjekt, Prädikat und Objekt | Folge von D-01 auf der Kantenebene |
| D-13 | Selbstrelationen stehen in Matrix, Graph und Cypher (`MERGE (NK81Wo)-[:EQUALS]->(NK81Wo)`), in RDF und AMT nicht | **überall ausgeschlossen** | Dass ein Intervall sich selbst gleicht, ist keine Aussage über die Chronologie. Java ist an dieser Stelle uneinheitlich, weil die sechs Schreiber zwei verschiedene Datenstrukturen lesen: `calculateAllenSigns` filtert `thisEvent != loopEvent` nur für die RDF-Listen, während Matrix, Graph und Cypher die vollständige `allenRelations`-Map durchlaufen |
| D-15 | die Alligator-Turtle typisiert jedes Ereignis als `alligator:event` | `alligator:Alligator_Event` | Die Klasse aus dem Java-String ist in **keiner** Fassung des Vokabulars deklariert — weder in der Triceratops Edition noch unter den beiden aufgegebenen URIs. Deklariert ist `:Alligator_Event rdfs:subClassOf time:Interval`. `a time:Interval` bleibt trotzdem ausdrücklich stehen, wie in der Referenz, damit ein Konsument ohne Reasoner es nicht verliert |
| D-16 | `writeRDFasText` schreibt `nfsn`/`nfen`, aber nicht `nfsnE`/`nfenE` | beide Nachbar-IRIs werden geschrieben | Das Vokabular deklariert `nfsnE` und `nfenE` als Object Properties, und `RDFEvents.writeRDF` — die Dateivariante derselben Klasse — schreibt sie. Nur der Pfad, den das Webtool aufruft, lässt sie weg, weshalb sie in den Golden Files fehlen. Ein Name ist keine Referenz: zwei Ereignisse dürfen denselben tragen |
| D-17 | die AMT-Datei legt Ereignisknoten (`rgzm:jNEOv3`) neben Rollen und Axiome (`rgzm:di`) in einen Namensraum | Ereignisse unter `ae:`, `rgzm:` nur noch Vokabular | Siehe A6. Nebenwirkung und eigentlicher Gewinn: Alligator-TTL und AMT-TTL eines Laufs benennen dieselben Ereignisse und lassen sich zu einem Graphen vereinigen. In Java war das ausgeschlossen, weil schon die IDs je Datei andere waren (D-01) |
| D-14 | `Cypher` verkettet den Ereignisnamen ohne Maskierung in das Statement | einfache Anführungszeichen und Backslashes werden maskiert | Ein Name mit Apostroph erzeugt in Java eine Datei, die Neo4j nicht liest. Für jeden Namen, der vorher funktioniert hat, ändert sich nichts — eine Abweichung ist es trotzdem |
| D-18 | — (in Java gab es keine Engine-Anbindung) | die Ausgabe von AMT.engine wird **nicht** versioniert, als einzige Ausgabe dieses Repos | `amt/core.py` iteriert die Axiomklassen über ein `set` von URIRefs, also entscheidet die String-Hashung die Anwendungsreihenfolge und damit die Reihenfolge der `amt:provenance`-Listen in `reasoned.ttl`, `.cypher` und `.edges.csv`. `PYTHONHASHSEED=0` legt sie fest, aber der gesetzte String-Hash hat zwischen Python 3.10 und 3.11 den Algorithmus gewechselt. Nachgewiesen: zwei Läufe ohne Saat unterscheiden sich, mit Saat nicht; sortiert man beide Dateien, sind sie inhaltsgleich. Fällt weg, sobald die Engine sortiert lädt |
| D-19 | der Axiomblock erklärt `q` und `e` für selbstdisjunkt (`SDA001`, `SDA002`) und leitet zugleich `x q x` und `x e x` ab | beide Axiome entfernt | Gefunden über S6: der Konsistenzcheck der Engine meldete auf `romanempire` 14 Verletzungen und auf `potterlimes` 18, alle abgeleitet, keine in unserer Datei. `RCA0091` (`e ∘ e → e`) schließt sich über eine Relation, die die Datei symmetrisch trägt — wo `A e B` steht, steht auch `B e A` —, und `RCA0117` (`d ∘ di → q`) über ein `di`, das schon per `InverseAxiom` aus jedem `d` folgt. Die Folgerungen sind richtig, die Verbote nicht: `e` ist per Definition reflexiv, `q` ist die volle Disjunktion und schließt Gleichheit ein. Drei weitere Rollen sind nach ihren Labels ebenfalls reflexiv — `hh` *head to head with*, `tt` *tail to tail with*, `ct` *contemporary of* — und behalten ihre Axiome: keine Kette und keine Inverse dieses Blocks erzeugt eine Freksa-Rolle, sie sind also wirkungslos, und ob sie strikt gemeint sind, ist nicht aus der Datei zu lesen |
| D-20 | drei Zeilen der Kompositionstafel liefern die Inverse statt der Identität: `RCA0105` (`s ∘ e → si`), `RCA0119` (`d ∘ e → di`), `RCA0133` (`f ∘ e → fi`) | auf `s`, `d` und `f` korrigiert | Die Verknüpfung mit `e` muss die Identität sein, und in elf der vierzehn Zeilen ist sie es auch. Betroffen sind genau die drei Rollen, die ohne `i` geschrieben werden und deren Inverse sich nur durch das angehängte `i` unterscheidet — ein systematischer Tippfehler. Nachgewiesen gegen eine ausgerechnete Allen-Kompositionstafel: von den 169 Einträgen sind 97 eindeutig, davon stehen 96 richtig im Block und drei falsch; die beiden Einträge mit voller Disjunktion stehen als `q`, die übrigen 70 mehrdeutigen fehlen, was in einem Formalismus ohne Disjunktion die einzige ehrliche Möglichkeit ist. Wirkung: auf `potterlimes` fallen 22 falsch abgeleitete Kanten weg (144 → 122), auf `romanempire` keine, weil dort kein Ereignispaar ein Ende teilt |

**Folgen von D-13, gemessen an `romanempire`:** die Allen-Matrix behält ihre
12×12-Form, aber die Hauptdiagonale wird leer statt `=`. Der Graph verliert 12
Kanten, Cypher 12 `MERGE`-Zeilen. RDF und AMT ändern sich nicht — dort waren
Selbstrelationen schon ausgeschlossen, die 68 Relationen und die 14 `rgzm:e`
bleiben. Die Golden-File-Tests für Matrix, Graph und Cypher müssen die Diagonale
also ausdrücklich ausnehmen.

---

# Teil B — Schrittübersicht

| ID | Schritt | hängt ab von | Status |
|---|---|---|---|
| S0 | Festlegungen, Repo-Skelett, kein Algorithmus | — | **erledigt** 2026-08-28 |
| S1 | Kern: AGT-Parser, Modell, Allen-Algebra, IDs | S0 | **erledigt** 2026-08-28 |
| S2 | Ausgaben: Timeline, Graph, Matrizen, Cypher, Abbildungen | S1 | **erledigt** 2026-08-28 |
| S3 | RDF-Ausgaben: Alligator-TTL und AMT-TTL | S1, S2 | **erledigt** 2026-08-28 |
| S4 | GitHub Pages | S2 | offen |
| S5 | CA-Phase: Zähltabelle → AGT | S1 | offen |
| S6 | AMT-Anbindung: `amt-engine` als optionale Phase | S3 | **erledigt** 2026-08-28 |
| S6b | Korrektur des Allen-Axiomblocks | S6 | **erledigt** 2026-08-28 |
| S7 | Politur: README, CITATION.cff, Pins, Zenodo | alle | offen |

S4 hängt nur an S2, nicht an S3 — die Seite liest JSON, kein RDF. S5 hängt an
S1, weil die CA-Phase gegen den AGT-Schreiber prüft, nicht gegen den
Algorithmus. S6 setzt S3 voraus, weil die Engine unsere AMT-Datei liest.

---

# Teil C — Die Schritte

## S0 — Festlegungen und Skelett

**Ziel:** die Entscheidungen treffen, die später teuer werden, und ein Repo, in
dem ab S1 nur noch Logik dazukommt.

**Uploads:** keine.

**Ergebnis:** Verzeichnisbaum, `pyproject.toml`, `requirements.txt`, `LICENSE`,
`.gitignore`, `.gitattributes`, `py/main.py` als leerer Orchestrator, dieser
PRIMER.

**Fertig, wenn:** `python py/main.py --list` die vier Phasen ausgibt.

### Verzeichnisbaum

```
alligator-py/
├── data/                          Eingaben, versioniert
│   └── romanempire/
│       ├── romanempire.csv            CA-Eingabe: name TAB name TAB count
│       ├── dates.csv                  CA-Eingabe: name,from,to,fixed,…
│       └── romanempire.agt            AGT — von der ca-Phase erzeugt, aufbewahrt
├── output/                        Ergebnisse, versioniert
│   └── romanempire/
│       ├── romanempire.ttl
│       ├── romanempire_amt.ttl
│       ├── romanempire.cypher
│       ├── romanempire_timeline.json
│       ├── romanempire_graph.json
│       ├── romanempire_matrix_allen.json  + .csv
│       └── romanempire_matrix_dist.json   + .csv
├── docs/                          GitHub Pages, erzeugt
│   ├── index.html
│   ├── vendor/                        vis.js, jQuery, Bootstrap, Fonts (MIT)
│   └── data/<dataset>/…
├── py/
│   ├── main.py                    der Einstiegspunkt
│   ├── alligator/
│   │   ├── agt.py                 Leser und Schreiber
│   │   ├── model.py               AlligatorEvent
│   │   ├── allen.py               Allen-Intervallalgebra
│   │   ├── ids.py                 deterministische IDs
│   │   ├── core.py                calculate()
│   │   ├── outputs/               timeline, graph, matrix, cypher, rdf, amt
│   │   └── vocab/                 alligator.ttl, amt_allen_axioms.ttl
│   ├── ca/ca.py                   Korrespondenzanalyse
│   └── build_docs.py
├── reference/
│   └── alligator-java/            der Java-Quelltext, unverändert, nur zum Nachschlagen
├── tests/
│   ├── reference/                 Golden Files aus dem Java-Werkzeug
│   └── test_*.py
├── .gitattributes  .gitignore  CITATION.cff  LICENSE  PRIMER.md  README.md
└── pyproject.toml  requirements.txt
```

### CLI

```bash
python py/main.py --list
python py/main.py ca         --dataset romanempire
python py/main.py alligator  --dataset romanempire
python py/main.py docs
python py/main.py all        --dataset romanempire
```

Global: `--dataset` · `--verbose` · `--strict` · `--out`.
Phase `alligator`: `--floating-value` · `--dimensions x|y|z` · `--formats` ·
`--max-neighbour-distance` · `--random-ids`.
Jedes Modul bleibt einzeln lauffähig; `main.py` orchestriert nur.

### S0 zu entscheiden

- **`ae:`-Namensraum** — `http://archaeology.link/event#` oder etwas anderes?
  Java nutzt `http://example.net/event#`, das ist in einer publizierten Datei
  kein haltbarer Namensraum.
- **Ort der Ereignisknoten in der AMT-Ausgabe** — `rgzm:` beibehalten oder
  trennen (A6)?
- ~~**Vergleich mit Float-Toleranz oder exakt?**~~ exakt, plus Warnung bei
  nicht ganzzahligen Daten — entschieden in S1, siehe A4.
- ~~**Spalte 7 gegen den Floating-Wert:**~~ Warnung, unter `--strict` Abbruch —
  entschieden in S1, siehe A4.

## S1 — Kern

**Ziel:** aus einem AGT-File die vollständig datierten Intervalle und ihre
Allen-Relationen, ohne jede Ausgabeformatierung.

**Uploads:** keine — `reference/alligator-java/` liegt im Repo.

**Ergebnis:** `agt.py`, `model.py`, `allen.py`, `ids.py`, `core.py` und ihre
Tests.

**Fertig, wenn:** `romanempire.agt` dieselben virtuellen Jahre und dieselbe
Allen-Matrix liefert wie `v1/alligator_re_results_allenmatrix.json` — bei
namensbasiertem Vergleich, nicht ID-basiert.

**Erledigt am 2026-08-28.** `calculate()` nimmt eine geparste AGT-Datei und
liefert ein `Result`; Dateien sieht der Kern nicht (A3). Geprüft wird gegen alle
drei Golden Files von `romanempire`: Allen-Matrix ohne Hauptdiagonale (D-13),
Distanzmatrix auf vier Nachkommastellen nach Komma-zu-Punkt (D-10), virtuelle
Jahre samt Nachbarnamen und Punktereignissen aus der Timeline. `potterlimes`
deckt die gewichteten Achsen und den gemischten Fall `120 … 9999` ab. 94 Tests.

### Das Distanzmodell

Die drei CA-Dimensionen werden am Verhältnis ihrer Eigenwerte skaliert; die
erste Achse behält Gewicht 1:

```
w₁ = 1
w₂ = d₂ / d₁
w₃ = d₃ / d₁

dist(P, Q) = √( (w₁Δx)² + (w₂Δy)² + (w₃Δz)² )
```

Bei `1.0|1.0|1.0` ist das der gewöhnliche euklidische Abstand. Bei
`0.365|0.149|0.145` werden die zweite und dritte Achse auf rund 0,41 und 0,40
gedämpft. Distanzen werden für **alle** Paare berechnet, auch für ein Ereignis
mit sich selbst.

### Die Datierung der floating events

Für jeden floating **Anfang** wird der nächstgelegene fixierte **Anfang**
gesucht und dessen Datum übernommen; unabhängig davon dasselbe für die Enden.
Das übernommene Datum ist das *virtuelle Jahr*.

Gegenprobe an `romanempire.agt`: `DomitianConsulate2` bekommt an beiden Enden
`Domitian` als Nachbarn und damit 81 bis 96 —
`v1/alligator_re_results_virtualtimeline.json` zeigt genau das, mit
`"className": "orange"` und `"content": "DomitianConsulate2-->Domitian,Domitian"`.

Zu beachten: bei Gleichstand behält Java den **ersten** Kandidaten in
Dateireihenfolge (strikt `<`). Das Ergebnis hängt damit an der Zeilenreihenfolge.
Das wird dokumentiert, nicht repariert.

### Die 13 Relationen

| Zeichen | Bedingung | Bedeutung | OWL-Time |
|---|---|---|---|
| `<` | `b₁ < a₂` | before | `time:intervalBefore` |
| `>` | `b₂ < a₁` | after | `time:intervalAfter` |
| `m` | `b₁ = a₂` | meets | `time:intervalMeets` |
| `mi` | `b₂ = a₁` | met-by | `time:intervalMetBy` |
| `o` | `a₁ < a₂ < b₁ < b₂` | overlaps | `time:intervalOverlaps` |
| `oi` | `a₂ < a₁ < b₂ < b₁` | overlapped-by | `time:intervalOverlappedBy` |
| `s` | `a₁ = a₂`, `b₁ < b₂` | starts | `time:intervalStarts` |
| `si` | `a₁ = a₂`, `b₂ < b₁` | started-by | `time:intervalStartedBy` |
| `f` | `b₁ = b₂`, `a₂ < a₁` | finishes | `time:intervalFinishes` |
| `fi` | `b₁ = b₂`, `a₁ < a₂` | finished-by | `time:intervalFinishedBy` |
| `d` | `a₂ < a₁`, `b₁ < b₂` | during | `time:intervalDuring` |
| `di` | `a₁ < a₂`, `b₂ < b₁` | contains | `time:intervalContains` |
| `=` | `a₁ = a₂`, `b₁ = b₂` | equals | `time:intervalEquals` |

Alle Bedingungen ausser `=` verlangen zusätzlich `a < b` auf beiden Intervallen.
**Punktereignisse bekommen deshalb nur `=`.** In `romanempire.agt` sind Galba,
Otho, Usurpator und Vitellius alle auf 69 datiert; die Referenzmatrix zeigt für
sie ausschliesslich `=` und sonst leere Zellen. Das ist keine Lücke im Port,
sondern das Verhalten des Originals.

Gespeichert wird nur die **erste** passende Relation. Ein Ereignis mit sich
selbst wird nicht bewertet (D-13).

### Deterministische IDs

```
id = "e" + base32( blake2s(f"{name}|{x}|{y}|{z}|{von}|{bis}", digest_size=8) )[:8]
```

Hängt nur an der eigenen AGT-Zeile, also stabil über Läufe, Maschinen und
Umsortierungen. Der führende Buchstabe ist nötig, weil Cypher-Variablennamen
nicht mit einer Ziffer beginnen dürfen — Java erzeugt den Hashid so lange neu,
bis das erfüllt ist.

Gehasht werden die **geparsten Zahlen**, jede in kanonischer Schreibweise —
`repr(float(...))`, also die kürzeste Zeichenkette, die wieder denselben Float
ergibt, seit Python 3.1 stabil. Eine ID benennt damit einen Punkt im CA-Raum mit
einem Datumsbereich, und `0.0810`, `0.081` und ` 0.081 ` sind derselbe Punkt.
Der Grund ist die CA-Phase: schriebe sie dieselben Koordinaten später mit vier
statt drei Nachkommastellen, würden bei einem Vergleich auf Zeichenebene
sämtliche Ereignisse im Repository umbenannt. Kanonisch heisst nicht unscharf —
`0.0811` bekommt eine andere ID.

Spalte 7 geht nicht ein, weil über das Floaten der Metadatenblock entscheidet
und nicht diese Spalte; die Zeilennummer auch nicht, damit Umsortieren die IDs
nicht neu vergibt. Beschlossen in S1, siehe A4.

**Achtung beim Vergleich mit `v1/`:** dort hat jede der sechs Dateien eigene
IDs. Golden-File-Tests müssen über `rdfs:label` beziehungsweise `content`
verknüpfen.

## S2 — Ausgaben ohne RDF

**Ziel:** Timeline, Graph, beide Matrizen, Cypher und die statischen Abbildungen.

**Uploads:** keine — die Golden Files liegen unter `tests/reference/`.

**Ergebnis:** `py/alligator/outputs/{timeline,graph,matrix,cypher,render}.py`,
dazu `outputs/files.py` für die Schreibkonventionen.

**Fertig, wenn:** die vier Dateien für `romanempire` gegen `v1/` bestehen und
zwei Läufe byte-identisch sind.

| Format | Datei | Anmerkung |
|---|---|---|
| Timeline | `<ds>_timeline.json` | vis.js-Items: `id`, `content`, `start`, `end`, `className`, `type`, `nn_start`, `nn_end` |
| Graph | `<ds>_graph.json` | `{nodes: [{id,label}], edges: [{from,to,label}]}` |
| Matrizen | `<ds>_matrix_allen.*`, `<ds>_matrix_dist.*` | Java liefert JSON-Arrays von Arrays; wir schreiben JSON **und** CSV — die Seite braucht JSON, die Auswertung CSV |
| Cypher | `<ds>.cypher` | `CREATE` / `MERGE` / `RETURN` |
| Abbildungen | `img/<ds>_{timeline,graph,matrix_allen,matrix_dist}.{svg,jpg}` | vier Ansichten, je zweimal; zusätzlich zur vis.js-Seite (A4) |

Farbregeln der Timeline, unverändert: `blue` = beide Enden fixiert, `orange` =
mindestens ein Ende über einen Nachbarn datiert, `red` = `b < a` nach der
Datierung. `a = b` ergibt zusätzlich `"type": "point"`.

Der Inhaltstext eines datierten Ereignisses lautet
`<name>-->` gefolgt von Anfangs- und Endnachbar, getrennt durch Komma, mit `*`
für ein fixiertes Ende. Bei zwei fixierten Enden steht nur der Name.

Zwei Stellen weichen hier bewusst von den Golden Files ab: die Cypher-Namen nach
D-02 (`CONTAINS` statt `DURINGi`) und die fehlenden Selbstrelationen nach D-13.
Beide gehören in den Testcode als ausdrückliche Ausnahme, nicht als
stillschweigend gelockerten Vergleich.

### Die Abbildungen

Vier Ansichten, jede einmal als SVG und einmal als JPEG mit 300 dpi aus
**einer** matplotlib-Figur — sonst können die beiden Fassungen auseinanderlaufen.
Das SVG ist die Archivfassung, das JPEG die, die sich überall einfügen lässt.

| Ansicht | Was sie zeigt |
|---|---|
| Timeline | ein Balken je Ereignis in Dateireihenfolge, in den drei Timeline-Farben; Punktereignisse als Raute |
| Graph | die Ereignisse auf einem Kreis, eine gebogene Kante je Relation, nach Allen-Zeichen eingefärbt, mit Legende. Keine Kantenbeschriftung — 68 Kanten tragen keine |
| Allen-Matrix | die Tafel als Farbfeld mit dem Zeichen in der Zelle, Hauptdiagonale leer (D-13) |
| Distanzmatrix | Heatmap mit Farbskala, Werte in den Zellen, solange die Matrix höchstens 20 Ereignisse hat |

Die Farben stammen nicht von uns. `CAA2026-alligator` zeichnet dieselben zwei
Ansichten für das Paper und hält in `py/viz/_prelude.py` fest, dass eine
Relation im Browser dieselbe Farbe haben muss wie im Druck. Übernommen sind
Palette, Abkürzungen, die Familienlegende und die graue Diagonale mit
Gedankenstrich. Zwei Dinge kommen hinzu, die dort nicht vorkommen können, weil
in jenen Daten jedes Clusterpaar in Beziehung steht: eine eigene, blassere
Füllung für ein Paar, das tatsächlich keine Relation hat — sonst läse sich die
Diagonale wie eine fehlende Antwort statt wie eine nicht gestellte Frage — und
in der Timeline ein Farbverlauf für ein Intervall mit einem datierten und einem
geschätzten Ende, das die Timeline-JSON zu schlichtem `orange` einebnet.

Byte-Gleichheit besorgt `py/wd_repro.py`, das Hausmodul der Familie, wortgleich
kopiert: es setzt `svg.hashsalt` auf `rcParamsDefault` statt auf `rcParams` —
sonst wirft ein späteres `plt.rcdefaults()` den Salt stillschweigend weg — und
`SOURCE_DATE_EPOCH=0`, sodass im SVG ein erkennbar synthetisches Datum steht
statt der Uhr. Lokal kommt dazu: Text als Pfade, damit die Datei nicht davon
abhängt, welche Schriften der Leser installiert hat, und das SVG wird **nicht**
von `savefig` geschrieben, sondern durch `outputs/files.py`. matplotlib öffnet
die Datei im Textmodus und schriebe unter Windows CRLF hinein, was
`.gitattributes` widerspricht und sie nach jedem Lauf als geändert erscheinen
liesse. Das ist die eine Stelle, an der dieses Repositorium etwas hat, das
`wd_repro` fehlt — gehört zurückgegeben.

Die Gleichheit gilt für einen installierten Satz von Versionen. Eine andere
matplotlib legt dieselbe Figur anders aus, ein anderes libjpeg komprimiert
anders — deshalb sind `matplotlib` und `pillow` in `requirements.txt` gepinnt.

**Erledigt am 2026-08-28.** `core.write()` schreibt die angeforderten Formate
und gibt zurück, was geschrieben wurde; `core.run()` ist nur noch die Schicht
darüber, die argparse auspackt. Geprüft gegen alle vier Golden Files von
`romanempire`, mit den zwei Abweichungen als benannte Ausnahmetabellen im
Testcode (`D_02_JAVA_NAMES` und der Diagonalfall) statt als gelockertem
Vergleich — eine dritte Abweichung fällt damit auf, statt durchzurutschen.
`ttl` und `amt` bleiben in `--formats` stehen und warnen, dass sie S3 sind.
Seit dem zweiten Referenzsatz aus `grapHNR23` wird der Cypher zusätzlich gegen
`potterlimes` geprüft, also gegen eine zweite Provenienz und die gewichteten
Achsen. 139 Tests.

## S3 — RDF

**Ziel:** die beiden Turtle-Ausgaben, gebaut mit rdflib und byte-stabil.
**Erledigt** am 2026-08-28.

**Ergebnis:** `outputs/turtle.py`, `outputs/rdf.py`, `outputs/amt.py`,
`vocab/amt_allen_axioms.ttl`, `tests/test_rdf.py`.

**Fertig, weil:** beide Dateien dieselben Tripel tragen wie die Referenz —
namensbasiert verglichen, jede Abweichung als benannte Tabelle in
`tests/test_rdf.py` —, die AMT-Datei die 921 Tripel der Allen-Axiome trägt und
drei Läufe in drei Prozessen byte-identisch sind. Die SHACL-Validierung durch
AMT.engine war zu diesem Zeitpunkt offen, weil deren Shapes nicht im Repo
liegen; sie ist mit S6 nachgeholt und besteht.
`test_the_axioms_are_the_ones_the_reference_carries` bleibt der Test, der ohne
die optionale Abhängigkeit läuft.

### Die Alligator-Datei

Je Ereignis: `a alligator:Alligator_Event` (D-15), `a time:Interval`,
`dc:identifier`, `rdfs:label`, `alligator:estimatedstart` / `estimatedend`,
`alligator:cax` / `cay` / `caz`, `alligator:startfixed` / `endfixed`; wo ein
Datum übernommen wurde zusätzlich `alligator:nfsn` / `nfen` mit dem Namen des
Nachbarn und `nfsnE` / `nfenE` mit seiner IRI (D-16). Danach die
Relationstripel über `time:`. In `romanempire` sind das 68 Relationen.

Die Literaltypen sind keine Ermessensfrage (D-06): das Vokabular schreibt sie
vor. `cax`, `cay`, `caz`, `estimatedstart` und `estimatedend` haben
`rdfs:range xsd:double`, `startfixed` und `endfixed` `xsd:boolean`, `nfsn` und
`nfen` `xsd:string`. Geschrieben wird die kürzeste Zahlform, die exakt
zurückliest — dieselbe Regel wie in `ids.normalise`, damit zwei Zeilen mit
gleicher ID auch gleiche Literale bekommen.

### Die AMT-Datei

Sie ist die Schnittstelle zu AMT.engine und wird deshalb an deren Format
ausgerichtet, nicht am Java-String:

- Knoten: `ae:<id> amt:instanceOf rgzm:Event` und `rdfs:label` (D-17).
- Kanten als Reifikation: `rdf:subject` / `rdf:predicate` / `rdf:object` plus
  `amt:weight` als `xsd:decimal`. Gewicht `0.99`, wenn beide Enden des Subjekts
  fixiert sind, sonst `0.95`. In `romanempire`: 61-mal `0.99`, 7-mal `0.95` —
  die sieben sind die Relationen mit `DomitianConsulate2` als Subjekt.
- Prädikate sind die Allen-Zeichen als Rollen, mit den Ersetzungen
  `<`→`b`, `>`→`a`, `=`→`e`.
- Die Axiome kommen wörtlich aus `vocab/amt_allen_axioms.ttl`: 921 Tripel,
  1 `amt:Concept`, 31 Rollen, 28 `InverseAxiom`, 126 `RoleChainAxiom`, 31
  `SelfDisjointAxiom`, 6 `DisjointAxiom`. Abschnittskommentare und Layout der
  veröffentlichten Datei bleiben stehen, damit ein Diff gegen eine bestehende
  AMT-Datei lesbar bleibt.
- Das allgemeine AMT-Vokabular (`amt:Concept rdfs:subClassOf rdfs:Class` und
  die zwölf Tripel daneben) wird **nicht** mitgeschrieben; AMT.engine lädt
  `ontology/amt.ttl` selbst. Genau diese dreizehn Tripel sind der ganze
  Unterschied zwischen unserer Vokabeldatei und dem Java-Block.

**Entschieden:** die alte zweistellige Form `amt:antecedent1` / `antecedent2`
bleibt. AMT.engine nimmt sie ausdrücklich an, die n-äre `amt:antecedents`-Liste
ist nur empfohlen, und 126 Axiome umzuschreiben ändert eine veröffentlichte
Datei ohne Not. Die Frage gehört auf die Engine-Seite; kommt sie von dort
zurück, ist es eine Ersetzung in einer statischen Datei und kein Codeeingriff.

### Kanonisches Turtle

**Gemessen, nicht geraten.** `rdflib.Graph.serialize` scheidet aus: derselbe
Graph mit Blank Nodes, dreimal in drei Prozessen serialisiert, ergibt drei
verschiedene SHA-256. Ohne Blank Nodes ist die Ausgabe stabil, aber das ist ein
Implementierungsdetail, das rdflib nirgends zusagt — und die AMT-Datei sind 68
Blank Nodes.

Deshalb `outputs/turtle.py`: der Graph wird weiter mit rdflib gebaut, rdflib
maskiert und kürzt auch die Terme, aber das Byte-Layout kommt von uns. Ein
Tripel pro Zeile, Subjekt wiederholt, Reihenfolge der AGT-Datei statt Sortierung
— wie in jeder anderen Ausgabe —, Blank-Node-Labels aus Subjekt, Rolle und
Objekt (D-12). Jedes Dokument parst am Ende seine eigene Ausgabe zurück und
vergleicht sie per `isomorphic` mit dem Graphen, aus dem es gebaut wurde; ein
Layoutfehler fällt beim Schreiben auf und nicht beim Lesen.

Der Test dafür startet drei Subprozesse mit verschiedenem `PYTHONHASHSEED`.
Zwei Läufe im selben Interpreter hätten das Problem nie gezeigt.

## S4 — GitHub Pages

**Ziel:** die Timeline und die übrigen Ansichten laufen ohne Server aus den
erzeugten Dateien.

**Uploads:** `alligator-app.zip` — die Front-End-Dateien liegen noch nicht im Repo.

**Ergebnis:** `docs/` und `py/build_docs.py`.

**Fertig, wenn:** die Seite auf GitHub Pages die Timeline von `romanempire`
zeigt und `python py/main.py docs` sie aus `output/` neu baut.

`alligator-app` rendert die Timeline bereits aus einem JSON-Array; zu ändern ist
allein die Herkunft. Aus

```javascript
$.ajax({ type: "POST", url: API_URL + selValue + "/", data: csvData, … })
```

wird ein `fetch` auf `data/<dataset>/timeline.json`. Damit entfallen API-URL,
CORS und das Upload-Formular.

Vendor-Dateien (vis.js, jQuery, CodeMirror, Bootstrap, Cairo, FontAwesome)
wandern unverändert mit ihren Lizenzen nach `docs/vendor/`; `alligator-app` ist
MIT. Ein Datensatz-Umschalter, sobald mehr als einer vorliegt. Links auf die
Turtle- und Cypher-Dateien in `output/`.

**Zu entscheiden.** Ein reiner Client-Modus, der ein hochgeladenes AGT im
Browser rechnet, hiesse den Algorithmus ein zweites Mal in JS zu halten.
Vorschlag: nein — die Seite ist ein Betrachter für abgelegte Ergebnisse.

## S5 — Korrespondenzanalyse

**Ziel:** ein eigenständiges Python-Skript, das aus einer Zähltabelle und einer
Datumsliste ein AGT-File erzeugt und dabei dem Ergebnis der ADP-Seite nahekommt.

**Uploads:** `alligator-ca.zip` — das R-Skript liegt noch nicht im Repo.

**Ergebnis:** `py/ca/ca.py`, die Phase `ca` in `main.py`, Testdaten unter
`data/<dataset>/`.

**Fertig, wenn:** `python py/ca/ca.py data/romanempire/romanempire.csv --dates
data/romanempire/dates.csv --out data/romanempire/romanempire.agt` ein AGT-File
schreibt, das die Alligator-Phase ohne Nacharbeit verarbeitet, und die
Koordinaten den ADP-Werten in der Grössenordnung der dritten Nachkommastelle
entsprechen.

### Vorlage

`alligator-ca/R/2021-05-27_ca_script.R` von Allard Mees — die Fassung, die auf
<https://www4.leiza.de/adp/> unter „Korrespondenzanalyse" läuft. Sie ist die
Referenz, nicht `ca_script.R` (das ist Sophie C. Schmidts Umbauversuch mit dem
`ca`-Paket statt FactoMineR).

Alles andere in `alligator-ca` war ein Versuch, der nie ganz funktioniert hat,
und wird nicht nachgebaut.

### Was das Skript tut

1. Langtabelle einlesen: drei Spalten `zeile`, `spalte`, `anzahl`.
2. Zur Kontingenztafel drehen, fehlende Kombinationen als 0.
3. Korrespondenzanalyse, drei Dimensionen.
4. Koordinaten mit `dates.csv` über den Namen verbinden.
5. AGT schreiben: Floating-Wert, `#true`, die drei Eigenwerte, `#data`, dann
   sieben TAB-getrennte Spalten.

Die CA selbst sind rund vierzig Zeilen numpy und stehen im README ausgeschrieben:

```
P = N / N.sum()                          Korrespondenzmatrix
r = P.sum(axis=1);  c = P.sum(axis=0)    Zeilen- und Spaltenmassen
S = (P - r⊗c) / sqrt(r⊗c)                standardisierte Residuen
U, d, Vᵀ = svd(S)                        Singulärwertzerlegung
eig = d²                                 Eigenwerte = Trägheiten je Achse
F = U·diag(d) / sqrt(r)                  Hauptkoordinaten der Zeilen
G = V·diag(d) / sqrt(c)                  Hauptkoordinaten der Spalten
```

Kein `prince` (A4). Vierzig nachlesbare Zeilen sind einer Abhängigkeit
vorzuziehen, deren Konventionen man ohnehin gegen FactoMineR prüfen müsste.

### Befund: die Rekonstruktion trägt

Gegenprobe am 2026-08-28, `romanempire.csv` gegen `romanempire.agt`, Zeilen- und
Spaltenkoordinaten aus einem Lauf des obigen Verfahrens:

| Name | AGT x | berechnet | AGT y | berechnet | AGT z | berechnet |
|---|---|---|---|---|---|---|
| fruehkaiserzeitlich | −0,2660 | −0,2108 | 0,2530 | 0,2647 | 0,0072 | 0,0067 |
| 2ndHalfFirstCentury | 0,1235 | 0,0703 | −0,4078 | −0,4207 | −0,0481 | −0,0479 |
| Usurpator | 2,3415 | 2,1726 | 0,5180 | 0,4113 | 0,0610 | 0,0611 |
| Galba | 1,3550 | 1,3883 | 0,3500 | 0,2437 | 0,0580 | 0,0580 |
| Vespasian | 0,0810 | 0,0749 | −0,1420 | −0,1566 | −0,1450 | −0,1459 |
| Titus | −0,1320 | −0,1440 | −0,2240 | −0,2233 | −0,1790 | −0,1798 |
| Domitian | −0,1430 | −0,1612 | −0,2960 | −0,2939 | 0,1180 | 0,1194 |
| Trajan | −0,4230 | −0,3772 | 0,5490 | 0,5711 | 0,0170 | 0,0133 |
| **Vitellius** | **2,2780** | **1,3883** | 0,1590 | 0,2437 | 0,0560 | 0,0580 |
| DomitianConsulate2 | −0,2646 | −0,3303 | −0,8560 | −0,8416 | 1,0336 | 1,0421 |

Vier Schlüsse daraus:

- **Das Verfahren stimmt.** Die dritte Achse trifft bis auf die vierte
  Nachkommastelle, die zweite meist auf 0,01. Es sind Hauptkoordinaten, keine
  Standardkoordinaten — sonst läge ein Faktor √λ ≈ 0,49 dazwischen.
- **Die Vorzeichen der ersten beiden Achsen sind gedreht.** In der Tabelle ist
  das bereits korrigiert; roh liefert numpy sie gespiegelt. Das ist genau der in
  A4 vorgesehene Fall und der Grund für eine feste Konvention.
- **Das AGT enthält Zeilen *und* Spalten.** Die vier Kontexte
  (`fruehkaiserzeitlich`, `2ndHalfFirstCentury`, `Usurpator`,
  `DomitianConsulate2`) sind Zeilen der Tafel, die acht Kaiser sind Spalten, und
  alle zwölf stehen im AGT. Das R-Skript nimmt mit `get_ca_col` **nur die
  Spalten**. Die Auswahl muss also ein Parameter sein.
- **`romanempire.csv` ist nicht die Quelle von `romanempire.agt`.** In der
  abgelegten CSV hat Vitellius dasselbe Profil wie Galba und Otho und bekommt
  deshalb identische Koordinaten; im AGT liegt Vitellius bei 2,2780 statt 1,3550.
  Eine Zählung weicht ab. Die Abnahme kann also nicht „CSV rein, AGT raus"
  lauten — sie muss gegen einen ADP-Lauf mit bekannter Eingabe gehen.

### Parameter

Alles, was das R-Skript hartkodiert, wird ein Schalter. Positional der Pfad zur
Zähltabelle, alles Weitere optional mit Vorgaben:

| Schalter | Vorgabe | Wirkung |
|---|---|---|
| `counts` (positional) | — | Langtabelle mit drei Spalten |
| `--dates PATH` | `dates.csv` neben `counts` | Datumsliste |
| `--out PATH` | `<counts-stem>.agt` | Zieldatei |
| `--sep` | `\t` | Trennzeichen der Zähltabelle |
| `--dates-sep` | `,` | Trennzeichen der Datumsliste |
| `--header / --no-header` | erkannt | `ca_potterlimes.csv` hat eine Kopfzeile, `romanempire.csv` nicht |
| `--coords {col,row,both}` | `both` | welche Punkte ins AGT gehen. `col` ist das R-Verhalten, `both` das, was `romanempire.agt` zeigt |
| `--dims` | `3` | Zahl der Achsen; das AGT-Format kennt genau drei |
| `--floating-value` | `9999` | Metadatenzeile 1 |
| `--weights {eigen,equal}` | `eigen` | Metadatenzeile 3: Eigenwerte oder `1.0\|1.0\|1.0` |
| `--sign-convention {maxabs,none}` | `maxabs` | Vorzeichenfestlegung, siehe unten |
| `--precision` | `4` | Nachkommastellen der Koordinaten |
| `--drop-unmatched / --strict` | drop + Warnung | Punkte ohne Datumszeile |

### Vorzeichenkonvention

Singulärvektoren sind vorzeichenunbestimmt; R und numpy liefern die Achsen
regelmässig gespiegelt, wie die Gegenprobe oben zeigt. Auf die
Alligator-Ergebnisse wirkt sich das **nicht** aus — Distanzen sind unter einer
Spiegelung invariant, und nur Distanzen gehen in die Datierung ein. Auf die Bytes
des AGT wirkt es sich sehr wohl aus, und damit auf jeden Diff.

`maxabs`: je Achse wird das Vorzeichen so gewählt, dass die betragsgrösste
Koordinate positiv ist. Deterministisch, unabhängig von der LAPACK-Version,
und in der Gegenprobe hätte es genau die beobachtete Spiegelung geheilt.

### Metadatenzeile 3, geklärt

Die Frage aus dem ersten Entwurf — Eigenwerte oder Varianzanteile — ist
gegenstandslos. In das Distanzmodell geht nur das Verhältnis ein (`w₂ = d₂/d₁`),
und weil der Varianzanteil `pctᵢ = eigᵢ / Σeig · 100` ist, sind beide Verhältnisse
**identisch**. Wir schreiben die Eigenwerte, weil sie die primäre Grösse sind, und
halten es im README fest.

Damit ist auch der Fehler im R-Export benennbar: `write.table` schreibt drei
Zeilen mit je drei Spalten (`eig|pct|kumuliert`), eine je Dimension. Der
Java-Parser teilt die Metadaten an `#` und nimmt `meta[3]` — das ist die **erste
dieser Zeilen**, also `eig₁|pct₁|kum₁`. Er liest den Eigenwert der ersten Achse
und zweimal einen Prozentwert als Gewichte der zweiten und dritten. Gebraucht
wird eine Zeile mit drei Eigenwerten, wie sie die von Hand erstellte
`ca_3Dcoordinates_4_2.agt` mit `#0.365|0.149|0.145` zeigt.

### Warum die Phase überhaupt existiert

Der R-Export ist nachweislich unbrauchbar. `alligator-ca/export/SinkCAValues.agt`
entsteht über `sink(print(...))` und ist deshalb Festbreitentext mit
umgebrochenen Spalten:

```
              name           x           y           z  von
          AlbLimes  0.08790414  0.44748958  1.63639857   97
…
 bis    fixed
 260    fixed
```

Keine Tabulatoren, `bis` und `fixed` stehen unter der Tabelle statt daneben,
dazu der Metadatenfehler von oben. Deshalb ist die funktionierende
`ca_3Dcoordinates_4_2.agt` von Hand entstanden. Sophies letzte Zeile im Skript
benennt es: *„für sowas braucht man python."*

### Offen

- **Gegen welchen ADP-Lauf wird abgenommen?** Gebraucht wird ein Paar aus
  Eingabetabelle und ADP-Ergebnis, das nachweislich zusammengehört —
  `romanempire.csv` und `romanempire.agt` tun das nicht. Am einfachsten ein
  frischer Lauf auf der ADP-Seite mit einer Datei, die wir behalten.
- **Wie nahe ist nahe genug?** Vorschlag: gleiche Vorzeichen nach Konvention,
  Abweichung je Koordinate unter 0,01, gleiche Reihenfolge der Achsen. Als Test
  formulieren, nicht als Gefühl.
- **Bleibt `alligator-ca` bestehen?** Solange die ADP-Seite darauf läuft, ja.
  Ein Umzug der ADP-Seite ist keine Frage dieses Repos.

## S6 — AMT-Anbindung

**Ziel:** die erzeugte AMT-Datei tatsächlich durch AMT.engine schicken und die
Alpaka-Kette einmal von Ende zu Ende zeigen.

**Uploads:** keine.

**Ergebnis:** `py/amt_phase.py`, die Phase `amt` in `main.py`, das optionale
Extra `[amt]`, `--with-amt` für `all`, ein Abschnitt im README.

**Fertig, wenn:** `python py/main.py amt --dataset romanempire` die Datei
validiert, reasoniert und die Ausgaben der Engine unter `output/romanempire/amt/`
ablegt. — Erfüllt: SHACL besteht, 68 gesetzte Relationen werden zu 138, sechs
Dateien werden geschrieben.

### Keine Kopie von `run_amt.py`

Die README von `amt-runner` empfiehlt, `run_amt.py` in das eigene Repo zu
kopieren statt zu forken. Wir tun es trotzdem nicht, und der Grund ist nicht
Geschmack: Das Skript löst zwei Probleme, und beide Lösungen passen hier nicht.
Es beschafft die Engine per `git clone` in einen Cache und `pip install` zur
Laufzeit in den laufenden Interpreter — ein Skript, das beim Ausführen Pakete
nachinstalliert, ist das Gegenteil des S7-Kriteriums. Und es legt je Lauf einen
zeitgestempelten Ordner an, damit nichts überschrieben wird — wir wollen genau
das Gegenteil, einen festen Ordner, den man diffen kann.

Beschafft wird die Engine also dort, wo Abhängigkeiten hingehören: als Extra
`[amt]` in der `pyproject.toml`, per `pip install git+…@<SHA>`. Getestet: die
`ontology/`-Dateien kommen bei der Installation mit, die Engine findet ihre
Shapes. Auf einen Tag kann nicht gepinnt werden, weil `amt-engine` keine hat;
der Pin steht auf `968e80e`.

### Aufruf als Subprozess

`py/amt_phase.py` ruft `python -m amt.runner` als Subprozess auf, nicht die
Bibliotheks-API. Das kostet einen Prozessstart und ist trotzdem richtig: Die
Engine lädt ihre Axiome mit `for atype in axiom_types:` über ein `set` von
URIRefs (`amt/core.py`), also entscheidet die String-Hashung, ob zuerst
Rollenketten oder Inverse angewandt werden. Der Graph ist in beiden Fällen
derselbe — die Reihenfolge der `amt:provenance`-Listen nicht, und drei der
sechs Ausgabedateien tragen Provenance. `PYTHONHASHSEED=0` legt das fest, und
eine Umgebungsvariable muss vor dem Interpreterstart gesetzt sein.

Was der Runner sonst noch anders macht als die CLI, nehmen wir mit: Er räumt
sein Ausgabeverzeichnis vor dem Schreiben leer, schreibt alle sechs Formate und
legt einen Markdown-Report dazu. Eine neue Ausgabeart der Engine landet damit
ohne Änderung hier.

### Was der erste Lauf ergeben hat

```
VAL  Validating romanempire_amt.ttl ...
OK   Validation passed.
OK   1 Concepts | 31 Roles | 12 Nodes | 68 Edges | 191 Axioms
FAIL 14 consistency violation(s)
     reasoning produced 70 inferred edge(s)
```

Die SHACL-Prüfung ist der eigentliche Abnahmetest für S3, und sie besteht. Der
Konsistenzcheck fiel zunächst durch, an keiner Stelle wegen unserer Daten: alle
14 Verletzungen waren Selbstschleifen, alle abgeleitet, keine davon stand in
unserer Datei. Sie folgten aus dem Axiomblock (D-19).

`potterlimes` hat dann etwas gezeigt, das `romanempire` nicht zeigen kann: 18
Verletzungen, darunter Selbstschleifen über `f` und `fi`, die auf drei
vertauschte Zeilen der Kompositionstafel führen (D-20). In `romanempire` teilt
sich kein Ereignispaar ein Ende, deshalb greift die Zeile dort nie. Das ist der
Grund, warum ein zweiter Datensatz mehr wert ist als ein zweiter Testlauf auf
demselben — und der Anlass für S6b, das beides behoben hat.

**Zu beachten:**

- Die Engine-Ausgabe bleibt git-ignoriert (D-18), anders als jede andere
  Ausgabe dieses Repos. Nicht wegen der Zeitstempel im Report — die betreffen
  nur eine der sechs Dateien —, sondern weil die Provenance-Reihenfolge an der
  Hash-Saat hängt und der gesetzte String-Hash sich zwischen Python 3.10 und
  3.11 geändert hat. Byte-Gleichheit gilt damit je Maschine, nicht über
  Versionen hinweg.
- Die zwei CSV-Ausgaben der Engine kommen mit CRLF. `amt_phase.normalise_newlines`
  schreibt sie auf LF um, damit der Arbeitsbaum der Zusage aus A3 entspricht und
  nicht nur der Git-Index über `.gitattributes`.
- Die Phase läuft in `all` nur mit `--with-amt`. Der ursprüngliche Grund — sie
  klont ein fremdes Repository — ist mit dem Extra entfallen; es bleibt, dass
  ein `pip install -r requirements.txt` die Engine nicht mitbringt.
- **[OFFEN] Zwei Punkte für `amt-engine`,** beide klein:
  `sorted(axiom_types, key=str)` in `core.py` macht die Ausgabe ohne Umweg
  reproduzierbar und lässt D-18 wegfallen; und
  `package-data = ["../ontology/*.ttl"]` legt bei der Installation ein
  Top-Level-`ontology/` in die `site-packages` statt es ins Paket zu nehmen.

## S6b — Korrektur des Allen-Axiomblocks

**Ziel:** die beiden Defekte beheben, die S6 im übernommenen Axiomblock
sichtbar gemacht hat, statt sie weiter zu erben.

**Uploads:** keine.

**Ergebnis:** `vocab/amt_allen_axioms.ttl` in fünf Tripeln geändert, beide
`output/*/[ds]_amt.ttl` neu erzeugt, die Ausnahmetabellen in `tests/test_rdf.py`.

**Fertig, wenn:** `python py/main.py amt --dataset <ds> --strict` für beide
Datensätze mit `Consistency check passed` und Rückgabewert 0 endet. — Erfüllt.

### Was geändert wurde

Fünf Tripel, in zwei Gruppen:

| | vorher | nachher |
|---|---|---|
| `RCA0105 amt:consequent` | `rgzm:si` | `rgzm:s` |
| `RCA0119 amt:consequent` | `rgzm:di` | `rgzm:d` |
| `RCA0133 amt:consequent` | `rgzm:fi` | `rgzm:f` |
| `SDA001` (`amt:role rgzm:q`) | vorhanden | entfernt |
| `SDA002` (`amt:role rgzm:e`) | vorhanden | entfernt |

Die Zahlen der Axiomdatei gehen damit von 921 auf 917 Tripel und von 31 auf 29
`SelfDisjointAxiom`; alles andere bleibt.

### Warum das keine Geschmacksfrage ist

Vor der Änderung ist die ganze Tafel gegen eine ausgerechnete
Allen-Kompositionstafel geprüft worden — 169 Einträge, per Brute Force über
alle Intervallpaare eines kleinen Zahlenbereichs bestimmt, nicht abgeschrieben.
Befund: 97 Einträge sind eindeutig, 96 davon stehen richtig im Block und drei
falsch. Die beiden Einträge, deren Ergebnis die volle Disjunktion ist (`b ∘ a`
und `d ∘ di`), stehen als `q`. Die übrigen 70 mehrdeutigen fehlen ganz, was in
einem Formalismus ohne Disjunktion die einzige ehrliche Möglichkeit ist. Die 28
`InverseAxiom` sind vollständig korrekt.

Es sind also genau drei Fehler, kein Muster, das man weiterdenken müsste — und
sie treffen genau die drei Rollen, die ohne `i` geschrieben werden und deren
Inverse sich nur durch das angehängte `i` unterscheidet.

### Wirkung

| | Verletzungen | Kanten nach Reasoning |
|---|---|---|
| `romanempire` vorher | 14 | 138 |
| `romanempire` nachher | 0 | 138 |
| `potterlimes` vorher | 18 | 144 |
| `potterlimes` nachher | 0 | **122** |

Die 22 Kanten, die auf `potterlimes` wegfallen, sind der eigentliche Gewinn:
`RCA0133` hat aus jedem `f` ein `fi` gemacht, also jede „endet mit"-Relation
über ein gleiches Intervall hinweg in die Gegenrichtung gedreht. Auf
`romanempire` greift die Zeile nie, weil dort kein Ereignispaar ein Ende teilt.

### Folgen für die Tests

`test_the_axioms_are_the_ones_the_reference_carries` vergleicht weiter Tripel
für Tripel mit der Java-Referenz, jetzt mit zwei benannten Ausnahmetabellen
(`D_20_FLIPPED_CONSEQUENTS`, `D_19_DROPPED_SELF_DISJOINT`) statt eines
gelockerten Vergleichs. Dazu kommt
`test_every_deviation_from_the_reference_block_is_a_registered_one`: die
Ausnahmen verbergen genau sieben Tripel der Referenz und fügen drei hinzu —
sieben, weil ein gestrichenes `SelfDisjointAxiom` zwei Tripel kostet. Damit
kann keine sechste Abweichung unbemerkt entstehen.

`amt_phase.review` bleibt, obwohl es nichts mehr zu melden hat. Es ist der
Wächter, der eine Rückkehr dieses Fehlerbilds als solche lesbar macht.

**Zu beachten:**

- Die Referenzdateien in `tests/reference/` tragen die Fehler weiter. Das ist
  richtig so — sie sind die Aufzeichnung dessen, was das Java-Werkzeug
  ausgibt, kein Sollwert.
- **[OFFEN]** Ob der Java-Alligator nachgezogen wird und was mit den bereits
  veröffentlichten AMT-Dateien in grapHNR23 geschieht. Das ist keine Frage
  dieses Repos, aber sie steht.

## S7 — Politur

**Ziel:** aus dem lauffähigen Werkzeug ein zitierbares Repositorium.

**Ergebnis:** README, `CITATION.cff`, geprüfte Versionspins, `.gitattributes`,
Release.

**Fertig, wenn:** ein frischer Klon nach `pip install -r requirements.txt` und
`python py/main.py all --dataset romanempire` alle Ausgaben erzeugt und
`git status` sauber bleibt.

- `CITATION.cff` aus der Java-Fassung abgeleitet: dieselben Autoren (Thiery,
  Mees), neuer Titel, neue `repository-code`, `version 0.1.0`, und ein
  `references`-Eintrag auf die DOI des Java-Alligators
  (`10.5281/zenodo.2540709`) — dies ist eine Portierung, kein Fork.
- README: was es ist · Installation · die Phasen mit Befehlen zum Kopieren ·
  AGT-Format · Ausgaben · Link auf die Pages-Seite · Verweis auf den PRIMER für
  die Begründungen · Zitation.
- Versionen erst pinnen, wenn sie installiert und gelaufen sind.
- **[OFFEN]** eigene Zenodo-DOI für alligator-py, oder Teil einer
  Alpaka-Sammlung?

---

# Teil D — Offene Punkte

Nicht einem Schritt zugeordnet, aber nicht zu vergessen:

- **Die Golden Files müssen neu gezogen werden.** Die sechs Dateien in `v1/`
  stammen aus einem früheren Stand und aus je einem eigenen API-Aufruf, weshalb
  jede andere IDs trägt. Für S1 bis S3 genügt das, weil namensbasiert verglichen
  wird. Für einen belastbaren Abnahmetest sollten alle sechs Ausgaben in einer
  Sitzung von <https://tools.leiza.de/alligator/> gezogen und mit dem
  Eingabefile zusammen unter `tests/reference/` abgelegt werden.
  **Teilweise entschärft am 2026-08-28:** `leiza-scit/grapHNR23` veröffentlicht
  Cypher, Turtle und AMT für genau den `potterlimes`-Datensatz — dieselbe
  AGT-Datei bis auf die Kopfzeilennamen. Sie liegen jetzt unter
  `tests/reference/potterlimes/` und bestätigen S1 und den Cypher-Teil von S2
  auf dem gewichteten Fall, unabhängig von `v1/`. Was weiterhin fehlt: eine
  einzige Sitzung, eine protokollierte Dienstversion, und Timeline, Graph und
  Matrizen für den zweiten Datensatz, die dort nie veröffentlicht wurden.
- **Der `ae:`-Namensraum ist in freier Wildbahn dreifach belegt.** Java schreibt
  `http://example.net/event#`, `grapHNR23` veröffentlicht
  `http://data.archaeology.link/data/ae/`, `CAA2026-alligator` nutzt
  `http://leiza-scit.github.io/CAA2026-alligator/`. Die gelebte Praxis ist also
  ein Namensraum **pro Datensatz beziehungsweise pro Repositorium**, nicht ein
  globaler. S3 hat den mittleren festgeschrieben, weil eine Festlegung besser
  ist als eine Vermutung (A6), aber der Punkt bleibt offen: sobald ein zweites
  Repositorium diese Ausgaben veröffentlicht, braucht `rdf.EVENT` ein
  `--base-uri` auf der Kommandozeile. Solange es eine Konstante an genau einer
  Stelle ist, kostet dieser Schritt eine Zeile.
- **Die SVG-Byte-Stabilität hält innerhalb einer Maschine, aber nicht über
  Maschinen hinweg.** Beim Neubau in S3 kamen `<ds>_timeline.svg` und
  `<ds>_matrix_dist.svg` beider Datensätze verändert heraus, obwohl an den
  Abbildungen nichts angefasst wurde. Der ganze Unterschied ist `M -0` statt
  `M 0` in einem Markerpfad und die daraus folgende andere Pfad-ID: negatives
  Null. Gleiche matplotlib-, pillow- und numpy-Version, zweimal hintereinander
  auf derselben Maschine byte-gleich — es liegt an der Gleitkommaarithmetik
  darunter, nicht an `wd_repro.py`. Für die Praxis heisst das: `output/` bleibt
  reproduzierbar für den, der es gebaut hat, und wer die Abbildungen auf einer
  anderen Maschine neu baut, bekommt einen Diff über vier Dateien ohne
  inhaltlichen Unterschied. Zu entscheiden in S7, ob `short_float_fmt` das
  Vorzeichen der Null normalisieren soll oder ob die SVGs aus `output/`
  ausziehen.
- Der Dezimaltrenner der Distanzmatrix hängt an der Server-Locale (D-10). Falls
  jemand veröffentlichte Alligator-Matrizen weiterverarbeitet, ist das eine
  Fussangel, die nicht bei uns liegt, aber erwähnt gehört.
- Die Freksa-Semi-Intervallrelationen sind in `AllenInttervalAlgebra`
  implementiert und werden nie aufgerufen; die 20 zugehörigen Rollen (`ol`,
  `yo`, `hh`, `tt`, `sv`, `sb`, `pr`, `sd`, `bd`, `db`, `ob`, `ys`, `sc`, `bc`,
  `oc`, `yc`, `ct`) stehen aber im AMT-Block und tragen dort Axiome. Sie kommen
  also nur über das Reasoning ins Spiel. Beim Extrahieren der Axiomdatei nicht
  wegkürzen.
- `getAllenRelationShortDescriptions` hat zwei kollidierende Zweige: `sb` gibt
  einmal *survived by* und einmal *survives* zurück, der zweite ist
  unerreichbar. Nur relevant, falls die Beschreibungen je in eine Ausgabe
  wandern.
- **`rgzm:q` ist geklärt** (S3). Die Rolle trägt das Label `questionmark`,
  steht in 30 der 126 Rollenkettenaxiome und hat keine Entsprechung unter den
  13 Allen-Zeichen — sie ist die *unbestimmte* Relation der Kompositionstafel.
  Zwei Eigenschaften belegen das: sobald `q` in einer Kette vorkommt, ist die
  Folgerung wieder `q`, sie absorbiert also; und sie ist die Folgerung überall
  dort, wo die Komposition zweier Relationen mehrdeutig ist (`b ∘ a`, `d ∘ di`).
  Wir schreiben sie nie als Kante — sie entsteht erst im Reasoning der Engine.
  Die Axiomdatei trägt sie vollständig. S6 hat die Deutung bestätigt: In Allens
  Kompositionstafel sind `b;bi` und `d;di` genau die beiden Einträge, deren
  Ergebnis die volle Menge aller 13 Relationen ist. AMT kann keine Disjunktion
  ausdrücken, also steht `q` für eine. Daraus folgt auch D-19: „irgendeine
  Relation" schließt Gleichheit ein, `q` kann nicht selbstdisjunkt sein.
- **Der Java-Axiomblock war an fünf Stellen falsch** (S6, S6b): drei Zeilen der
  Kompositionstafel (D-20) und zwei `SelfDisjointAxiom` (D-19). Beides ist in
  `vocab/amt_allen_axioms.ttl` korrigiert, in einem Zug, weil ein Teilfix die
  Verletzungen nur verschoben hätte. Die veröffentlichten Java-Ausgaben in
  `tests/reference/` tragen die Fehler weiter; wer sie mit unseren vergleicht,
  findet genau diese fünf Stellen und keine sechste — `test_rdf.py` prüft das.
  Offen bleibt, ob der Java-Alligator und die Dateien in grapHNR23 nachgezogen
  werden.
- `Timeline.writeTimeline` und `Graph.writeGraph` schreiben nach `../timeline/`
  und `../graph/`, `AlligatorAPI.loadCAgetRDF` nach
  `/opt/tomcat/webapps/alligator-files/`. Alle drei sind tote Pfade aus der
  Serverzeit und erklären, warum das Werkzeug nie Dateien abgelegt hat, die
  jemand wiederfinden konnte.
- **Läuft der Java-Alligator noch, wenn wir ihn brauchen?** Die Golden Files
  hängen daran. Sobald sie einmal gezogen und im Repo sind, ist die Abhängigkeit
  erledigt — das sollte früh geschehen, nicht in S7. Beim Neuziehen zu
  protokollieren: Datum, die von `GET /` gemeldete Version aus `POM.getInfo()`,
  und dass alle sieben Ausgaben aus **einer** Sitzung mit **einer**
  Eingabedatei stammen. Beides gehört nach `tests/reference/README.md`.
- `alligator-app` liest die AGT-Datei clientseitig mit `jquery.csv` und schickt
  sie unverändert weiter. Der Parser dort ist also gar keiner; falls die
  Pages-Seite je wieder Dateien annehmen soll, ist das eine offene Baustelle.
- **`data/romanempire/romanempire.csv` und `romanempire.agt` gehören nicht
  zusammen** (S5). Beide bleiben als Testdaten liegen, die CSV taugt aber nicht
  als Abnahmefall für die CA-Phase. Wenn ein passendes Paar vorliegt, wird die
  alte CSV entweder ersetzt oder als „Beispiel, nicht Quelle" gekennzeichnet.
- Der Java-Alligator wertet die Zeile `#true` / `#false` aus, aber weder das
  R-Skript noch die Formatbeschreibung sagen, wann `false` sinnvoll ist. Mit
  `--weights equal` bildet die CA-Phase es ab; ob es jemals benutzt wurde, ist
  unklar.
- Die JPEGs sind das erste Binärformat im versionierten `output/`. Bei zwei
  Datensätzen sind das rund 3 MB; bei einer CA über 500 Töpfer wird die
  Distanzmatrix als Bild sinnlos und als Datei gross. Zusammen mit dem Punkt
  unten neu zu entscheiden — womöglich Bilder nur für die Datensätze, die auch
  im Paper stehen.
- Ob `output/` dauerhaft versioniert bleibt, hängt daran, wie viele Datensätze
  dazukommen. Bei einem Dutzend Ereignissen sind es Kilobytes; bei einer CA über
  500 Töpfer wächst die Distanzmatrix quadratisch. Neu entscheiden, sobald der
  erste grosse Datensatz vorliegt.
