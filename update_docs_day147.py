#!/usr/bin/env python3
"""
update_docs_day147.py — aRGus NDR DAY 147
Actualiza docs/BACKLOG.md y README.md con el trabajo completado en DAY 147:

  README.md:
    1. Tag activo: v0.7.1-day146 → v0.7.1-day147
    2. Estado actual: DAY 146 → DAY 147
    3. Paper: v20 → v22
    4. Hitos DAY 147 (pipeline-status, paper v21/v22, Zeek experiment)
    5. Milestone ✅ DAY 147
    6. Validated Results: añade fila Zeek
    7. NEXT section: actualiza

  BACKLOG.md:
    1. Añade sección ✅ CERRADO DAY 147
    2. Actualiza estado global (paper v22, Zeek experiment)
    3. Añade Consejo DAY 147 notas

Uso:
    python3 update_docs_day147.py [--dry-run]
"""

import argparse
import shutil
import sys
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# README.md CHANGES
# ─────────────────────────────────────────────────────────────────────────────

# 1. Tag line (badge section)
OLD_TAG_BADGE = "✅ `main` is tagged `v0.7.1-day146`. Branch activa: `main` — Experimento comparativo Suricata vs aRGus completado (DAY 146). Paper v20 generado."
NEW_TAG_BADGE = "✅ `main` is tagged `v0.7.1-day147`. Branch activa: `main` — Experimento comparativo tres paradigmas completado (DAY 147). Paper v22 generado."

# 2. Estado actual header
OLD_ESTADO = "## Estado actual — DAY 146 (2026-05-09)"
NEW_ESTADO  = "## Estado actual — DAY 147 (2026-05-10)"

# 3. Tag activo + paper en estado actual
OLD_TAG_ESTADO = """**Tag activo:** `v0.7.1-day146` | **Branch activa:** `main`
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`
**Paper:** arXiv:2604.04952 · Draft v20 (Suricata comparative + DAY 146)
**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026"""
NEW_TAG_ESTADO = """**Tag activo:** `v0.7.1-day147` | **Branch activa:** `main`
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`
**Paper:** arXiv:2604.04952 · Draft v22 (tres paradigmas: Suricata + Zeek + aRGus + DAY 147)
**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026"""

# 4. Hitos DAY 146 → añadir DAY 147 después
OLD_HITOS_146 = """### Hitos DAY 146 🎉
- **EMECAS verde** — 4 deudas técnicas cerradas: DEBT-IRP-TMPFILES-001, DEBT-IRP-IPSET-TMP-001, DEBT-BOOTSTRAP-SNIFFER-VERIFY-001, DEBT-EMECAS-VERIFICATION-001.
- **Experimento comparativo Suricata 6.0.10 vs aRGus NDR** — CTU-13 Neris, mismas condiciones. Suricata: 0 alertas (ET Open no cubre Neris 2011). aRGus: F1=0.9985, Recall=1.0000.
- **Makefile**: `make up-argus`, `make up-suricata`, `make halt-argus`, `make halt-suricata`, `make experiment-suricata-run/results`.
- **Paper Draft v20** generado — nueva §8.13 con comparativa directa, Tabla comparación actualizada con datos empíricos Suricata.
- **Vagrantfile Suricata** operativo — `nictype1 virtio` (fix crítico DHCP NAT), 50,010 reglas ET Open cargadas."""
NEW_HITOS_146 = """### Hitos DAY 146 🎉
- **EMECAS verde** — 4 deudas técnicas cerradas: DEBT-IRP-TMPFILES-001, DEBT-IRP-IPSET-TMP-001, DEBT-BOOTSTRAP-SNIFFER-VERIFY-001, DEBT-EMECAS-VERIFICATION-001.
- **Experimento comparativo Suricata 6.0.10 vs aRGus NDR** — CTU-13 Neris, mismas condiciones. Suricata: 0 alertas (ET Open no cubre Neris 2011). aRGus: F1=0.9985, Recall=1.0000.
- **Makefile**: `make up-argus`, `make up-suricata`, `make halt-argus`, `make halt-suricata`, `make experiment-suricata-run/results`.
- **Paper Draft v20** generado — nueva §8.13 con comparativa directa, Tabla comparación actualizada con datos empíricos Suricata.
- **Vagrantfile Suricata** operativo — `nictype1 virtio` (fix crítico DHCP NAT), 50,010 reglas ET Open cargadas.

### Hitos DAY 147 🎉
- **Bug fix pipeline-status** — pgrep fallback para procesos huérfanos (tmux + pgrep OR). Commit `42c04b06`.
- **Búsqueda ruleset ET Open 2011** — no encontrado en fuentes públicas. Hallazgo clave: Neris CTU-13 escenario 42 usa HTTP C2, no solo IRC. Paper v21 §8.13 actualizado.
- **Experimento Zeek 8.1.2 (tres paradigmas)** — modo offline (`zeek -r pcap`), scripts por defecto, determinístico:
  - Suricata 6.0.10: F1=0.000, TP=0 (sin firmas para Neris 2011)
  - Zeek 8.1.2 (default): F1=0.042, Precision=1.000, TP=14 (SSL::Invalid_Server_Cert)
  - aRGus NDR: F1=0.9985, Recall=1.000, TP=646
- **weird.log**: Zeek observa IRC, HTTP beaconing, SMB lateral movement, spam — sin alertar. Distinción observabilidad vs detección.
- **Paper Draft v21** — §8.13 hallazgos reales DAY 147 + Springer 2023 (signature aging).
- **Paper Draft v22** — §8.14 Three Paradigms (tablas + análisis + §13 reproducibilidad Zeek).
- **Makefile**: `make experiment-zeek-up/run/results`. Infraestructura `experiments/zeek-comparative/`.
- **Tag:** `v0.7.1-day147`."""

