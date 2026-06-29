#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_day170_docs.py — Actualiza los tres ficheros de DAY 170 de forma SEGURA.

Lección de hoy (DEBT-DOCS-BACKLOG-DEDUP-001): nunca insertar a ciegas.
Este script:
  1. Hace backup .bak-day170 de cada fichero ANTES de tocar nada.
  2. Verifica que cada ancla aparece EXACTAMENTE una vez (si no, ABORTA ese
     fichero sin escribir — no hay daño porque las ediciones son en memoria).
  3. Es idempotente: si el marcador nuevo ya existe, no reinserta.
  4. Tras escribir BACKLOG, verifica duplicados de cabecera con uniq -d lógico.
  5. Imprime un resumen y un diff corto.

Uso (desde la raíz del repo):
    python3 tools/update_day170_docs.py
    python3 tools/update_day170_docs.py --dry-run   # no escribe, solo informa

Rutas por defecto (ajusta con flags si difieren):
    docs/BACKLOG.md
    README.md
    docs/continuity/PROMPT_CONTINUE_CLAUDE.md
"""

import argparse
import difflib
import os
import shutil
import sys
from datetime import datetime

BAK_SUFFIX = ".bak-day170"

# ───────────────────────── utilidades ─────────────────────────

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def backup(path):
    bak = path + BAK_SUFFIX
    shutil.copy2(path, bak)
    return bak

def insert_once(content, anchor, block, marker, label):
    """Inserta `block` justo ANTES de `anchor`. Idempotente por `marker`.
    Devuelve (nuevo_contenido, estado_str). No escribe nada.
    ABORTA (raise) si el ancla no aparece exactamente una vez."""
    if marker in content:
        return content, f"  SKIP  {label}: marcador ya presente (idempotente)"
    n = content.count(anchor)
    if n != 1:
        raise RuntimeError(
            f"ABORT {label}: el ancla aparece {n} veces (esperado 1). "
            f"No se modifica el fichero.\n        ancla: {anchor[:70]!r}"
        )
    new = content.replace(anchor, block + anchor, 1)
    return new, f"  OK    {label}: bloque insertado"

def replace_once(content, old, new, marker, label):
    """Reemplaza `old` por `new`. Idempotente por `marker`.
    ABORTA si `old` no aparece exactamente una vez."""
    if marker in content:
        return content, f"  SKIP  {label}: marcador ya presente (idempotente)"
    n = content.count(old)
    if n != 1:
        raise RuntimeError(
            f"ABORT {label}: el texto a reemplazar aparece {n} veces (esperado 1). "
            f"No se modifica el fichero.\n        texto: {old[:70]!r}"
        )
    return content.replace(old, new, 1), f"  OK    {label}: reemplazado"

def header_dupes(content):
    """Réplica lógica de: grep '^###' | sort | uniq -d. Devuelve duplicados."""
    heads = {}
    for line in content.splitlines():
        s = line.strip()
        if s.startswith("###"):
            heads[s] = heads.get(s, 0) + 1
    return {h: c for h, c in heads.items() if c > 1}

def short_diff(old, new, path, ctx=2):
    a = old.splitlines(keepends=True)
    b = new.splitlines(keepends=True)
    d = list(difflib.unified_diff(a, b, fromfile=path, tofile=path + " (nuevo)", n=ctx))
    # solo las líneas añadidas, recortado
    added = [l for l in d if l.startswith("+") and not l.startswith("+++")]
    return added

# ───────────────────────── bloques de contenido ─────────────────────────

BACKLOG_COUNCIL_BLOCK = r"""## 📝 Notas del Consejo de Sabios — DAY 170 (8/8)

