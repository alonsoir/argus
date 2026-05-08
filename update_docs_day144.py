#!/usr/bin/env python3
# update_docs_day144.py — Actualiza README.md y docs/BACKLOG.md con el estado DAY 144
# Ejecutar desde la raíz del repo: python3 update_docs_day144.py

import re
from pathlib import Path

ROOT = Path(__file__).parent

# ─────────────────────────────────────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────────────────────────────────────

readme = ROOT / "README.md"
txt = readme.read_text()

# 1. Estado actual header
txt = txt.replace(
    "## Estado actual — DAY 143 (2026-05-06)",
    "## Estado actual — DAY 144 (2026-05-07)"
)

# 2. Branch commit
txt = txt.replace(
    "**Branch activa:** `feature/variant-b-libpcap` @ `f00b1809`",
    "**Branch activa:** `feature/variant-b-libpcap` @ `e52870d5`"
)

# 3. Pipeline tests
txt = txt.replace(
    "- `make test-all`: ALL TESTS COMPLETE (9/9 sniffer Variant B PASSED)",
    "- `make test-all`: ALL TESTS COMPLETE (65/65 PASSED — 0 FAILED) ✅\n- `make PROFILE=production all`: Gate ODR — ALL COMPONENTS BUILT ✅"
)

# 4. Hitos DAY 142 → añadir DAY 143 y DAY 144
old_hitos = "### Hitos DAY 142 🎉"
new_hitos = "### Hitos DAY 144 🎉\n- **Gate ODR production SUPERADO** — `make PROFILE=production all` limpio. 3 ODR violations reales detectadas y corregidas (anonymous namespace, protobuf stale, -UNDEBUG en tests).\n- **DEBT-IRP-SIGCHLD-001 CERRADA** — `SA_NOCLDWAIT` en `setup_signal_handlers()`. `SigchldTest.NoZombiesAfterNForks` PASSED.\n- **DEBT-IRP-AUTOISO-FALSE-001 CERRADA** — `isolate.json` única fuente de verdad. Campo obligatorio, fallo ruidoso si ausente. `parse_irp()` public. 5 tests nuevos PASSED.\n- **DEBT-IRP-BACKUP-DIR-001 CERRADA** — `/tmp` → `/run/argus/irp/`. AppArmor + provision.sh actualizados. Dry-run PASSED.\n- **DEBT-COMPILER-WARNINGS-CLEANUP-001 PARCIALMENTE CERRADA** — ODR violations bajo LTO.\n\n### Hitos DAY 143 🎉\n- **DEBT-IRP-NFTABLES-001 CERRADA** — IRP completo: config → disparo → fork()+execv() → AppArmor 7/7 enforce → 12/12 tests.\n\n### Hitos DAY 142 🎉"

txt = txt.replace(old_hitos, new_hitos)

# 5. Tabla deuda técnica abierta — marcar cerradas y añadir nuevas
old_debt_table = """| Deuda | Prioridad | Target |
|-------|-----------|--------|
| ~~DEBT-IRP-NFTABLES-001~~ | ✅ CERRADA | DAY 143 |
| DEBT-IRP-SIGCHLD-001 | 🔴 P0 | pre-merge (SA_NOCLDWAIT) |
| DEBT-IRP-AUTOISO-FALSE-001 | 🔴 P0 | pre-merge (auto_isolate false) |
| DEBT-IRP-BACKUP-DIR-001 | 🔴 P0 | pre-merge (/run/argus/irp/) |"""

new_debt_table = """| Deuda | Prioridad | Target |
|-------|-----------|--------|
| ~~DEBT-IRP-NFTABLES-001~~ | ✅ CERRADA | DAY 143 |
| ~~DEBT-IRP-SIGCHLD-001~~ | ✅ CERRADA | DAY 144 |
| ~~DEBT-IRP-AUTOISO-FALSE-001~~ | ✅ CERRADA | DAY 144 |
| ~~DEBT-IRP-BACKUP-DIR-001~~ | ✅ CERRADA | DAY 144 |
| DEBT-IRP-TMPFILES-001 | 🟡 P1 | post-merge (tmpfiles.d reboot) |
| DEBT-IRP-IPSET-TMP-001 | 🟡 P1 | post-merge (ipset_wrapper /tmp) |
| DEBT-EMECAS-VERIFICATION-001 | 🟢 P2 | post-merge (README devs) |"""

