#!/usr/bin/env python3
"""
update_day173_adr051.py — Actualiza BACKLOG.md, README.md y el prompt de continuidad
tras la ratificación de ADR-051 v2.2 (Community ID Parity Gate & Correlation Health).

FILOSOFÍA (Via Appia):
- NO reescribe ficheros completos con cat>. Hace ediciones por ANCLA de texto.
- Backup automático con timestamp ANTES de tocar nada.
- Si un ancla esperada no aparece exactamente una vez -> ABORTA sin escribir, dice cuál.
- Verificación post-edición: grep de cabeceras de sección | sort | uniq -d == vacío
  (la regla de integridad de la lección DAY 170).
- Idempotente: si una inserción ya está presente (detectada por un marcador único),
  la salta en vez de duplicarla.

USO (desde la raíz del repo, macOS):
    python3 update_day173_adr051.py            # aplica
    python3 update_day173_adr051.py --dry-run  # muestra qué haría, no escribe
    python3 update_day173_adr051.py --check     # solo verifica integridad actual

Tras ejecutar: revisar git diff, secret-scan, y commitear en una sola piedra.
"""

import argparse
import datetime as _dt
import re
import shutil
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Rutas (relativas a la raíz del repo)
# ---------------------------------------------------------------------------
BACKLOG = Path("docs/BACKLOG.md")
README = Path("README.md")
PROMPT = Path("docs/continuity/PROMPT_CONTINUE_CLAUDE.md")

TS = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
class EditError(Exception):
    pass


def read(path: Path) -> str:
    if not path.exists():
        raise EditError(f"No existe el fichero: {path}")
    return path.read_text(encoding="utf-8")


def backup(path: Path) -> Path:
    dst = path.with_suffix(path.suffix + f".bak-{TS}")
    shutil.copy2(path, dst)
    return dst


def count(haystack: str, needle: str) -> int:
    return haystack.count(needle)


def already_present(text: str, marker: str) -> bool:
    """Idempotencia: ¿ya está aplicada esta inserción?"""
    return marker in text


def insert_after(text: str, anchor: str, payload: str, *, label: str) -> str:
    """Inserta payload justo DESPUÉS de la primera (y única) aparición de anchor."""
    n = count(text, anchor)
    if n == 0:
        raise EditError(f"[{label}] ancla NO encontrada:\n    {anchor[:80]!r}")
    if n > 1:
        raise EditError(
            f"[{label}] ancla AMBIGUA ({n} apariciones), no es seguro insertar:\n    {anchor[:80]!r}"
        )
    idx = text.index(anchor) + len(anchor)
    return text[:idx] + payload + text[idx:]


def replace_once(text: str, old: str, new: str, *, label: str) -> str:
    """Reemplaza old por new exigiendo que old aparezca exactamente una vez."""
    n = count(text, old)
    if n == 0:
        raise EditError(f"[{label}] texto a reemplazar NO encontrado:\n    {old[:80]!r}")
    if n > 1:
        raise EditError(
            f"[{label}] texto a reemplazar AMBIGUO ({n} apariciones):\n    {old[:80]!r}"
        )
    return text.replace(old, new)


def verify_no_dup_sections(text: str, path: Path) -> None:
    """
    Regla de integridad DAY 170: cabeceras de sección de cierre no deben duplicarse.
    Verifica '## ✅ CERRADO DAY' y '## ✅ RATIFICADO DAY' por su línea completa.
    """
    headers = re.findall(r"^## ✅ (?:CERRADO|RATIFICADO) DAY.*$", text, flags=re.MULTILINE)
    seen, dups = set(), set()
    for h in headers:
        if h in seen:
            dups.add(h)
        seen.add(h)
    if dups:
        raise EditError(
            f"[{path}] VERIFICACIÓN uniq -d FALLA — cabeceras duplicadas:\n  "
            + "\n  ".join(sorted(dups))
        )


# ---------------------------------------------------------------------------
# Contenidos a insertar
# ---------------------------------------------------------------------------

# --- BACKLOG: sección de ratificación de ADR-051 + DEBTs nuevas -------------
BACKLOG_ADR051_MARKER = "ADR-051 v2.2 — Community ID Parity Gate & Correlation Health — RATIFICADA"

