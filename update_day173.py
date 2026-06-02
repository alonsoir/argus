#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_day173.py — Actualiza README.md, docs/BACKLOG.md y docs/continuity/PROMPT_CONTINUE_CLAUDE.md
para reflejar la RATIFICACIÓN de ADR-052 v3.2 (Consejo 8/8, DAY 173), sus DEBTs P0->P3 de identidad
de flujo, el stub ADR-053 y el estado de ADR-050 (pendiente). Coherente entre los tres ficheros.

Diseño:
  - Inserción por ANCLAS DE TEXTO EXISTENTES (tolerante a espacios finales). No usa números de línea.
  - IDEMPOTENTE: cada operación lleva un centinela; si ya está aplicada, se omite.
  - SEGURO: copia de seguridad .bak.<timestamp> antes de tocar nada. Si falta un ancla, ABORTA
    sin escribir (ningún fichero queda a medias).
  - DRY-RUN por defecto. Para escribir de verdad: --apply.

Uso (desde la raíz del repo, p.ej. test-zeromq-docker/):
  python3 update_day173.py            # dry-run: informa qué haría y si encuentra todas las anclas
  python3 update_day173.py --apply    # aplica los cambios (crea .bak de cada fichero)

Rutas por defecto (relativas). Override con flags si hiciera falta:
  --readme README.md  --backlog docs/BACKLOG.md  --prompt docs/continuity/PROMPT_CONTINUE_CLAUDE.md