txt = txt.replace(old_debt_table, new_debt_table)

# 6. Milestone DAY 144
old_milestone = "- 🔜 DAY 144: **Merge feature/variant-b-libpcap → main · PROFILE=production gate · ADR-029 benchmark**"
new_milestone = """- ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 3 ODR violations corregidas · 65/65 tests** 🎉
- 🔜 DAY 145: **PCAP relay Variant A vs B · Merge → main · v0.7.0-variant-b · experiment-comparative diseño**"""
txt = txt.replace(old_milestone, new_milestone)

# 7. NEXT section DAY 144 → DAY 145
old_next = """### 🔜 NEXT — DAY 144

| Priority | Task |
|---|---|
| 🔴 P0 | Merge `feature/variant-b-libpcap` → main · `PROFILE=production` gate ODR |
| 🔴 P0 | DEBT-IRP-SIGCHLD-001 — `SA_NOCLDWAIT` pre-merge |
| 🔴 P0 | DEBT-IRP-AUTOISO-FALSE-001 — `auto_isolate: false` por defecto |
| 🔴 P0 | DEBT-IRP-BACKUP-DIR-001 — `/run/argus/irp/` + Falco |
| 🟡 P1 | ADR-029 Variant A vs B benchmark — contribución científica paper |"""

new_next = """### 🔜 NEXT — DAY 145

| Priority | Task |
|---|---|
| 🔴 P0 | EMECAS ritual obligatorio |
| 🔴 P0 | PCAP relay x86 eBPF (Variant A) — baseline F1=0.9985 |
| 🔴 P0 | PCAP relay x86 libpcap (Variant B) — métricas nuevas ADR-029 |
| 🔴 P0 | Merge `feature/variant-b-libpcap` → main · tag `v0.7.0-variant-b` |
| 🟡 P1 | Refactor Makefile — targets explícitos por arquitectura |
| 🟡 P1 | Diseño `experiment-comparative` (aRGus + Suricata + Zeek) |
| 🟡 P1 | Abrir `feature/adr029-variant-c-arm64` con scope definido |"""

txt = txt.replace(old_next, new_next)

# 8. Línea de estado principal
txt = txt.replace(
    "✅ `main` is tagged `v0.6.0-hardened-variant-a`. Branch activa: `feature/variant-b-libpcap` — ADR-029 Variant B pipeline completo + IRP sesiones 1-2/3 (DAY 142).",
    "✅ `main` is tagged `v0.6.0-hardened-variant-a`. Branch activa: `feature/variant-b-libpcap` @ `e52870d5` — 3 P0 IRP cerradas + Gate ODR production PASSED (DAY 144). Listo para merge → `v0.7.0-variant-b`."
)

readme.write_text(txt)
print("✅ README.md actualizado")

# ─────────────────────────────────────────────────────────────────────────────
# docs/BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────

backlog = ROOT / "docs" / "BACKLOG.md"
txt = backlog.read_text()

# 1. Header fecha
txt = txt.replace(
    "*Última actualización: DAY 143 — 6 Mayo 2026*",
    "*Última actualización: DAY 144 — 7 Mayo 2026*"
)