> "DAY 170 — Cierre community_id cross-sensor + saneamiento BACKLOG + ritual del Consejo. Veredicto 8/8: aprobado con nota alta. El community_id pasa de campo del protobuf a invariante de identidad operacional verificable.
>
> **community_id sellado en los tres sensores de red:** aRGus (nativo, 8/8 tests contra oráculo pycommunityid v1.5.0 byte a byte, campo protobuf field 18), Zeek 8.2.0 (provisión local.zeek site/ con @load community-id-logging + redef CommunityID::seed=0) y Suricata 7.0.10 (community-id:yes + community-id-seed:0 en suricata.yaml). Diana E2E: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E= sobre flujo Neris 147.32.84.165:1027 -> 74.125.232.195:80. Seed 0 explícito garantizado por provisión en los tres. DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 y DEBT-ARGUSPP-COMMUNITY-ID-001 CERRADAS.
>
> **De-duplicación BACKLOG (DEBT-DOCS-BACKLOG-DEDUP-001 CERRADA):** corrupción arrastrada desde DAY 158 (append manual cat>>, no el script). 5336->2839 líneas. Lección elevada a regla: integridad documental se verifica con `grep secciones | sort | uniq -d` sobre el fichero completo, no con `grep -c` de cabecera. Idempotencia de provisión por LÍNEA, no por bloque.
>
> **Consenso 8/8 en las tres preguntas de arquitectura (sin segunda pasada):**
>
> **P1 — Wazuh <-> red:** (A)+(C). Descartar (B) como base. Grafo de doble arista: flujo<->flujo por community_id (determinista), host<->flujo por nodo Host identificado por host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal. Ventana host<->red más laxa y causal-bidireccional que red<->red. NAT = agujero peligroso: menú de mecanismos (Translation node / agent_id / proceso+puerto_local / fallback temporal), SIEMPRE anotando en grafo y log el método usado y su confianza. (B) solo enriquecimiento oportunista.
>
> **P2 — Invariante seed:** gate de arranque P0 (análogo a NTP) + health-check de huérfanos continuo. Refinamiento Alonso+Qwen+Gemini: el gate se basa en el DATA-PLANE (el community_id que cada componente EMITE en runtime sobre un flujo de referencia), NO en lectura de config JSON/yaml — el fichero puede mentir; engañar al pipeline exigiría modificar binarios/plugins. Este enfoque unifica el gate sobre los tres sensores y disuelve la bifurcación que propuso Gemini (gate-estricto-aRGus + canario-pasivo-externos), resolviendo su preocupación de fragilidad ante cambios de versión por otra vía.
>
> **P3 — Identidad de flujo multi-nodo:** clave compuesta CON componente temporal. Refinamiento (objeción DeepSeek + formalización Gemini/Qwen): la 5-tupla se recicla en el tiempo, luego (node_id, community_id) tampoco es único. Identidad del nodo-flujo en Neo4j = flow_uid = hash(node_id || community_id || flow_start_window). community_id permanece como propiedad indexada (clave de correlación intra-nodo + verificable contra oráculo), nunca como identidad de nodo.
>
> **DAY 171 aprobado sin bloqueos:** cross-check E2E tres ventanas (cliente .50 replaya Neris; aRGus+Suricata+Zeek capturan en paralelo de eth1; los 3 deben emitir el mismo community_id sobre el mismo paquete). Añadidos del Consejo: registrar timestamp relativo de emisión + nº de paquete/flow por sensor; caso de IPs invertidas (respuesta); NAT simulado si es posible.
>
> 'El verdadero activo no es el hash — es que todos los sensores producen exactamente el mismo hash.' — ChatGPT · DAY 170"
> — Consejo de Sabios (8/8) · DAY 170

### Entradas DAY 170 derivadas del Consejo — ADRs + DEBTs

> **Nota de numeración (lección de hoy):** ADR-050 ya está reservado en este BACKLOG para la sesión MITRE + corrección cripto telemetría (DAY 169, pendiente redacción). Por tanto las dos ADRs nuevas toman 051 y 052. Verificado contra el BACKLOG antes de asignar.