BACKLOG_ADR051_BLOCK = f"""

## ✅ RATIFICADO DAY 173 — ADR-051 v2.2 (Consejo 8/8) + DEBTs de paridad de community_id

### {BACKLOG_ADR051_MARKER} Y CERRADA
- **Status:** ✅ RATIFICADA v2.2 (Consejo 8/8) DAY 173 — confirmación de fidelidad, sin 3ª deliberación.
- **Título anterior (v1):** "Seed Parity Gate & Correlation Health". El identificador `DEBT-CORRELATION-SEED-GATE-001` se CONSERVA por trazabilidad pese al renombrado.
- **Recoge:** P2 del Consejo DAY 170 (gate de arranque data-plane + health-check de huérfanos).
- **Evolución:** v1 (3 preguntas abiertas) → v2 (consenso 8/8 + N-version oracle divergence) → v2.1 (3 correcciones quirúrgicas) → v2.2 (correcciones de fidelidad: reintegración binaria simétrica, ausencia≠divergencia blindada, split-brain léxico).
- **Principio:** data-plane > control-plane. El gate mide el `community_id` que cada sensor EMITE en runtime, no lo que declara la config. El cross-check E2E DAY 171/172 es su implementación de referencia.
- **Decisiones núcleo:**
  - **Community ID Parity Gate (arranque):** BLOQUEANTE fail-closed. Diagnóstico verbose obligatorio (sensor / cid esperado / cid emitido / config-hash informativo).
  - **Oracle Divergence (N-version):** sensores coinciden entre sí pero no con `pycommunityid` → ARRANCA con WARNING crítico, NO fail-closed. Fail-closed solo por disparidad ENTRE sensores. Válido por heterogeneidad de implementaciones; consenso-de-error mitigado por batería de vectores + orphan_rate, no por el oráculo.
  - **Máquinas de estado:** gate (Correlation Safe / Oracle Divergence / Correlation Broken + split-brain) y confianza del sensor (TRUSTED / DEGRADED / QUARANTINED). DEGRADED por estadística (orphan_rate); QUARANTINED por divergencia binaria confirmada. Reintegración exige re-verificación binaria, no solo orphan_rate bajo.
  - **orphan_rate per-sensor** + distinción huérfano/pendiente por wall-clock (hallazgo timestamps DAY 172). Umbrales 5%/15% = placeholder provisional, recalibrar desde baseline.
  - **Inyección sintética** en segmento monitorizado, marca identificable, descarte en el correlation-engine antes de Neo4j (sensores SÍ procesan el flujo).
  - **Despliegue por fases:** Fase 1 gate completo + health-check Suricata↔Zeek; Fase 2 +aRGus cuando cierre COUNTER-DUMP-001.
- **Riesgo conocido documentado:** latencia de detección del orphan_rate en valles de tráfico (la sonda activa diferida lo mitigaría).
- **Entregable:** `ADR-051_v2.2.md` (ratificada) + cadena v2.1/v2/v1 + síntesis de deliberación.
- **ALCANCE (crítico para el plan del mes):** diseño ratificado PARA ARCHIVAR, no mandato de implementación. De todo el ADR, solo el gate de arranque mínimo (ya hecho como cross-check DAY 171/172) está en camino crítico. El resto duerme como backlog hasta que exista correlation-engine que proteger. Lo que desbloquea el engine es `DEBT-NEO4J-FLOW-KEY-001` (de ADR-052), no este ADR.

### DEBT-CID-TEST-VECTORS-001 — Batería de vectores de referencia (fixture compartido)
**Severidad:** 🟡 P1 (camino crítico del gate)
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2 §3.6)
**Componente:** `tools/` + sniffer + correlation-engine
Batería V1–V4: V1 TCP IPv4 (Neris, regresión `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`), V2 UDP IPv4 (mDNS), V3 TCP IPv6, V4 dirección invertida (canonicidad, verificar POR PROTOCOLO). Un único flujo TCP/IPv4 deja pasar bugs IPv6/canonicalización. **Fixture COMPARTIDO con `DEBT-FLOWUID-CANONICAL-ENCODING-001`** — no duplicar.
**Test de cierre:** los N sensores emiten el mismo cid para cada vector vs oráculo. V4 A→B == B→A por protocolo. V3 valida implementación IPv6 (no cobertura operacional).
**Estimación:** 1 sesión.

### DEBT-SEED-GATE-DIAGNOSTIC-001 — Diagnóstico verbose del fallo del gate + runbook
**Severidad:** 🟡 P1 (camino crítico del gate)
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2 §3.1)
**Componente:** correlation-engine / gate de arranque
Volcado por sensor: identidad, cid esperado (oráculo) + seed del oráculo, cid emitido, SHA-256 del config cargado (SOLO diagnóstico, nunca criterio del gate). Runbook de recuperación de fallo de paridad. Inferencia de seed = enhancement opcional acotado a set ENUMERADO (incluir seeds del mapa de provisión de cada sensor, no solo 0), nunca barrido ciego. Nota seguridad (Kimi): marca de inyección fija es vector DoS/insider → preferir token efímero HMAC de nonce.
**Test de cierre:** gate falla → mensaje accionable con los 4 campos + referencia al runbook. Operador realinea sin arqueología.
**Estimación:** 1 sesión.

### DEBT-CID-STATE-MACHINE-001 — Máquinas de estado del gate y de confianza del sensor
**Severidad:** 🟡 P1 (gate states = Fase 1; sensor states = con health-check)
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2 §3.3/§3.4, propuesta ChatGPT)
**Componente:** correlation-engine
Implementación + tests (unitarios + property-based) de: estados del gate (Correlation Safe / Oracle Divergence / Correlation Broken + split-brain) y confianza del sensor (TRUSTED / DEGRADED / QUARANTINED). Transiciones: gate_fail, orphan_rate_high (→DEGRADED), divergencia_confirmada (→QUARANTINED), recovery (re-verificación binaria), operator_override, split_brain (suspende correlación cross-sensor sin marcar QUARANTINED).
**Test de cierre:** cada transición cubierta. QUARANTINED no se alcanza solo por orphan_rate. Reintegración exige prueba binaria. Split-brain no marca QUARANTINED a nadie.
**Estimación:** 1-2 sesiones.

### DEBT-CID-CROSSCHECK-CI-001 — make crosscheck-up/run como gate de CI
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2 §3.5, propuesta Grok)
**Componente:** Jenkinsfile.dev + Makefile
`make crosscheck-up`/`crosscheck-run` obligatorio en CI para cualquier cambio que toque sensores o `community_id`. El gate de regresión empírico del community_id.
**Test de cierre:** PR que rompe la paridad cross-sensor → CI rojo.
**Estimación:** 1 sesión (requiere Jenkins en hardware FEDER para el gate completo).

### DEBT-CID-ORACLE-QUORUM-001 — Oráculo dos niveles + quórum + versionado
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2 §3.2, propuesta ChatGPT/Mistral)
**Componente:** correlation-engine / gate
Nivel 1 (paridad entre sensores) + Nivel 2 (paridad con oráculo). Lógica de quórum significativa solo con N≥3. Versionar el oráculo (hash/versión de `pycommunityid`) en el diagnóstico. El quórum NUNCA anula al oráculo como criterio; emite WARNING ("posible drift del oráculo o versión desincronizada").
**Test de cierre:** sensores coinciden + oráculo discrepa → WARNING, arranca. Sensores discrepan → fail-closed. N=2 → sin quórum, WARNING elevado.
**Estimación:** 1 sesión.

### DEBT-SEED-CHAOS-TEST-001 — Pruebas de caos de drift de seed
**Severidad:** 🟢 P2
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2, propuesta Mistral)
**Componente:** tests E2E / correlation-engine
Forzar drift de seed en un sensor y verificar: (a) el gate falla en arranque, (b) orphan_rate sube en runtime, (c) la degradación N-1 funciona y anota en el grafo.
**Test de cierre:** drift inyectado → gate-fail en arranque; en runtime → DEGRADED→ (tras confirmación binaria) QUARANTINED, correlación continúa N-1 anotada.
**Estimación:** 1-2 sesiones.

### DEBT-SEED-ACTIVE-PROBE-001 — Sonda activa periódica no bloqueante (DIFERIDA)
**Severidad:** ⚪ P3 — DIFERIDA / OPCIONAL
**Estado:** ABIERTO — DAY 173 (Consejo 8/8, ADR-051 v2.2 §2/§5.1)
**Componente:** correlation-engine (opcional, off por defecto)
Sonda activa configurable que re-inyecta la batería periódicamente para detectar drift en valles de tráfico (donde orphan_rate tarda en acumular evidencia). NO entra en el núcleo: orphan_rate es el mecanismo continuo primario. Si se implementa, puede actuar como disparador de re-verificación binaria para reintegración. Mitiga el riesgo conocido §5.1.
**Test de cierre:** sonda activa detecta drift en red sin tráfico orgánico, sin contaminar producción (off por defecto).
**Estimación:** post-engine.

### DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 — Verificar reloj inyectado en path de producción
**Severidad:** 🟡 P1 — corrección latente (NO de ADR-051; hallazgo DAY 172)
**Estado:** ABIERTO — DAY 173
**Componente:** `sniffer/src/flow/community_id_log.cpp`
El TSV de cross-check de aRGus estampa timestamp SINTÉTICO porque `community_id_log.cpp` corre bajo reloj inyectado en el build de cross-check. PENDIENTE VERIFICAR si el path de PRODUCCIÓN heredó ese reloj inyectado en vez de `system_clock` real. Si se filtró fuera del gate `ARGUS_CID_CROSSCHECK=1`, es un bug de corrección, no un artefacto del cross-check.
**Test de cierre:** confirmar que el binario de producción usa `system_clock` real, no el reloj inyectado del build de cross-check. Si está contaminado → corregir y test de regresión.
**Estimación:** 0.5 sesión (investigación) + fix si aplica.
"""

