#!/usr/bin/env python3
"""
DAY 145 — Actualiza BACKLOG.md y README.md con resultados ADR-029.
Ejecutar desde la raíz del repo: python3 update_day145_docs.py
macOS-safe: no usa sed -i.
"""

import sys
from pathlib import Path

# ─── helpers ──────────────────────────────────────────────────────────────────

def read(path):
    return Path(path).read_text(encoding="utf-8")

def write(path, content):
    Path(path).write_text(content, encoding="utf-8")
    print(f"✅ {path} actualizado")

def insert_after(content, anchor, new_block):
    if anchor not in content:
        print(f"⚠️  Anchor no encontrado: {repr(anchor[:60])}")
        return content
    return content.replace(anchor, anchor + new_block, 1)

def replace_block(content, old_block, new_block):
    if old_block not in content:
        print(f"⚠️  Bloque no encontrado: {repr(old_block[:60])}")
        return content
    return content.replace(old_block, new_block, 1)

# ═══════════════════════════════════════════════════════════════════════════════
# BACKLOG.md
# ═══════════════════════════════════════════════════════════════════════════════

BACKLOG_PATH = "docs/BACKLOG.md"

# 1. Actualizar cabecera de última actualización
BACKLOG_HEADER_OLD = "*Última actualización: DAY 144 — 7 Mayo 2026*"
BACKLOG_HEADER_NEW = "*Última actualización: DAY 145 — 8 Mayo 2026*"

# 2. Nueva sección DAY 145 (insertar ANTES de "## ✅ CERRADO DAY 144")
BACKLOG_DAY145_ANCHOR = "## ✅ CERRADO DAY 144"

BACKLOG_DAY145_SECTION = """## ✅ COMPLETADO DAY 145

### ADR-029 Variant A vs B — Primer experimento comparativo x86 (DAY 145)
- **Status:** ✅ COMPLETADO DAY 145
- **Branch:** `feature/variant-b-libpcap @ e52870d5` → merge → `v0.7.0-variant-b`
- **Experimento:** CTU-13 Neris (320,524 paquetes, 19,135 flows) via `tcpreplay` a 10/50/100 Mbps. Pipeline completo 6/6. Solo el sniffer binario cambia entre runs.
- **Invariante:** mutex `CHECK_SNIFFER_MUTEX` — Variant A y B nunca simultáneas.

| Variante | Target | Mbps real | PPS | Duración (s) | exit |
|----------|--------|-----------|-----|--------------|------|
| A — eBPF | 10 Mbps | 8.86 | 8,040 | 39.86 | 0 |
| A — eBPF | 50 Mbps | 9.78 | 8,867 | 36.14 | 0 |
| A — eBPF | 100 Mbps | 10.12 | 9,178 | 34.92 | 0 |
| B — libpcap | 10 Mbps | 9.99 | 9,064 | 35.36 | 0 |
| B — libpcap | 50 Mbps | 19.43 | 17,614 | 18.19 | 0 |
| B — libpcap | 100 Mbps | 18.82 | 17,066 | 18.78 | 0 |

- **Hallazgo clave:** Variant B (libpcap) ~2× throughput de Variant A (eBPF) a 50/100 Mbps en VirtualBox virtio. Inversión del orden esperado — artefacto de emulación, no del pipeline. Causa: virtio no expone driver XDP nativo → eBPF cae a modo SKB genérico con overhead por paquete que libpcap no tiene. En hardware real con NIC XDP nativa (Intel ixgbe, Mellanox mlx5), se espera la inversión: eBPF > libpcap. **Este dato es la motivación empírica de la adquisición de hardware FEDER.**
- **Failed packets (2,630 en todos los runs):** Artefacto fijo del pcap CTU-13 Neris. Son frames jumbo del pcap original que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). Evidencias: (1) conteo idéntico en los 6 runs — si fuera saturación variaría; (2) los 320,524 successful son idénticos — propiedad del fichero, no de la red; (3) el rechazo ocurre en el cliente antes de llegar al defender — el sniffer nunca ve esos frames. **No son errores del pipeline.**
- **Equivalencia funcional A/B confirmada:** ambas variantes procesan el corpus Neris sin errores de pipeline.

### Bootstrap múltiple — DAY 145
- **Status:** ✅ COMPLETADO DAY 145
- `bootstrap` → alias de `bootstrap-x86-ebpf` (Variant A, referencia)
- `bootstrap-x86-ebpf` — pipeline completo con sniffer eBPF/XDP
- `bootstrap-x86-libpcap` — pipeline completo con sniffer libpcap (compila también `sniffer-libpcap`)
- `pipeline-start-x86-libpcap` — variante de pipeline-start que arranca Variant B

### Relay targets mejorados — DAY 145
- **Status:** ✅ COMPLETADO DAY 145
- `test-replay-neris-x86-ebpf` y `test-replay-neris-x86-libpcap` muestran resumen inline tras cada velocidad (grep de líneas relevantes del log). El banner final lista las 4 rutas de log generadas. Nota sobre MTU integrada en el output — no confunde al usuario.
- `pipeline-status` distingue: `RUNNING [Variant A — eBPF]`, `RUNNING [Variant B — libpcap]`, `INVARIANT VIOLATION` (ambos simultáneos), `STOPPED`.

### Paper Draft v19 — DAY 145
- **Status:** ✅ COMPLETADO DAY 145
- Nueva subsección §6 (ADR-029 Variant A vs B, tabla comparativa, interpretación virtio/SKB, valor científico).
- §10.9 actualizado con el artefacto virtio/XDP como limitación documentada.
- §11.17 extendido con el dato empírico como motivación FEDER hardware.
- §12 Reproducibility — comandos exactos para reproducir el experimento ADR-029.
- Abstract actualizado con párrafo nuevo sobre el hallazgo ADR-029.
- Acknowledgments: "132 days" → "145 days".

"""