#### ADR-051 — Seed Parity Gate & Correlation Health (PENDIENTE redacción)
**Estado:** ⏳ BORRADOR PENDIENTE — DAY 170 (Consejo 8/8) · recoge P2
Gate de arranque P0 basado en data-plane: el correlation-engine mide el community_id que cada sensor EMITE en runtime sobre un flujo de referencia y verifica paridad. Divergencia -> `SEED_MISMATCH`, abort. Health-check continuo: métrica `community_id.orphan_rate` (flujos sin corroboración cross-sensor cuando deberían tenerla); caída de matches a ~0 u orfandad sistemática >umbral en N ventanas -> alerta CRITICAL. NO lee config JSON/yaml — el fichero puede mentir. Flujo: borrador -> Consejo -> aprobación -> implementación.

#### ADR-052 — Multi-node Flow Identity & Host<->Net Correlation (PENDIENTE redacción)
**Estado:** ⏳ BORRADOR PENDIENTE — DAY 170 (Consejo 8/8) · recoge P3 + P1
Identidad del nodo-flujo en Neo4j = `flow_uid = hash(node_id || community_id || flow_start_window)`. community_id como propiedad indexada (clave de correlación intra-nodo). Doble arista: flujo<->flujo (community_id, determinista) + host<->flujo (host_id/agent_id canónico + ventana temporal laxa causal-bidireccional). NAT: menú de mecanismos con anotación de método y confianza en grafo+log. Esquema Neo4j compartido -> P1 y P3 en un mismo ADR (separable a ADR-053 si el Consejo lo pide).

#### DEBT-NEO4J-FLOW-KEY-001 — Clave de flujo temporal compuesta en Neo4j
**Severidad:** 🔴 P0 esquema — bloquea diseño del correlation-engine
**Estado:** ABIERTO — DAY 170 (Consejo 8/8) · recoge ADR-052
`flow_uid = hash(node_id || community_id || flow_start_window)` como identidad del nodo-flujo. `node_id` propiedad obligatoria en :NetworkFlow, :Alert, :TelemetryEvent. Constraint compuesto nativo Neo4j 5.x. Decidirlo con el grafo vacío es gratis; retrofitear con datos en producción es doloroso (unánime). Correlación intra-nodo por community_id; identidad/dedup inter-nodo por flow_uid.
**Test de cierre:** dos flujos misma 5-tupla en nodos distintos -> flow_uid distinto. Misma 5-tupla reciclada en el tiempo en el mismo nodo -> flow_uid distinto.
**Estimación:** 1 sesión (diseño esquema + constraint) antes de poblar el grafo.

#### DEBT-CORRELATION-SEED-GATE-001 — Gate paridad seed data-plane + health-check huérfanos
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 170 (Consejo 8/8) · recoge ADR-051
Implementación del gate P0 data-plane + health-check `community_id.orphan_rate`. Prerequisito: correlation-engine con al menos dos sensores emitiendo sobre el mismo flujo.
**Test de cierre:** sensor con seed!=0 -> SEED_MISMATCH, abort. Orfandad sistemática inyectada -> alerta CRITICAL.
**Estimación:** 1-2 sesiones.

#### BACKLOG-RESEARCH-NAT-HOSTNET-001 — Puente host<->red bajo NAT
**Estado:** RESEARCH/FUTURE — DAY 170 (Consejo 8/8) · recoge P1
Mecanismos de correlación host<->red cuando IP interna (Wazuh) != IP observada (sensor red): Translation node con logs NAT / identidad agent_id-hostname / puente (proceso, puerto_local, timestamp) / fallback temporal degradado. SIEMPRE anotar en grafo y log el método usado y su confianza. Cubrir explícitamente los casos correctos, incorrectos e incompletos de medida. Nunca fallo silencioso por IP no coincidente. Prereq: Wazuh integrado (DEBT-ARGUSPP-WAZUH-001).

---