# --- BACKLOG: actualizar estado de DEBT-CORRELATION-SEED-GATE-001 -----------
BACKLOG_SEEDGATE_OLD = """#### DEBT-CORRELATION-SEED-GATE-001 — Gate paridad seed data-plane + health-check huérfanos
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 170 (Consejo 8/8) · recoge ADR-051"""
BACKLOG_SEEDGATE_NEW = """#### DEBT-CORRELATION-SEED-GATE-001 — Gate paridad seed data-plane + health-check huérfanos
**Severidad:** 🟡 P1
**Estado:** ABIERTO — DAY 170 (Consejo 8/8) · DISEÑO CERRADO por ADR-051 v2.2 (DAY 173) · recoge ADR-051"""

# --- BACKLOG: cerrar el cabo de enterprise_vendor.pub ----------------------
BACKLOG_VENDORPUB_MARKER = "DEBT-GITIGNORE-VENDOR-PUB-001"
BACKLOG_VENDORPUB_ANCHOR = "## 🔴 DEUDAS ABIERTAS — Seguridad y arquitectura\n"
BACKLOG_VENDORPUB_BLOCK = f"""
### {BACKLOG_VENDORPUB_MARKER} — enterprise_vendor.pub huérfana en raíz (CERRADA DAY 173)
**Severidad:** 🟢 P3 (higiene, sin fuga)
**Estado:** ✅ CERRADA DAY 173 — commit `5c8dc37d`
`enterprise_vendor.pub` (clave pública huérfana de DAY 160, `b2ce9afc`) vivía trackeada en la raíz, distinta de la activa en `enterprise/` (correctamente ignorada por `.gitignore:268`). Verificado que NINGUNA clave privada estuvo nunca trackeada (`git log --all -- '*vendor.key'` vacío) — sin fuga. `git rm --cached` + borrado físico. La activa en `enterprise/` intacta.
**Test de cierre:** `git ls-files | grep enterprise_vendor.pub` solo devuelve la de `enterprise/` (ignorada). ✅

"""

