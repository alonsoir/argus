#!/usr/bin/env bash
# higiene-adr-day198.sh — normalización de nombres de ADR + consolidación debt/.
#
# CONVENCIÓN CANÓNICA:
#   ADR-NNN[-vVERSION]-slug-en-minusculas-con-guiones.md
#   - NNN = 3 dígitos SIEMPRE
#   - versión solo si el fichero la tenía (se CONSERVA, no se colapsa: registro TDH)
#   - sin ':', '—', '→', '·', paréntesis, acentos ni espacios
#
# INVARIANTES:
#   - TODO es `git mv` -> preserva historia (el registro de cómo iterabas con el Consejo).
#   - NADA se borra. NADA se archiva. Las versiones se conservan con sufijo -vN.
#   - Cero ediciones de contenido: medido DAY 198, no hay enlaces markdown a estos
#     ficheros (grep de `](...)` vacío) -> las menciones en prosa siguen válidas.
#
# USO:
#   bash higiene-adr-day198.sh --dry-run    # imprime el plan, NO ejecuta, valida orígenes
#   bash higiene-adr-day198.sh              # ejecuta de verdad
#
#   Correr en la rama de higiene (day198/docs-adr-naming-hygiene), NO en day196.

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

DRY=0
case "${1:-}" in
  --dry-run|-n) DRY=1 ;;
  "") DRY=0 ;;
  *) echo "uso: $0 [--dry-run|-n]"; exit 2 ;;
esac

ERRORS=0
PLANNED=0

safe_mv() {
  local src="$1" dst="$2"
  PLANNED=$((PLANNED+1))
  if [[ ! -e "$src" ]]; then
    echo "  ✗ FALTA ORIGEN: $src"; ERRORS=$((ERRORS+1)); return
  fi
  if [[ -e "$dst" ]]; then
    echo "  ✗ DESTINO YA EXISTE (colisión): $dst"; ERRORS=$((ERRORS+1)); return
  fi
  if [[ "$DRY" -eq 1 ]]; then
    echo "  → git mv \"$src\" \"$dst\""
  else
    git mv "$src" "$dst"; echo "  ✓ $dst"
  fi
}

safe_mkdir() {
  local d="$1"
  if [[ "$DRY" -eq 1 ]]; then
    [[ -d "$d" ]] && echo "  (ya existe: $d)" || echo "  → mkdir -p $d"
  else
    mkdir -p "$d"
  fi
}

[[ "$DRY" -eq 1 ]] && echo "=== MODO DRY-RUN — nada se ejecuta, solo se valida ===" || echo "=== EJECUTANDO ==="
echo "rama actual: $(git branch --show-current)"
echo

echo "== FASE 0: ADR-058 — NO en este PR (va en day196). Recordatorio, no se ejecuta. =="
echo

echo "== FASE A: consolidar docs/debts/ -> docs/debt/ (canónico singular) =="
safe_mv "docs/debts/DEBT-PACKAGE-DEB-001.md"            "docs/debt/DEBT-PACKAGE-DEB-001.md"
safe_mv "docs/debts/DEBT-CONFIG-JINJA2-PIPELINE-001.md" "docs/debt/DEBT-CONFIG-JINJA2-PIPELINE-001.md"
safe_mv "docs/debts/DEBT-DOCS-BACKLOG-DEDUP-001.md"     "docs/debt/DEBT-DOCS-BACKLOG-DEDUP-001.md"
if [[ "$DRY" -eq 0 ]]; then rmdir "docs/debts" 2>/dev/null || echo "  (docs/debts no vacío; revisar a mano)"; fi
echo

echo "== FASE B: mover DEBT-*.md y BACKLOG-*.md fuera de docs/adr/ =="
safe_mv "docs/adr/DEBT-ODR-CI-GATE-001.md"            "docs/debt/DEBT-ODR-CI-GATE-001.md"
safe_mv "docs/adr/DEBT-MAYBE-UNUSED-MIGRATION-001.md" "docs/debt/DEBT-MAYBE-UNUSED-MIGRATION-001.md"
safe_mv "docs/adr/DEBT-LLAMA-API-UPGRADE-001.md"      "docs/debt/DEBT-LLAMA-API-UPGRADE-001.md"
safe_mv "docs/adr/DEBT-GENERATED-CODE-CI-001.md"      "docs/debt/DEBT-GENERATED-CODE-CI-001.md"
safe_mv "docs/adr/DEBT-EMECAS-AUTOMATION-001.md"      "docs/debt/DEBT-EMECAS-AUTOMATION-001.md"
safe_mkdir "docs/backlog"
safe_mv "docs/adr/BACKLOG-ZMQ-TUNING-001 — Optimización Empírica de Parámetros ZeroMQ y Pipeline.md" \
        "docs/backlog/BACKLOG-ZMQ-TUNING-001-optimizacion-empirica-zeromq-pipeline.md"
