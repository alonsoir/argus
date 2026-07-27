# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 234

## Punto de entrada (mide, no asumas)
    git log --oneline -6 main
    vagrant status          # el stack se paró al cerrar DAY 233 (make pipeline-stop)
Tras DAY 233: día de MEDICIÓN, sin código nuevo. Commits solo docs
(este prompt + BACKLOG). Artefactos del día bajo /vagrant/logs/ (ignorado):
oros argus-A.parquet / suricata-A.parquet y la BD logs/day233-kuzu/mitre.kuzu.

## El estado que ordena el día
**Paso 2 del cierre CERRADO (DAY 233).** MITRE → grafo por los dos sensores,
con dato FRESCO (no el Neris de 2011):
- nmap -sS NO disparó ET Open (52.058 reglas cargadas → cobertura ciega a un
  SYN scan; PÁGINA DE PAPER). hydra descartado (ssh de defender key-only).
  **nmap -A SÍ disparó** (ET SCAN Nmap User-Agent en 8080/Jenkins).
- aRGus capturó (2a: 2.625 filas oro) + Suricata alertó (48 alert → oro).
- Los dos oros a una Kuzu fresca (loader ×2, NO verifica HMAC → conviven la
  clave real de aRGus y la de juguete de Suricata) → poblador CORRELATES_FLOW.
- MEDIDO: **44 community_id corroborados cross-sensor**, **253 aristas** de
  observación, invariante (cids distintos en extremos) = **0**, ambos sensores
  TelemetryEvent (Reading A).
- Números honestos para el paper: 44 flujos corroborados (titular); 253 =
  pares de observación, NO 44... digo NO "253 flujos".

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando.
- Join SIEMPRE por community_id, nunca por flow_uid.
- Un día, una batalla. Via Appia (un criterio que no puede ponerse rojo no mide).
- No `grep -rn` desde raíz (usa `git grep`). No encadenar salidas grandes.
  `git add` explícito por fichero. A horas malas, parar.

## Candidatos de batalla DAY 234 (decide Alonso)
- **A — Reproducibilidad (recomendado).** El resultado de DAY 233 se construyó
  A MANO; el criterio de cierre exige que TODO dato sea generable por tareas del
  Makefile. Convertir el recorrido de hoy (up → pipeline-start → clave del REST →
  nmap -A → adapters → converters → loader ×2 → poblador → consultas) en un target
  reproducible. Sin esto, el titular del paper no es "reproducible", es anecdótico.
- **B — Paso 4: el paper.** Empezar a redactar con los números de hoy + el
  hallazgo ET Open (52k reglas ciegas a -sS, sí a -A). Verificar citas
  (Sommer & Paxson, Arp et al.) ANTES de usarlas.
- **C — D4 / alcance.** Traer el 98,7% de Suricata (dns/http/tls) al grafo, o
  el zeek-adapter, o imagen vulnerable (paso B, cadenas de ataque reales).

## Deudas afloradas DAY 233 (registrar en docs/BACKLOG.md)
- **DEBT-EVENT-ID-COLLISION-001** (NUEVA): argus 2.625 filas bronce → 1.522
  TelemetryEvent. El event_id = timestamp_(src^dst) colisiona bajo carga de scan
  (mismo segundo + mismo XOR). No toca la correlación (va por community_id), sí
  la cardinalidad de eventos. Data-quality.
- **window sin bucket** (ADR-052 §3.1.4 nunca implementado): window a microsegundo
  → cada sensor registra una conversación como varios NetworkFlow → 37/44 cids
  dan 253 aristas. Es la causa de la "inflación" de aristas. Ligada a
  DEBT-FLOWSTART-CLOCK-DOMAIN-001 y a node_id por-sensor (§3.1.2), aún pendientes
  de registrar reencuadradas desde DAY 232.

## Notas de fontanería DAY 233 (medidas, no re-medir)
- Clave HMAC del bronce de aRGus: la LEE el etcd-server, no Vault.
  `curl -s http://localhost:2379/secrets/ml-detector` (campo `key`, 64 hex) con el
  stack arriba. NO `etcdctl` (sirve HTTP plano en :2379, no KV). Efímera: no parar
  el pipeline entre firmar bronce y convertir.
- suricata-adapter: binario en `build-suricata/suricata_adapter` (guion bajo);
  CLI posicional `<config.json>`, sin --help; alert-only (D4). Firma con
  ARGUS_BRONZE_HMAC_KEY_HEX (juguete 0123456789abcdef×4 vale para Suricata).
- Poblador y consultas cross-sensor: en [[mitre-ataque]] de la memoria.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. `make pipeline-stop` al cerrar.