# --- README: actualizar tabla DAY-STATUS -----------------------------------
README_STATUS_OLD = "| Arquitectura | ✅ ADR-046 v4 + AdapterSpec v1 · ✅ ADR-052 v3.2 RATIFICADA (8/8 DAY 173) · ⏳ ADR-050 (MITRE) + ADR-053 (JA3/JA4/BGP) + ADR-051 (Seed Parity) pendientes |"
README_STATUS_NEW = "| Arquitectura | ✅ ADR-046 v4 + AdapterSpec v1 · ✅ ADR-052 v3.2 RATIFICADA · ✅ ADR-051 v2.2 RATIFICADA (Community ID Parity Gate, 8/8 DAY 173) · ⏳ ADR-050 (MITRE) + ADR-053 (JA3/JA4/BGP) pendientes |"

README_NEXTHITO_OLD = "| Próximo hito | DEBTs P0 identidad de flujo (NODEID + FLOWUID + NEO4J-FLOW-KEY) + ADR-051 borrador |"
README_NEXTHITO_NEW = "| Próximo hito | DEBT-NEO4J-FLOW-KEY-001 (esquema Neo4j) → correlation-engine. ADR-051/052 ratificados y archivados |"

# --- README: bloque de Hitos DAY 173 (insertar tras la cabecera existente) --
README_HITOS_MARKER = "**ADR-051 v2.2 RATIFICADA — Consejo 8/8.**"
README_HITOS_ANCHOR = "### Hitos DAY 173 🏛️\n"
README_HITOS_BLOCK = """- {marker} Community ID Parity Gate & Correlation Health. Confirmación de fidelidad sin 3ª deliberación (precedente ADR-052). Renombrado desde "Seed Parity Gate" (el gate valida paridad de `community_id` emitido, de la que el drift de seed es una causa, no la única). Decisión clave: **Oracle Divergence** — si los sensores heterogéneos coinciden entre sí pero no con `pycommunityid`, arranca con WARNING crítico, NO fail-closed (argumento N-version); fail-closed reservado a disparidad ENTRE sensores. Máquinas de estado del gate y de confianza del sensor (DEGRADED estadístico / QUARANTINED binario confirmado). **Diseño ratificado para archivar** — solo el gate de arranque mínimo (cross-check DAY 171/172) está en camino crítico; el resto duerme hasta que exista engine que proteger. Entregable `ADR-051_v2.2.md`.
  - **DEBTs nuevas (corte camino-crítico/diferible):** P1 `DEBT-CID-TEST-VECTORS-001` (fixture compartido con FLOWUID), `DEBT-SEED-GATE-DIAGNOSTIC-001`, `DEBT-CID-STATE-MACHINE-001`, `DEBT-CID-CROSSCHECK-CI-001`; P2 `DEBT-CID-ORACLE-QUORUM-001`, `DEBT-SEED-CHAOS-TEST-001`; P3 diferida `DEBT-SEED-ACTIVE-PROBE-001`. Más `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001` (P1, hallazgo DAY 172: verificar que producción no heredó el reloj inyectado del cross-check).
  - **Higiene DAY 173:** `enterprise_vendor.pub` huérfana destrackeada de la raíz (commit `5c8dc37d`). Verificado sin fuga de clave privada.
""".format(marker=README_HITOS_MARKER)


