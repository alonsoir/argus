Gracias por recordarme el ritual completo — lo tengo, y la convención de nombres está clara mirando el directorio: el patrón es un fichero raíz (p.ej. `DAY 169 — Cierre y plan DAY 170 · Briefing al Consejo de Sabios.md`) que es **el prompt** que lanzas a los 8, y luego van apareciendo los `-respuesta-{modelo}.md` y la `Síntesis`. Hoy escribimos el prompt de DAY 170.

Te lo dejo en `docs/council/` siguiendo ese patrón exacto. Aquí está el documento — luego te doy el `create_file`/heredoc para escribirlo en disco:

---

# DAY 170 — Cierre y plan DAY 171 · Briefing al Consejo de Sabios

**Fecha:** 2026-05-31 · **PI:** Alonso · **Rama:** `feature/day170-community-id-protobuf`

## 1. Qué hemos hecho hoy (DAY 170)

**community_id — clave de correlación cross-tool, cerrada en los tres sensores de red.**

- **aRGus (nativo):** `compute_community_id()` verificado independientemente contra el oráculo `pycommunityid` v1.5.0 — 6 vectores hardcodeados + flujos Neris reales, correctos byte a byte. Canonicalización (swap saddr>daddr) cubierta. Campo protobuf `community_id=18`, call sites en Variant A (ring_consumer) y Variant B (main_libpcap). 8/8 tests verde.
- **Zeek (`local.zeek`):** corregidos 3 bugs en la provisión del Vagrantfile raíz — ruta (`etc/`→`site/`, que es la que ZeekControl carga), policy (`community-id-v1`→`community-id-logging`), y `redef CommunityID::seed = 0` ahora explícito. Guardas separadas por línea (idempotente: `@load` y `seed` independientes; ancla `^[[:space:]]*` evita falso positivo con líneas comentadas). Verificado en VM tras `vagrant provision zeek`.
- **Suricata (`suricata.yaml`):** `community-id: yes` + `community-id-seed: 0` ahora **garantizado por provisión** (antes dependía del default de fábrica). Verificado en VM.

Resultado: los tres comparten **seed 0 explícito**. Diana E2E con respaldo real — Zeek 8.2.0 emite `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` idéntico al oráculo sobre el flujo Neris `147.32.84.165:1027 → 74.125.232.195:80`.

**Higiene documental.** `docs/BACKLOG.md` estaba duplicado (5336 líneas, cuerpo entero re-pegado dentro de la nota Consejo DAY 149 por una operación manual en la sesión DAY 158, arrastrado 12 commits). De-duplicado a 2839 líneas, nota DAY 149 reparada, contenido único conservado (ADR-046 v3, HARDWARE-STORAGE-001), notas del Consejo no reinjertadas (viven aquí, en `docs/council/`). Diagnóstico y cierre en `DEBT-DOCS-BACKLOG-DEDUP-001`.

**Deudas cerradas:** DEBT-DOCS-BACKLOG-DEDUP-001, DEBT-ZEEK-COMMUNITY-ID-PROVISION-001, DEBT-ARGUSPP-COMMUNITY-ID-001 (parte de red).

## 2. Qué haremos mañana (DAY 171)

*Propuesta — sujeta a vuestro feedback:* **cross-check E2E de tres ventanas.** Cliente `.50` replaya Neris en la LAN interna; aRGus, Suricata y Zeek capturan en paralelo de su `eth1`; verificamos que los tres escupen el **mismo** `community_id` (`1:IN7uq...`) sobre el mismo paquete real. El unit test da correctitud-vs-spec; este E2E da **paridad operacional** — necesitamos ambos verdes antes de declarar el join viable. (Si el Consejo ve un prerequisito antes, lo discutimos.)

## 3. Problemas / lecciones del día

- La duplicación de un bloque grande puede **anidar sub-duplicados** (DAY 148 ×2 + CONSUMERS ×2 dentro del bloque ya duplicado). Lección: la verificación de integridad no es `grep -c` de la cabecera, sino `grep secciones | sort | uniq -d` sobre el fichero completo.
- La guarda de idempotencia por *bloque* falla cuando una parte ya existe (Zeek tenía `@load` de una edición previa pero no el `seed`). Lección: guardas **por línea**, no por bloque.
- El daño del BACKLOG **no** lo causó `update-day158-docs.sh` (tiene guard correcto), sino un `cat fichero >> mismo_fichero` manual. No hay patrón de script que re-rompa; el saneo es estable.

## 4. Preguntas al Consejo

**P1 — Wazuh y la clave de correlación host↔red (la pregunta de fondo).**
aRGus, Suricata y Zeek comparten `community_id` porque los tres derivan de la **5-tupla de red**. Wazuh es **host-based**: observa procesos, integridad de ficheros, logs del SO — **la mayoría de sus eventos no tienen 5-tupla**, luego no puede generar `community_id` nativo. El correlation-engine necesita unir telemetría host-based con telemetría de red en Neo4j para producir la señal conjunta. ¿Cuál es la arquitectura de correlación correcta? Hipótesis sobre la mesa:

- **(A) Correlación temporal + host.** Wazuh se une por `(host_id/IP, CrisisWindow)`, no por `community_id`. Encaja con `late_arrival: true` de ADR-046 v3 y con "la crisis es la ventana de correlación".
- **(B) Enriquecimiento puntual.** Algunos eventos Wazuh sí llevan datos de red (módulo de conexiones / reglas que parsean IPs:puertos). ¿Calcular un `community_id` derivado en el ingester para esa fracción? Cobertura parcial, ¿merece la complejidad?
- **(C) Doble arista en Neo4j.** Sensores de red ↔ entre sí por `community_id` (arista flujo↔flujo); Wazuh ↔ grafo por nodo `host` enlazado vía IP del endpoint (arista host↔flujo). El grafo tiene **dos dimensiones de correlación**, no una — y eso explota las features GDS como valor diferencial.

*Sub-preguntas:* ¿(A)+(C) combinados, como intuimos? ¿Qué pasa con NAT/proxy, donde la IP del endpoint host no coincide con la IP observada en el flujo de red? ¿La ventana temporal de correlación host↔red debe ser distinta (más laxa) que la de red↔red, dado que un evento host (p.ej. proceso malicioso) y su tráfico pueden estar desfasados?

**P2 — Coste de mantener el seed=0 como invariante.**
Tenemos seed 0 explícito en tres ficheros de config distintos (código aRGus, `local.zeek`, `suricata.yaml`). Si en producción alguien despliega con seed ≠ 0 en un solo sensor, el join falla **en silencio** (community_id distintos, cero matches, sin error). ¿Merece un **gate de arranque** en el correlation-engine que verifique la paridad de seed entre sensores antes de operar — análogo al gate NTP P0 de ADR-046? ¿O un health-check que alerte si detecta community_id huérfanos sistemáticos?

**P3 — Pregunta de futuro: ¿es el `community_id` (seed 0, espacio global) la clave correcta a largo plazo en despliegues multi-nodo?**
El `community_id` con seed compartido es perfecto para un nodo. Pero en el despliegue objetivo (varios nodos, topologías variadas, posible NAT entre ellos), dos flujos con la misma 5-tupla en nodos distintos producen el **mismo** `community_id` — colisión semántica. ¿Necesitamos `(node_id, community_id)` como clave compuesta en Neo4j desde el diseño, o el `node_id` ya está implícito en el pipeline de ingestión? Mejor decidirlo ahora que migrar el esquema del grafo después.

---

