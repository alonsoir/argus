#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_day176.py — Inserta el material de DAY 176 en los tres ficheros de continuidad.

Targets:
  docs/BACKLOG.md                       -> 4 deudas nuevas DAY 176 + decisiones Consejo (ADR-055)
  README.md                             -> Lecciones operativas (DAY 176)
  docs/continuity/PROMPT_CONTINUE_CLAUDE.md -> bloque de ARRANQUE DAY 177 (prepend)

Propiedades:
  - IDEMPOTENTE: cada bloque lleva un centinela; si ya existe, se omite. Correrlo dos
    veces no duplica nada (lección DAY 158: idempotencia por bloque centinela).
  - BACKUP: crea <fichero>.bak antes de tocar cada uno.
  - DRY-RUN: --dry-run muestra qué haría sin escribir.

Uso (desde la raíz del repo, el directorio que contiene README.md y docs/):
  python3 update_day176.py
  python3 update_day176.py --dry-run
  python3 update_day176.py --root /ruta/al/repo

NOTA: el primer comando DAY 177 (grep de test_correlation_roundtrip) NO estaba en el
material recibido. El bloque del PROMPT deja un placeholder visible para que lo rellenes.
"""

import argparse
import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# BLOQUES DE CONTENIDO
# ─────────────────────────────────────────────────────────────────────────────

# --- docs/BACKLOG.md ---------------------------------------------------------
BACKLOG_SENTINEL = "## 🆕 Entradas DAY 176 — Deudas del cableado de injectors + ADR-055"
BACKLOG_ANCHOR = "## ✅ CERRADO DAY 175 — Zona bronce correlation_v1 cableada + verificada E2E"
BACKLOG_BLOCK = """## 🆕 Entradas DAY 176 — Deudas del cableado de injectors + ADR-055

> Origen: sesión DAY 176 (injectors sintéticos + community_id). Decisiones del Consejo
> de Sabios (8/8) destinadas a **ADR-055** (pendiente de redacción). Voto dividido en Q3
> (ChatGPT 1 vs 7) resuelto por "medir, no votar".
>
> **Q1** → node_id sintético `synth-node-00` (isomorfo). **Q2** → perseguir el gap con
> todos los métodos. **Q3** → medir el golden antes de decidir el orden B-vs-A. **Q4** →
> estrés no bloqueante. **Q5** → extraer la lib como prerrequisito de los adaptadores.
>
> **Nota de numeración:** ADR-053 RESERVADO (JA3/JA4 + TLS profunda + anomalía L3/BGP),
> ADR-054 PENDIENTE (modelo de confianza bronce multi-nodo Ed25519/HMAC). Estas decisiones
> toman **ADR-055**. Verificado contra el BACKLOG antes de asignar.

### DEBT-INJECTOR-NODEID-001 — node_id vacío en injector → flow_uid degenerado
**Severidad:** 🔴 P0 — Alta
**Estado:** ABIERTO — DAY 176 (Consejo 8/8, Q1)
**Componente:** `tools/synthetic_sniffer_injector.cpp` + resto de injectors
El injector deja `node_id` (col 3 del contrato `correlation_v1`) vacío. Como
`flow_uid = hash(node_id ‖ community_id ‖ flow_start_window)`, un `node_id` vacío
degenera el `flow_uid` (identidad no canónica / colisión). Fix: poblar `node_id`
sintético por eje de modo — isomorfo realista → `synth-node-00`; mock
auto-identificable → `synth:node:<id>`. Decisión Alonso/Consejo Q1: el isomorfo usa
`synth-node-00`.
**Test de cierre:** injector isomorfo → `node_id=synth-node-00`, `flow_uid` no
degenerado. Injector mock → `node_id` reconocible como sintético (`synth:node:<id>`),
descartado por el correlation-engine antes de Kuzu.
**Estimación:** 0.5–1 sesión.

### DEBT-INJECTOR-ROWGAP-001 — gap ~8 de 50 filas (no es community_id)
**Severidad:** 🟡 P1 — bloqueante para conteo exacto en CI
**Estado:** ABIERTO — DAY 176 (Consejo 8/8, Q2)
**Componente:** `tools/synthetic_sniffer_injector.cpp` + `CorrelationWriter` (ml-detector)
Con `--attack` aparece un gap de ~8 filas de 50; descartado que sea por `community_id`.
Sospechosos: `dontwait` (no determinista — política NDR de no bloquear el loop de
captura) o el threshold del `CorrelationWriter` (determinista). Consejo Q2: perseguir el
gap con todos los métodos disponibles. Bloqueante para conteo exacto en CI (un bronce
determinista exige N inyectadas → N filas).
**Test de cierre:** inyectar N filas → exactamente N filas en bronce, reproducible en
repeticiones. Causa raíz del gap identificada y documentada.
**Estimación:** 1 sesión (investigación + fix).