# ---------------------------------------------------------------------------
# Aplicación
# ---------------------------------------------------------------------------
def apply_backlog(text: str) -> str:
    # 1) Bloque ADR-051 + DEBTs (insertar justo antes de la sección DAY 171)
    if not already_present(text, BACKLOG_ADR051_MARKER):
        anchor = "## ✅ CERRADO DAY 171\n"
        text = text[: text.index(anchor)] + BACKLOG_ADR051_BLOCK + "\n" + text[text.index(anchor):]
    # 2) Estado de DEBT-CORRELATION-SEED-GATE-001
    if BACKLOG_SEEDGATE_OLD in text:
        text = replace_once(text, BACKLOG_SEEDGATE_OLD, BACKLOG_SEEDGATE_NEW,
                            label="BACKLOG seed-gate status")
    # 3) Cierre de enterprise_vendor.pub
    if not already_present(text, BACKLOG_VENDORPUB_MARKER):
        text = insert_after(text, BACKLOG_VENDORPUB_ANCHOR, BACKLOG_VENDORPUB_BLOCK,
                            label="BACKLOG vendor.pub")
    return text


def apply_readme(text: str) -> str:
    if README_STATUS_OLD in text:
        text = replace_once(text, README_STATUS_OLD, README_STATUS_NEW, label="README status row")
    if README_NEXTHITO_OLD in text:
        text = replace_once(text, README_NEXTHITO_OLD, README_NEXTHITO_NEW, label="README next-hito row")
    if not already_present(text, README_HITOS_MARKER):
        text = insert_after(text, README_HITOS_ANCHOR, README_HITOS_BLOCK, label="README hitos DAY173")
    return text