safe_mv "docs/adr/BACKLOG-CI-ENTERPRISE-001.md" \
        "docs/backlog/BACKLOG-CI-ENTERPRISE-001.md"
safe_mv "docs/adr/BACKLOG-BENCHMARK-CAPACITY-001 — Empirical Capacity Benchmark: eBPF vs libpcap vs ARM64.md" \
        "docs/backlog/BACKLOG-BENCHMARK-CAPACITY-001-empirical-capacity-ebpf-libpcap-arm64.md"
echo

echo "== FASE C: renombrar ADR a formato canónico =="

safe_mv "docs/adr/ADR-0043 - un grafo dirigido, temporal, dinámico, cíclico, versionado y con propiedades.md" \
        "docs/adr/ADR-043-grafo-dirigido-temporal-dinamico-ciclico-versionado-propiedades.md"

safe_mv "docs/adr/ADR-057: Capa de consulta del grafo (Kuzu) bitemporalidad y acceso NL V2.md" \
        "docs/adr/ADR-057-capa-consulta-grafo-kuzu-bitemporalidad-nl-v2.md"

safe_mv "docs/adr/ADR-052 V1 (Multi-node Flow Identity & Host↔Net Correlation).md" \
        "docs/adr/ADR-052-v1-multi-node-flow-identity-host-net-correlation.md"
safe_mv "docs/adr/ADR-052 V2 (Multi-node Flow Identity & Host↔Net Correlation).md" \
        "docs/adr/ADR-052-v2-multi-node-flow-identity-host-net-correlation.md"
safe_mv "docs/adr/ADR-052 V3 (Multi-node Flow Identity & Host↔Net Correlation).md" \
        "docs/adr/ADR-052-v3-multi-node-flow-identity-host-net-correlation.md"
safe_mv "docs/adr/ADR-052 V3.1 (Multi-node Flow Identity & Host↔Net Correlation).md" \
        "docs/adr/ADR-052-v3.1-multi-node-flow-identity-host-net-correlation.md"
safe_mv "docs/adr/ADR-052 V3.2 (Multi-node Flow Identity & Host↔Net Correlation).md" \
        "docs/adr/ADR-052-v3.2-multi-node-flow-identity-host-net-correlation.md"

safe_mv "docs/adr/ADR-051_v1_Seed Parity Gate & Correlation Health.md" \
        "docs/adr/ADR-051-v1-seed-parity-gate-correlation-health.md"
safe_mv "docs/adr/ADR-051_v2_Seed Parity Gate & Correlation Health.md" \
        "docs/adr/ADR-051-v2-seed-parity-gate-correlation-health.md"
safe_mv "docs/adr/ADR-051_v2.1_Seed Parity Gate & Correlation Health.md" \
        "docs/adr/ADR-051-v2.1-seed-parity-gate-correlation-health.md"
safe_mv "docs/adr/ADR-051_v2.2-FINAL_Seed Parity Gate & Correlation Health.md" \
        "docs/adr/ADR-051-v2.2-final-seed-parity-gate-correlation-health.md"

safe_mv "docs/adr/ADR-050 — Metodología de ground truth por emulación adversaria multi-sensor.md" \
        "docs/adr/ADR-050-metodologia-ground-truth-emulacion-adversaria-multi-sensor.md"

safe_mv "docs/adr/ADR-046 V4 — Multi-Source Enriched Pipeline: aRGus++ (NDR-EDR Híbrido Distribuido).md" \
        "docs/adr/ADR-046-v4-multi-source-enriched-pipeline-argus-ndr-edr-hibrido.md"

safe_mv "docs/adr/ADR-045 — VaultClient Decomposition by Composition.md" \
        "docs/adr/ADR-045-vaultclient-decomposition-by-composition.md"

safe_mv "docs/adr/ADR-042-incident-response-recovery-protocol.md" \
        "docs/adr/ADR-042-v1-incident-response-recovery-protocol.md"
safe_mv "docs/adr/ADR-042-incident-response-recovery-protocol.V2.md" \
        "docs/adr/ADR-042-v2-incident-response-recovery-protocol.md"

safe_mv "docs/adr/ADR-041 — Hardware Acceptance Metrics for Hardened Variants (FEDER Baseline).md" \
        "docs/adr/ADR-041-hardware-acceptance-metrics-hardened-variants-feder-baseline.md"

safe_mv "docs/adr/ADR-040 ML PLUGIN RETRAINING CONTRACT.md" \
        "docs/adr/ADR-040-ml-plugin-retraining-contract.md"