# 5. Fila Zeek en Validated Results
OLD_RESULTS_TABLE = """| **F1-score (CTU-13 Neris)** | **0.9985** | Stable across 4 replay runs |
| **Precision** | **0.9969** | |
| **Recall** | **1.0000** | Zero missed attacks (FN=0) |"""
NEW_RESULTS_TABLE = """| **F1-score (CTU-13 Neris)** | **0.9985** | Stable across 4 replay runs |
| **Precision** | **0.9969** | |
| **Recall** | **1.0000** | Zero missed attacks (FN=0) |
| **Suricata 6.0.10 F1 (CTU-13 Neris)** | **0.000** | 0 alerts — ET Open rules retired for 2011 threats |
| **Zeek 8.1.2 F1 (CTU-13 Neris, default)** | **0.042** | Precision=1.000, 14 TP (SSL::Invalid_Server_Cert) |"""

# 6. Milestone ✅ DAY 147
OLD_MILESTONE_146 = "- ✅ DAY 146: **Experimento Suricata comparativo · 0 alertas ET Open vs F1=0.9985 aRGus · Paper v20 §8.13 · v0.7.1-day146** 🎉"
NEW_MILESTONE_146 = """- ✅ DAY 146: **Experimento Suricata comparativo · 0 alertas ET Open vs F1=0.9985 aRGus · Paper v20 §8.13 · v0.7.1-day146** 🎉
- ✅ DAY 147: **Experimento tres paradigmas (Suricata+Zeek+aRGus) · Paper v22 §8.14 · HTTP C2 hallazgo · weird.log behavioral profile · v0.7.1-day147** 🎉"""

# 7. NEXT section
OLD_NEXT = """| 🟡 P1 | DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot |
| 🟡 P1 | DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp |
| 🟡 P1 | Diseño experiment-comparative (aRGus + Suricata + Zeek como cooperadores) |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |
| 🟢 P2 | DEBT-EMECAS-VERIFICATION-001 — párrafo README para devs |"""
NEW_NEXT = """| 🔴 P0-bloqueante | `suricata -r neris.pcap` offline — verificar 0 alertas (blinda comparativa ante revisores) |
| 🔴 P0-paper | Refinar §8.14: "measurement layer" vs "classification layer" (framing Consejo DAY 147) |
| 🔴 P0-paper | §10 Future Work: añadir Zeek Phase 2 (Intel framework, detect-botnets.zeek) |
| 🟡 P1 | DEBT-IRP-FLOAT-TYPES-001 — unificar tipos score float/double pre-FEDER |
| 🟡 P1 | Tabla §8.2 comparison: añadir fila Zeek 8.1.2 |
| 🟡 P1 | Decisión arXiv replace v22 (tras verificación suricata -r) |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |"""