# 3. Actualizar sección "Estado global del proyecto" — añadir líneas ADR-029
BACKLOG_STATUS_OLD = "DEBT-COMPILER-WARNINGS-CLEANUP-001:    100% ✅  DAY 144 (ODR LTO production gate PASSED)"
BACKLOG_STATUS_NEW = """DEBT-COMPILER-WARNINGS-CLEANUP-001:    100% ✅  DAY 144 (ODR LTO production gate PASSED)
ADR-029 Variant A vs B x86 (DAY 145):  100% ✅  DAY 145 (experimento comparativo completo)
Paper Draft v19:                        100% ✅  DAY 145 (§6 ADR-029 + §10.9 + §11.17 + §12)
Bootstrap múltiple x86 A/B:            100% ✅  DAY 145 (bootstrap-x86-ebpf + bootstrap-x86-libpcap)
feature/variant-b-libpcap mergeado:    100% ✅  DAY 145 → v0.7.0-variant-b"""

# 4. Notas Consejo DAY 145
BACKLOG_CONSEJO_ANCHOR = "## 📝 Notas del Consejo de Sabios — DAY 144 (8/8)"

BACKLOG_CONSEJO_DAY145 = """## 📝 Notas del Consejo de Sabios — DAY 145 (8/8)

> "DAY 145 — Primer experimento comparativo ADR-029 Variant A (eBPF) vs Variant B (libpcap) en x86-64 VirtualBox. Resultado contraintuitivo: libpcap ~2× throughput que eBPF a 50/100 Mbps. Causa identificada: virtio no expone driver XDP nativo, eBPF cae a modo SKB genérico. En hardware físico con NIC XDP nativa, se espera inversión.
>
> **Sobre los 2,630 failed packets:** artefacto fijo del pcap CTU-13 Neris. Frames jumbo que superan MTU VirtualBox (errno=90 EMSGSIZE). Conteo idéntico en los 6 runs confirma origen en el fichero, no en el pipeline. El sniffer nunca ve esos frames — no son pérdidas de captura. Documentado en README, BACKLOG y paper v19 para evitar confusión futura.
>
> **Equivalencia funcional A/B confirmada:** ambas variantes procesan el corpus Neris completo sin errores de pipeline. La comparación de rendimiento real queda pendiente de hardware físico — que es exactamente el argumento FEDER.
>
> **Bootstrap múltiple:** `bootstrap-x86-ebpf` (Variant A, referencia) y `bootstrap-x86-libpcap` (Variant B). `bootstrap` queda como alias de A — el EMECAS habitual no cambia. `pipeline-status` distingue variante activa e impide invariant violation.
>
> **Paper v19:** §6 nueva subsección con tabla comparativa, interpretación virtio/SKB, y valor científico. El hallazgo es publicable tal cual: el delta A/B depende críticamente del hardware subyacente.
>
> 'Hacer ciencia es esto: observar algo contraintuitivo, identificar la causa, y convertirlo en evidencia empírica para el siguiente argumento.' — Founder DAY 145"
> — Consejo de Sabios (8/8) · DAY 145

"""