"""

import argparse
import datetime as _dt
import os
import shutil
import sys

# ──────────────────────────────────────────────────────────────────────────────
# Utilidades de anclas (tolerantes a espacios finales)
# ──────────────────────────────────────────────────────────────────────────────

class AnchorError(Exception):
    pass


def _find_line_idx(lines, anchor_substr, occurrence=1):
    """Devuelve el índice de la línea cuya forma .rstrip() CONTIENE anchor_substr.
    occurrence=1 -> primera coincidencia. Lanza AnchorError si no se encuentra."""
    seen = 0
    for i, ln in enumerate(lines):
        if anchor_substr in ln.rstrip("\n").rstrip():
            seen += 1
            if seen == occurrence:
                return i
    raise AnchorError(f"ancla no encontrada (occurrence={occurrence}): {anchor_substr!r}")


def _has(text, sentinel):
    return sentinel in text


# ──────────────────────────────────────────────────────────────────────────────
# Operaciones
# ──────────────────────────────────────────────────────────────────────────────

def op_replace_first_line_containing(text, anchor_substr, new_line):
    """Reemplaza la PRIMERA línea que contiene anchor_substr por new_line (sin \\n final extra)."""
    lines = text.split("\n")
    idx = _find_line_idx(lines, anchor_substr)
    lines[idx] = new_line
    return "\n".join(lines)


def op_insert_before_line_containing(text, anchor_substr, block):
    lines = text.split("\n")
    idx = _find_line_idx(lines, anchor_substr)
    block_lines = block.split("\n")
    lines[idx:idx] = block_lines
    return "\n".join(lines)


def op_insert_after_line_containing(text, anchor_substr, block):
    lines = text.split("\n")
    idx = _find_line_idx(lines, anchor_substr)
    block_lines = block.split("\n")
    lines[idx + 1:idx + 1] = block_lines
    return "\n".join(lines)


def op_replace_between_markers(text, start_marker, end_marker, new_inner):
    """Reemplaza el contenido ENTRE dos líneas marcador (exclusivas) por new_inner."""
    lines = text.split("\n")
    s = _find_line_idx(lines, start_marker)
    e = _find_line_idx(lines, end_marker)
    if e <= s:
        raise AnchorError(f"marcador final {end_marker!r} antes que inicial {start_marker!r}")
    new_lines = new_inner.split("\n")
    lines[s + 1:e] = new_lines
    return "\n".join(lines)


def op_replace_block(text, anchor_first_substr, anchor_last_substr, new_block):
    """Reemplaza desde la línea que contiene anchor_first_substr hasta la que contiene
    anchor_last_substr (ambas inclusive) por new_block."""
    lines = text.split("\n")
    s = _find_line_idx(lines, anchor_first_substr)
    e = _find_line_idx(lines, anchor_last_substr)
    if e < s:
        raise AnchorError(
            f"orden de anclas inválido: {anchor_first_substr!r} .. {anchor_last_substr!r}")
    new_lines = new_block.split("\n")
    lines[s:e + 1] = new_lines
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# CONTENIDO NUEVO
# ──────────────────────────────────────────────────────────────────────────────

TODAY = "2026-06-02"

# ===== README: tabla DAY-STATUS (reemplaza el interior entre marcadores) =====
README_DAYSTATUS = """| Campo | Valor |
|---|---|
| DAY | 173 |
| Tag | v1.0.0-day166 |
| Branch | feature/day170-community-id-protobuf |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ✅ VERDE — 3 actos + Jenkins gate (DAY 167) |
| Pipeline | 6/6 RUNNING |
| NTP/chrony | ✅ DEBT-ARGUSPP-NTP-001 — health-check rechaza offset >1s (DAY 167) |
| correlation-engine | 🟡 scaffold ADR-048 F2 (DAY 167) |
| Multi-VM | ✅ Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24 (DAY 168) |
| community_id | ✅ paridad OPERACIONAL cross-sensor — cross-check E2E reproducible (DAY 171/172) |
| Arquitectura | ✅ ADR-046 v4 + AdapterSpec v1 · ✅ ADR-052 v3.2 RATIFICADA (8/8 DAY 173) · ⏳ ADR-050 (MITRE) + ADR-053 (JA3/JA4/BGP) + ADR-051 (Seed Parity) pendientes |
| Próximo hito | DEBTs P0 identidad de flujo (NODEID + FLOWUID + NEO4J-FLOW-KEY) + ADR-051 borrador |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |"""

# ===== README: bloque de hitos DAY 173 (insert antes de "### Hitos DAY 171") =====
README_HITOS_173 = """### Hitos DAY 173 🏛️
- **ADR-052 v3.2 RATIFICADA — Consejo 8/8.** Multi-node Flow Identity & Host↔Net Correlation. Confirmación de fidelidad unánime, sin tercera deliberación. Principio ordenador §0: *"El grafo no es el producto. El producto es el corpus."* `flow_uid = base64(BLAKE2b(node_id ‖ community_id ‖ flow_start_window [‖ seq_in_window]))`; `node_id` = string legible declarado en inventario firmado (NO derivado del keypair efímero); `community_id` = clave de correlación, nunca identidad. Dos anulaciones de árbitro: hash anclado a libsodium (§3.1.1) y señales TCP/TLS de host dentro del ADR (§3.11). Entregable `ADR-052_v3.2.md`. **Desbloquea `DEBT-NEO4J-FLOW-KEY-001`.**
  - **DEBTs de identidad de flujo registradas (orden de dependencia P0→P3):** P0 `DEBT-NODEID-CRYPTO-IDENTITY-001` (reescrita) + `DEBT-FLOWUID-CANONICAL-ENCODING-001` + `DEBT-NEO4J-FLOW-KEY-001`; P1 `DEBT-SENSOR-COVERAGE-MAP-001` / `DEBT-LABEL-WAL-001` (hash-chain) / `DEBT-ARGUSPP-ARP-MONITOR-001` / `DEBT-ARGUSPP-HOST-TCP-001`; P2 `DEBT-CERT-EXPECTATION-STORE-001` / `DEBT-SEQWINDOW-PERSIST-001` / `DEBT-ARGUSPP-OOB-MITM-001` / `DEBT-CORPUS-QUALITY-METRICS-001`; P3 `DEBT-ARCH-FLOW-OBSERVATION-001`.
  - **ADR-053 stub abierto** — JA3/JA4, cadena TLS profunda, anomalía de ruta L3/BGP (diferido conscientemente de ADR-052 para evitar scope creep). **ADR-050 (MITRE) y ADR-051 (Seed Parity Gate) siguen pendientes de redacción.**
"""

# ===== README: línea de milestone DAY 173 (insert tras "🔜 DAY 172:") =====
README_MILESTONE_173 = "  - ✅ DAY 173: **ADR-052 v3.2 RATIFICADA (Consejo 8/8)** — Multi-node Flow Identity & Host↔Net · DEBTs P0→P3 de identidad de flujo · ADR-053 stub (JA3/JA4/BGP) · desbloquea DEBT-NEO4J-FLOW-KEY-001 🏛️"

# ===== BACKLOG: línea "Última actualización" =====
BACKLOG_FECHA_NUEVA = f"*Última actualización: DAY 173 — {TODAY}*"

# ===== BACKLOG: sección consolidada DAY 173 (insert antes de "## ✅ CERRADO DAY 171") =====
BACKLOG_SECCION_173 = """## ✅ RATIFICADO DAY 173 — ADR-052 v3.2 (Consejo 8/8) + DEBTs de identidad de flujo