# 2. Añadir sección CERRADO DAY 144 antes de CERRADO DAY 143
new_day144_section = """## ✅ CERRADO DAY 144

### DEBT-IRP-SIGCHLD-001 — Zombie reaper SA_NOCLDWAIT
- **Status:** ✅ CERRADO DAY 144 — **Commits:** `a44b7ab3`
- **Fix:** `sigaction(SIGCHLD, SA_NOCLDWAIT)` en `setup_signal_handlers()`. El kernel recoge hijos automáticamente sin handler ni polling. Una línea.
- **Test de cierre:** `SigchldTest.NoZombiesAfterNForks` — 20 forks con `/bin/true`, 500ms, cero `defunct` en `/proc`. PASSED.

### DEBT-IRP-AUTOISO-FALSE-001 — auto_isolate false por defecto
- **Status:** ✅ CERRADO DAY 144 — **Commits:** `a44b7ab3`
- **Fix:** `isolate.json` es la ÚNICA fuente de verdad. Campo `auto_isolate` obligatorio — si falta, `parse_irp()` lanza `runtime_error` con mensaje claro. Sin fallback silencioso. `provision.sh` falla con `exit 1` si el fichero fuente no existe. `parse_irp()` movida a `public` para testabilidad directa.
- **Consejo 8/8 unánime:** un FP sobre ventilador mecánico es un evento clínico, no un bug.
- **Tests de cierre:** `DefaultStructIsFalse`, `FileMissingThrows`, `MissingFieldThrows`, `ExplicitFalseIsRespected`, `ExplicitTrueIsRespected` — 5/5 PASSED.

### DEBT-IRP-BACKUP-DIR-001 — /tmp peligroso para artefactos IRP
- **Status:** ✅ CERRADO DAY 144 — **Commits:** `646713e7`
- **Fix:** artefactos nftables migrados a `/run/argus/irp/` (tmpfs, 0700 argus:argus). AppArmor actualizado: eliminadas reglas `/tmp/argus-*.nft`, añadidas `/run/argus/irp/**` y `/var/lib/argus/irp/**`. `provision.sh` crea ambos directorios. `isolate.hpp` default actualizado.
- **Deudas derivadas:** `DEBT-IRP-TMPFILES-001` (tmpfiles.d reboot) + `DEBT-IRP-IPSET-TMP-001` (ipset_wrapper.cpp).
- **Test de cierre:** dry-run → `backup=/run/argus/irp/argus-backup-*.nft`. `ls /tmp/argus-*` vacío. PASSED.

### DEBT-COMPILER-WARNINGS-CLEANUP-001 — ODR violations bajo LTO (parcial)
- **Status:** ✅ PARCIALMENTE CERRADO DAY 144 — **Commits:** `e52870d5`
- **Gate:** `make PROFILE=production all` detectó 4 categorías de ODR violations reales bajo `-flto -Werror`.
- **Fix 1:** anonymous namespace en `internal_trees_inline.hpp` + `traffic_trees_inline.hpp` — `tree_0[]`..`tree_99[]` con tipos distintos visibles cross-módulo.
- **Fix 2:** `contract_validator.h` incluía protobuf stale (`src/protobuf/`, noviembre 2025). Path corregido + `src/protobuf/` eliminado (40k líneas de código generado fuera del repo).
- **Fix 3:** `-UNDEBUG` en targets de test de rag-ingester, rag y etcd-server — `assert()` siempre activo en tests independientemente del PROFILE.
- **Nuevo invariante:** `make PROFILE=production all` — gate ODR pre-merge obligatorio. Confirmado: `ALL COMPONENTS BUILT [production]`.
- **Test de cierre:** `make PROFILE=production all` PASSED — 0 ODR violations.

### DEBT-EMECAS-VERIFICATION-001 — P2 post-merge
- **Status:** ✅ REGISTRADA — P2 post-merge
- **Descripción:** El protocolo EMECAS en sí es correcto. El checklist de verificación post-EMECAS debe documentar explícitamente que el banner `ALL TESTS COMPLETE` + `FAILED=0` son el veredicto autoritativo. Errores intermedios de bootstrap son transientes esperados por diseño. Añadir párrafo en README para desarrolladores.
- **Estimación:** 30 minutos post-merge.

"""

txt = txt.replace(
    "## ✅ CERRADO DAY 143",
    new_day144_section + "## ✅ CERRADO DAY 143"
)

# 3. Actualizar estado de las deudas P0 en sección DEUDAS ABIERTAS
for debt_id, old_severity in [
    ("DEBT-IRP-SIGCHLD-001", "**Severidad:** 🔴 P0 pre-merge\n**Estado:** ABIERTO — DAY 143"),
    ("DEBT-IRP-AUTOISO-FALSE-001", "**Severidad:** 🔴 P0 pre-merge\n**Estado:** ABIERTO — DAY 143"),
    ("DEBT-IRP-BACKUP-DIR-001", "**Severidad:** 🔴 P0 pre-merge\n**Estado:** ABIERTO — DAY 143"),
]:
    txt = txt.replace(
        old_severity,
        f"**Severidad:** ✅ CERRADA DAY 144\n**Estado:** CERRADO — ver sección DAY 144"
    )