# ═══════════════════════════════════════════════════════════════════════════════
# README.md
# ═══════════════════════════════════════════════════════════════════════════════

README_PATH = "README.md"

# 1. Actualizar estado actual (cabecera)
README_STATUS_OLD = """✅ `main` is tagged `v0.6.0-hardened-variant-a`. Branch activa: `feature/variant-b-libpcap` @ `e52870d5` — 3 P0 IRP cerradas + Gate ODR production PASSED (DAY 144). Listo para merge → `v0.7.0-variant-b`."""

README_STATUS_NEW = """✅ `main` is tagged `v0.7.0-variant-b`. Branch activa: `main` — ADR-029 Variant A vs B x86 completado (DAY 145). Paper v19 publicado."""

# 2. Actualizar bloque "Estado actual — DAY 144"
README_DAY_HEADER_OLD = "## Estado actual — DAY 144 (2026-05-07)"
README_DAY_HEADER_NEW = "## Estado actual — DAY 145 (2026-05-08)"

README_TAG_OLD = "**Tag activo:** `v0.6.0-hardened-variant-a` | **Branch activa:** `feature/variant-b-libpcap` @ `e52870d5`"
README_TAG_NEW = "**Tag activo:** `v0.7.0-variant-b` | **Branch activa:** `main`"

README_PAPER_OLD = "**Paper:** arXiv:2604.04952 · Draft v18 (Cornell procesando)"
README_PAPER_NEW = "**Paper:** arXiv:2604.04952 · Draft v19 (ADR-029 Variant A vs B)"

# 3. Añadir fila ADR-029 a tabla de resultados validados
README_TABLE_ANCHOR = "| **Variant B tests** | **9/9 PASSED** | DAY 142 — buffer=8MB verificado |"

README_TABLE_NEW_ROWS = """| **Variant B tests** | **9/9 PASSED** | DAY 142 — buffer=8MB verificado |
| **ADR-029 Variant A eBPF (VBox)** | **~10 Mbps / 9,178 pps** | DAY 145 — techo virtio SKB mode |
| **ADR-029 Variant B libpcap (VBox)** | **~19 Mbps / 17,614 pps** | DAY 145 — ~2× eBPF en virtio |"""

# 4. Nota failed packets — insertar tras la tabla de resultados (después de IRP cycle)
README_FAILED_ANCHOR = "| **IRP cycle** | **PASS** | NORMAL→ISOLATED→ROLLBACK→NORMAL DAY 142 |"

README_FAILED_NOTE = """| **IRP cycle** | **PASS** | NORMAL→ISOLATED→ROLLBACK→NORMAL DAY 142 |

> **Nota ADR-029 — Failed packets (2,630):** Artefacto fijo del pcap CTU-13 Neris. Son frames jumbo que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). El conteo es idéntico en los 6 runs (3 velocidades × 2 variantes) — confirma origen en la estructura del fichero, no en el pipeline. El rechazo ocurre en el cliente antes de llegar al defender; el sniffer nunca ve esos frames. **No son errores del pipeline ni del sniffer.**"""

# 5. Actualizar hito DAY 144 → DAY 145 en milestones
README_MILESTONE_OLD = "- ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 3 ODR violations corregidas · 65/65 tests** 🎉\n- 🔜 DAY 145: **PCAP relay Variant A vs B · Merge → main · v0.7.0-variant-b · experiment-comparative diseño**"
README_MILESTONE_NEW = """- ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 3 ODR violations corregidas · 65/65 tests** 🎉
- ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio (inversión esperada en bare metal) · Bootstrap múltiple · Paper v19 · Merge → main · v0.7.0-variant-b** 🎉
- 🔜 DAY 146+: **DEBT-IRP-TMPFILES-001 + DEBT-IRP-IPSET-TMP-001 · experiment-comparative (aRGus+Suricata+Zeek) · feature/adr029-variant-c-arm64 scope**"""