safe_mv "docs/adr/ADR-039 Runtime Separation for Production Variants.md" \
        "docs/adr/ADR-039-runtime-separation-production-variants.md"

safe_mv "docs/adr/ADR-037 — Static Analysis Security Hardening: Snyk C++ Findings.md" \
        "docs/adr/ADR-037-static-analysis-security-hardening-snyk-cpp-findings.md"

safe_mv "docs/adr/ADR-035 — etcd-server Alta Disponibilidad.md" \
        "docs/adr/ADR-035-etcd-server-alta-disponibilidad.md"

safe_mv "docs/adr/ADR-034 — Deployment Topology Declarativa.md" \
        "docs/adr/ADR-034-deployment-topology-declarativa.md"

safe_mv "docs/adr/ADR-033 — Institutional Knowledge Capture and Retrieval: Operational, Security and Recovery Knowledge in the RAG System.md" \
        "docs/adr/ADR-033-institutional-knowledge-capture-retrieval-rag-system.md"

safe_mv "docs/adr/ADR-031 — aRGus-seL4-Genode (investigación pura, QEMU, spike técnico previo, XDP como riesgo crítico).md" \
        "docs/adr/ADR-031-argus-sel4-genode-investigacion-qemu-spike-xdp.md"

safe_mv "docs/adr/ADR-030 — aRGus-AppArmor-Hardened (variante simple, Vagrant viable, realista para producción).md" \
        "docs/adr/ADR-030-argus-apparmor-hardened-variante-simple-vagrant.md"

safe_mv "docs/adr/ADR-029: rag-security Plugin Integration (g_plugin_loader + async-signal-safe).md" \
        "docs/adr/ADR-029-rag-security-plugin-integration-async-signal-safe.md"

safe_mv "docs/adr/ADR-028: RAG Ingestion Trust Model (FAISS Integrity & Anti-Poisoning).md" \
        "docs/adr/ADR-028-rag-ingestion-trust-model-faiss-integrity-anti-poisoning.md"

safe_mv "docs/adr/ADR-025: Plugin Integrity Verification (Ed25519 + SHA-256 + TOCTOU-safe dlopen).md" \
        "docs/adr/ADR-025-plugin-integrity-verification-ed25519-sha256-toctou-safe-dlopen.md"

safe_mv "docs/adr/ADR-022 threat model opcion2 descartada.md" \
        "docs/adr/ADR-022-threat-model-opcion2-descartada.md"

safe_mv "docs/adr/ADR-021 deployment topology seed families.md" \
        "docs/adr/ADR-021-deployment-topology-seed-families.md"

safe_mv "docs/adr/ADR-020 crypto mandatory v2.md" \
        "docs/adr/ADR-020-crypto-mandatory-v2.md"

safe_mv "docs/adr/ADR-019 os hardening secure deployment.md" \
        "docs/adr/ADR-019-os-hardening-secure-deployment.md"

safe_mv "docs/adr/ADR-018 ebpf kernel plugin loader.md" \
        "docs/adr/ADR-018-ebpf-kernel-plugin-loader.md"

safe_mv "docs/adr/ADR-016 ebpf runtime kernel telemetry.md" \
        "docs/adr/ADR-016-ebpf-runtime-kernel-telemetry.md"

safe_mv "docs/adr/ADR-015 ebpf program integrity.md" \
        "docs/adr/ADR-015-ebpf-program-integrity.md"

safe_mv "docs/adr/ADR-014 fuzzing strategy.md" \
        "docs/adr/ADR-014-fuzzing-strategy.md"

safe_mv "docs/adr/ADR-013 seed distribution component authentication.md" \
        "docs/adr/ADR-013-seed-distribution-component-authentication.md"

safe_mv "docs/adr/ADR-012 plugin loader architecture.md" \
        "docs/adr/ADR-012-plugin-loader-architecture.md"

echo
echo "================== RESUMEN =================="
echo "operaciones planificadas: $PLANNED"
echo "errores (orígenes faltantes / colisiones): $ERRORS"
if [[ "$ERRORS" -gt 0 ]]; then
  echo "✗ HAY ERRORES — corrige antes de ejecutar sin --dry-run."; exit 1
fi
if [[ "$DRY" -eq 1 ]]; then
  echo "✓ dry-run limpio. Ejecuta sin --dry-run para aplicar."
else
  echo "✓ aplicado. Revisar: git status && git diff --staged --stat"
fi
echo "NOTA: ADR-001..011, 017, 023, 024, 026, 027, 032, 036, 038, 044, 047, 048,"
echo "      049, 055 YA estaban en formato canónico -> no se tocan."