README_CHANGES = [
    ("Tag badge",           OLD_TAG_BADGE,      NEW_TAG_BADGE),
    ("Estado header",       OLD_ESTADO,         NEW_ESTADO),
    ("Tag + paper estado",  OLD_TAG_ESTADO,     NEW_TAG_ESTADO),
    ("Hitos DAY 147",       OLD_HITOS_146,      NEW_HITOS_146),
    ("Results table Zeek",  OLD_RESULTS_TABLE,  NEW_RESULTS_TABLE),
    ("Milestone DAY 147",   OLD_MILESTONE_146,  NEW_MILESTONE_146),
    ("NEXT section",        OLD_NEXT,           NEW_NEXT),
]

# ─────────────────────────────────────────────────────────────────────────────
# BACKLOG.md CHANGES
# ─────────────────────────────────────────────────────────────────────────────

# 1. Sección DAY 147 — insertar antes de ✅ CERRADO DAY 146
OLD_BACKLOG_146_HEADER = "## ✅ CERRADO DAY 146"
NEW_BACKLOG_147_SECTION = """## ✅ CERRADO DAY 147

### Bug fix pipeline-status — pgrep fallback para procesos huérfanos
- **Status:** ✅ CERRADO DAY 147 — **Commit:** `42c04b06`
- **Problema:** sniffer PID visible en `pipeline-health` pero STOPPED en `pipeline-status` (proceso huérfano fuera de tmux).
- **Fix:** OR lógico `tmux has-session || pgrep -x <binary>` para los 6 componentes. Script `fix_pipeline_status.py`.
- **Test de cierre:** `make pipeline-status` muestra 6/6 ✅ incluyendo procesos huérfanos.

### Paper v21 — §8.13 hallazgos reales DAY 147
- **Status:** ✅ CERRADO DAY 147 — **Commit:** `a7bfa0bb`
- **Contenido:** búsqueda infructuosa ruleset ET Open 2011 (Wayback Machine, GitHub ET, SecurityOnion/ossim). Hallazgo HTTP C2: Neris escenario 42 usa HTTP C2, no solo IRC — paradigma gap más profundo que signature aging solo. Añade @article{asad2023perspective} (Springer 2023, DOI 10.1007/s10207-023-00794-9).
- **Script:** `upgrade_to_v21.py` — 7/7 verificaciones verdes.

### Experimento comparativo Zeek 8.1.2 vs aRGus NDR — DAY 147 (tres paradigmas)
- **Status:** ✅ COMPLETADO DAY 147 — **Commit:** `[pending git commit tras branch merge]`
- **Infraestructura:** `experiments/zeek-comparative/` — Vagrantfile (debian/bookworm64, 8192MB, 6vCPU, VirtIO), `parse_results_zeek_v2.py`, `makefile_targets.mk`.
- **Protocolo:** Zeek 8.1.2 en modo offline (`zeek -r neris.pcap local`), scripts por defecto, sin tuning. Tres runs (10/50/100 Mbps) — resultado determinístico idéntico en los tres.

**Resultados (CTU-13 Neris, ground truth: 147.32.84.165, 646 flows maliciosos):**

| Sistema | Paradigma | TP | FP | F1 | Precision | Recall |
|---------|-----------|-----|-----|-----|-----------|--------|
| Suricata 6.0.10 | Signature (ET Open) | 0 | 0 | 0.000 | — | 0.000 |
| Zeek 8.1.2 (default) | Scripted behavioral | 14 | 0 | 0.042 | **1.000** | 0.022 |
| **aRGus NDR** | ML behavioral | **646** | 2 | **0.9985** | 0.997 | **1.000** |

**Hallazgos científicos clave:**
- Zeek Precision=1.000: cada alerta identifica correctamente el host malicioso. Los 6 "FP" originales son CaptureLoss (infraestructura, excluidos de métricas corregidas).
- `weird.log` (182 eventos en host malicioso): `irc_invalid_command:30`, `bad_HTTP_request:31`, `empty_http_request:31`, `unknown_dce_rpc_auth_type:33`, `premature_connection_reuse:28`. Zeek observa todo el perfil behavioral sin alertar.
- `irc_invalid_command:30` confirma IRC presente en la captura — refuta parcialmente el README que describe solo HTTP C2.
- Distinción central: Zeek es una plataforma de observabilidad de red (measurement layer). aRGus es un clasificador behavioral (classification layer). No son competidores — son capas distintas.

**Paper v22:** §8.14 "Three Paradigms" — dos tablas (detección + visibilidad Zeek), análisis espectro paradigmas, §13 reproducibilidad Zeek.
**Scripts creados:** `setup_zeek_experiment.py`, `fix_zeek_makefile.py`, `fix_zeek_offline.py`, `parse_results_zeek_v2.py`, `upgrade_to_v22.py`.

## ✅ CERRADO DAY 146"""