"""

# Ancla del BACKLOG: insertamos antes del header de ADR-046 v3.
BACKLOG_ANCHOR = "## ADR-046 v3 — aRGus++ Multi-Source Pipeline (DAY 158)"
BACKLOG_MARKER = "## 📝 Notas del Consejo de Sabios — DAY 170 (8/8)"


# README — bloque DAY-STATUS nuevo (reemplazo completo del bloque marcado).
README_DAYSTATUS_OLD_START = "<!-- DAY-STATUS -->"
README_DAYSTATUS_OLD_END = "<!-- /DAY-STATUS -->"

README_DAYSTATUS_NEW = """<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 170 |
| Tag | v1.0.0-day166 |
| Branch | feature/day170-community-id-protobuf @ af9cd812 |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ✅ VERDE — 3 actos + Jenkins gate (DAY 167) |
| Pipeline | 6/6 RUNNING |
| NTP/chrony | ✅ DEBT-ARGUSPP-NTP-001 — health-check rechaza offset >1s (DAY 167) |
| correlation-engine | 🟡 scaffold ADR-048 F2 (DAY 167) |
| Multi-VM | ✅ Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24 (DAY 168) |
| community_id | ✅ aRGus (nativo, 8/8 vs oráculo) + Zeek + Suricata — seed 0 explícito en los 3 (DAY 170) |
| Arquitectura | ✅ ADR-046 v4 + AdapterSpec v1 (DAY 169) · ADR-050 (MITRE) + ADR-051/052 pendientes |
| Próximo hito | DAY 171 cross-check E2E community_id tres ventanas + ADR-051/052 borrador |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->"""

README_HEADER_OLD = "## Estado actual — DAY 169 (2026-05-29)"
README_HEADER_NEW = "## Estado actual — DAY 170 (2026-05-31)"

README_HITOS_ANCHOR = "### Hitos DAY 169 🏛️"
README_HITOS_MARKER = "### Hitos DAY 170 🎉"
README_HITOS_BLOCK = """### Hitos DAY 170 🎉
- **community_id cross-sensor sellado** — aRGus (nativo, 8/8 tests contra oráculo pycommunityid v1.5.0 byte a byte, campo protobuf field 18), Zeek 8.2.0 (provisión `local.zeek` site/: `@load community-id-logging` + `redef CommunityID::seed=0`) y Suricata 7.0.10 (`community-id:yes` + `community-id-seed:0`). Diana E2E `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` sobre flujo Neris. Seed 0 explícito en los 3 garantizado por provisión. `DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001` + `DEBT-ARGUSPP-COMMUNITY-ID-001` CERRADAS.
  - **DEBT-ZEEK-COMMUNITY-ID-PROVISION-001 CERRADA** — guardas de idempotencia por línea en el Vagrantfile (no por bloque). `vagrant provision zeek` deja `local.zeek` con `@load` + `seed=0` sin intervención manual.
  - **DEBT-DOCS-BACKLOG-DEDUP-001 CERRADA** — `docs/BACKLOG.md` corrupto desde DAY 158 (append manual `cat>>`, no el script). 5336->2839 líneas. Lección: verificar integridad con `grep secciones | sort | uniq -d` del fichero completo, no `grep -c` de cabecera.
  - **Consejo de Sabios (8/8) — consenso unánime P1/P2/P3.** Gate seed por data-plane (no config), identidad de flujo `hash(node_id || community_id || flow_start_window)`, doble arista host<->red con host_id canónico. ADR-051 (Seed Parity Gate) + ADR-052 (Multi-node Flow Identity & Host<->Net) pendientes de redacción. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema).