### DEBT-LIB-001 — extraer flow/community_id a libs/flow-identity/
**Severidad:** 🟡 P1 — prerrequisito de adaptadores Suricata/Zeek
**Estado:** ABIERTO — DAY 176 (Consejo 8/8, Q5)
**Componente:** `sniffer/src/flow/community_id*` → `libs/flow-identity/`
Extraer el cálculo de `community_id` (hoy en el sniffer) a una librería reutilizable
`libs/flow-identity/`. Refactor mecánico (no cambia el algoritmo). Prerrequisito de los
adaptadores Suricata/Zeek/Wazuh, que necesitan `compute_community_id` sin arrastrar el
sniffer entero.
**Test de cierre:** sniffer y banco de adaptadores enlazan `libs/flow-identity/`;
`community_id` idéntico byte a byte al oráculo `pycommunityid` (sin regresión).
**Estimación:** 1 sesión (refactor mecánico).

### DEBT-STRESS-BRONZE-001 — prueba de estrés del CorrelationWriter
**Severidad:** 🟢 P2 — pre-merge, no bloqueante
**Estado:** ABIERTO — DAY 176 (Consejo 8/8, Q4)
**Componente:** `ml-detector/tests/` — `CorrelationWriter`
Prueba de estrés del `CorrelationWriter`: 10 threads × 10.000 escrituras con asserts de
(1) conteo exacto de filas, (2) 18 comas por fila (19 columnas del contrato
`correlation_v1`), (3) HMAC válido en cada fila. Pre-merge, no bloqueante (Consejo Q4).
**Test de cierre:** 10×10K filas → conteo exacto, cada fila con 18 comas, todas validan
HMAC en tiempo constante.
**Estimación:** 1 sesión.

"""

# --- README.md ---------------------------------------------------------------
README_SENTINEL = "### Lecciones operativas (DAY 176)"
README_ANCHOR = "### Hardened VM (ADR-030 Variant A)"
README_BLOCK = """### Lecciones operativas (DAY 176)

> Lecciones de la sesión de cableado/verificación del bronce. Operacionales, no de diseño.

- **Recetas `make` desde el HOST.** Los targets del Makefile raíz se ejecutan desde el
  anfitrión macOS; envolverlos en `vagrant ssh -c` rompe con `vagrant: not found` (el
  binario `vagrant` no existe dentro del guest). El Makefile ya hace `vagrant ssh -c`
  internamente donde corresponde.
- **Limpiar bronce SIEMPRE con el ml-detector parado.** Secuencia correcta:
  `tmux kill-session` → `rm` del CSV → `make ml-detector-start`. Borrar el fichero en
  caliente deja un inode huérfano (el proceso sigue escribiendo al inode borrado) →
  filas perdidas silenciosamente.
- **El injector necesita `sudo env LD_LIBRARY_PATH=/usr/local/lib`.** Lee `seed.bin`
  (permisos `0400 root`), por lo que requiere `sudo`; y `env LD_LIBRARY_PATH=/usr/local/lib`
  para localizar las `.so` instaladas (libsodium, crypto_provider, etc.).

"""

# --- docs/continuity/PROMPT_CONTINUE_CLAUDE.md -------------------------------
PROMPT_SENTINEL = "ARRANQUE DAY 177 — LEER ESTO PRIMERO"
PROMPT_BLOCK = """═══════════════════════════════════════════════════════════════════════════════
ARRANQUE DAY 177 — LEER ESTO PRIMERO (encima del prompt DAY 175 histórico).
═══════════════════════════════════════════════════════════════════════════════
DAY 176 trabajó los injectors sintéticos que pueblan community_id (camino a un bronce
determinista en CI). De ahí salieron 4 deudas nuevas y las decisiones del Consejo que
alimentan ADR-055.

PRIMER COMANDO DAY 177 — comando 0: resolver el ORDEN (B-vs-A) con datos, no intuición.
¿test_correlation_roundtrip usa filas del injector o de referencia propias? Según eso se
decide si va primero (B) el cambio de col 17 a string simbólico, o (A) los injectors.
NO se decide por voto (Q3: "medir, no votar").

  vagrant ssh -c "grep -rn 'synthetic\\|inject\\|create_synthetic\\|hardcod\\|reference\\|expected\\|fixture' /vagrant/ml-detector/tests/integration/test_correlation_roundtrip* 2>/dev/null; echo '=== como construye las filas ==='; sed -n '1,60p' /vagrant/ml-detector/tests/integration/test_correlation_roundtrip.cpp 2>/dev/null"

DEUDAS NUEVAS DAY 176 (detalle en docs/BACKLOG.md → "Entradas DAY 176"):
- DEBT-INJECTOR-NODEID-001 (P0 Alta): el injector deja node_id (col 3) vacío → flow_uid
  degenerado. Fix: node_id sintético por eje de modo. Q1 → isomorfo usa `synth-node-00`;
  mock usa `synth:node:<id>`.
