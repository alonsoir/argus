#!/usr/bin/env bash
set -euo pipefail

echo "=== DAY 157 — Actualizando docs y preparando tag v0.9.2-day157 ==="

# ── 1. Verificar que estamos en la rama correcta ──────────────────────────
BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [[ "$BRANCH" != "feature/day157-autonomy-state-persistence" ]]; then
  echo "❌ Rama incorrecta: $BRANCH"
  echo "   Esperada: feature/day157-autonomy-state-persistence"
  exit 1
fi

# ── 2. Verificar que el working tree está limpio ──────────────────────────
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "❌ Working tree no está limpio. Haz commit o stash primero."
  git status --short
  exit 1
fi

echo "✅ Rama: $BRANCH"
echo "✅ Working tree limpio"

# ── 3. Actualizar README.md ───────────────────────────────────────────────
echo "📝 Actualizando README.md..."

python3 << 'PYEOF'
import re

with open("README.md", "r", encoding="utf-8") as f:
    content = f.read()

# Badge hardened: v0.9.1--day156 → v0.9.2--day157
content = content.replace(
    "Security-v0.9.1--day156-brightgreen",
    "Security-v0.9.2--day157-brightgreen"
)

# Nota superior: tag + branch activa
content = content.replace(
    "✅ `main` is tagged `v0.9.1-day156`. Branch activa: `feature/day157-autonomy-state-persistence` — PR pendiente → `v0.9.2-day157` — Schema Parquet Arrow v1.0, Vault CI/CD pipeline, ADR-044 aprobado (DAY 149).\n**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**",
    "✅ `main` is tagged `v0.9.2-day157`. DAY 157: 4 deudas cerradas (DEBT-AUTONOMY-STATE-PERSISTENCE-001, DEBT-BOOTSTRAP-STATUS-SIGNATURE-001, DEBT-KEYPAIR-LIFECYCLE-PROD-001, DEBT-CRYPTO-RECONCILIATION-001 + staleness guard). Consejo 8/8. EMECAS VERDE.\n**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**"
)

# Estado actual header: DAY 156 (2026-05-18) → DAY 157 (2026-05-19)
content = content.replace(
    "## Estado actual — DAY 156 (2026-05-18)",
    "## Estado actual — DAY 157 (2026-05-19)"
)

# Tag activo + branch
content = content.replace(
    "**Tag activo:** `v0.9.1-day156` | **Branch activa:** `feature/day157-autonomy-state-persistence`",
    "**Tag activo:** `v0.9.2-day157` | **Branch activa:** `main`"
)

# Keypair activo (referencia DAY 156 → DAY 157)
content = content.replace(
    "**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa` *(regenera en cada EMECAS)*\n**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv",
    "**Keypair activo:** `b5b6cbdf67dad75cdd7e3169d837d1d6d4c938b720e34331f8a73f478ee85daa` *(regenera en cada EMECAS)*\n**Paper:** arXiv:2604.04952 · Draft v24 local · v3 en arXiv\n**Principio rector:** calidad sobre fechas — los datasets se generan cuando el pipeline esté listo"
)

# Milestone DAY 157: (pending) → limpio
content = content.replace(
    "- ✅ DAY 157: **4 deudas cerradas · Consejo 8/8 · Staleness guard · Keypair lifecycle prod · Bootstrap firmado · EMECAS VERDE · v0.9.2-day157 (pending)** 🎉",
    "- ✅ DAY 157: **4 deudas cerradas · Consejo 8/8 · Staleness guard · Keypair lifecycle prod · Bootstrap firmado · EMECAS VERDE · v0.9.2-day157** 🎉"
)

# Próxima frontera: actualizar el bloque post-DAY 157
OLD_FRONTERA = """### Próxima frontera — DAY 156+
1. ✅ **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA DAY 156**
2. ✅ **DEBT-AUTONOMY-STATE-PERSISTENCE-001 CERRADA DAY 157**
3. ✅ **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 CERRADA DAY 157**
4. ✅ **DEBT-KEYPAIR-LIFECYCLE-PROD-001 CERRADA DAY 157**
5. ✅ **DEBT-CRYPTO-RECONCILIATION-001 CERRADA DAY 157 (staleness guard B1)**
6. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 P2** — ExecStartPre= + check-bootstrap-status.sh — Estado firmado Ed25519 en `/var/lib/argus/crypto-autonomy-state.json` (Consejo 6/8: fichero regular + fsync, NO tmpfs). Arranque desde AUTONOMOUS si firma válida y timestamp < 24h.
3. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 P1** — Firma Ed25519 en bootstrap status.
4. **DEBT-CRYPTO-AUTONOMY-001 P2** — Máquina de estados EXTENDED_AUTONOMY completa en `etcd-server`.
5. **DEBT-CRYPTO-RECONCILIATION-001 P1** — Handshake de validación al recuperar Vault.
6. **DEBT-ALERTING-EDGE-SOS-001 P1** — Webhook SOS configurable por despliegue.
7. **BACKLOG-BENCHMARK-CAPACITY-001** — Benchmarks sintéticos VirtualBox (baseline) + hardware físico FEDER."""