# 2. Actualizar estado global (añadir entradas DAY 147)
OLD_GLOBAL_STATUS_END = """Paper Draft v20:                        100% ✅  DAY 146 (§8.13 Suricata + tab:comparison empírico)"""
NEW_GLOBAL_STATUS_END = """Paper Draft v20:                        100% ✅  DAY 146 (§8.13 Suricata + tab:comparison empírico)
Paper Draft v21:                        100% ✅  DAY 147 (§8.13 hallazgos reales + HTTP C2 + Springer 2023)
Paper Draft v22:                        100% ✅  DAY 147 (§8.14 tres paradigmas + abstract + conclusion + §13)
Experimento Zeek 8.1.2 (DAY 147):     100% ✅  DAY 147 (offline, 3 runs determinísticos, parse_results_zeek_v2.py)
Bug fix pipeline-status pgrep:          100% ✅  DAY 147 (commit 42c04b06)"""

# 3. Consejo DAY 147 — insertar antes de la nota DAY 146
OLD_CONSEJO_146 = """## 📝 Notas del Consejo de Sabios — DAY 146 (8/8)"""
NEW_CONSEJO_147 = """## 📝 Notas del Consejo de Sabios — DAY 147 (8/8)

> "DAY 147 — Experimento de tres paradigmas completado. CTU-13 Neris, condiciones idénticas.
>
> **Resultados:** Suricata 6.0.10: F1=0.000 (sin firmas, comportamiento correcto). Zeek 8.1.2 (default): F1=0.042, Precision=1.000, 14 TP (SSL::Invalid_Server_Cert). aRGus NDR: F1=0.9985, Recall=1.000, 646 TP.
>
> **Consenso P1 — Validez metodológica (7/8):** El modo offline de Zeek es estándar aceptado para pcaps históricos. La asimetría favorece a Zeek (100% paquetes vs Suricata live con 2,630 dropped). Declarar explícitamente en el paper — ya está hecho. Kimi (1/8): ejecutar `suricata -r neris.pcap` offline para blindar completamente la comparativa. Acción: P0 bloqueante DAY 148.
>
> **Consenso P2 — Framing científico (8/8):** Framing correcto y publicable. Refinamiento: usar 'measurement layer' (Zeek) vs 'classification layer' (aRGus) — más preciso que observabilidad/detección (Claude). ChatGPT: 'Observability does not imply classification' como frase del abstract. Kimi: elevar de benchmark a contribución taxonómica (arquitecturas de decisión, no ranking de rendimiento). Qwen: 'registrar el mundo vs juzgarlo automáticamente'. El experimento de tres vías es el único que produce el hallazgo — con dos sistemas sería invisible.
>
> **Consenso P3 — Zeek Phase 2 (7/8 → future work):** Phase 1 out-of-the-box suficiente para arXiv. Phase 2 con Intel framework, threat feeds, detect-botnets.zeek queda como future work explícito en §10. Gemini: feeds de 2026 no encontrarían nada de 2011 — Phase 2 reintroduce el paradigma de firmas. DeepSeek: si hay tiempo, un solo script IRC (detect-botnets.zeek) cierra el flanco del revisor.
>
> **Hallazgo adicional DAY 147:** Búsqueda ruleset ET Open agosto 2011 — no encontrado en fuentes públicas (Wayback Machine, GitHub ET, SecurityOnion, ossim). Neris escenario 42 usa HTTP C2 (no IRC según README), pero weird.log confirma IRC presente (irc_invalid_command:30). El paradigma gap es más profundo que signature aging solo.
>
> **Acciones DAY 148:**
> (1) `suricata -r neris.pcap` — 10 minutos, blinda la comparativa.
> (2) Refinar §8.14: measurement/classification layer.
> (3) §10 Future Work: Zeek Phase 2 con detect-botnets.zeek mencionado.
> (4) DEBT-IRP-FLOAT-TYPES-001 — aplazada de DAY 147.
> (5) Decisión arXiv replace v22.
>
> 'No estamos comparando herramientas — estamos comparando filosofías: registrar el mundo vs juzgarlo automáticamente.' — Qwen · DAY 147"
> — Consejo de Sabios (8/8) · DAY 147

## 📝 Notas del Consejo de Sabios — DAY 146 (8/8)"""

