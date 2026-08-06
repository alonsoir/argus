# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 253

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    git branch --show-current
Tras DAY 252: rama de trabajo `feat/ctu-start`, **ya mergeada a main** (PR #135,
merge `eedad038`). main contiene el paper v25 + join_bias_labels.py extendido +
bias_denominator_true.py + autopsy_67.py + los 3 targets nuevos del Makefile.
Puede quedar 1 commit suelto sin pushear (el fix del abstract "ancla 646"): mira
`git status` y `git log origin/main..main`.

## Estado que ordena el día — PAPER SUBIDO, EMPIEZA EL README
DAY 252 cerró (a)+(b) del paper y **subió a arXiv la v25** (arxiv.org/abs/2604.04952):
la subsección `sec:eval:bias` (sesgo por-lente + denominador verdadero) con cada número
detrás de un `make`. Compilación limpia (58 pp, 0 refs undefined). Abstract del PDF y de
la página de arXiv coherentes: 0.9985 anclado al subconjunto conductual de 646, más el
eje per-lens/denominador-verdadero/0.47%.

- ✅ Subsección `sec:eval:bias` en main.tex, anclada a artefacto (STAMP 20260804-080140):
    - denominadores 646 (conductual) / 14188 (lens-observable) / 14255 (true pcap); tabla `tab:denominators`.
    - per-lens `tab:perlens`: zeek 14178/99.9% (14447/16484), suricata 206/1.5% (212/243),
      argus 32/0.2% (**48/1369 = ×28.5** — NO 74/×18.5, corregido contra artefacto).
    - 5 caveats: suri anomalía-no-firma; argus granularidad (×28.5); **ML ciego** (945 MALICIOUS,
      overall/fast 0.75, ml medio 0.0745, 894 botnet/51 sin-label); precision trivial vs CTU; zeek visibilidad.
    - los 67 (0.47%) = fidelidad de replay (0/67 conn.log crudo, 0/67 bronce argus eth2, 17/67 en 1er 5%).
- ✅ `join_bias_labels.py` EXTENDIDO (aditivo; `load_csv()` intacta porque la importan los otros 2 scripts):
  granularidad por-lente + `load_argus_extra()` (split fast/ml de MALICIOUS + top IPs destino).
- ✅ Makefile: targets `neris-pcap-5tuples` (file target `$(NERIS_RAW)` vía tshark host),
  `bias-denominator-true`, `autopsy-67`, en `.PHONY`. Comando tshark: 8 campos
  (ip.proto/src/dst, tcp+udp sport/dport, frame.len), `-E separator=, -E occurrence=f`.

## Batalla DAY 253 = REESCRITURA TOTAL del README.md (mide primero: `cat README.md`)
El README lleva sin tocarse desde ~DAY 191-211 y MIENTE respecto al estado actual:
- **Se contradice la fecha:** encabezado "DAY 191", tabla `DAY|211`, "Tag activo v1.0.0-day166",
  paper "Draft v19 / v24 / v3 en arXiv". Nada dice DAY 252 / v25.
- **Afirma sin matizar:** badge "F1=0.9985 Validated" + tabla "Recall 1.0000 · Zero missed
  attacks" SIN el subconjunto conductual de 646 → el repo desmiente al paper que enlaza.
- **Es un diario, no una puerta:** 200+ líneas de hitos DAY 143-204 entierran qué-es/cómo-se-corre/cómo-reproduce.
  DECISIÓN de Alonso pendiente al arrancar: (A) parche de verdad (tocar solo lo que miente) o
  (B) poda Vía Appia (reescribir para quien llega del paper; mover el diario a CHANGELOG/docs/HITOS.md).
  Alonso se inclinó a B. Regla dura: el README refleja el ESTADO ACTUAL del pipeline (misma regla
  que el paper), no el histórico; lo que no se pueda anclar a algo medido, fuera, no se afirma.
  Encuadre honesto obligatorio: artefacto de INVESTIGACIÓN, no producción (lo fijó Alonso DAY 241).
  Debe incluir el arranque reproducible que el paper promete: `vagrant up`→pipeline→
  `make bias-report`/`bias-denominator-true`/`autopsy-67`.

## Batalla DAY 253 — andamio ejecutable: "escribe tu ataque, recibe tu dataset". Salda DEBT-DATASET-DRIVER-CONTRACT-001. El investigador SOLO escribe las invocaciones de sus herramientas de terceros contra una interfaz de red dada; el resto (bronce CSV sellado → oro AVRO/Parquet → Kuzu → SELECT/export con contrato de cabecera) es invariante y ya existe. La guía documenta EL HUECO que rellena, no el pipeline entero.
Tres piezas, TODAS extraídas de leer scripts/mitre_start.sh + scripts/ctu_start.sh lado a lado (NO proponer el contrato — destilarlo de los dos drivers que ya lo cumplen):

scripts/custom_start.sh.template — comentado, con la sección "AQUÍ van tus invocaciones contra $IFACE" aislada y el resto (curl clave HMAC, ventana por mtime, adapters, converters, loaders, poblador) ya cableado e intocable.
Enganche automático: un make custom-start DRIVER=… (hermano de mitre-start/ctu-start) que corre el custom y arrastra su tráfico por las 3 lentes hasta el grafo.
Gate: make validate-driver que comprueba que el custom dejó los artefactos con el contrato correcto (bronce sellado, STAMP coherente, oro convertible, filas en Kuzu) y falla con mensaje si no — para que el investigador no dependa de Alonso para depurar.
Entregable narrado como cadena verificable: "tus invocaciones a $IFACE → estos CSV bronce → estos Parquet oro → este .kuzu → este SELECT → tu dataset con contrato de cabecera X, y X es así por esto y esto". Cada eslabón, un artefacto que el investigador ve aparecer.
DECIDIDO por Alonso: nivel 3 completo (plantilla + enganche + gate). MEDIR PRIMERO: cat de los dos drivers, extraer el contrato real antes de escribir una línea de la guía.

## Cierre del proyecto — lo que queda tras el README
1. README reescrito (B). 2. Overhaul pipeline-start/status (DEBT-PIPELINE-START-DISABLE-RAG-001,
   -BINARY-GUARD-001, -STATUS-ALL-VMS-001, -STATUS-LOGFILES-001; ver [[cierre-paper]]).
3. Repo en modo lectura. El pipeline multi-sensor + paper honesto YA está; esto es la cara pública.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO. Conjetura etiquetada como tal o no se dice.
  (DAY 252: la memoria decía argus ×18.5; el artefacto midió ×28.5. Mandó el fichero.)
- Fidelidad de reuso: scripts nuevos IMPORTAN canon()/loaders, no reimplementan. `load_csv()`
  de join_bias_labels.py es API pública (la importan bias_denominator_true.py y autopsy_67.py): NO cambiar su firma.
- Reproducibilidad = propiedad del repo: cada número del paper, generable por un `make`.
- Procedencia: el pcap Neris es de 2011, ajeno, condiciones desconocidas → declarar, no interpretar.
- Alonso pilota; mide contra fichero y pega salida. Alonso NO tiene str_replace: script completo.
- No `grep -rn` desde la raíz (arrastra build/.git/.venv): `git grep` o fichero concreto.
- sed de macOS/BSD: `sed -i ''`. arXiv compila el .tex del .zip; el .zip lleva main.tex+references.bib+main.bbl.

## Hilos de memoria
[[cierre-paper]] (agenda de cierre, tesis honesta, las 3 lentes) · [[join-bias-ground-truth]]
(la batalla del sesgo/denominador, artefacto-locked, la corrección ×28.5) · [[ctu-start]] (2º driver).