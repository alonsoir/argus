#!/usr/bin/env python3
"""
update_docs_day148_consejo.py — Consejo DAY 148 + ajustes README NEXT
Uso: python3 update_docs_day148_consejo.py [--dry-run]
"""
import argparse, sys
from pathlib import Path

DRY_RUN = False

def apply(path, old, new, label):
    content = Path(path).read_text()
    if old in content:
        if not DRY_RUN:
            Path(path).write_text(content.replace(old, new, 1))
        print(f"  ✅ {label}")
        return True
    print(f"  ❌ NO ENCONTRADO — {label}")
    return False

BACKLOG = "docs/BACKLOG.md"
README  = "README.md"

# ── BACKLOG: reemplazar placeholder Consejo DAY 148 ──────────────────────────
B1_OLD = """## 📝 Notas del Consejo de Sabios — DAY 148 (pendiente)

> [Ver síntesis Consejo DAY 148 — pendiente de elaborar]"""

B1_NEW = """## 📝 Notas del Consejo de Sabios — DAY 148 (8/8)

> "DAY 148 — Validación offline Suricata irrefutable. Paper v23. DEBT-IRP-FLOAT-TYPES-001 cerrada.
>
> **P1 — Framing de complementariedad (8/8 MANTENER EN ABSTRACT):**
> Consenso unánime: la afirmación es una contribución arquitectónica válida. Los tres sistemas
> operan en capas de encoding distintas (telemetría, firmas, clasificación behavioral) y sus
> outputs son ortogonales — la complementariedad es una inferencia válida de los datos, no una
> promesa de integración. Refinamiento recomendado (ChatGPT, DeepSeek, Kimi, Qwen convergentes):
> cambiar 'are complementary' → 'are architecturally complementary by design'. Una palabra,
> máximo blindaje ante revisores. Acción: aplicar en v24 / próxima revisión. No urgente.
>
> **P2 — DEBT-PARQUET-SCHEMA-001 (8/8 consenso técnico):**
> Granularidad: 8/8 por flow sin excepción. Política de registro: dividido en dos posiciones —
> (4/8: ChatGPT, Mistral, Kimi, Qwen) todos los eventos + relevance_flag para máxima flexibilidad;
> (4/8: Claude, DeepSeek, Grok, Gemini) solo alertas/denies + muestreo 1% de normales. Decisión:
> híbrida — todos los eventos de ml-detector, solo DENY/DROP de firewall-acl-agent. Confirmar
> con datos reales en la sesión Vagrant.
> Tipos Arrow acordados (8/8): int64 epoch ns para timestamps, float32 para scores, utf8
> dictionary-encoded para IDs pseudonimizados, int8/dictionary para enums, int64/int32 para
> contadores.
>
> **P3 — Secuencia DAY 149+ (8/8):**
> DAY 149: A) DEBT-PARQUET-SCHEMA-001 — P0 bloqueante, desbloquea todo ADR-0043.
> DAY 150-152: C) Vault prototype (K_pseudo, Ed25519) — antes que Jenkins.
> DAY 153-155: B) Jenkins seed distribution.
> DAY 156+: D) ARM64 scope — solo si A+B+C verdes. No portar antes de estabilizar.
> Buffer E: ½ día cada 10 días de desarrollo intenso.
> Dependencia oculta crítica (Qwen + DeepSeek): contactar Dr. Andrés Caro Lindo ESTA SEMANA
> para iniciar DEBT-LEGAL-DATA-RETENTION-001 en paralelo. El proceso jurídico tiene latencia
> externa independiente del trabajo técnico.
>
> 'El schema Parquet no es un detalle de implementación — es el contrato de soberanía entre
> el edge y el centro.' — Qwen · DAY 148"
> — Consejo de Sabios (8/8) · DAY 148"""

# ── README: actualizar sección NEXT con secuencia confirmada ─────────────────
R1_OLD = """### 🔜 NEXT — DAY 146+

| Priority | Task |
|---|---|
| 🔴 P0 | DEBT-PARQUET-SCHEMA-001 — validar schema Parquet contra CSVs reales en Vagrant |
| 🟡 P1 | DEBT-JENKINS-SEED-DISTRIBUTION-001 — pre-FEDER |
| 🟡 P1 | DEBT-CRYPTO-MATERIAL-STORAGE-001 — HashiCorp Vault prototype |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |
| 🟡 P1 | DEBT-IRP-PROB-CONJUNTA-001 — función probabilidad conjunta multi-señal |"""

R1_NEW = """### 🔜 NEXT — DAY 149+ (secuencia confirmada Consejo 8/8)

| Priority | Task |
|---|---|
| 🔴 P0 | **DAY 149** — DEBT-PARQUET-SCHEMA-001: CSVs reales Vagrant → schema Arrow v1.0 → ADR-0043 D4b |
| 🟡 P1 | **DAY 150-152** — DEBT-CRYPTO-MATERIAL-STORAGE-001: Vault prototype (K_pseudo + Ed25519) |
| 🟡 P1 | **DAY 153-155** — DEBT-JENKINS-SEED-DISTRIBUTION-001: CI/CD seed distribution |
| 🟡 P1 | **DAY 156+** — feature/adr029-variant-c-arm64: solo si A+B+C verdes |
| 🟡 P1 | **Esta semana** — Email Dr. Andrés Caro Lindo: iniciar DEBT-LEGAL-DATA-RETENTION-001 |"""

def main():
    global DRY_RUN
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    DRY_RUN = args.dry_run
    if DRY_RUN:
        print("🔍 DRY-RUN")

    ok = True
    print("── BACKLOG.md ─────────────────────────────────────────────────────")
    ok &= apply(BACKLOG, B1_OLD, B1_NEW, "Notas Consejo DAY 148")

    print("── README.md ──────────────────────────────────────────────────────")
    ok &= apply(README, R1_OLD, R1_NEW, "NEXT section secuencia DAY 149+")

    if ok:
        print("\n✅ OK" if not DRY_RUN else "\n✅ Dry-run OK")
    else:
        print("\n❌ Revisar marcadores")
        sys.exit(1)

if __name__ == '__main__':
    main()