"""

README_MILESTONE_OLD = "  - 🔜 DAY 170: **community_id nativo en aRGus (protobuf + sniffer, canonicalización Kimi) + ADR-050 borrador + RSS bajo carga (pipeline+client+tcpreplay) + DEBT-ARGUSPP-SURICATA-001 (eve.json → correlation-engine)**"
README_MILESTONE_MARKER = "  - ✅ DAY 170: **community_id cross-sensor sellado"
README_MILESTONE_NEW = (
    "  - ✅ DAY 170: **community_id cross-sensor sellado (aRGus+Zeek+Suricata, seed 0, vs oráculo) · de-dup BACKLOG · Consejo 8/8 P1/P2/P3 · ADR-051/052 pendientes** 🎉\n"
    "  - 🔜 DAY 171: **cross-check E2E community_id tres ventanas (.50 replaya Neris → aRGus+Suricata+Zeek paralelo eth1) + ADR-051/052 borrador + DEBT-NEO4J-FLOW-KEY-001 (esquema Neo4j) + RSS bajo carga + ADR-050 MITRE borrador**"
)


# Prompt de continuidad — reescritura completa para DAY 171.
PROMPT_CONTINUE_NEW = r"""DAY 171 — aRGus NDR (arXiv:2604.04952)

Estado: rama feature/day170-community-id-protobuf @ af9cd812 (community_id cross-sensor + de-dup BACKLOG + provisión Zeek/Suricata). Tag estable v1.0.0-day166.
DAY 170 cerrado: community_id sellado en aRGus(nativo)+Zeek+Suricata con seed 0 explícito; BACKLOG de-duplicado (5336->2839); ritual del Consejo completado (síntesis en docs/council/). Consenso 8/8 en P1/P2/P3.

CONTEXTO DE LOS ÚLTIMOS DÍAS:
DAY 167: NTP/chrony (P0). correlation-engine scaffold (ADR-048 F2). Jenkins gate make emecas++.
DAY 168: Vagrantfile multi-VM Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24.
DAY 169: Día de arquitectura. ADR-046 v4 + AdapterSpec v1 + separación de planos. ADR-050 (MITRE) pendiente.
DAY 170: community_id cross-sensor (3 sensores, seed 0, byte a byte vs oráculo pycommunityid; diana 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=). De-dup BACKLOG (DEBT-DOCS-BACKLOG-DEDUP-001). Consejo 8/8.

═══════════════════════════════════════════════════════════════════════════════
CONSENSO DEL CONSEJO DAY 170 — base de DAY 171 (síntesis en docs/council/)
═══════════════════════════════════════════════════════════════════════════════
P1 (Wazuh <-> red): (A)+(C). Doble arista en Neo4j. flujo<->flujo por community_id (determinista);
   host<->flujo por host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal MÁS LAXA y
   causal-bidireccional. NAT = menú de mecanismos, SIEMPRE anotando método y confianza en grafo+log.
   (B) solo enriquecimiento oportunista, nunca base.
P2 (seed): gate de arranque P0 (análogo NTP) + health-check huérfanos continuo. Basado en DATA-PLANE:
   se mide el community_id que cada sensor EMITE en runtime, NO se lee config JSON/yaml (el fichero miente).
   -> ADR-051 + DEBT-CORRELATION-SEED-GATE-001.
P3 (identidad flujo multi-nodo): flow_uid = hash(node_id || community_id || flow_start_window).
   community_id permanece como propiedad indexada (clave de correlación + verificable contra oráculo),
   nunca como identidad de nodo. Decidir con grafo vacío = gratis; retrofit = doloroso.
   -> ADR-052 + DEBT-NEO4J-FLOW-KEY-001 (P0 esquema).

NUMERACIÓN ADR (verificado contra BACKLOG): ADR-050 ya cogido (MITRE, pendiente). Nuevos: 051 y 052.

═══════════════════════════════════════════════════════════════════════════════
PRIORIDAD DAY 171 #1 — cross-check E2E community_id (tres ventanas)
═══════════════════════════════════════════════════════════════════════════════
Cierra la paridad OPERACIONAL del community_id (la de especificación + provisión ya está).
1. Cliente .50 replaya el flujo Neris por eth1 (tcpreplay) en la LAN ml_defender_gateway_lan.
2. aRGus + Suricata + Zeek capturan en PARALELO de eth1 (promiscuo) — el MISMO paquete.
3. Verificar que los 3 emiten el MISMO community_id STRING A STRING (diana 1:IN7uqVpMWxpmuhQTowSQB2XEe0E=).
   No confiar en que coincidan: OBSERVARLO sobre el mismo paquete real.
