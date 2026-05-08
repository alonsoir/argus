#!/usr/bin/env python3
"""
update-docs-day143.py
Ejecutar desde la raíz del repo: python3 update-docs-day143.py
Actualiza README.md y docs/BACKLOG.md con los cambios del DAY 143.
"""

import re

# ─────────────────────────────────────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────────────────────────────────────

with open("README.md", "r") as f:
    readme = f.read()

# 1. Badge AppArmor 6/6 → 7/7
readme = readme.replace(
    "[![AppArmor](https://img.shields.io/badge/AppArmor-6%2F6_enforce-brightgreen)]()",
    "[![AppArmor](https://img.shields.io/badge/AppArmor-7%2F7_enforce-brightgreen)]()"
)

# 2. Estado actual DAY 142 → DAY 143
readme = readme.replace(
    "## Estado actual — DAY 142 (2026-05-05)",
    "## Estado actual — DAY 143 (2026-05-06)"
)

readme = readme.replace(
    "**Tag activo:** `v0.6.0-hardened-variant-a` | **Branch activa:** `feature/variant-b-libpcap` @ `9458a90d`",
    "**Tag activo:** `v0.6.0-hardened-variant-a` | **Branch activa:** `feature/variant-b-libpcap` @ `f00b1809`"
)

# 3. Hitos DAY 142 → añadir DAY 143
readme = readme.replace(
    "- 🔜 DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 — integración firewall-acl-agent**",
    """- ✅ DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA — IRP completo · AppArmor 7/7 · 12 tests** 🎉
- 🔜 DAY 144: **Merge feature/variant-b-libpcap → main · PROFILE=production gate · ADR-029 benchmark**"""
)

# 4. NEXT DAY 143 → DAY 144
readme = readme.replace(
    """### 🔜 NEXT — DAY 143

| Priority | Task |
|---|---|
| 🔴 P0 | `DEBT-IRP-NFTABLES-001` sesión 3/3 — integración firewall-acl-agent + AppArmor |""",
    """### 🔜 NEXT — DAY 144

| Priority | Task |
|---|---|
| 🔴 P0 | Merge `feature/variant-b-libpcap` → main · `PROFILE=production` gate ODR |
| 🔴 P0 | DEBT-IRP-SIGCHLD-001 — `SA_NOCLDWAIT` pre-merge |
| 🔴 P0 | DEBT-IRP-AUTOISO-FALSE-001 — `auto_isolate: false` por defecto |
| 🔴 P0 | DEBT-IRP-BACKUP-DIR-001 — `/run/argus/irp/` + Falco |
| 🟡 P1 | ADR-029 Variant A vs B benchmark — contribución científica paper |"""
)

# 5. Tabla deudas — marcar IRP-NFTABLES como cerrada, añadir nuevas
readme = readme.replace(
    "| DEBT-IRP-NFTABLES-001 sesión 3/3 | 🔴 P0 | pre-FEDER (DAY 143) |",
    """| ~~DEBT-IRP-NFTABLES-001~~ | ✅ CERRADA | DAY 143 |
| DEBT-IRP-SIGCHLD-001 | 🔴 P0 | pre-merge (SA_NOCLDWAIT) |
| DEBT-IRP-AUTOISO-FALSE-001 | 🔴 P0 | pre-merge (auto_isolate false) |
| DEBT-IRP-BACKUP-DIR-001 | 🔴 P0 | pre-merge (/run/argus/irp/) |
| DEBT-IRP-FLOAT-TYPES-001 | 🟡 P1 | pre-FEDER (tipos score) |
| DEBT-IRP-PROB-CONJUNTA-001 | 🟡 P1 | post-FEDER (señal conjunta) |"""
)

# 6. IRP section — actualizar auto_isolate note
readme = readme.replace(
    "**Por defecto activo** (`auto_isolate: true`). Instalar y funcionar.",
    "**Por defecto:** `auto_isolate: false` — habilitar explícitamente tras configurar whitelist. (DEBT-IRP-AUTOISO-FALSE-001)"
)

# 7. AppArmor table — añadir argus-network-isolate
readme = readme.replace(
    "| argus-network-isolate | `cap_net_admin` (AppArmor profile — DAY 143) |",
    "| argus-network-isolate | `cap_net_admin` (AppArmor enforce — DAY 143) |"
)