- DEBT-INJECTOR-ROWGAP-001 (P1, bloqueante CI): gap ~8 de 50 incluso en --attack; NO es
  community_id. Sospechosos: `dontwait` (no determinista) o threshold del CorrelationWriter
  (determinista). Q2 → perseguir con todos los métodos.
- DEBT-LIB-001 (P1): extraer flow/community_id a libs/flow-identity/. Prereq de adaptadores
  Suricata/Zeek. Refactor mecánico. Q5 → es prerrequisito.
- DEBT-STRESS-BRONZE-001 (P2, no bloqueante): estrés CorrelationWriter (10 threads × 10K;
  asserts conteo + 18 comas + HMAC). Q4 → no bloqueante.

DECISIONES DEL CONSEJO (8/8) → ADR-055 (pendiente de redacción):
- Q1: node_id sintético `synth-node-00` (isomorfo).
- Q2: perseguir el gap de filas con todos los métodos.
- Q3: medir el golden ANTES de decidir el orden B-vs-A. Voto dividido (ChatGPT 1 vs 7)
  resuelto por "medir, no votar".
- Q4: prueba de estrés no bloqueante.
- Q5: extraer la lib (DEBT-LIB-001) como prerrequisito de los adaptadores.
NUMERACIÓN: ADR-053 RESERVADO (JA3/JA4 + TLS + BGP) · ADR-054 PENDIENTE (modelo de
confianza bronce multi-nodo Ed25519/HMAC) · ADR-055 = estas decisiones de injectors/golden/lib.

(El prompt DAY 175 completo queda intacto debajo, como histórico.)

"""

# ─────────────────────────────────────────────────────────────────────────────
# MOTOR
# ─────────────────────────────────────────────────────────────────────────────

def apply_edit(path, sentinel, block, anchor=None, prepend=False, dry_run=False):
    """Devuelve un string describiendo la acción tomada."""
    if not os.path.isfile(path):
        return f"  ✗ NO ENCONTRADO: {path}  (¿estás en la raíz del repo? usa --root)"

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if sentinel in content:
        return f"  • SIN CAMBIOS (centinela ya presente): {path}"

    if prepend:
        new_content = block + "\n" + content
        where = "prepend (al inicio del fichero)"
    elif anchor and anchor in content:
        new_content = content.replace(anchor, block + "\n" + anchor, 1)
        where = f"insertado antes del ancla: «{anchor[:48]}…»"
    else:
        # Fallback robusto: append al final con separador claro.
        sep = "\n" if content.endswith("\n") else "\n\n"
        new_content = content + sep + block
        where = "ANCLA NO ENCONTRADA → append al final (revisar a mano)"

    if dry_run:
        return f"  [dry-run] SE MODIFICARÍA: {path}  ({where})"

    # Backup + escritura.
    bak = path + ".bak"
    with open(bak, "w", encoding="utf-8") as f:
        f.write(content)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    return f"  ✓ MODIFICADO: {path}  ({where})  [backup: {bak}]"


def main():
    ap = argparse.ArgumentParser(description="Actualiza ficheros de continuidad con material DAY 176.")
    ap.add_argument("--root", default=".", help="Raíz del repo (por defecto: directorio actual).")
    ap.add_argument("--dry-run", action="store_true", help="Muestra qué haría sin escribir.")
    args = ap.parse_args()

    root = args.root
    backlog = os.path.join(root, "docs", "BACKLOG.md")
    readme = os.path.join(root, "README.md")
    prompt = os.path.join(root, "docs", "continuity", "PROMPT_CONTINUE_CLAUDE.md")

    print(f"Raíz: {os.path.abspath(root)}")
    print(f"Modo: {'DRY-RUN (no escribe)' if args.dry_run else 'ESCRITURA (con backup .bak)'}")
    print()

    edits = [
        ("docs/BACKLOG.md",
         apply_edit(backlog, BACKLOG_SENTINEL, BACKLOG_BLOCK, anchor=BACKLOG_ANCHOR, dry_run=args.dry_run)),
        ("README.md",
         apply_edit(readme, README_SENTINEL, README_BLOCK, anchor=README_ANCHOR, dry_run=args.dry_run)),
        ("docs/continuity/PROMPT_CONTINUE_CLAUDE.md",
         apply_edit(prompt, PROMPT_SENTINEL, PROMPT_BLOCK, prepend=True, dry_run=args.dry_run)),
    ]

    for name, result in edits:
        print(f"[{name}]")
        print(result)
        print()

    if not args.dry_run:
        print("Recordatorio: rellena el placeholder [PEGAR AQUÍ el grep...] en")
        print("docs/continuity/PROMPT_CONTINUE_CLAUDE.md antes de arrancar DAY 177.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