4. Añadidos del Consejo (Kimi/Grok/Mistral):
   - Registrar por sensor: community_id + timestamp relativo de emisión + nº de paquete/flow.
     (los 3 pueden converger en valor pero diferir en CUÁNDO emiten — Suricata flow.timeout, Zeek cierre TCP).
   - Caso con IPs invertidas (paquete de respuesta) -> mismo community_id (bidireccionalidad canónica).
   - NAT simulado si es viable.
Resultado verde -> el join red<->red basado en community_id es viable en producción, no solo en lab.

PRIORIDAD DAY 171 (resto, arrastrado de DAY 170 + nuevo del Consejo):
2. ADR-051 (Seed Parity Gate & Correlation Health) — borrador para el Consejo. Recoge P2.
3. ADR-052 (Multi-node Flow Identity & Host<->Net Correlation) — borrador para el Consejo. Recoge P3+P1.
4. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema) — diseñar flow_uid + node_id obligatorio + constraint Neo4j 5.x
   ANTES de poblar el grafo. Bloquea el diseño del correlation-engine.
5. RSS bajo carga (arrastrado DAY 170) — pipeline + client + tcpreplay escalonado. Mide CPU/RAM de las
   4 fuentes -> calibra tiers RPi5/N100 (DEBT-ARGUSPP-RESOURCE-001). NO necesita víctima MITRE.
6. ADR-050 (MITRE) — borrador (arrastrado). 6 vectores + bootstrap víctima + corrección cripto telemetría.
7. DEBT-ARGUSPP-SURICATA-001 (P1) — Suricata en EMECAS + eve.json -> correlation-engine.
8. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1, arrastrado) — lint CI targets duplicados CMake. ADR-028 propuesto.

DEUDAS ABIERTAS NUEVAS DAY 170 (Consejo):
- ADR-051 — Seed Parity Gate & Correlation Health (data-plane). Borrador pendiente.
- ADR-052 — Multi-node Flow Identity & Host<->Net Correlation. Borrador pendiente.
- DEBT-NEO4J-FLOW-KEY-001 — flow_uid temporal compuesto (P0 esquema).
- DEBT-CORRELATION-SEED-GATE-001 — gate data-plane + health-check huérfanos (P1).
- BACKLOG-RESEARCH-NAT-HOSTNET-001 — puente host<->red bajo NAT (RESEARCH). Prereq: Wazuh.

DEUDAS ABIERTAS RELEVANTES (arrastradas):
- DEBT-ARGUSPP-SURICATA-001 — Suricata en EMECAS + eve.json -> correlation-engine. P1.
- DEBT-ARGUSPP-WAZUH-001 — Wazuh password via Vault en prod FEDER. P2. (clave correlación = diseño abierto, host-based)
- DEBT-ARGUSPP-MITRE-001 — script ataque MITRE con atomic-red-team (post-FEDER). ADR-047.
- DEBT-ARGUSPP-RESOURCE-001 — medir CPU/RAM/disco 4 fuentes en RPi5/N100. P1 con hardware.
- DEBT-CMAKE-GRAPH-INVARIANTS-001 — lint CI targets duplicados CMake. P1.
- ADR-050 — sesión MITRE + corrección cripto telemetría. Borrador pendiente.

PENDIENTE DE PROPAGACIÓN (cuando correlation-engine gradúe de scaffold):
- Makefile: target `cp network_security.pb.*` + meterlo en scripts/verify_protobuf.sh
  (DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 dejó esto anotado P0 para cuando el engine consuma el campo).

VMs (autostart: false — arrancar individualmente):
defender 192.168.100.1 aRGus completo · suricata .10 (Suricata 7.0.10, community-id:yes seed 0, PROMISC)
zeek .11 (Zeek 8.2.0, community-id-logging seed 0, PROMISC) · wazuh .12 (Wazuh 4.x, NTP OK)
client .50 (tcpreplay + nmap/hydra/sqlmap/atomic-red-team)