# 8. Hitos milestone — actualizar DAY 143
readme = readme.replace(
    "✅ DAY 142: **IRP pasos 1-6 · buffer=8MB · mutex Nivel 1 · Consejo 8/8** 🎉\n- 🔜 DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 — integración firewall-acl-agent**",
    "✅ DAY 142: **IRP pasos 1-6 · buffer=8MB · mutex Nivel 1 · Consejo 8/8** 🎉\n- ✅ DAY 143: **IRP sesión 3/3 · auto-isolate fork()+execv() · AppArmor 7/7 · 12 tests · Consejo 8/8** 🎉\n- 🔜 DAY 144: **Merge variant-b → main · benchmark A vs B · PROFILE=production gate**"
)

with open("README.md", "w") as f:
    f.write(readme)
print("✅ README.md actualizado")


# ─────────────────────────────────────────────────────────────────────────────
# docs/BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────

with open("docs/BACKLOG.md", "r") as f:
    backlog = f.read()

# 1. Header fecha
backlog = backlog.replace(
    "*Última actualización: DAY 142 — 5 Mayo 2026*",
    "*Última actualización: DAY 143 — 6 Mayo 2026*"
)

# 2. DEBT-IRP-NFTABLES-001 → 100% cerrada
backlog = backlog.replace(
    "DEBT-IRP-NFTABLES-001:                  60% 🟡  DAY 142 sesiones 1-2/3 (sesión 3 pendiente)",
    "DEBT-IRP-NFTABLES-001:                 100% ✅  DAY 143 — CERRADA (sesión 3/3 completa)"
)

# 3. Añadir nuevas deudas en el estado global
backlog = backlog.replace(
    "DEBT-ETCD-HA-QUORUM-001:                0% ⏳  P0 post-FEDER (OBLIGATORIO)",
    """DEBT-IRP-SIGCHLD-001:                   0% ⏳  P0 pre-merge (SA_NOCLDWAIT zombie reaper)
DEBT-IRP-AUTOISO-FALSE-001:             0% ⏳  P0 pre-merge (auto_isolate false por defecto)
DEBT-IRP-BACKUP-DIR-001:                0% ⏳  P0 pre-merge (/run/argus/irp/ + Falco)
DEBT-IRP-FLOAT-TYPES-001:              0% ⏳  P1 pre-FEDER (unificar tipos score float/double)
DEBT-IRP-PROB-CONJUNTA-001:             0% ⏳  P1 post-FEDER (función prob. conjunta multi-señal)
DEBT-PROTO-DETECTION-TYPES-001:         0% ⏳  Baja post-MITRE/CTF (ampliar enum DetectionType)
DEBT-ETCD-HA-QUORUM-001:                0% ⏳  P0 post-FEDER (OBLIGATORIO)"""
)

# 4. Marcar IRP-NFTABLES como CERRADA en sección deudas abiertas
backlog = backlog.replace(
    "### DEBT-IRP-NFTABLES-001 — sesión 3/3 pendiente\n**Severidad:** 🔴 Alta — P0 pre-FEDER\n**Estado:** 🟡 60% — sesiones 1 y 2 cerradas — DAY 142",
    "### ~~DEBT-IRP-NFTABLES-001~~ — CERRADA ✅ DAY 143\n**Severidad:** ~~🔴 Alta — P0 pre-FEDER~~\n**Estado:** ✅ 100% — sesión 3/3 CERRADA — DAY 143"
)