# 4. Añadir nuevas deudas antes de DEBT-IRP-FLOAT-TYPES-001
new_debts = """### DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/
**Severidad:** 🟡 P1 post-merge
**Estado:** ABIERTO — DAY 144
**Componente:** `tools/provision.sh` + configuración systemd

`/run/argus/irp/` es tmpfs — desaparece en cada reboot. En producción, el directorio debe recrearse automáticamente al arrancar. Fix: fichero `tmpfiles.d` en `/etc/tmpfiles.d/argus-irp.conf`:d /run/argus/irp 0700 argus argus -O en `provision.sh`: `systemd-tmpfiles --create` tras instalación.

**Test de cierre:** reboot → `/run/argus/irp/` existe con permisos correctos → dry-run IRP PASSED.
**Estimación:** 30 minutos post-merge.

---

### DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
**Severidad:** 🟡 P1 post-merge
**Estado:** ABIERTO — DAY 144
**Componente:** `firewall-acl-agent/src/core/ipset_wrapper.cpp`

`ipset_wrapper.cpp` usa `/tmp/ipset_restore.tmp` y `/tmp/ipset_delete.tmp`. Scope distinto al IRP (ipset, no nftables) pero mismo problema de seguridad. Migrar a `/run/argus/` con permisos apropiados.

**Test de cierre:** `grep -r '/tmp' firewall-acl-agent/src/` = 0 resultados (excluir .old/.backup).
**Estimación:** 1 hora post-merge.

---

"""

txt = txt.replace(
    "### DEBT-IRP-FLOAT-TYPES-001",
    new_debts + "### DEBT-IRP-FLOAT-TYPES-001"
)

# 5. Añadir reglas permanentes DAY 144
new_rules = """- **REGLA PERMANENTE (DAY 144 — Consejo 8/8):** `isolate.json` es la ÚNICA fuente de verdad para `auto_isolate`. Campo obligatorio — sin fallback silencioso. Si falta el fichero o el campo, el arranque falla ruidosamente con mensaje claro. Sin excepciones.
- **REGLA PERMANENTE (DAY 144 — Consejo 8/8):** `assert()` debe estar activo en todos los tests independientemente del PROFILE. Usar `target_compile_options(test_target PRIVATE -UNDEBUG)` en CMakeLists de tests. `-DNDEBUG` de producción no debe silenciar la cobertura de tests.
- **REGLA PERMANENTE (DAY 144 — gate ODR confirmado):** `make PROFILE=production all` detecta ODR violations reales bajo `-flto`. Confirmado en DAY 144: 3 categorías de violations encontradas y corregidas. El gate es obligatorio pre-merge sin excepciones.
"""

txt = txt.replace(
    "- **REGLA PERMANENTE (DAY 142 — macOS):**",
    new_rules + "- **REGLA PERMANENTE (DAY 142 — macOS):**"
)

# 6. Actualizar estado global
replacements_global = [
    ("DEBT-IRP-SIGCHLD-001:                   0% ⏳  P0 pre-merge (SA_NOCLDWAIT zombie reaper)",
     "DEBT-IRP-SIGCHLD-001:                 100% ✅  DAY 144 (SA_NOCLDWAIT + test NoZombiesAfterNForks)"),
    ("DEBT-IRP-AUTOISO-FALSE-001:             0% ⏳  P0 pre-merge (auto_isolate false por defecto)",
     "DEBT-IRP-AUTOISO-FALSE-001:           100% ✅  DAY 144 (única fuente verdad + 5 tests)"),
    ("DEBT-IRP-BACKUP-DIR-001:                0% ⏳  P0 pre-merge (/run/argus/irp/ + Falco)",
     "DEBT-IRP-BACKUP-DIR-001:             100% ✅  DAY 144 (/run/argus/irp/ + AppArmor)"),
    ("DEBT-COMPILER-WARNINGS-CLEANUP-001:     100% ✅  DAY 140 (192→0 warnings, ODR limpio)",
     "DEBT-COMPILER-WARNINGS-CLEANUP-001:    100% ✅  DAY 144 (ODR LTO production gate PASSED)"),
]

for old, new in replacements_global:
    txt = txt.replace(old, new)