### ADR-052 v3.2 — Multi-node Flow Identity & Host↔Net Correlation — RATIFICADA Y CERRADA
- **Status:** ✅ RATIFICADA 8/8 DAY 173 — confirmación de fidelidad sin reservas, sin 3ª deliberación.
- **Evolución:** v1→v2 (misión §0, Q1–Q7, node_id) → v3 (bug N1 `node_id ≠ SHA256(pubkey)`, `seq_in_window` transportado, WAL externo, hash anclado a libsodium, event time, TCP/TLS dentro por anulación de árbitro) → v3.1 (4 auto-correcciones C1–C4) → **v3.2** (3 retoques de cierre R1–R3).
- **Principio ordenador (§0):** *"El grafo no es el producto. El producto es el corpus."* Neo4j fabrica el corpus de entrenamiento de modelos ensemble plugin firmados. Suricata/Zeek/Wazuh = testigos/oráculos/corroboradores (maestros del modelo), NUNCA activadores del firewall (3-paradigmas F1 Suricata=0.000/Zeek=0.042/aRGus=0.9985 + soberanía ENS/NIS2/GDPR). Invariante: retención + integridad de etiqueta ganan sobre correlación-online.
- **Decisión núcleo:** `flow_uid = base64(BLAKE2b(node_id ‖ 0x00 ‖ community_id ‖ 0x00 ‖ uint64_be(flow_start_window) [‖ 0x00 ‖ uint32_be(seq_in_window)]))`. `H = BLAKE2b` (`crypto_generichash`, libsodium 1.0.19, fijado documentalmente además del invariante "lo que dé la libsodium congelada"). `node_id` = string legible declarado en inventario firmado, NO derivado del keypair efímero. `community_id` = clave de correlación, nunca identidad (recicla 5-tupla, colisiona multi-nodo). `seq_in_window` transportado en el evento Protobuf (no recomputado offline). `sensor_native_flow_id` = propiedad de trazabilidad, nunca componente del hash.
- **Correlación host↔red:** doble arista (flujo↔flujo determinista por community_id; host↔flujo por `agent_id` canónico + ventana temporal asimétrica en EVENT TIME con watermark, Red→Host 5s / Host→Red 30s). NAT: menú de mecanismos con anotación obligatoria de método+confianza; conflicto → `CONFLICT_NAT`, peso de muestra penalizado en ADR-040.
- **Anulaciones de árbitro (Alonso):** (1) función de hash anclada a libsodium congelada §3.1.1; (2) señales TCP/TLS de host dentro de ADR-052 §3.11 — TCP ligero (RST/seqnum) entra; mismatch TLS acotado a destinos gestionados con cert-expectation store. Límite §3.4.1: con host comprometido toda la telemetría de host miente → vector A indetectable sin fuente out-of-band. Cobertura L7 asimétrica (R1): limitada al perímetro gestionado hasta cerrar `DEBT-CERT-EXPECTATION-STORE-001`.
- **Entregables:** `ADR-052_v3.2.md` (ratificada) + cadena v3.1/v3/v2 + síntesis de deliberación.
- **Desbloquea:** `DEBT-NEO4J-FLOW-KEY-001` (P0 esquema) y el diseño del correlation-engine.

### ADR-053 — JA3/JA4, cadena TLS profunda, anomalía de ruta L3/BGP (STUB)
- **Status:** ⏳ STUB NUEVO — DAY 173. Diferido conscientemente desde ADR-052 para evitar scope creep.
- **Contenido a redactar:** fingerprinting JA3/JA4, validación de cadena TLS profunda (más allá del cert-expectation store del perímetro gestionado), detección de anomalía de ruta L3/BGP (BGP hijack). Flujo: borrador → Consejo → aprobación.