# 5. Añadir nuevas deudas abiertas (antes de DEBT-ETCD-HA-QUORUM-001)
new_debts = """
---

### DEBT-IRP-SIGCHLD-001 — Zombie reaper SA_NOCLDWAIT
**Severidad:** 🔴 P0 pre-merge
**Estado:** ABIERTO — DAY 143
**Componente:** `firewall-acl-agent/src/main.cpp`

`fork()+execv()` sin `wait()` genera zombies acumulados en ataques persistentes.
Fix: `sigaction(SIGCHLD, SA_NOCLDWAIT)` al inicializar `firewall-acl-agent` —
el kernel recoge los hijos automáticamente sin handler ni polling.
Es el mecanismo más cercano al kernel. Una línea. Sin threads adicionales.

**Consejo 8/8 DAY 143:** SA_NOCLDWAIT (Qwen) es la solución más kernel-centric.
**Test de cierre:** N disparos IRP en loop → `ps aux | grep -c defunct` = 0.
**Estimación:** 30 minutos pre-merge.

---

### DEBT-IRP-AUTOISO-FALSE-001 — auto_isolate false por defecto
**Severidad:** 🔴 P0 pre-merge
**Estado:** ABIERTO — DAY 143
**Componente:** `tools/argus-network-isolate/config/isolate.json` + documentación

**Consejo 8/8 DAY 143 — UNÁNIME:** `auto_isolate: false` por defecto en producción
hospitalaria. Un ventilador mecánico o bomba de infusión no puede quedar aislado
por señal única sin confirmación humana explícita. "Instalar y funcionar" es válido
para entornos SOHO — inaceptable para hospitales sin onboarding explícito.

Cambio: `isolate.json` default → `false`. Añadir WARNING prominente al arrancar
`firewall-acl-agent` con IRP desactivado. Activar requiere acto explícito y consciente
del administrador tras configurar `whitelist_ips` con activos críticos.

La regla DAY 142 ("auto_isolate: true por defecto") queda **REEMPLAZADA** por esta.

**Test de cierre:** `vagrant destroy && vagrant up && make bootstrap` → IRP arranca
con `auto_isolate: false` y loguea WARNING visible.
**Estimación:** 1 hora pre-merge.

---

### DEBT-IRP-BACKUP-DIR-001 — /tmp peligroso para artefactos IRP
**Severidad:** 🔴 P0 pre-merge
**Estado:** ABIERTO — DAY 143
**Componente:** `tools/argus-network-isolate/isolate.cpp` + AppArmor profile

**Consejo 8/8 DAY 143 — UNÁNIME:** `/tmp/argus-*.nft` es un vector.
Glob en `/tmp` permite interferencia por race condition o symlink attack.

Fix:
- Artefactos transaccionales volátiles → `/run/argus/irp/` (tmpfs, desaparece en reboot)
- Estado persistente → `/var/lib/argus/irp/`
- Permisos: `0700 argus:argus`
- AppArmor: eliminar reglas `/tmp/**`, añadir `/run/argus/irp/**` y `/var/lib/argus/irp/**`
- Falco: vigilar ambas rutas — escritura por proceso no autorizado = alerta

**Test de cierre:** AppArmor en enforce + dry-run IRP → artefactos en `/run/argus/irp/`.
`ls /tmp/argus-*` vacío.
**Estimación:** 2 horas pre-merge.

---

### DEBT-IRP-FLOAT-TYPES-001 — Unificar tipos score float/double
**Severidad:** 🟡 P1 pre-FEDER
**Estado:** ABIERTO — DAY 143
**Componente:** `firewall-acl-agent/include/firewall/config_loader.hpp` + `batch_processor.cpp`

El bug IEEE 754 detectado por los tests DAY 143: `static_cast<double>(0.95f)` = `0.9499...`
Corregido con tolerancia `1e-6` — parche funcional pero no la solución de raíz.

El problema real: `IsolateConfig::threat_score_threshold` es `double` pero
`Detection::confidence` es `float`. Mezcla de tipos en lógica de decisión crítica.

Preguntas a responder antes del fix:
1. ¿Qué tipo produce exactamente el ml-detector? ¿float 32-bit o double 64-bit?
2. ¿Qué precisión tiene el score en el pipeline ZMQ → protobuf → BatchProcessor?
3. ¿Qué tipo es matemáticamente correcto para el score de un clasificador ML?

**Consejo DAY 143:** Dividido — Claude/Gemini/Grok/DeepSeek prefieren `float` consistente;
Mistral/Qwen prefieren `double` + tolerancia. ChatGPT propone enteros escalados (uint32_t)
para sistemas críticos. Resolver con análisis del pipeline completo antes de FEDER
porque los tests MITRE pueden revelar comportamientos en distribuciones fuera de CIC-IDS-2017.

**Test de cierre:** stress test con CTU-13 + pcap relay + MITRE → 0 disparos IRP
inesperados por error de precisión numérica.
**Estimación:** 1 sesión pre-FEDER.

---

### DEBT-IRP-PROB-CONJUNTA-001 — Función probabilidad conjunta multi-señal
**Severidad:** 🟡 P1 post-FEDER
**Estado:** ABIERTO — DAY 143
**Componente:** `firewall-acl-agent/src/core/` — nuevo módulo IrpDecisionEngine

**Consejo 8/8 DAY 143:** Dos señales AND no son suficientes para producción hospitalaria.
Arquitectura acordada: función de decisión que combina TODAS las señales disponibles
con sus pesos, produce una probabilidad conjunta, y la decisión queda completamente
auditada — se sabe exactamente qué señales contribuyeron y con qué peso.

Señales candidatas (no todas obligatorias):
- score >= threshold (necesaria)
- event_type IN lista (necesaria)
- src_ip NOT IN whitelist_assets_criticos (gate de seguridad)
- N eventos en ventana T segundos (correlación temporal — Qwen)
- confirmación segundo sensor ±5s (Falco, Suricata — Mistral)
- segmento de red del activo (Gemini — no escala globalmente)

La función de decisión debe ser: explicable, auditable, publicable en paper.
La probabilidad conjunta de todas las señales disponibles elimina el umbral binario.

**No implementar Gemini's topología por quirófano** — inviable mantener catálogo
de todos los hospitales del mundo.

**Registrado como:** IDEA-IRP-DECISION-MATRIX-001 (referencia cruzada DEBT-IRP-MULTI-SIGNAL-001)
**Test de cierre:** decisión IRP con ≥3 señales → log JSON con contribución de cada señal.
**Estimación:** 3 sesiones post-FEDER.

---

### DEBT-PROTO-DETECTION-TYPES-001 — Ampliar enum DetectionType
**Severidad:** 🟢 Baja — post-fase-MITRE/CTF
**Estado:** ABIERTO — DAY 143
**Componente:** `protobuf/network_security.proto`

`DetectionType` solo modela 4 tipos: DDOS, RANSOMWARE, SUSPICIOUS_TRAFFIC, INTERNAL_THREAT.
El mapeo actual en `should_auto_isolate()` usa aproximaciones:
`DETECTION_INTERNAL_THREAT → "lateral_movement"` y
`DETECTION_SUSPICIOUS_TRAFFIC → "c2_beacon"`.

Ampliar cuando el pipeline enfrente MITRE ATT&CK y CTFs reales y se observen
tipos de ataque no modelados. No antes — sin datos no hay diseño.

Opción B (ampliar proto) descartada conscientemente DAY 143 para no romper
compatibilidad con v0.6.0-hardened-variant-a.

**Test de cierre:** pipeline contra MITRE ATT&CK → 0 eventos "tipo no mapeado" en logs IRP.
**Estimación:** 1 sesión post-MITRE.

"""