def build_new_prompt() -> str:
    """El prompt de continuidad se REESCRIBE entero — es un documento de estado, no acumulativo.
    Apunta DAY 174 al correlation-engine vía DEBT-NEO4J-FLOW-KEY-001."""
    return """DAY 174 — aRGus NDR (arXiv:2604.04952)

ÚLTIMO HITO DAY 173: ADR-051 v2.2 RATIFICADA (Consejo 8/8, confirmación de fidelidad, sin 3ª deliberación)
— Community ID Parity Gate & Correlation Health. Junto con ADR-052 v3.2 (ratificada el mismo día), la
arquitectura de identidad/correlación queda CERRADA Y ARCHIVADA. DAY 173 también cerró el cabo de
enterprise_vendor.pub (commit 5c8dc37d). Tag estable v1.0.0-day166. Rama feature/day170-community-id-protobuf.

═══════════════════════════════════════════════════════════════════════════════
EL PLAN DEL MES — leerlo antes de cualquier otra cosa
═══════════════════════════════════════════════════════════════════════════════
La cadena de valor científico que define el próximo mes (ADR-048):
    correlation-engine -> ingesta al grafo Neo4j con relaciones -> sesiones MITRE
    -> datasets de cada fase -> plugins ensemble (curva F1 multi-fuente).
Esa curva F1 es la contribución publicable para Andrés/UEx.

LECCIÓN DAY 173 (no repetir): dos días seguidos (052 ayer, 051 hoy) se fueron en ADRs de arquitectura
cada vez más finos. El Consejo diverge hacia el detalle por naturaleza — cada sabio añade un caso de
borde, y sumados producen robustez de producción para un sistema que aún no se ha construido. RESISTIR
eso. La sobreingeniería se siente como rigor en el momento; la diferencia es si lo que endureces YA EXISTE.
A partir de DAY 174 toca CONSTRUIR el engine, no diseñar más alrededor de él.

═══════════════════════════════════════════════════════════════════════════════
PRIMERO DE TODO DAY 174 — commit/push de DAY 173
═══════════════════════════════════════════════════════════════════════════════
Commitear en la misma piedra: ADR-051_v2.2.md (+ cadena v2.1/v2/v1 + síntesis), las entradas nuevas en
docs/BACKLOG.md (sección RATIFICADO DAY 173 ADR-051 + 8 DEBTs nuevas), README.md (DAY-STATUS + Hitos DAY 173),
y este prompt actualizado. El commit de higiene de enterprise_vendor.pub (5c8dc37d) ya está pusheado.
Verificar antes: git status; git diff --cached | grep -iE 'PRIVATE KEY|vendor.key|password|token';
grep -E '^## ✅ (CERRADO|RATIFICADO) DAY' docs/BACKLOG.md | sort | uniq -d (vacío).
Docs puras = excepción razonada al PR obligatorio (igual que ADR-052), pero el commit incluye solo docs.

═══════════════════════════════════════════════════════════════════════════════
EL SIGUIENTE PASO REAL — DEBT-NEO4J-FLOW-KEY-001 (P0 esquema)
═══════════════════════════════════════════════════════════════════════════════
Esto es lo que DESBLOQUEA el correlation-engine. Es el primer eslabón de la cadena del mes y NO es de
ADR-051 — es de ADR-052 (que lo ratifica). Trabajo de ESQUEMA, no de ADR. Antes de poblar el grafo:
  - flow_uid = base64(BLAKE2b(node_id || community_id || uint64_be(flow_start_window) [|| seq_in_window]))
    con crypto_generichash (libsodium 1.0.19). node_id = string canónico declarado (NO keypair efímero).
  - node_id propiedad OBLIGATORIA en :NetworkFlow, :Alert, :TelemetryEvent.
  - Constraint compuesto nativo Neo4j 5.x. Decidirlo con el grafo VACÍO es gratis; retrofitear con datos
    en producción es doloroso (unánime Consejo DAY 170).
  - Correlación intra-nodo por community_id (propiedad indexada); identidad/dedup inter-nodo por flow_uid.
TEST DE CIERRE: dos flujos misma 5-tupla en nodos distintos -> flow_uid distinto. Misma 5-tupla reciclada
en el tiempo en el mismo nodo -> flow_uid distinto.
DEPENDE DE (ambas P0, también de ADR-052, hacer en este orden):
  - DEBT-NODEID-CRYPTO-IDENTITY-001 — node_id = string declarado en inventario firmado, no keypair.
  - DEBT-FLOWUID-CANONICAL-ENCODING-001 — codificación canónica BLAKE2b + paridad C++/Python sobre la
    MISMA versión de libsodium (mismo patrón que pycommunityid). Caso 2-sensores misma 5-tupla -> distinto.
    Su batería de vectores es COMPARTIDA con DEBT-CID-TEST-VECTORS-001 (ADR-051) — no duplicar.

PRIORIDAD DAY 174 (en orden):
1. commit/push DAY 173 (arriba).
2. DEBT-NODEID-CRYPTO-IDENTITY-001 + DEBT-FLOWUID-CANONICAL-ENCODING-001 (P0) — la pieza de identidad
   que el esquema necesita. Paridad C++/Python verificable contra vectores.
3. DEBT-NEO4J-FLOW-KEY-001 (P0 esquema) — flow_uid + node_id obligatorio + constraint Neo4j 5.x.
   Bloquea el diseño del correlation-engine. CONSTRUCCIÓN, no diseño.
4. DEBT-ARGUSPP-COUNTER-DUMP-001 (P1) — volcado de contadores de aRGus a fichero parseable. Lo necesita
   el health-check de orphan_rate (Fase 2 de ADR-051) Y la cadena ADR-048. 1 sesión.
5. B = DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1) — wall-clock de aparición, 2-3 formas de flujo. Entorno
   reproducible (make crosscheck-up). Sesión propia. Recibe los inputs de calibración de ADR-051 §5.3.
6. ADR-050 (MITRE) — borrador (arrastrado, P1 para la cadena del mes). 6 vectores + bootstrap víctima +
   corrección cripto telemetría. Es el ground truth de los datasets. Trabajo de CABEZA — fresco.
7. DEBT-ARGUSPP-SURICATA-001 (P1) — Suricata en EMECAS + eve.json -> correlation-engine (Fase 2 ADR-048).
8. RSS bajo carga (arrastrado) — pipeline + tcpreplay escalonado, mide CPU/RAM 4 fuentes -> tiers RPi5/N100
   (DEBT-ARGUSPP-RESOURCE-001). Apagar ARGUS_CID_CROSSCHECK=1 para medir el hot path real.
9. DEBT-CMAKE-GRAPH-INVARIANTS-001 (P1, arrastrado) — lint CI targets duplicados. ADR-028 propuesto.

ADR-051 — DEBTs GENERADAS (todas DIFERIBLES salvo donde se indique; duermen hasta que exista engine):
- DEBT-CID-TEST-VECTORS-001 (P1, camino crítico, fixture compartido con FLOWUID) — batería V1-V4.
- DEBT-SEED-GATE-DIAGNOSTIC-001 (P1, camino crítico) — diagnóstico verbose + runbook.
- DEBT-CID-STATE-MACHINE-001 (P1) — máquinas de estado gate + confianza sensor.
- DEBT-CID-CROSSCHECK-CI-001 (P1) — crosscheck-up/run en CI (requiere Jenkins hardware FEDER).
- DEBT-CID-ORACLE-QUORUM-001 (P2) — oráculo dos niveles + quórum N>=3.
- DEBT-SEED-CHAOS-TEST-001 (P2) — pruebas de caos de drift.
- DEBT-SEED-ACTIVE-PROBE-001 (P3, DIFERIDA) — sonda activa, mitiga latencia orphan_rate en valles.
- DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001 (P1) — verificar que producción no heredó el reloj inyectado
  del build de cross-check (community_id_log.cpp). Bug latente, hallazgo DAY 172.

═══════════════════════════════════════════════════════════════════════════════
CONSENSO DEL CONSEJO DAY 170 — base de la arquitectura de correlación (ya ratificada en 051+052)
═══════════════════════════════════════════════════════════════════════════════
P1 (Wazuh <-> red): (A)+(C). Doble arista Neo4j. flujo<->flujo por community_id; host<->flujo por
   host_id/agent_id CANÓNICO (nunca IP cruda) + ventana temporal MÁS LAXA causal-bidireccional. NAT =
   menú de mecanismos, SIEMPRE anotando método+confianza. -> ADR-052 (RATIFICADA).
P2 (seed): gate de arranque P0 data-plane + health-check huérfanos. -> ADR-051 (RATIFICADA v2.2).
P3 (identidad flujo): flow_uid = hash(node_id || community_id || flow_start_window). community_id =
   propiedad indexada, nunca identidad de nodo. -> ADR-052 (RATIFICADA) + DEBT-NEO4J-FLOW-KEY-001 (P0).

HALLAZGO TIMESTAMPS DAY 172 (sigue vigente): Suricata ancla a FIN de flujo (flow.timeout), Zeek a INICIO
de conexión, aRGus reloj sintético. Spreads 9.7ms-116s. NO comparables. Correlación temporal por WALL-CLOCK
de aparición (time.monotonic en host), nunca por ts interno. Los 5/10/20s de ADR-046 v4 son casi seguro
muy bajos para Suricata en flujos largos -> los recalibra B (DEBT-CORRELATION-TIMEOUT-CALIB-001).

VMs (autostart: false — arrancar individualmente):
defender 192.168.100.1 aRGus completo · suricata .10 (7.0.10, community-id:yes seed 0, PROMISC)
zeek .11 (8.2.0, community-id-logging seed 0, PROMISC, escribe en /opt/zeek/spool/zeek/) · wazuh .12 (4.x)
client .50 (tcpreplay + nmap/hydra/sqlmap/atomic-red-team)
NOTA: wazuh estaba 'aborted' en DAY 172 (no bloquea cross-check de los 3 sensores de red).

ARRANQUE CROSS-CHECK (reproducible, DAY 172):
- make crosscheck-up   # etcd-server-start + test-provision-1 -> trunca 3 logs ->
                       #   sniffer(ARGUS_CID_CROSSCHECK=1) -> zeekctl deploy -> confirma suricata. Idempotente.
- make crosscheck-run  # test-replay-neris -> sleep 45 -> verificador --zeek-conn /opt/zeek/spool/zeek/conn.log.
                       #   exit 2 = anomalías (esperado); exit 1 = fallo real.
- sniffer eBPF: build-active -> build-debug, ./sniffer, NO libpcap. Requiere etcd vivo + claves o aborta.
- diana: 1:IN7uqVpMWxpmuhQTowSQB2XEe0E= sobre flujo Neris 147.32.84.165:1027 -> 74.125.232.195:80.

REGLAS CRÍTICAS:
- community_id: SHA1 (Corelight), NO HMAC-SHA256. Canonicalización byte-idéntica a Zeek/Suricata o el
  join falla en silencio. Oráculo: pycommunityid. Seed 0 idéntico en los 3 (garantizado por provisión).
- flow_uid: BLAKE2b (libsodium 1.0.19), NO la misma función que community_id. node_id = string declarado.
- Oracle divergence (ADR-051): sensores coinciden entre sí pero no con oráculo -> WARNING, arranca.
  Fail-closed SOLO por disparidad entre sensores. (N-version: 3 implementaciones independientes coincidiendo
  es evidencia fuerte de corrección; un oráculo solo discrepante es más probablemente el desfasado.)
- Helper community_id observable: gateado ARGUS_CID_CROSSCHECK=1 (OFF por defecto, coste nulo hot path).
  compute_community_id permanece PURA. Apagar para medir RSS/hot path real.
- Gate de seed: data-plane (lo que el binario EMITE), nunca config JSON/yaml.
- NAT host<->red: SIEMPRE anotar método y confianza en grafo+log. Nunca fallo silencioso por IP no coincidente.
- if(NOT TARGET) obligatorio en bloques CMake condicionales.
- EMECAS = vagrant destroy -f && vagrant up && make bootstrap && make test-all.
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

PRIMER COMANDO DAY 174:
git status   # revisar lo de DAY 173 sin commitear (ADR-051 v2.2 + síntesis, BACKLOG, README, este prompt)
             # commitear todo en la misma piedra tras secret-scan + uniq -d
             # LUEGO: bajar a DEBT-NODEID/FLOWUID/NEO4J-FLOW-KEY. CONSTRUIR el engine, no más ADRs.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="Actualiza docs tras ADR-051 v2.2 (DAY 173).")
    ap.add_argument("--dry-run", action="store_true", help="No escribe; muestra qué haría.")
    ap.add_argument("--check", action="store_true", help="Solo verifica integridad de BACKLOG.")
    args = ap.parse_args()

    # Comprobar que estamos en la raíz del repo
    for p in (BACKLOG, README, PROMPT):
        if not p.exists():
            print(f"ERROR: no encuentro {p}. Ejecuta desde la raíz del repo.", file=sys.stderr)
            return 2

    if args.check:
        try:
            verify_no_dup_sections(read(BACKLOG), BACKLOG)
            print("OK: BACKLOG.md sin cabeceras de cierre duplicadas (uniq -d vacío).")
            return 0
        except EditError as e:
            print(f"FALLO DE INTEGRIDAD:\n{e}", file=sys.stderr)
            return 1

    plan = [
        (BACKLOG, apply_backlog, True),   # True = verificar uniq -d después
        (README, apply_readme, False),
    ]

    # Fase 1: calcular todas las ediciones en memoria. Si algo falla, NO se escribe nada.
    results = []
    try:
        for path, fn, verify in plan:
            original = read(path)
            updated = fn(original)
            if verify:
                verify_no_dup_sections(updated, path)
            results.append((path, original, updated))
        new_prompt = build_new_prompt()
    except EditError as e:
        print(f"ABORTADO (ninguna escritura realizada):\n\n{e}", file=sys.stderr)
        return 1

    # Reporte
    for path, original, updated in results:
        changed = original != updated
        delta = len(updated) - len(original)
        print(f"{path}: {'CAMBIA' if changed else 'sin cambios'} ({delta:+d} chars)")
    print(f"{PROMPT}: REESCRITO COMPLETO (documento de estado, DAY 173 -> DAY 174)")

    if args.dry_run:
        print("\n--dry-run: no se ha escrito nada.")
        return 0

    # Fase 2: backups + escritura
    for path, original, updated in results:
        if original != updated:
            b = backup(path)
            path.write_text(updated, encoding="utf-8")
            print(f"  escrito {path} (backup: {b.name})")
    b = backup(PROMPT)
    PROMPT.write_text(new_prompt, encoding="utf-8")
    print(f"  escrito {PROMPT} (backup: {b.name})")

    # Verificación final de integridad
    verify_no_dup_sections(read(BACKLOG), BACKLOG)
    print("\nOK. Verificación uniq -d post-escritura: vacío.")
    print("Siguiente: git diff  ·  git diff | grep -iE 'PRIVATE KEY|vendor.key|password|token'  ·  commit en una piedra.")
    return 0


if __name__ == "__main__":
    sys.exit(main())