### DEBT-NODEID-CRYPTO-IDENTITY-001 — node_id como string declarado (REESCRITA)
**Severidad:** 🔴 P0 — desbloquea Neo4j
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 C1)
**Componente:** inventario firmado (ADR-046 §3.9) + sniffer + correlation-engine
`node_id` NO puede derivarse del keypair Ed25519 (se regenera en cada `vagrant destroy+up` → rompería la identidad de corpus). `node_id` = string canónico legible declarado en inventario firmado (ej. `argus-sensor-gw-lan-01`), estable a años vista, auditable en forense. El keypair firma los eventos (autenticidad, ADR-027); el inventario firmado protege la integridad del `node_id`. Dos líneas de defensa distintas que no deben confundirse (R3).
**Test de cierre:** `flow_uid` idéntico antes/después de `vagrant destroy+up` con el mismo `node_id` declarado. `node_id` no presente en inventario → rechazo.
**Estimación:** 1 sesión.

### DEBT-FLOWUID-CANONICAL-ENCODING-001 — codificación canónica flow_uid + paridad
**Severidad:** 🔴 P0 — desbloquea Neo4j
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2)
**Componente:** sniffer (C++) + correlation-engine (Python) + common
Implementar `flow_uid = base64(BLAKE2b(node_id ‖ 0x00 ‖ community_id ‖ 0x00 ‖ uint64_be(flow_start_window) [‖ 0x00 ‖ uint32_be(seq_in_window)]))` con `crypto_generichash` (libsodium 1.0.19). `node_id` entra como string canónico no derivado; `seq_in_window` es INPUT del vector (transportado en el evento, no recomputado offline). Test de paridad cross-implementación C++/Python sobre la MISMA versión de libsodium (mismo patrón que `pycommunityid`).
**Test de cierre:** C++ y Python producen `flow_uid` idéntico sobre el vector + verifican misma versión de libsodium. Caso dos-sensores misma 5-tupla → `flow_uid` distinto por `node_id` distinto.
**Estimación:** 1-2 sesiones.

### DEBT-SENSOR-COVERAGE-MAP-001 — Mapa de cobertura sensor↔segmento
**Severidad:** 🟡 P1 — prerrequisito de orphan_rate / IPW
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.8)
**Componente:** orquestador (Vagrant/Ansible) + cache declarativa (Redis/etcd)
Tabla/cache declarativa sensor↔segmento, DECLARADA (no auto-descubierta), versionada y timestampeada, fuente = orquestador. Validación por beacons. Sin este mapa, `community_id.orphan_rate` e IPW son ruido (no se sabe cuántos testigos se ESPERABAN por flujo: `expected_witnesses`).
**Test de cierre:** `expected_witnesses` por flujo calculable desde el mapa. Beacon de validación detecta deriva mapa↔realidad.
**Estimación:** 1-2 sesiones.

### DEBT-LABEL-WAL-001 — WAL externo append-only con hash-chain
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.7, C4)
**Componente:** correlation-engine + etcd HA (ADR-048)
WAL externo append-only con hash-chain (`prev_hash = H(entrada_{i-1})`) como fuente de no-repudio del etiquetado; Neo4j = vista materializada. Verificación periódica de la cadena. Dos detecciones independientes: cadena rota (manipulación WAL) vs divergencia grafo↔WAL (manipulación Neo4j). Provenance en 2 campos ortogonales que nunca se colapsan: `provenance_suspected` (heurística runtime) vs `provenance_ground_truth` (manifiesto MITRE); su delta = métrica honesta precision/recall. Eje separado del enum congelado de `acceptance_criteria.md` (DROP/CONFIG/POLICY/BUG/UNKNOWN).
**Test de cierre:** manipular una entrada del WAL → cadena rota detectada. Divergir Neo4j del WAL → divergencia detectada. `provenance_suspected` y `provenance_ground_truth` nunca colapsados.
**Estimación:** 2 sesiones (depende de ADR-048 etcd HA).

### DEBT-ARGUSPP-ARP-MONITOR-001 — ARP/NDP como nodo de estado de primera clase
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.9)
**Componente:** sniffer / host plane
ARP/NDP modelado como nodo de estado (`:IpMacBinding` con `valid_from`/`valid_to`), re-binding = señal (vector A / MITM L2). NO volcado de paquetes. Línea de defensa L2 del vector A (no sujeta a la limitación L7 asimétrica de §3.4).
**Test de cierre:** re-binding IP↔MAC anómalo → `:IpMacBinding` con `valid_to` + señal. ARP gratuito legítimo no genera falso positivo.
**Estimación:** 1-2 sesiones.