backlog = backlog.replace(
    "\n---\n\n### DEBT-ETCD-HA-QUORUM-001",
    new_debts + "\n---\n\n### DEBT-ETCD-HA-QUORUM-001"
)

# 6. Añadir al CERRADO DAY 143
cerrado_day143 = """
---

## ✅ CERRADO DAY 143

### DEBT-IRP-NFTABLES-001 — sesión 3/3 (integración firewall-acl-agent + AppArmor)
- **Status:** ✅ CERRADO DAY 143 — **Commits:** `c6e3f4ab` `888bfcbd` `f1ab0c79` `e08f394d` `f00b1809` `7716423b`
- **Bloque 1:** `isolate.json` + `IsolateConfig` — campos `auto_isolate`, `threat_score_threshold`, `auto_isolate_event_types`, `isolate_interface`. Test `test_isolate_config` 9/9.
- **Bloque 2:** `firewall-acl-agent` — `IrpConfig`, `should_auto_isolate()` (función pura testeable), `check_auto_isolate()` con `fork()+execv()`. Mapeo `DetectionType→string`. Bug IEEE 754 detectado por tests y corregido con tolerancia `1e-6`.
- **Bloque 3:** AppArmor profile `argus.argus-network-isolate` — sintaxis validada, 7/7 perfiles enforce en hardened VM. `setup-apparmor.sh` actualizado.
- **Bloque 4:** `test_auto_isolate` 12/12 PASSED (10 unitarios + 2 integración fork/exec).
- **Regresiones EMECAS resueltas:** DEBT-BOOTSTRAP-ORDER-001 (check-build-artifacts separado) + firma `PcapBackend::open()` en 5 test files.
- **Invariante:** EMECAS verde. `make test-all` ALL TESTS COMPLETE.

"""

