# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 249

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    git branch --show-current
    vagrant status
Tras DAY 248: `main` con `scripts/dataset_export.py` (A/B/C) + targets del Makefile (commit
`feat(dataset-export)...`). Si algo quedó sin commitear, ciérralo primero. VMs probablemente aborted.

## Estado que ordena el día — herramienta de datasets HECHA y validada; empieza el 2º traffic driver
- ✅ Pipeline multi-sensor en main, tag `pre-release-0.0.1` (DAY 247).
- ✅ `dataset_export.py` A/B/C (DAY 248). A = veredicto del ORO HMAC-sellado + topología del grafo
  (cross_sensor_corroborations, reuse_degree por `count(DISTINCT g)`). B = veredicto LEÍDO del grafo por
  event_id. C = validador del loader (diff ORO↔grafo por event_id, campo a campo del veredicto).
- ✅ 🟢🟢🟢 MODO C: **LOADER FIEL 4195/4195, 0 dropados, 0 mismatch** → el grafo es proyección
  bit-a-bit del ORO sellado. La garantía Vía Appia deja de ser afirmación y es NÚMERO reproducible por comando.
  Corolario medido: **B ≡ A** (no hay pérdida en la proyección). Tres CSV en `logs/datasets/` por `make`.
- ✅ Cuatro hallazgos medidos (corrida nmap -A `20260803-064544`, `dataset-modeA-*.csv`):
  (1) `overall_threat_score = 0.75` LITERAL en los 1089 MALICIOUS = flag disfrazado de score continuo;
  (2) `flow_start_sec = 0` ⟺ EXACTAMENTE los MALICIOUS/fast-alert (reloj localizado en esa ruta);
  (3) 43% de eventos argus con `authoritative_source = DETECTOR_SOURCE_DIVERGENCE` (el sistema discrepó de su ML);
  (4) `authoritative_source` polimórfico (argus = arbitraje; suricata/zeek = nombre del sensor).
- 🎯 REENCUADRE (Alonso, DAY 248): el entregable NO es "un dataset", es un **INSTRUMENTO reproducible que
  genera un dataset EN FUNCIÓN de un traffic driver** (script de la familia `mitre_start.sh`). Driver simple →
  dataset simple; driver sofisticado → dataset rico. Dos capas: (1) traffic driver [VARIABLE] |
  (2) downstream fijo bronce→oro→grafo→`dataset_export` [INVARIANTE, agnóstico del driver, ancla al STAMP].
  Terceros (alumnos de Andrés) podrían enchufar SU driver. Caveat honesto: el contrato driver↔harness es
  IMPLÍCITO hoy (`DEBT-DATASET-DRIVER-CONTRACT-001`) → el paper NO vende "plug-and-play", vende
  "demostramos 2 drivers y especificamos el contrato del tercero".

## Batalla candidata DAY 249 — el 2º traffic driver: replay del CTU (mide primero)
1. Es un HERMANO de `mitre_start.sh`, NO un modo de `dataset_export.py`. Mismo downstream, distinta fuente de
   tráfico: `tcpreplay` del pcap Neris del CTU-13 en vez de `nmap -A`. Target nuevo `ctu-start` (molde: [[mitre-start-repro]]).
2. MEDIR primero: ¿dónde está el pcap/traza del CTU en disco? ¿el driver puede reusar TODO el downstream de
   `mitre_start.sh` (curl clave viva → captura → converters → loaders → poblador) cambiando SOLO el generador de
   tráfico? Localizar el seam = primer paso de `DEBT-DATASET-DRIVER-CONTRACT-001`.
3. Correr → `dataset_export.py` A/B/C sobre esa corrida → segundo CSV + su validación C.
   Encuadre DAY 247 a respetar: el valor es caracterizar el SESGO de cada lente contra el ground-truth
   ETIQUETADO del CTU, NO "reproducimos el CTU".
4. Con los DOS datasets (nmap sintético + CTU etiquetado) → listos para las conclusiones del paper.

## Deudas nuevas DAY 248 (en BACKLOG, correlacionadas con tareas — BACKLOG↔PROMPT trazables)
`DEBT-OVERALL-SCORE-LITERAL-001` (overall=0.75 constante en MALICIOUS = binario disfrazado; FASE FIX / honestidad del paper) ·
`DEBT-DATASET-DRIVER-CONTRACT-001` (contrato traffic-driver↔harness implícito; nombrarlo → tarea ctu-start + sección del paper) ·
`DEBT-FLOWSTART-CLOCK-DOMAIN-001` (REFINADA: reloj 0 localizado 100% en ruta fast-alert) ·
`DEBT-DATASET-AUTHSOURCE-POLYMORPHIC-001` (vocabulario de authoritative_source cambia por sensor; documentar en la data card).

## Diferidas post-0.0.1 (apuntadas, NO bloqueantes)
DEBT-HMAC-KEY-INSECURE-TRANSPORT-001 · Vault productivo · rotación de claves · fault-injection real ·
DEBT-ENV-BOOTSTRAP-NOT-REPRODUCIBLE-001 · DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001 · DEBT-MITRE-START-WAZUH-REACT-001 ·
bugs menores del harness.

## Para el PAPER (cuando lleguen las conclusiones)
- La contribución = el INSTRUMENTO, no el dataset. Sección explícita: "la generación de datasets es función de
  un script de la familia mitre_start.sh"; documentar el CONTRATO del traffic driver para que terceros integren el suyo.
- Números honestos ya medidos: loader fiel 4195/4195 (Vía Appia); 0.75 literal; 43% divergencia de detectores;
  reloj 0 en fast-alert; Alert SOLO de argus (Suricata/Zeek = contexto, no veredicto). Corroboración cross-sensor
  real ~5% de las aristas (argus↔zeek domina; suricata = sensor de evento raro).
- Alcance declarado (no sobrevender): C valida el VEREDICTO, no la 5-tupla (no está en el grafo a propósito);
  una corrida por driver; tráfico nmap -A / CTU Neris, no el universo de ataques.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando/fichero. (DAY 248: me inventé un
  bug de coma/awk para no creer una salida sorprendente — la medición corrigió. No votar.)
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; grafo = proyección, AHORA certificada por modo C).
- Reproducibilidad = propiedad del repo: todo dato del paper, generable por un comando del Makefile.
- Grafo RED = fresco por medición. sed -i de macOS/BSD exige sufijo: `sed -i ''`.
- Alonso no tiene str_replace: entregar script completo o parcheador idempotente (ancla por texto).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Hilos de memoria: [[dashboard-export]] (herramienta A/B/C +
los 4 hallazgos + loader fiel), [[cierre-paper]] (tesis honesta + framing del instrumento), [[parquet-a-kuzu]]
(loader/consulta del grafo red), [[mitre-start-repro]] (el driver mitre = molde de ctu-start).