### DEBT-ARGUSPP-HOST-TCP-001 — Señales TCP de host (RST/seqnum)
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.11a, anulación de árbitro)
**Componente:** host plane (osquery / Wazuh ligero)
Señales TCP ligeras de host (RST inesperados, saltos de seqnum del kernel) como ganchos del vector A ampliado. Límite documentado §3.4.1: con host comprometido toda la telemetría de host miente → vector A indetectable sin fuente out-of-band.
**Test de cierre:** RST/seqnum anómalo bajo supuesto de host sano → `:HostAnomaly` TCP. Host comprometido documentado como límite, no como cobertura.
**Estimación:** 1-2 sesiones.

### DEBT-CERT-EXPECTATION-STORE-001 — Cert-expectation store (mismatch TLS)
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 C2/R1)
**Componente:** host plane + store declarativo
Store de expectativa de certificado para destinos gestionados; habilita la señal de mismatch TLS del vector A en L7. Sin él, la cobertura L7 del vector A está limitada al perímetro gestionado (nota de cobertura asimétrica §3.4, R1): el tráfico saliente a destinos arbitrarios — donde más MITM real ocurre — no queda cubierto en L7. L2 (ARP/NDP) y L4 (RST/seqnum) no tienen esta limitación.
**Test de cierre:** mismatch TLS en destino gestionado con expectativa declarada → señal. Destino arbitrario → sin falso positivo (no cubierto, documentado).
**Estimación:** 2 sesiones.

### DEBT-SEQWINDOW-PERSIST-001 — Persistencia de seq_in_window en el sensor
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2)
**Componente:** sniffer
Persistencia local (fsync) del contador `seq_in_window` para sobrevivir a reinicios del sensor dentro del mismo bucket temporal. Un crash justo tras computar el contador pero antes de emitir es delicado (riesgo de colisión UDP en el mismo `flow_start_window`).
**Test de cierre:** crash del sensor + restart dentro del mismo window → `seq_in_window` no reutilizado.
**Estimación:** 1 sesión.

### DEBT-ARGUSPP-OOB-MITM-001 — Fuente out-of-band para vector A con host comprometido
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §3.4.1)
**Componente:** switch (port-security / DAI / DHCP snooping) / SPAN-TAP / Canary Host
Límite fundamental §3.4.1: con host comprometido toda la telemetría de host miente → vector A indetectable sin fuente out-of-band. La fuente OOB no elimina el problema, reubica la confianza al elemento menos comprometible ("escudo, nunca espada").
**Test de cierre:** vector A con host comprometido + fuente OOB → detectable. Sin fuente OOB → documentado como indetectable por diseño.
**Estimación:** post-hardware (switch gestionable).

### DEBT-CORPUS-QUALITY-METRICS-001 — KPIs de calidad del corpus
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2 §0.1)
**Componente:** correlation-engine + pipeline ML (ADR-040)
KPIs §0.1: % flujos con `provenance_ground_truth` validado, % flujos con `witness_count ≥ 2` en segmentos de cobertura solapada, tiempo de reconstrucción de `flow_uid` desde pcap, cobertura de técnicas MITRE, balance de clases benigno/malicioso. Confianza-por-corroboración (feature, sube con testigos) y peso-de-de-duplicación (sampler, baja con testigos) SEPARADAS; el IPW real lo posee ADR-040. `trust_tier` enum en grafo, score continuo en pipeline ML (no en Neo4j). Normalizado por `expected_witnesses` del mapa de cobertura.
**Test de cierre:** KPIs calculables por sesión. Confianza y peso de de-dup nunca colapsados en un solo número.
**Estimación:** 1-2 sesiones.

### DEBT-ARCH-FLOW-OBSERVATION-001 — Separar FlowObservation de FlowIdentity
**Severidad:** ⚪ P3
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-052 v3.2)
**Componente:** modelo de datos correlation-engine + Neo4j
Distinguir formalmente `FlowObservation` (lo que un sensor concreto observó) de `FlowIdentity` (la identidad de corpus, `flow_uid`). Refactorización de modelo de datos post-FEDER.
**Test de cierre:** el modelo separa observación de identidad. Múltiples `FlowObservation` → un `FlowIdentity` vía community_id.
**Estimación:** post-FEDER.