ARQUITECTURA MULTI-VM (ml_defender_gateway_lan 192.168.100.0/24):
- eth0: NAT (gestión) · eth1: intnet (tráfico ataque, promiscuo en sniffer/suricata/zeek)
- client inyecta -> todos los engines ven el mismo flujo -> community_id coherente (seed 0 en los 3)
- correlation-engine: source_wait_timeout argus=5s/suricata=10s/zeek=20s/wazuh=90s; crisis_idle 120s
- Neo4j: grafo de correlación cross-engine. Identidad de nodo-flujo = flow_uid (P3). Post-FEDER.
- separación de planos (DAY 169): datos / correlación (CrisisWindow + community_id) / decisión.
  AdapterSpec v1 = contrato del adaptador por fuente.

REGLAS CRÍTICAS:
- community_id: canonicalización byte-idéntica a Zeek/Suricata o el join falla en silencio.
  Verificar con pycommunityid (oráculo). Seed 0 idéntico en los 3 (garantizado por provisión DAY 170).
- Gate de seed (futuro): basado en data-plane (lo que el binario EMITE), nunca en config JSON/yaml.
- Identidad de flujo Neo4j: flow_uid = hash(node_id || community_id || flow_start_window). community_id es
  propiedad indexada, no identidad de nodo.
- NAT host<->red: SIEMPRE anotar método y confianza en grafo+log. Nunca fallo silencioso por IP no coincidente.
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS++ = 3 actos antes de cualquier merge enterprise. >1h. No negociable.
- Python3 heredoc en macOS (nunca sed -i sin -e ''). vagrant ssh -c siempre con -c. -Werror permanente.
- Nunca merge directo a main — siempre PR con EMECAS++ verde (docs puras = excepción razonada).
- vendor.key nunca en disco ni repo — solo Vault dev (Modelo B).
- ZMQ PUB hace bind() ANTES de SUB connect().
- Nunca set -e en provisions Vagrantfile — usar || true o || { exit 1; } explícito.
- DNS fix en provisions nuevos: chattr +i /etc/resolv.conf DESPUÉS de chrony.
- Nunca cat << 'EOF' anidado en <<-SHELL — usar printf.
- Idempotencia de provisión por LÍNEA, no por bloque (lección DAY 170 Zeek).
- Integridad de docs grandes: grep secciones | sort | uniq -d del fichero completo (lección DAY 170 BACKLOG).
- alert_client.hpp nunca incluido en componentes que linkan libetcd_client.so.

ENTORNO: macOS M2 Pro · i9 8 núcleos · 32GB RAM · Vagrant/VirtualBox Debian Bookworm · vagrant/dev/
KEYPAIR: efímero, regenera en cada EMECAS.
PAPER: arXiv:2604.04952 · Draft v24 local · v3 en arXiv.
FEDER: colaboración UEx/INCIBE con Dr. Andrés Caro Lindo. No deadline duro — gate real es demostrar
datasets de valor científico (curva F1 multi-fuente, ADR-048). El 22-09-2026 era referencia de ritmo.