NEW_FRONTERA = """### Próxima frontera — DAY 158+
1. ✅ **DEBT-AUTONOMY-CRYPTO-INTEGRATION-001 CERRADA DAY 156**
2. ✅ **DEBT-AUTONOMY-STATE-PERSISTENCE-001 CERRADA DAY 157**
3. ✅ **DEBT-BOOTSTRAP-STATUS-SIGNATURE-001 CERRADA DAY 157**
4. ✅ **DEBT-KEYPAIR-LIFECYCLE-PROD-001 CERRADA DAY 157**
5. ✅ **DEBT-CRYPTO-RECONCILIATION-001 CERRADA DAY 157 (staleness guard B1)**
6. **DEBT-BOOTSTRAP-STATUS-SIGNATURE-CONSUMERS-001 P2** — `ExecStartPre=` + `check-bootstrap-status.sh`. Verificar firma Ed25519 antes de iniciar componentes dependientes.
7. **DEBT-CRYPTO-AUTONOMY-001 P2** — Máquina de estados EXTENDED_AUTONOMY completa en `etcd-server`.
8. **DEBT-ALERTING-EDGE-SOS-001 P1** — Webhook SOS configurable por despliegue.
9. **BACKLOG-BENCHMARK-CAPACITY-001** — Benchmarks sintéticos VirtualBox (baseline) + hardware físico FEDER."""

content = content.replace(OLD_FRONTERA, NEW_FRONTERA)

with open("README.md", "w", encoding="utf-8") as f:
    f.write(content)

print("  ✅ README.md actualizado")
PYEOF

# ── 4. Actualizar BACKLOG.md ──────────────────────────────────────────────
echo "📝 Actualizando BACKLOG.md..."

python3 << 'PYEOF'
with open("docs/BACKLOG.md", "r", encoding="utf-8") as f:
    content = f.read()

# Header actualización
content = content.replace(
    "*Última actualización: DAY 156 — 18 Mayo 2026*",
    "*Última actualización: DAY 157 — 19 Mayo 2026*"
)

# Última línea del fichero: (pending merge) → merged
content = content.replace(
    "*DAY 157 — 19 Mayo 2026 · feature/day157-autonomy-state-persistence @ v0.9.2-day157 (pending merge)*",
    "*DAY 157 — 19 Mayo 2026 · main @ v0.9.2-day157*"
)

# Sección "Próxima frontera" del BACKLOG
content = content.replace(
    "### Próxima frontera — DAY 156+",
    "### Próxima frontera — DAY 158+"
)

# Status entries: DEBT-KEYPAIR pendiente → cerrada
content = content.replace(
    "DEBT-KEYPAIR-LIFECYCLE-PROD-001:           0% ⏳  P1 pre-FEDER (3 niveles: dev/staging/prod — Consejo 8/8)",
    "DEBT-KEYPAIR-LIFECYCLE-PROD-001:          100% ✅  DAY 157 — 3 niveles dev/staging/prod, exit 1 en prod sin keypair"
)

with open("docs/BACKLOG.md", "w", encoding="utf-8") as f:
    f.write(content)

print("  ✅ docs/BACKLOG.md actualizado")
PYEOF

# ── 5. Verificar cambios ──────────────────────────────────────────────────
echo ""
echo "=== Diff README.md ==="
git diff README.md | head -60

echo ""
echo "=== Diff docs/BACKLOG.md ==="
git diff docs/BACKLOG.md | head -40

# ── 6. Confirmar antes de continuar ──────────────────────────────────────
echo ""
read -p "¿Continuar con git add + commit + tag + push? [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo "Abortado. Los ficheros ya están modificados — puedes revisarlos."
  exit 0
fi

# ── 7. Commit docs ────────────────────────────────────────────────────────
git add README.md docs/BACKLOG.md
git commit -m "docs(day157): update README and BACKLOG for v0.9.2-day157

- README: tag activo v0.9.2-day157, Estado actual DAY 157, milestone limpio
- BACKLOG: última actualización DAY 157, Próxima frontera DAY 158+,
  DEBT-KEYPAIR-LIFECYCLE-PROD-001 marcada 100% cerrada DAY 157
- Todas las deudas DAY 157 reflejadas: AUTONOMY-STATE-PERSISTENCE,
  BOOTSTRAP-STATUS-SIGNATURE, KEYPAIR-LIFECYCLE-PROD,
  CRYPTO-RECONCILIATION (staleness guard B1)"

echo "✅ Commit docs listo"

# ── 8. Tag v0.9.2-day157 ─────────────────────────────────────────────────
# Si ya existía (del intento anterior sin docs), lo forzamos al nuevo HEAD
if git tag | grep -q "^v0.9.2-day157$"; then
  echo "⚠️  Tag v0.9.2-day157 ya existe — forzando al nuevo HEAD (con docs)"
  git tag -f v0.9.2-day157
else
  git tag v0.9.2-day157
fi

echo "✅ Tag v0.9.2-day157 → $(git rev-parse --short HEAD)"

# ── 9. Push branch + tag ──────────────────────────────────────────────────
echo ""
echo "=== Pushing branch + tag ==="
git push origin feature/day157-autonomy-state-persistence
git push origin v0.9.2-day157 --force  # --force por si ya existía sin docs

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ DAY 157 — Todo listo para el PR                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Próximos pasos:"
echo "  1. Abrir PR: feature/day157-autonomy-state-persistence → main"
echo "  2. Merge (squash o merge commit, según el proyecto)"
echo "  3. Si el tag debe quedar sobre main:"
echo "       git checkout main && git pull"
echo "       git tag -f v0.9.2-day157 && git push origin v0.9.2-day157 --force"