"""

# ===== BACKLOG: flip del heading del stub ADR-052 (PENDIENTE -> RATIFICADA) =====
BACKLOG_ADR052_HEAD_OLD = "ADR-052"  # se filtra además por "PENDIENTE redacción"
BACKLOG_ADR052_HEAD_NEW = "#### ADR-052 — Multi-node Flow Identity & Host<->Net Correlation (RATIFICADA v3.2 — DAY 173)"
BACKLOG_ADR052_STATUS_NEW = "**Estado:** ✅ RATIFICADA v3.2 (Consejo 8/8) — DAY 173. Ver sección \"RATIFICADO DAY 173\" arriba. · recoge P3 + P1"

# ===== PROMPT: nota de cabecera (insert tras la línea 'DAY 173 — aRGus NDR') =====
PROMPT_HEADER_NOTE = """
ÚLTIMO HITO DAY 173: ADR-052 v3.2 RATIFICADA por el Consejo (8/8, confirmación de fidelidad sin reservas,
sin 3ª deliberación). Entregable ADR-052_v3.2.md. Genera las DEBTs P0->P3 de identidad de flujo (abajo) y
el stub ADR-053. PENDIENTE aún en DAY 173: commit/push DAY 172, ADR-051 borrador, y empezar las DEBTs P0
(NODEID + FLOWUID + NEO4J-FLOW-KEY) que ADR-052 desbloquea.
"""

# ===== PROMPT: reemplazo de la prioridad #3 (bloque de 2 líneas) =====
PROMPT_PRIO3_FIRST = "3. ADR-052 (Multi-node Flow Identity & Host<->Net Correlation) — borrador para el Consejo. Recoge P3+P1."
PROMPT_PRIO3_LAST = "   Estaba a medio escribir en el working tree al empezar DAY 172. Ratifica flow_uid ANTES de Neo4j."
PROMPT_PRIO3_NEW = """3. ✅ ADR-052 v3.2 RATIFICADA (Consejo 8/8, DAY 173) — Multi-node Flow Identity & Host<->Net Correlation.
   Confirmación de fidelidad unánime, sin 3a deliberacion. flow_uid = base64(BLAKE2b(node_id || community_id ||
   flow_start_window [|| seq_in_window])); node_id = string legible declarado (no keypair efimero); community_id =
   clave de correlacion, nunca identidad. Anulaciones de arbitro: hash libsodium (3.1.1) + TCP/TLS host (3.11).
   Entregable ADR-052_v3.2.md. DESBLOQUEA DEBT-NEO4J-FLOW-KEY-001 (#4). Genera DEBTs P0->P3 de identidad de flujo
   (ver lista de deudas) + stub ADR-053 (JA3/JA4, TLS profundo, BGP). ADR-051 (#2) SIGUE pendiente de redaccion."""

# ===== PROMPT: reemplazo de la línea de deuda abierta de ADR-052 =====
PROMPT_DEBT052_OLD = "- ADR-052 — Multi-node Flow Identity & Host<->Net Correlation. Borrador pendiente (a medio escribir)."
PROMPT_DEBT052_NEW = """- ADR-052 — Multi-node Flow Identity & Host<->Net Correlation. RATIFICADA v3.2 (8/8, DAY 173). Entregable ADR-052_v3.2.md.
- ADR-053 — JA3/JA4, cadena TLS profunda, anomalia de ruta L3/BGP. STUB (diferido de ADR-052). Borrador pendiente.
- DEBT-NODEID-CRYPTO-IDENTITY-001 — node_id = string declarado en inventario firmado, no keypair efimero (P0, ADR-052 C1). Desbloquea Neo4j.
- DEBT-FLOWUID-CANONICAL-ENCODING-001 — codificacion canonica BLAKE2b + paridad C++/Python + seq_in_window transportado + caso 2-sensores (P0, ADR-052).
- DEBT-SENSOR-COVERAGE-MAP-001 — mapa sensor<->segmento declarativo, versionado, beacons (P1, ADR-052 3.8). Prereq de orphan_rate/IPW.
- DEBT-LABEL-WAL-001 — WAL externo append-only hash-chain (prev_hash), Neo4j vista materializada, doble deteccion (P1, ADR-052 3.7).
- DEBT-ARGUSPP-ARP-MONITOR-001 — ARP/NDP como :IpMacBinding, re-binding=senal vector A L2 (P1, ADR-052 3.9).
- DEBT-ARGUSPP-HOST-TCP-001 — senales TCP host RST/seqnum, vector A ampliado (P1, ADR-052 3.11a).
- DEBT-CERT-EXPECTATION-STORE-001 — store expectativa cert para mismatch TLS; cobertura L7 asimetrica hasta cerrarlo (P2, ADR-052 C2/R1).
- DEBT-SEQWINDOW-PERSIST-001 — persistencia fsync de seq_in_window en sensor (P2, ADR-052).
- DEBT-ARGUSPP-OOB-MITM-001 — fuente out-of-band (port-security/SPAN/Canary) para vector A con host comprometido (P2, ADR-052 3.4.1).
- DEBT-CORPUS-QUALITY-METRICS-001 — KPIs corpus 0.1; confianza-corroboracion vs peso-de-dedup separados; IPW en ADR-040 (P2, ADR-052).
- DEBT-ARCH-FLOW-OBSERVATION-001 — separar FlowObservation de FlowIdentity (P3, ADR-052)."""


# ──────────────────────────────────────────────────────────────────────────────
# Plan de operaciones por fichero
# Cada entrada: (descripcion, sentinel_idempotencia, funcion(text)->text)
# Si sentinel ya está en el texto -> se omite (idempotente).
# ──────────────────────────────────────────────────────────────────────────────

def build_readme_ops():
    ops = []
    ops.append((
        "README: tabla DAY-STATUS -> DAY 173",
        "| DAY | 173 |",
        lambda t: op_replace_between_markers(t, "<!-- DAY-STATUS -->", "<!-- /DAY-STATUS -->", README_DAYSTATUS),
    ))
    ops.append((
        "README: header 'Estado actual' -> DAY 173",
        "## Estado actual — DAY 173",
        lambda t: op_replace_first_line_containing(t, "## Estado actual — DAY 170", f"## Estado actual — DAY 173 ({TODAY})"),
    ))
    ops.append((
        "README: bloque Hitos DAY 173",
        "### Hitos DAY 173",
        lambda t: op_insert_before_line_containing(t, "### Hitos DAY 171", README_HITOS_173),
    ))
    ops.append((
        "README: milestone DAY 173",
        "✅ DAY 173: **ADR-052 v3.2 RATIFICADA",
        lambda t: op_insert_after_line_containing(t, "🔜 DAY 172:", README_MILESTONE_173),
    ))
    return ops


def build_backlog_ops():
    ops = []
    ops.append((
        "BACKLOG: fecha 'Última actualización' -> DAY 173",
        "*Última actualización: DAY 173",
        lambda t: op_replace_first_line_containing(t, "*Última actualización: DAY 170", BACKLOG_FECHA_NUEVA),
    ))
    ops.append((
        "BACKLOG: sección consolidada DAY 173 (DEBTs P0->P3 + ADR-052/053)",
        "## ✅ RATIFICADO DAY 173 — ADR-052 v3.2",
        lambda t: op_insert_before_line_containing(t, "## ✅ CERRADO DAY 171", BACKLOG_SECCION_173),
    ))
    # Flip del stub ADR-052: heading + línea de estado. Se localizan por doble criterio.
    ops.append((
        "BACKLOG: flip heading stub ADR-052 (PENDIENTE -> RATIFICADA)",
        "(RATIFICADA v3.2 — DAY 173)",
        _backlog_flip_adr052_heading,
    ))
    ops.append((
        "BACKLOG: flip estado stub ADR-052 (BORRADOR PENDIENTE -> RATIFICADA)",
        "✅ RATIFICADA v3.2 (Consejo 8/8) — DAY 173. Ver sección",
        _backlog_flip_adr052_status,
    ))
    return ops


def _backlog_flip_adr052_heading(text):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        s = ln.rstrip()
        if "ADR-052" in s and "PENDIENTE redacción" in s and s.startswith("####"):
            lines[i] = BACKLOG_ADR052_HEAD_NEW
            return "\n".join(lines)
    raise AnchorError("BACKLOG: no se encontró el heading '#### ADR-052 ... (PENDIENTE redacción)'")


def _backlog_flip_adr052_status(text):
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        s = ln.rstrip()
        if "BORRADOR PENDIENTE" in s and "recoge P3 + P1" in s:
            lines[i] = BACKLOG_ADR052_STATUS_NEW
            return "\n".join(lines)
    raise AnchorError("BACKLOG: no se encontró la línea de estado del stub ADR-052 (recoge P3 + P1)")


def build_prompt_ops():
    ops = []
    ops.append((
        "PROMPT: nota de cabecera DAY 173",
        "ÚLTIMO HITO DAY 173: ADR-052 v3.2 RATIFICADA",
        lambda t: op_insert_after_line_containing(t, "DAY 173 — aRGus NDR (arXiv:2604.04952)", PROMPT_HEADER_NOTE),
    ))
    ops.append((
        "PROMPT: prioridad #3 -> ADR-052 RATIFICADA",
        "3. ✅ ADR-052 v3.2 RATIFICADA (Consejo 8/8, DAY 173)",
        lambda t: op_replace_block(t, PROMPT_PRIO3_FIRST, PROMPT_PRIO3_LAST, PROMPT_PRIO3_NEW),
    ))
    ops.append((
        "PROMPT: lista de deudas -> ADR-052 ratificada + ADR-053 + DEBTs P0->P3",
        "ADR-052 — Multi-node Flow Identity & Host<->Net Correlation. RATIFICADA v3.2",
        lambda t: op_replace_first_line_containing(t, PROMPT_DEBT052_OLD, PROMPT_DEBT052_NEW),
    ))
    return ops


# ──────────────────────────────────────────────────────────────────────────────
# Motor
# ──────────────────────────────────────────────────────────────────────────────

def process_file(path, ops, apply, report):
    if not os.path.isfile(path):
        report.append(("ERROR", path, "fichero no encontrado"))
        return False, None
    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    text = original
    applied, skipped = [], []
    try:
        for desc, sentinel, fn in ops:
            if _has(text, sentinel):
                skipped.append(desc)
                continue
            text = fn(text)
            applied.append(desc)
    except AnchorError as e:
        report.append(("ABORT", path, f"{e}  (NO se escribe este fichero)"))
        return False, None

    for d in applied:
        report.append(("APLICAR", path, d))
    for d in skipped:
        report.append(("YA-OK", path, d))

    changed = (text != original)
    if apply and changed:
        ts = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = f"{path}.bak.{ts}"
        shutil.copy2(path, bak)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        report.append(("ESCRITO", path, f"backup -> {bak}"))
    elif apply and not changed:
        report.append(("SIN-CAMBIOS", path, "todas las operaciones ya estaban aplicadas"))
    return True, text


def main():
    ap = argparse.ArgumentParser(description="Actualiza los 3 ficheros DAY 173 (ADR-052 v3.2).")
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--backlog", default="docs/BACKLOG.md")
    ap.add_argument("--prompt", default="docs/continuity/PROMPT_CONTINUE_CLAUDE.md")
    ap.add_argument("--apply", action="store_true", help="escribe los cambios (por defecto: dry-run)")
    args = ap.parse_args()

    plan = [
        (args.readme, build_readme_ops()),
        (args.backlog, build_backlog_ops()),
        (args.prompt, build_prompt_ops()),
    ]

    report = []
    all_ok = True
    for path, ops in plan:
        ok, _ = process_file(path, ops, args.apply, report)
        all_ok = all_ok and ok

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"=== update_day173.py [{mode}] ===\n")
    cur = None
    for status, path, msg in report:
        if path != cur:
            print(f"\n# {path}")
            cur = path
        print(f"  [{status:11}] {msg}")

    print()
    if not all_ok:
        print("RESULTADO: ABORTADO en al menos un fichero (ancla no encontrada). "
              "Ningún fichero con ABORT fue modificado. Revisa el ancla indicada.")
        sys.exit(1)
    if not args.apply:
        print("RESULTADO: dry-run OK. Repite con  --apply  para escribir (se crea .bak de cada fichero).")
    else:
        print("RESULTADO: aplicado. Revisa los .bak.<timestamp> si necesitas revertir.")
    sys.exit(0)


if __name__ == "__main__":
    main()