PRIMER COMANDO DAY 171:
git checkout feature/day170-community-id-protobuf && vagrant up suricata zeek defender client
"""


# ───────────────────────── main ─────────────────────────

def process_backlog(path, dry):
    print(f"\n[BACKLOG] {path}")
    content = read(path)
    orig = content
    content, st = insert_once(content, BACKLOG_ANCHOR, BACKLOG_COUNCIL_BLOCK,
                              BACKLOG_MARKER, "Consejo DAY 170 + ADR-051/052 + DEBTs")
    print(st)
    if content != orig and not dry:
        write(path, content)
    # verificación de duplicados
    dupes = header_dupes(content)
    legit = 0
    if dupes:
        print("  [uniq -d] cabeceras ### duplicadas:")
        for h, c in sorted(dupes.items()):
            print(f"      x{c}  {h}")
        print("  (revisa que sean duplicados por-diseño, p.ej. DEBT en CERRADO + ABIERTAS)")
    else:
        print("  [uniq -d] sin cabeceras ### duplicadas nuevas")
    return content != orig


def process_readme(path, dry):
    print(f"\n[README] {path}")
    content = read(path)
    orig = content
    # 1) header de fecha
    content, st = replace_once(content, README_HEADER_OLD, README_HEADER_NEW,
                               README_HEADER_NEW, "header fecha DAY 170")
    print(st)
    # 2) bloque DAY-STATUS (reemplazo del bloque entre marcadores)
    if "| DAY | 170 |" in content:
        print("  SKIP  DAY-STATUS: ya en DAY 170 (idempotente)")
    else:
        s = content.find(README_DAYSTATUS_OLD_START)
        e = content.find(README_DAYSTATUS_OLD_END)
        if s == -1 or e == -1 or content.count(README_DAYSTATUS_OLD_START) != 1:
            raise RuntimeError("ABORT README: bloque DAY-STATUS no localizado de forma única.")
        e_full = e + len(README_DAYSTATUS_OLD_END)
        content = content[:s] + README_DAYSTATUS_NEW + content[e_full:]
        print("  OK    DAY-STATUS: bloque reemplazado a DAY 170")
    # 3) Hitos DAY 170
    content, st = insert_once(content, README_HITOS_ANCHOR, README_HITOS_BLOCK,
                              README_HITOS_MARKER, "Hitos DAY 170")
    print(st)
    # 4) milestone
    content, st = replace_once(content, README_MILESTONE_OLD, README_MILESTONE_NEW,
                               README_MILESTONE_MARKER, "milestone DAY 170 -> 171")
    print(st)
    if content != orig and not dry:
        write(path, content)
    return content != orig


def process_continuity(path, dry):
    print(f"\n[CONTINUITY] {path}")
    content = read(path)
    if content.startswith("DAY 171 — aRGus NDR"):
        print("  SKIP  ya es el prompt de DAY 171 (idempotente)")
        return False
    if not dry:
        write(path, PROMPT_CONTINUE_NEW)
    print("  OK    reescrito como prompt de continuidad DAY 171")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="docs/BACKLOG.md")
    ap.add_argument("--readme", default="README.md")
    ap.add_argument("--continuity", default="docs/continuity/PROMPT_CONTINUE_CLAUDE.md")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = [args.backlog, args.readme, args.continuity]
    for f in files:
        if not os.path.isfile(f):
            print(f"ERROR: no existe {f} (ejecuta desde la raíz del repo)", file=sys.stderr)
            sys.exit(2)

    if args.dry_run:
        print("=== DRY-RUN (no se escribe nada) ===")
    else:
        print(f"=== Backups .bak-day170 ({datetime.now():%H:%M:%S}) ===")
        for f in files:
            print(f"  {backup(f)}")

    changed = False
    try:
        changed |= process_backlog(args.backlog, args.dry_run)
        changed |= process_readme(args.readme, args.dry_run)
        changed |= process_continuity(args.continuity, args.dry_run)
    except RuntimeError as e:
        print(f"\n!!! {e}", file=sys.stderr)
        print("!!! Ningún fichero quedó a medias: la edición es en memoria y solo se escribe si todas las guardas pasan dentro de cada fichero.", file=sys.stderr)
        print("!!! Restaura desde *.bak-day170 si hace falta. Revisa el ancla reportada y reejecuta.", file=sys.stderr)
        sys.exit(1)

    print("\n=== RESUMEN ===")
    print("Cambios aplicados." if changed else "Sin cambios (todo idempotente / ya aplicado).")
    if not args.dry_run and changed:
        print("Revisa con: git diff docs/BACKLOG.md README.md docs/continuity/PROMPT_CONTINUE_CLAUDE.md")
        print("Backups en: *.bak-day170 (bórralos tras validar).")


if __name__ == "__main__":
    main()