# Añadir nuevas deudas al estado global
txt = txt.replace(
    "DEBT-IRP-FLOAT-TYPES-001:              0% ⏳  P1 pre-FEDER (unificar tipos score float/double)",
    "DEBT-IRP-TMPFILES-001:                  0% ⏳  P1 post-merge (tmpfiles.d reboot)\nDEBT-IRP-IPSET-TMP-001:                  0% ⏳  P1 post-merge (ipset_wrapper /tmp)\nDEBT-EMECAS-VERIFICATION-001:             0% ⏳  P2 post-merge (README devs)\nDEBT-IRP-FLOAT-TYPES-001:              0% ⏳  P1 pre-FEDER (unificar tipos score float/double)"
)

# 7. Añadir notas Consejo DAY 144
new_council_note = """## 📝 Notas del Consejo de Sabios — DAY 144 (8/8)

> "DAY 144 — Tres deudas P0 IRP cerradas en una sesión de madrugada (04:00-08:00). Gate ODR production superado tras corregir tres categorías de violaciones reales bajo `-flto -Werror`.
>
> **DEBT-IRP-SIGCHLD-001 (8/8):** `SA_NOCLDWAIT` en `setup_signal_handlers()`. El kernel recoge hijos muertos automáticamente. `SigchldTest.NoZombiesAfterNForks` — 20 forks, 500ms, cero zombies. PASSED.
>
> **DEBT-IRP-AUTOISO-FALSE-001 (8/8 unánime):** `isolate.json` es la única fuente de verdad. Campo `auto_isolate` obligatorio. Fallo ruidoso si falta. Sin fallback silencioso. Un FP sobre ventilador mecánico es un evento clínico, no un bug. 5 tests nuevos PASSED.
>
> **DEBT-IRP-BACKUP-DIR-001 (8/8 unánime):** `/tmp` eliminado de la ruta IRP. `/run/argus/irp/` (tmpfs, 0700). AppArmor actualizado. provision.sh actualizado. Dry-run PASSED.
>
> **Gate ODR (confirmación empírica):** `make PROFILE=production all` encontró 3 ODR violations reales que el build debug nunca habría detectado: (1) `tree_0[]`..`tree_99[]` con tipos distintos en dos headers incluidos en distintas unidades de compilación → anonymous namespace; (2) protobuf stale de noviembre 2025 en `src/protobuf/` → eliminado (40k líneas); (3) `assert()` desactivado por `-DNDEBUG` en tests → `-UNDEBUG` en targets de test.
>
> **Consenso sobre experimento comparativo (P4):** No es una competición. Es una caracterización de paradigmas complementarios. La afirmación publicable es: 'Los sistemas basados en firmas y los basados en comportamiento son complementarios. Un despliegue hospitalario óptimo combinaría ambos.' aRGus como cooperador, no como sustituto.
>
> **Consenso P3 multi-señal:** Qwen propone acumulador de evidencia con decadencia exponencial — determinista, sin reentrenamiento, auditable, estándar NIST/MITRE. Superior a regresión logística para infraestructura crítica. Adoptado.
>
> 65/65 tests verdes. Gate ODR: ALL COMPONENTS BUILT [production].
>
> 'El gate ODR no es burocracia — es la única herramienta que ve lo que el compilador diario no ve.' — ChatGPT"
> — Consejo de Sabios (8/8) · DAY 144

"""

txt = txt.replace(
    "## 📝 Notas del Consejo de Sabios — DAY 143 (8/8)",
    new_council_note + "## 📝 Notas del Consejo de Sabios — DAY 143 (8/8)"
)

# 8. Footer fecha
txt = txt.replace(
    "*DAY 143 — 6 Mayo 2026 · feature/variant-b-libpcap @ f00b1809*",
    "*DAY 144 — 7 Mayo 2026 · feature/variant-b-libpcap @ e52870d5*"
)

backlog.write_text(txt)
print("✅ docs/BACKLOG.md actualizado")

print("\n✅ Listo. Revisar cambios con: git diff README.md docs/BACKLOG.md")
print("   Commit sugerido:")
print("   git add README.md docs/BACKLOG.md")
print("   git commit -m 'docs: DAY 144 — 3 P0 IRP cerradas + gate ODR production PASSED'")