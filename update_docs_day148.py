#!/usr/bin/env python3
"""
update_docs_day148.py — aRGus NDR DAY 148
Actualiza README.md y docs/BACKLOG.md con el trabajo completado en DAY 148.
Uso: python3 update_docs_day148.py [--dry-run]
"""

import argparse
import sys
from pathlib import Path

DRY_RUN = False

def apply(path, old, new, label):
    content = Path(path).read_text()
    if old in content:
        if not DRY_RUN:
            Path(path).write_text(content.replace(old, new, 1))
        print(f"  ✅ {label}")
        return True
    else:
        print(f"  ❌ NO ENCONTRADO — {label}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────────────────────────────────────

README = "README.md"

R1_OLD = "✅ `main` is tagged `v0.7.1-day147`. Branch activa: `main` — Experimento comparativo tres paradigmas completado (DAY 147). Paper v22 generado."
R1_NEW = "✅ `main` is tagged `v0.7.1-day148`. Branch activa: `main` — Validación offline Suricata irrefutable (DAY 148). Paper v23. DEBT-IRP-FLOAT-TYPES-001 cerrada."

R2_OLD = "## Estado actual — DAY 147 (2026-05-10)"
R2_NEW = "## Estado actual — DAY 148 (2026-05-11)"

R3_OLD = """**Tag activo:** `v0.7.1-day147` | **Branch activa:** `main`
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`
**Paper:** arXiv:2604.04952 · Draft v22 (tres paradigmas: Suricata + Zeek + aRGus + DAY 147)
**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026"""
R3_NEW = """**Tag activo:** `v0.7.1-day148` | **Branch activa:** `main`
**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa`
**Paper:** arXiv:2604.04952 · Draft v23 (offline validation DAY 148 + abstract tres paradigmas + complementariedad)
**FEDER deadline:** 22-Sep-2026 | **Go/no-go:** 1-Ago-2026"""

R4_OLD = "### Hitos DAY 147 🎉"
R4_NEW = """### Hitos DAY 148 🎉
- **Suricata offline validation** — `suricata -r neris.pcap -k none`, 50,010 ET Open rules (251 IRC, 475 botnet/C2, 853 trojan). 323,154 paquetes. 0 firmas ET disparadas. 128 alertas internas de motor. Criterio de Kimi satisfecho — conclusión irrefutable.
- **§8.13 paper** — párrafo "Offline validation with full ruleset enforcement" insertado (DAY 148).
- **§8.14 paper** — framing taxonómico: "decision architecture taxonomies", "measurement layer", "telemetry platform", "Observability does not imply classification".
- **§10 Future Work** — 5 subsecciones completas: baremetal, corpus, acrl, hardened, Zeek Phase 2 (`detect-botnets.zeek`, Intel framework temporal limitation).
- **Tabla §8.2** — fila Zeek 8.1.2 añadida (F1=0.042, Prec=1.000, Recall=0.022).
- **Abstract v23** — tres paradigmas + complementariedad (Zeek telemetry + Suricata signatures + aRGus ML behavioral).
- **arXiv replace v19→v23** — submitted como v3 (submit/7576269).
- **DEBT-IRP-FLOAT-TYPES-001 CERRADA** — `IrpConfig::threat_score_threshold` double→float. Parche IEEE 754 eliminado. EMECAS PROFILE=production ALL TESTS COMPLETE.
- **fix(.gitignore)** — excluir protocol-EMECAS-output-*.md, docs/argus_ndr_v*.pdf, docs/latex/*.zip. Untrack build symlinks.
- **Tag:** `v0.7.1-day148`.

### Hitos DAY 147 🎉"""

R5_OLD = "| DEBT-IRP-FLOAT-TYPES-001 | 🟡 P1 | pre-FEDER (tipos score float/double) |"
R5_NEW = "| DEBT-IRP-FLOAT-TYPES-001 | ✅ CERRADA DAY 148 | float consistente con Detection::confidence (protobuf) |"

R6_OLD = """| Priority | Task |
|---|---|
| 🔴 P0-bloqueante | `suricata -r neris.pcap` offline — verificar 0 alertas (blinda comparativa ante revisores) |
| 🔴 P0-paper | Refinar §8.14: "measurement layer" vs "classification layer" (framing Consejo DAY 147) |
| 🔴 P0-paper | §10 Future Work: añadir Zeek Phase 2 (Intel framework, detect-botnets.zeek) |
| 🟡 P1 | DEBT-IRP-FLOAT-TYPES-001 — unificar tipos score float/double pre-FEDER |
| 🟡 P1 | Tabla §8.2 comparison: añadir fila Zeek 8.1.2 |
| 🟡 P1 | Decisión arXiv replace v22 (tras verificación suricata -r) |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |"""
R6_NEW = """| Priority | Task |
|---|---|
| 🔴 P0 | DEBT-PARQUET-SCHEMA-001 — validar schema Parquet contra CSVs reales en Vagrant |
| 🟡 P1 | DEBT-JENKINS-SEED-DISTRIBUTION-001 — pre-FEDER |
| 🟡 P1 | DEBT-CRYPTO-MATERIAL-STORAGE-001 — HashiCorp Vault prototype |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |
| 🟡 P1 | DEBT-IRP-PROB-CONJUNTA-001 — función probabilidad conjunta multi-señal |"""

R7_OLD = "- ✅ DAY 147: **ADR-0043 v4 ACEPTADO** — Memoria Episódica Distribuida, Consejo 8/8, 4 versiones 🎉"
R7_NEW = """- ✅ DAY 147: **ADR-0043 v4 ACEPTADO** — Memoria Episódica Distribuida, Consejo 8/8, 4 versiones 🎉
- ✅ DAY 148: **Suricata offline irrefutable · Paper v23 · arXiv replace v3 · DEBT-IRP-FLOAT-TYPES-001 cerrada · v0.7.1-day148** 🎉"""

# ─────────────────────────────────────────────────────────────────────────────
# BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────

BACKLOG = "docs/BACKLOG.md"

B1_OLD = "## ✅ CERRADO DAY 147"
B1_NEW = """## ✅ CERRADO DAY 148

### DEBT-IRP-FLOAT-TYPES-001 — Unificar tipos score float/double
- **Status:** ✅ CERRADO DAY 148 — **Commits:** `21b52347` (fix) · `82e81c3f` (untrack symlinks)
- **Fix:** `IrpConfig::threat_score_threshold`: `double 0.95` → `float 0.95f`. Consistente con `Detection::confidence` (protobuf `float`). Parche IEEE 754 (`static_cast<double>(...) < threshold - 1e-6`) eliminado de `batch_processor.cpp` `should_auto_isolate()`. Comparación directa `float < float`.
- **Decisión técnica:** `float` correcto para scores de salida del clasificador ML (0.0-1.0). `double` se mantiene en features de entrada del proto (mediciones de paquetes). Contrato protobuf no modificado.
- **EMECAS:** `make PROFILE=production test-all` — ALL TESTS COMPLETE.
- **Rama:** `fix/debt-irp-float-types-001` → PR #58 → main.

### Paper Draft v23 — DAY 148
- **Status:** ✅ CERRADO DAY 148
- **Cambios:** §8.13 párrafo offline validation (suricata -r -k none, 0 ET signatures). §8.14 framing taxonómico (decision architecture taxonomies, measurement layer, telemetry, observability does not imply classification). §10 Future Work 5 subsecciones (baremetal, corpus, acrl, hardened, Zeek Phase 2 detect-botnets.zeek). Tabla §8.2 fila Zeek 8.1.2. Abstract v23 con complementariedad tres paradigmas.
- **arXiv replace:** v19→v23 submitted como v3 (submit/7576269).

### Experimento Suricata offline — DAY 148 (validación irrefutable)
- **Status:** ✅ COMPLETADO DAY 148
- **Protocolo:** `suricata -r botnet-capture-20110810-neris.pcap -S /var/lib/suricata/rules/suricata.rules -k none`. 323,154 paquetes procesados directamente desde pcap. Sin infraestructura live-capture.
- **Ruleset:** 50,010 reglas ET Open (suricata-update 11 Mayo 2026): 251 IRC, 475 botnet/C2, 853 trojan.
- **Resultado:** 0 firmas ET externas disparadas. 128 alertas internas de motor (stream anomalies, protocol detection) — ninguna constituye detección de amenaza. `eve.json` confirma 0 eventos `event_type: alert` de firma ET.
- **Significado:** Elimina throughput, packet loss y timing como explicaciones alternativas al resultado DAY 146. Conclusión irrefutable: el gap es de cobertura de ruleset, no de metodología.
- **Satisface criterio Kimi** (P1 bloqueante Consejo DAY 147): ✅

### fix(.gitignore) + untrack — DAY 148
- **Status:** ✅ CERRADO DAY 148 — **Commit:** `69cdf144`
- Excluir `protocol-EMECAS-output-*.md`, `docs/argus_ndr_v*.pdf`, `docs/latex/*.zip`.
- Untrack build symlinks: `etcd-server/build`, `rag-ingester/build`, `tools/build`.
- Vagrantfile suricata-comparative: `mkdir -p suricata-offline suricata-nochecksum` en provision.

---

## ✅ CERRADO DAY 147"""

B2_OLD = "DEBT-IRP-FLOAT-TYPES-001:              0% ⏳  P1 pre-FEDER (unificar tipos score float/double)"
B2_NEW = "DEBT-IRP-FLOAT-TYPES-001:              100% ✅  DAY 148 — CERRADA (float consistente, parche IEEE 754 eliminado)"

B3_OLD = "Paper Draft v22:                        100% ✅  DAY 147 (§8.14 tres paradigmas + abstract + conclusion + §13)"
B3_NEW = """Paper Draft v22:                        100% ✅  DAY 147 (§8.14 tres paradigmas + abstract + conclusion + §13)
Paper Draft v23:                        100% ✅  DAY 148 (offline validation + §10 Future Work + abstract complementariedad)
arXiv replace v3 (v19→v23):            100% ✅  DAY 148 (submit/7576269)
Experimento Suricata offline (DAY 148): 100% ✅  DAY 148 (0 ET signatures, 323,154 pkts, irrefutable)"""

B4_OLD = "*DAY 147 — 10 Mayo 2026 · main @ v0.7.1-day147*"
B4_NEW = "*DAY 148 — 11 Mayo 2026 · main @ v0.7.1-day148*"

B5_OLD = "*\"Via Appia Quality — Un escudo que aprende de su propia sombra.\"*"
B5_NEW = """*\"Via Appia Quality — Un escudo que aprende de su propia sombra.\"*

## 📝 Notas del Consejo de Sabios — DAY 148 (pendiente)

> [Ver síntesis Consejo DAY 148 — pendiente de elaborar]"""

# ─────────────────────────────────────────────────────────────────────────────
# EJECUCIÓN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    global DRY_RUN
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    DRY_RUN = args.dry_run

    if DRY_RUN:
        print("🔍 DRY-RUN")

    ok = True
    print(f"── README.md ──────────────────────────────────────────────────────")
    ok &= apply(README, R1_OLD, R1_NEW, "Badge tag v0.7.1-day148")
    ok &= apply(README, R2_OLD, R2_NEW, "Estado actual DAY 148")
    ok &= apply(README, R3_OLD, R3_NEW, "Tag + paper v23")
    ok &= apply(README, R4_OLD, R4_NEW, "Hitos DAY 148")
    ok &= apply(README, R5_OLD, R5_NEW, "DEBT-IRP-FLOAT-TYPES-001 cerrada en tabla")
    ok &= apply(README, R6_OLD, R6_NEW, "NEXT section actualizada")
    ok &= apply(README, R7_OLD, R7_NEW, "Milestone DAY 148")

    print(f"── BACKLOG.md ─────────────────────────────────────────────────────")
    ok &= apply(BACKLOG, B1_OLD, B1_NEW, "Sección CERRADO DAY 148")
    ok &= apply(BACKLOG, B2_OLD, B2_NEW, "Estado global DEBT-IRP-FLOAT-TYPES-001")
    ok &= apply(BACKLOG, B3_OLD, B3_NEW, "Estado global Paper v23 + arXiv replace")
    ok &= apply(BACKLOG, B4_OLD, B4_NEW, "Fecha footer")
    ok &= apply(BACKLOG, B5_OLD, B5_NEW, "Notas Consejo DAY 148 placeholder")

    if ok:
        print("\n✅ Todos los cambios aplicados" if not DRY_RUN else "\n✅ Dry-run OK — todos los marcadores encontrados")
    else:
        print("\n❌ Cambios no encontrados — revisar marcadores")
        sys.exit(1)

if __name__ == '__main__':
    main()
