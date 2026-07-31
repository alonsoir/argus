# PROMPT DE CONTINUIDAD — aRGus NDR — DAY 241

## Punto de entrada (mide, no asumas)
    git log --oneline -6
    git status
    vagrant status
DAY 240 cerró el **paso 2 (medir + diseñar el contrato host_domain_v1)**. Rama `feat/zeek-to-graph`.
Lo primero al arrancar: confirmar que HEAD es **`5e5018ca`** ("added new host-domain-contract/
host_domain_v1-contract.md and .../evidencia/ files") — salvo que hayas metido por encima la limpieza
del `.gitignore` duplicado (ver deudas). Árbol limpio, pusheado. `git add` explícito (nunca `-a`/`-u`).
**NO mergear a main** (decisión DAY 237, reafirmada: no está integrado, hay que probar en esta rama
primero + EMECAS+++ verde). Las VMs probablemente `aborted` tras el sueño del host (o `poweroff` si
hiciste `vagrant halt`); se recuperan con `vagrant up NAME`.

## Estado que ordena el día — PASO 2 (diseño) CERRADO, empieza la Pieza 0
El contrato `host_domain_v1` está **diseñado, decidido y commiteado** (`5e5018ca`):
- **✅ Doc de diseño** en `docs/design/host-domain-contract/host_domain_v1-contract.md` (puerta-multisensor,
  cada afirmación [MEDIDO]/[DECISIÓN]/[PENDIENTE]) + snapshot de evidencia `evidencia/alerts-day240-snapshot.json`.
- **✅ Decisiones firmes** (Alonso, DAY 240): `event_id` = **hash de la línea cruda** (`"wz1:" +
  base64(BLAKE2b-256("argus-hostevent-v1" ‖ raw_line))`, idempotente por fichero) · PK del nodo `Host`
  = **`agent.id`** · modelo de 4 nodos (Host, HostEvent, Rule, MitreTechnique; Control opcional) ·
  identidad del evento = host + regla + timestamp, NO 5-tupla.
- **✅ P5 y P3 resueltas por precedente medido**: los adapters de red (suricata/zeek) producen **bronce
  y paran** (0 `parquet`/`gold` en sus dirs); el bronze→gold→Kuzu vive aguas abajo. ⇒ **el host es
  hermano fiel**: `wazuh-adapter` emitirá `host_domain_v1` **bronce sellado en CSV** (HMAC vía
  `serialize()`), NO carga directo. El detalle vive en [[host-domain-contract]].

## Candidato de batalla DAY 241 (Alonso decide el corte midiendo)
**Pieza 0 — crear `libs/host-domain-v1/`**, la biblioteca del contrato (mirror de `libs/correlation-v1`).
OJO al matiz medido DAY 240: los adapters de red enlazan `correlation-v1` que YA EXISTE y su `to_row`
es espejo de un oráculo (`ml-detector/src/correlation_writer.cpp`). Para host **no hay lib ni oráculo**
— `alerts.json` es la única fuente, así que **esta lib ES la definición primaria** del contrato. Orden
sugerido (medir la plantilla antes de escribir):
1. **Medir `libs/correlation-v1`** como plantilla: `git ls-files libs/correlation-v1/` + leer la API
   pública (el `Row`, `validate()`, `serialize()` con el HMAC como última columna, el formato CSV, los
   vectores/tests congelados). NO reinventar la forma; copiarla.
2. **Definir el `Row` de `host_domain_v1`** con los campos del doc §5 (schema_version, source_sensor,
   event_id, host_id, hmac_row + los copiados de Wazuh: timestamp, agent_*, os_hostname, rule_*,
   decoder, location, full_log, data_json + comunes, mitre_*, cumplimiento). `event_id` lo acuña la lib
   (hash de línea cruda), `hmac_row` lo sella `serialize()`.
3. **`validate()` + `serialize()` + vectores congelados** propios de host (BLAKE2b/base64 como flow_uid;
   golden byte-idéntico contra referencia Python, mismo patrón que correlation-v1).
   Entregable probable del día: `libs/host-domain-v1/` compilando con sus tests verdes; cada decisión de
   formato marcada [MEDIDO]/[DECISIÓN]/[PENDIENTE]. **NO el adapter todavía** (Pieza 1, batalla siguiente).

**Primera micro-decisión del día** (barata, fíjala midiendo el coste): clave HMAC del ledger host —
¿la MISMA que la red (`ARGUS_BRONZE_HMAC_KEY_HEX`) o una PROPIA (`ARGUS_HOST_HMAC_KEY_HEX`)? Como el
ledger y el loader host son separados, una clave propia AÍSLA mejor; es la inclinación, a confirmar.

## Invariantes (no negociar)
- Medir, no votar. HECHO ≠ SOSPECHADO; cada afirmación a salida de comando / fichero.
- Un día, una batalla. Vía Appia (el oro/bronce es la fuente de verdad, el grafo es proyección
  reconstruible). A horas malas, parar.
- No `grep -rn` desde raíz (usa `git grep` o apunta al fichero/dir). No encadenar salidas grandes.
  `git add` explícito. Build/commit/push desde el host. macOS: nunca `sed -i` sin `-e ''`.
- **Wazuh = HOST-DOMAIN, NO red.** Su bronce/oro/grafo van a SU PROPIA BD Kuzu, NUNCA al `$KUZU`
  compartido de red. Contrato `host_domain_v1` separado de correlation_v1.
- **El host es hermano fiel de suricata/zeek**: el adapter produce bronce sellado (CSV) y para; el
  bronze→gold→Kuzu es aguas abajo. La lib de contrato NO reimplementa nada ajeno; es la definición host.
- **El dato de host_domain_v1 debe nacer de `destroy&up` + MITRE**, no de toques a mano (el snapshot de
  DAY 240 es dato de DISEÑO, no evidencia del paper).
- **SIN merge a main** hasta probar en esta rama + EMECAS+++ verde.

## Deudas vivas (registradas, no urgentes)
- `.gitignore`: el bloque `!provisioning/wazuh/*.deb` está DUPLICADO (dos commits idénticos DAY 240,
  `334898fe` + `0eb2565f`) → regla de negación repetida, inocua; limpiar con una línea suelta cuando quieras.
- DEBT-HOST-DOMAIN-P1: FIM/SCA/rootcheck NO se han observado (el baseline de Wazuh es auth/sesión). Se
  provocan con técnica MITRE host-touching en `mitre-start` (paso 3); ahí se mide su forma de `data` y
  se amplía el contrato. Sin eso, el grafo host solo muestra higiene de auth, no "Wazuh cazó el ataque".
- DEBT-HOST-DOMAIN-P2: rotación de `alerts.json` en el watermark/offset del adapter (batalla Pieza 1).
- DEBT-WAZUH-AGENT-INSTALL-ORDER-001: en destroy&up-desde-cero el manager (wazuh, autostart:false) debe
  estar arriba antes que los agentes; el orden no lo garantiza el Vagrantfile (relevante para EMECAS+++).
- authd abierto (enrollment sin contraseña) → `authd.pass`. Familia "dev, no producción", P2/P3.

## Recordatorio de tono
Alonso pilota; mide contra fichero y pega salida. Rama `feat/zeek-to-graph`, sin merge a main. Hilos de
memoria: [[host-domain-contract]] (contrato host, diseño cerrado DAY 240 — leer primero), [[wazuh-host-domain]]
(Wazuh/host-domain, A cerrada), [[contrato-multisensor]] (contrato de red = plantilla de la lib host),
[[cierre-paper]] (criterios de cierre y roadmap del paper honesto).