backlog = backlog.replace(
    "\n---\n\n## ✅ CERRADO DAY 142",
    cerrado_day143 + "\n---\n\n## ✅ CERRADO DAY 142"
)

# 7. Añadir notas Consejo DAY 143
consejo_day143 = """
## 📝 Notas del Consejo de Sabios — DAY 143 (8/8)

> "DAY 143 — DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA. IRP completo: config → disparo → fork()+execv() → AppArmor enforce → 12 tests. Bug IEEE 754 encontrado por tests — `float 0.95f → double 0.9499...` — corregido. 7/7 perfiles AppArmor enforce en hardened VM.
>
> Cinco deudas nuevas registradas tras Consejo:
>
> **DEBT-IRP-SIGCHLD-001 (8/8 unánime):** SA_NOCLDWAIT — el kernel recoge hijos muertos automáticamente. Sin zombies en ataques persistentes. P0 pre-merge.
>
> **DEBT-IRP-AUTOISO-FALSE-001 (8/8 unánime):** auto_isolate: false por defecto. La regla DAY 142 queda reemplazada. En hospitales, la automatización sin onboarding explícito es un riesgo de vida. P0 pre-merge.
>
> **DEBT-IRP-BACKUP-DIR-001 (8/8 unánime):** /tmp es peligroso para artefactos IRP. Migrar a /run/argus/irp/ (volátil) + /var/lib/argus/irp/ (persistente). Falco vigila ambas rutas. P0 pre-merge.
>
> **DEBT-IRP-FLOAT-TYPES-001 (dividido):** Mezcla float/double en lógica de decisión es un error de diseño. La tolerancia 1e-6 es un parche. Unificar tipos. Investigar qué produce exactamente el ml-detector antes de decidir el tipo correcto. P1 pre-FEDER.
>
> **DEBT-IRP-PROB-CONJUNTA-001 (8/8):** Dos señales AND no son suficientes para hospital. Función probabilidad conjunta sobre todas las señales disponibles — explicable, auditable, publicable. No implementar topología por quirófano (Gemini) — inviable a escala global. P1 post-FEDER.
>
> 'Un escudo que corta sin medir no protege: amputa.' — Qwen"
> — Consejo de Sabios (8/8) · DAY 143

"""

backlog = backlog.replace(
    "\n## 📝 Notas del Consejo de Sabios — DAY 142",
    consejo_day143 + "\n## 📝 Notas del Consejo de Sabios — DAY 142"
)

# 8. Añadir decisiones de diseño DAY 143
new_decisions = """| **auto_isolate: false por defecto** | REEMPLAZA regla DAY 142. En hospitales, default false + WARNING. Activar es acto explícito. | Consejo 8/8 · DAY 143 |
| **SA_NOCLDWAIT para IRP** | fork()+execv() → sigaction SA_NOCLDWAIT. Kernel recoge hijos. Sin zombies. | Consejo 8/8 · DAY 143 |
| **/run/argus/irp/ para IRP** | Artefactos nftables fuera de /tmp. /run/ (volátil) + /var/lib/ (persistente). Falco vigila. | Consejo 8/8 · DAY 143 |
| **DEBT-PROTO-DETECTION-TYPES-001** | No ampliar enum sin datos MITRE reales. Sin datos no hay diseño. | Founder · DAY 143 |
| **IRP prob. conjunta multi-señal** | No topología por quirófano (inviable). Función de decisión con todas las señales disponibles + pesos. | Consejo 8/8 · DAY 143 |
"""

backlog = backlog.replace(
    "| **etcd-server HA es deuda crítica**",
    new_decisions + "| **etcd-server HA es deuda crítica**"
)

# 9. Footer fecha
backlog = backlog.replace(
    "*DAY 142 — 5 Mayo 2026 · feature/variant-b-libpcap @ 9458a90d*",
    "*DAY 143 — 6 Mayo 2026 · feature/variant-b-libpcap @ f00b1809*"
)

with open("docs/BACKLOG.md", "w") as f:
    f.write(backlog)
print("✅ docs/BACKLOG.md actualizado")

print("\n✅ Todos los documentos actualizados para DAY 143.")
print("   Siguiente: git add README.md docs/BACKLOG.md && git commit -m 'docs: DAY 143 — IRP completo + 5 deudas Consejo'")