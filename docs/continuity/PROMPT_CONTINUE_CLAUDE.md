# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 245

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
HEAD = commits de cierre DAY 244 (permisos + Pieza 2) en feat/zeek-to-graph, árbol limpio.
SIN merge a main. Untracked benigno: create_wazuh_adapter_skeleton.py, verify_host_gold.py
(scratch, no entregables). VMs probablemente aborted tras el sueño del host.

## Estado que ordena el día — Piezas 0,1,2 CERRADAS; el oro host ya EXISTE y es fiel
- ✅ Pieza 0 libs/host-domain-v1/ — contrato bronce 34 cols, verde en test-libs.
- ✅ Pieza 1 wazuh-adapter/ — alerts.json → bronce host_domain_v1 sellado.
- ✅ DEBT-HOST-ADAPTER-ALERTS-PERMS-001 (DAY 244) — permisos cableados en el Vagrantfile;
  bronce host REAL reproducible desde destroy&up en frío, cero pasos manuales.
- ✅ Pieza 2 host-engine/ (DAY 244) — converter bronce CSV → oro Parquet (isla:
  arrow+parquet+OpenSSL, sin correlation_engine). Verde en defender: 533/533, puerta HMAC
  C++ (2ª impl independiente), oro Parquet 34 cols releído con pyarrow (rule_level int32,
  hmac_row, T1548.003 intacto). El oro host es proyección FIEL del bronce; las 10 listas
  van como string JSON (opción a — el re-modelado a aristas es de HOY).

## Batalla candidata DAY 245 — Pieza 3 (DEBT-HOST-PIEZA-3-KUZU-001): el grafo host REAL
Objetivo: oro host Parquet → Kuzu en SU PROPIA BD (nunca el $KUZU de red). Es el último
eslabón: el grafo host deja de ser diseño y pasa a existir.
1. MEDIR PRIMERO (no asumir el template): el loader de red es
   `correlation-engine/tools/parquet_to_kuzu_loader.cpp` + `KuzuGraphSink`. Medir su
   interfaz — ¿KuzuGraphSink se reusa parametrizado (ruta de BD + esquema) o es
   correlation-específico? El grafo host tiene nodos DISTINTOS (Host/HostEvent/Rule/
   MitreTechnique + Control opcional, doc de diseño DAY 240) → muy probablemente el host
   necesita su PROPIO loader + DDL, isla en host-engine/tools/, no un parámetro del de red.
   `git grep -n 'class KuzuGraphSink\|CREATE NODE\|CREATE REL' -- correlation-engine/`
2. DDL Kuzu de los 4 nodos + aristas (del doc host_domain_v1-contract.md §nodos): Host
   (PK agent.id), HostEvent (PK event_id wz1:), Rule, MitreTechnique; aristas HostEvent→Host,
   HostEvent→Rule, Rule→MitreTechnique (las 10 listas JSON del oro se DESPLIEGAN aquí en
   aristas, es su sitio). BD host separada, nunca $KUZU.
3. CIERRE con dientes: loader lee el Parquet oro de hoy → Kuzu host → `MATCH` confirma
   N nodos Host (=host_id distintos), N HostEvent (=533), y ≥1 arista Rule→MitreTechnique
   T1548.003 desde una fila 5403. Medido en la BD, no self-report.

## Arco después (una batalla por sesión)
- mitre-start reacciona a Wazuh (DEBT-MITRE-START-WAZUH-REACT-001): que una corrida
  arrastre alerts.json → bronce → oro → grafo host, automático.
- EMECAS+++ con host verde en esta rama (DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001) → PR a main.
- Post-main: migración de secretos (DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001): vault-client
  HTTPS, etcd-client liveness, rotación con solape.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando / fichero.
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; el grafo es proyección).
- Circuito host = ISLA: bronce/oro/grafo/loader/BD propios. host-engine standalone, corre
  en defender. NUNCA el $KUZU de red.
- No `grep -rn` desde raíz (git grep o apunta al fichero). No encadenar salidas grandes.
  git add explícito.
- SIN merge a main hasta EMECAS+++ verde con host en esta rama.
- Trazabilidad: cada tarea cita su deuda del BACKLOG (BACKLOG↔PROMPT).

## Deudas vivas (en docs/BACKLOG.md)
DEBT-HOST-PIEZA-3-KUZU-001 (batalla de hoy) · DEBT-MITRE-START-WAZUH-REACT-001 ·
DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001 · DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001 ·
DEBT-HOST-DOMAIN-P1 (host-touching: Wazuh caza el ataque, no actividad ordinaria) ·
DEBT-HOST-DOMAIN-P2 (watermark inode,offset en el adapter).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Compilación DENTRO de la VM (defender
para host-engine). Rama feat/zeek-to-graph, sin merge a main. Hilos de memoria:
[[host-gold-converter]] (Pieza 2 + build), [[host-domain-contract]] (contrato + nodos del
grafo), [[parquet-a-kuzu]] (loader de red como template), [[wazuh-host-domain]], [[cierre-paper]].