# 4. Fecha última actualización
OLD_BACKLOG_DATE = "*DAY 146 — 9 Mayo 2026 · main @ v0.7.1-day146*"
NEW_BACKLOG_DATE = "*DAY 147 — 10 Mayo 2026 · main @ v0.7.1-day147*"

BACKLOG_CHANGES = [
    ("Sección DAY 147",         OLD_BACKLOG_146_HEADER,   NEW_BACKLOG_147_SECTION),
    ("Estado global DAY 147",   OLD_GLOBAL_STATUS_END,    NEW_GLOBAL_STATUS_END),
    ("Consejo DAY 147",         OLD_CONSEJO_146,          NEW_CONSEJO_147),
    ("Fecha BACKLOG",           OLD_BACKLOG_DATE,         NEW_BACKLOG_DATE),
]

# ─────────────────────────────────────────────────────────────────────────────

def apply_changes(path: Path, changes: list, dry_run: bool) -> bool:
    content = path.read_text(encoding="utf-8")
    ok = True
    for label, old, new in changes:
        if old not in content:
            print(f"  ❌ NO ENCONTRADO — {label}")
            ok = False
        elif dry_run:
            print(f"  🔍 OK — {label}")
        else:
            content = content.replace(old, new, 1)
            print(f"  ✅ Aplicado — {label}")
    if not dry_run and ok:
        path.write_text(content, encoding="utf-8")
    return ok


def main():
    parser = argparse.ArgumentParser(
        description="Actualiza README.md y docs/BACKLOG.md con DAY 147"
    )
    parser.add_argument("--readme",  default="README.md")
    parser.add_argument("--backlog", default="docs/BACKLOG.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    readme  = Path(args.readme)
    backlog = Path(args.backlog)

    for p in (readme, backlog):
        if not p.exists():
            print(f"❌ No se encuentra: {p}")
            sys.exit(1)

    print(f"{'🔍 DRY-RUN' if args.dry_run else '✏️  Escritura'}\n")

    if not args.dry_run:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(readme,  readme.with_suffix(f".bak_{ts}.md"))
        shutil.copy2(backlog, backlog.with_suffix(f".bak_{ts}.md"))
        print(f"📦 Backups creados ({ts})\n")

    print(f"── README.md ({readme}) ─────────────────────────────────")
    readme_ok = apply_changes(readme, README_CHANGES, args.dry_run)

    print(f"\n── BACKLOG.md ({backlog}) ───────────────────────────────")
    backlog_ok = apply_changes(backlog, BACKLOG_CHANGES, args.dry_run)

    if args.dry_run:
        status = "✅ Dry-run OK" if (readme_ok and backlog_ok) else "❌ Cambios no encontrados"
        print(f"\n{status}")
        return

    if readme_ok and backlog_ok:
        print("""
╔════════════════════════════════════════════════════════════╗
║  ✅ README.md y BACKLOG.md actualizados — DAY 147        ║
╠════════════════════════════════════════════════════════════╣
║  Siguiente:                                               ║
║  git add README.md docs/BACKLOG.md                       ║
║  git commit -m "docs: DAY 147 — tres paradigmas + v22"   ║
╚════════════════════════════════════════════════════════════╝""")
    else:
        print("\n❌ Algunos cambios no se aplicaron — revisa los errores.")
        sys.exit(1)


if __name__ == "__main__":
    main()