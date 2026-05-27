#!/usr/bin/env python3
"""
aRGus NDR — DAY 166 documentation update script
Actualiza README.md y docs/BACKLOG.md con el estado final de DAY 166.
Uso: python3 update_day166_docs.py [--dry-run]
"""

import sys
import os

DRY_RUN = "--dry-run" in sys.argv

def apply_replacements(path, replacements, label):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    changed = []
    for old, new, name in replacements:
        if old in content:
            content = content.replace(old, new, 1)
            changed.append(name)
        else:
            print(f"  ⚠️  [{label}] No encontrado — '{name}' (verificar manualmente)")

    if DRY_RUN:
        print(f"\n[DRY-RUN] {label}: {len(changed)} sustituciones:")
        for c in changed: print(f"    ✓ {c}")
        return

    if content != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"\n✅ {label}: {len(changed)} sustituciones aplicadas:")
        for c in changed: print(f"    ✓ {c}")
    else:
        print(f"\nℹ️  {label}: sin cambios (¿ya actualizado?)")


# ─── README.md ────────────────────────────────────────────────────────────────

README_PATH = "README.md"

README_REPLACEMENTS = [
    (
        "## Estado actual — DAY 159 (2026-05-21)",
        "## Estado actual — DAY 166 (2026-05-27)",
        "Cabecera Estado actual DAY 159 → DAY 166"
    ),
    (
        "✅ DAY 165: FASE 3 wire header epoch_id (13/13 tests) + EMECAS++ OSS verde + Consejo 8/8 EMECAS++ protocolo 3 actos definido. Branch `feature/day161-enterprise-crypto-integration`. DAY 164: FASE 2a+2b (HttpEtcdRegistrar + CryptoEpochCoordinator, 10/10 tests).",
        "✅ DAY 166: EMECAS++ 3 actos verdes y reproducibles. VaultProvider caché RCU confirmado. vault-fault-inject PASSED. Zero downtime demostrado. Branch `feature/day161-enterprise-crypto-integration` → mergeado a main. Tag `v1.0.0-day166`.",
        "Línea introductoria DAY 165 → DAY 166"
    ),
    (
        "| Tag | pendiente v1.0.0-day166 |",
        "| Tag | v1.0.0-day166 |",
        "DAY-STATUS Tag: pendiente → definitivo"
    ),
    (
        "**Tag activo:** `v0.9.3-day158` | **Branch activa:** `main`",
        "**Tag activo:** `v1.0.0-day166` | **Branch activa:** `main`",
        "Tag activo v0.9.3-day158 → v1.0.0-day166"
    ),
    (
        "  - ✅ DAY 166: **EMECAS++ 3 actos verdes · merge enterprise a main · VaultProvider caché RCU confirmado · vault-fault-inject PASSED · Zero downtime demostrado** 🎉\n  - 🔜 DAY 166+: **VaultProvider retry/cache + test-e2e-vault Acto I + EMECAS++ 3 actos**",
        "  - ✅ DAY 166: **EMECAS++ 3 actos verdes · merge enterprise a main · VaultProvider caché RCU confirmado · vault-fault-inject PASSED · Zero downtime demostrado · Tag v1.0.0-day166** 🎉\n  - 🔜 DAY 167: **BACKLOG-CI-ENTERPRISE-001 (Jenkins gate `make emecas++`) + ADR-048 F2 (DEBT-ARGUSPP-NTP-001 + DEBT-ARGUSPP-COMMUNITY-ID-001) + DEBT-ARGUSPP-SURICATA-001**",
        "Milestones: DAY 166 definitivo + DAY 167 siguiente"
    ),
]

# ─── docs/BACKLOG.md ──────────────────────────────────────────────────────────

BACKLOG_PATH = "docs/BACKLOG.md"

BACKLOG_REPLACEMENTS = [
    (
        "BACKLOG-CRYPTO-E2E-ROTATION-001 (FakeEtcd):     60% 🟡  DAY 165 — FakeEtcdServer 5/5 + test-e2e-vault PASSED; live rotation pendiente",
        "BACKLOG-CRYPTO-E2E-ROTATION-001:                 100% ✅  DAY 166 — Live rotation Acto II+III verdes, gate completado",
        "BACKLOG-CRYPTO-E2E-ROTATION-001: 60% → 100%"
    ),
    (
        "BACKLOG-EMECAS-ENTERPRISE-001:                   0% ⏳  P0 — protocolo EMECAS++ 3 actos, bloqueante de merge",
        "BACKLOG-EMECAS-ENTERPRISE-001:                   100% ✅  DAY 166 — EMECAS++ 3 actos verdes, merge a main",
        "BACKLOG-EMECAS-ENTERPRISE-001: 0% → 100%"
    ),
    (
        "DEBT-VAULT-RECONNECT-001:                         0% ⏳  P0 — VaultProvider retry/cache estado desconocido (inspeccionar DAY 166)",
        "DEBT-VAULT-RECONNECT-001:                        100% ✅  DAY 165/166 — caché inline preexistente confirmada, Acto III no requirió código nuevo",
        "DEBT-VAULT-RECONNECT-001: 0% → 100%"
    ),
    (
        "DEBT-CRYPTO-NEGATIVE-TEST-001:                    0% ⏳  P0 — test negativo epoch_id incorrecto, bloqueante pre-merge",
        "DEBT-CRYPTO-NEGATIVE-TEST-001:                   100% ✅  DAY 166 — test epoch_id=0xFFFF rechazado, EMECAS++ verde",
        "DEBT-CRYPTO-NEGATIVE-TEST-001: 0% → 100%"
    ),
]

# ─── ejecución ────────────────────────────────────────────────────────────────

print("aRGus NDR — DAY 166 documentation update")
print("=" * 50)

for path, replacements, label in [
    (README_PATH, README_REPLACEMENTS, "README.md"),
    (BACKLOG_PATH, BACKLOG_REPLACEMENTS, "docs/BACKLOG.md"),
]:
    if not os.path.exists(path):
        print(f"\n❌ No encontrado: {path}")
        continue
    apply_replacements(path, replacements, label)

print("\n" + ("=" * 50))
if DRY_RUN:
    print("DRY-RUN completado. Ningún fichero modificado.")
else:
    print("Actualización completada. Verificar con: git diff README.md docs/BACKLOG.md")