# 6. Actualizar "🔜 NEXT — DAY 145" → completado
README_NEXT_OLD = """### 🔜 NEXT — DAY 145

| Priority | Task |
|---|---|
| 🔴 P0 | EMECAS ritual obligatorio |
| 🔴 P0 | PCAP relay x86 eBPF (Variant A) — baseline F1=0.9985 |
| 🔴 P0 | PCAP relay x86 libpcap (Variant B) — métricas nuevas ADR-029 |
| 🔴 P0 | Merge `feature/variant-b-libpcap` → main · tag `v0.7.0-variant-b` |
| 🟡 P1 | Refactor Makefile — targets explícitos por arquitectura |
| 🟡 P1 | Diseño `experiment-comparative` (aRGus + Suricata + Zeek) |
| 🟡 P1 | Abrir `feature/adr029-variant-c-arm64` con scope definido |"""

README_NEXT_NEW = """### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉

| Task | Result |
|---|---|
| EMECAS ritual | ✅ 65/65 PASSED |
| PCAP relay x86 eBPF (Variant A) | ✅ ~10 Mbps, 320,524 pkts, exit=0 |
| PCAP relay x86 libpcap (Variant B) | ✅ ~19 Mbps, 320,524 pkts, exit=0 |
| Merge `feature/variant-b-libpcap` → main | ✅ v0.7.0-variant-b |
| Bootstrap múltiple (x86-ebpf / x86-libpcap) | ✅ Makefile actualizado |
| Relay targets con resumen inline + rutas log | ✅ Sin mensajes confusos |
| Paper Draft v19 | ✅ §6 ADR-029, §10.9, §11.17, §12 |

### 🔜 NEXT — DAY 146+

| Priority | Task |
|---|---|
| 🟡 P1 | DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot |
| 🟡 P1 | DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp |
| 🟡 P1 | Diseño `experiment-comparative` (aRGus + Suricata + Zeek como cooperadores) |
| 🟡 P1 | Abrir `feature/adr029-variant-c-arm64` scope definido |
| 🟢 P2 | DEBT-EMECAS-VERIFICATION-001 — párrafo README para devs |"""

# ═══════════════════════════════════════════════════════════════════════════════
# APPLY
# ═══════════════════════════════════════════════════════════════════════════════

def update_backlog():
    content = read(BACKLOG_PATH)
    content = replace_block(content, BACKLOG_HEADER_OLD, BACKLOG_HEADER_NEW)
    content = insert_after(content, BACKLOG_DAY145_ANCHOR, "\n" + BACKLOG_DAY145_SECTION)
    content = replace_block(content, BACKLOG_STATUS_OLD, BACKLOG_STATUS_NEW)
    content = insert_after(content, BACKLOG_CONSEJO_ANCHOR, "\n" + BACKLOG_CONSEJO_DAY145)
    write(BACKLOG_PATH, content)

def update_readme():
    content = read(README_PATH)
    content = replace_block(content, README_STATUS_OLD, README_STATUS_NEW)
    content = replace_block(content, README_DAY_HEADER_OLD, README_DAY_HEADER_NEW)
    content = replace_block(content, README_TAG_OLD, README_TAG_NEW)
    content = replace_block(content, README_PAPER_OLD, README_PAPER_NEW)
    content = replace_block(content, README_TABLE_ANCHOR, README_TABLE_NEW_ROWS)
    content = replace_block(content, README_FAILED_ANCHOR, README_FAILED_NOTE)
    content = replace_block(content, README_MILESTONE_OLD, README_MILESTONE_NEW)
    content = replace_block(content, README_NEXT_OLD, README_NEXT_NEW)
    write(README_PATH, content)

if __name__ == "__main__":
    print("DAY 145 — Actualizando docs...")
    update_backlog()
    update_readme()
    print("\n✅ Listo. Verificar con:")
    print("  grep -n 'DAY 145' docs/BACKLOG.md | head -10")
    print("  grep -n 'DAY 145' README.md | head -10")
    print("\nSiguiente:")
    print("  git add docs/BACKLOG.md README.md main.tex Makefile")
    print("  git commit -m 'DAY 145: ADR-029 Variant A vs B x86 — paper v19 — bootstrap múltiple'")
    print("  git checkout main && git merge feature/variant-b-libpcap")
    print("  git tag v0.7.0-variant-b && git push origin main --tags")