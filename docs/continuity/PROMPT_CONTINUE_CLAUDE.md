# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 246

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
HEAD = commit de cierre Pieza 3 (DAY 245) + PROMPT/BACKLOG en feat/zeek-to-graph, árbol
limpio. SIN merge a main. Untracked benigno: build-hostfile.sh, create_wazuh_adapter_skeleton.py,
verify_host_gold.py (scratch). VMs probablemente aborted tras el sueño del host.

## Estado que ordena el día — circuito host COMPLETO, falta integrarlo en el gate
- ✅ Piezas 0/1/2/3 CERRADAS. El grafo host EXISTE, medido en la BD (no self-report):
  Host=1, HostEvent=533, Rule=14, MitreTechnique=3; T1548.003 desde 5402+5403 en UN solo
  nodo (dedup), 5715 → T1078+T1021 con Lateral Movement literal en tactics.
- ✅ Circuito host de punta a punta e ISLA: alerts.json → bronce (wazuh-adapter) → oro
  Parquet (host-engine converter) → grafo Kuzu (host_parquet_to_kuzu_loader), su propia BD,
  NUNCA el $KUZU de red. Loader con self-mkdir (cierra la fragilidad DAY 228).
- 🔴 LO QUE FALTA: host-engine (converter + loader + test) NO está en el Makefile ni en
  EMECAS+++. Se compila a mano. Ese es el gate antes del PR a main.

## Batalla candidata DAY 246 — EMECAS+++ con host (DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001)
Objetivo: cablear la isla host-engine en el Makefile y en el gate; host verde en EMECAS+++.
1. MEDIR PRIMERO (no asumir): targets actuales del Makefile raíz —
   `git grep -n 'host-domain-v1\|pipeline-build\|mitre-start\|emecas' -- Makefile` — y cómo
   se enganchan las libs (patrón host-domain-v1-build/test de Pieza 0) y cómo mitre-start
   invoca converter+loader de red.
2. Targets nuevos: `host-engine-build` (vagrant ssh defender → cmake Release + make),
   `host-engine-test` (: host-engine-build → ctest = test_host_row). Enganchados al grupo de
   build/test que corresponda, no sueltos.
3. Una tarea reproducible que lleve alerts.json → bronce → oro → grafo host de una corrida
   (equivalente host de mitre-start; o `host-graph-start`), para que el dato del grafo host
   sea generable desde el Makefile (criterio de cierre).
4. CIERRE con dientes: EMECAS+++ verde CON host en esta rama; los recuentos del grafo host
   salen de una tarea, no de comandos a mano.

## Arco después (una batalla por sesión) — refinamiento DAY 245
- etcd-client en los adapters ANTES del PR a main (adelanta la migración de secretos que el
  roadmap ponía post-main): que traigan la clave HMAC de etcd/Jenkins/Vault en vez de leer
  ruta/clave del JSON o usar TOY_KEY. Hipótesis: CMakeLists + poco código en el main. MEDIR
  el coste real antes de prometer que es pequeño.
- Automatizar aguas abajo: meter los adapters en `pipeline-start` y que aparezcan en
  `pipeline-status`; enriquecer `pipeline-status` con más info (ficheros de log actuales para
  `tail` rápido).
- mitre-start reacciona a Wazuh (DEBT-MITRE-START-WAZUH-REACT-001).
- EMECAS+++ estable con host + etcd-client probado → PR a main. Resto de migración de
  secretos (vault-client HTTPS, rotación) post-main.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando / fichero.
- Un día, una batalla. Vía Appia (bronce/oro = fuente de verdad; el grafo es proyección).
- Circuito host = ISLA: bronce/oro/grafo/loader/BD propios, corren en defender. NUNCA $KUZU red.
- No `grep -rn` desde raíz (git grep o apunta al fichero). No encadenar salidas grandes.
  git add explícito.
- SIN merge a main hasta EMECAS+++ verde con host en esta rama.
- Trazabilidad: cada tarea cita su deuda del BACKLOG (BACKLOG↔PROMPT).

## Deudas vivas (en docs/BACKLOG.md)
DEBT-HOST-DOMAIN-EMECAS-INTEGRATION-001 (batalla de hoy) ·
DEBT-HOST-LOADER-CYPHER-INTERPOLATION-001 · DEBT-HOST-LOADER-SCHEMA-VALIDATION-001 ·
DEBT-MITRE-START-WAZUH-REACT-001 · DEBT-ADAPTER-AUTOMATION-DOWNSTREAM-001 (etcd-client, ahora
pre-main) · DEBT-PIPELINE-STATUS-LOGFILES-001 · DEBT-HOST-DOMAIN-P1 (Wazuh caza el ataque, no
higiene) · DEBT-HOST-DOMAIN-P2 (watermark inode,offset).

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Compilación DENTRO de la VM (defender para
host-engine). Rama feat/zeek-to-graph, sin merge a main. Hilos de memoria: [[host-a-kuzu]]
(Pieza 3 + grafo host), [[host-gold-converter]] (Pieza 2), [[emecas-vagrant]] (gate +
Vagrantfile), [[hmac-secrets-provisioning]] (etcd-client/secretos), [[cierre-paper]] (roadmap).