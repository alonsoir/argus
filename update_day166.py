#!/usr/bin/env python3
"""
update_day166.py — Actualiza BACKLOG.md, README.md y genera prompt DAY 167
Ejecutar desde la raíz del proyecto: python3 update_day166.py
DAY 166 — 2026-05-27 — EMECAS++ verde en main, merge completado
"""

import os
import re
import sys
from pathlib import Path

# ─── Constantes ──────────────────────────────────────────────────────────────
DAY          = 166
NEXT_DAY     = 167
DATE         = "2026-05-27"
KEYPAIR      = "c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90"
BRANCH       = "main"
TAG          = "pendiente v1.0.0-day166"  # ajustar si se crea el tag

BACKLOG_PATH = Path("docs/BACKLOG.md")
README_PATH  = Path("README.md")
PROMPT_PATH  = Path("docs/continuity/PROMPT_CONTINUE_CLAUDE.md")

# ─── Helpers ──────────────────────────────────────────────────────────────────
def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")

def write(p: Path, content: str):
    p.write_text(content, encoding="utf-8")
    print(f"  ✅ {p} actualizado")

def replace_first(text: str, old: str, new: str) -> str:
    if old not in text:
        print(f"  ⚠️  No encontrado: {old[:60]!r}")
        return text
    return text.replace(old, new, 1)

# ─── BACKLOG.md ───────────────────────────────────────────────────────────────
BACKLOG_DAY166_SECTION = """## ✅ CERRADO DAY 166

### BACKLOG-EMECAS-ENTERPRISE-001 — Protocolo EMECAS++ 3 actos (P0 bloqueante de merge)
- **Status:** ✅ COMPLETADO DAY 166 — merge a main realizado directamente
- **Acto I — Arranque nominal:** test-e2e-vault PASSED. Todos los componentes se autentican contra Vault dev, `ICryptoProvider` fingerprint estable (`485f90db2f324895...`), `CryptoEpochCoordinator` en watch `/v1/epoch`, `crypto_errors==0`.
- **Acto II — Rotación controlada:** test-e2e-synthetic-full PASSED bajo tráfico activo. Delta ml-detector=100, firewall=100, `crypto_errors==0`, `events_dropped==0`. Pipeline no para durante la rotación.
- **Acto III — Fallo Vault controlado (vault-fault-inject):** token hijo revocado → componente entra en caché RCU (AUTONOMOUS) → pipeline sigue operativo → token revocado confirmado → PASSED. Zero downtime demostrado.
- **EMECAS++ OSS también verde:** test-all ✅ · test-e2e-synthetic-full ✅ · test-e2e-synthetic-firewall ✅ (546 eventos, 0 crypto_errors)
- **Keypair efímero activo (DAY 166):** `c76e5e10e2a5a5ebcbf249a2d36a2a18d88b05aa75552bb7042353221484cf90`
- **Regla permanente (DAY 166):** EMECAS++ tiene tres actos obligatorios. Los tres deben ser verdes antes de cualquier merge enterprise a main. Enterprise ⊃ OSS — no puede haber EMECAS++ verde con EMECAS roto.

### BACKLOG-CRYPTO-E2E-ROTATION-001 — Live rotation con pipeline activo (Actos II+III)
- **Status:** ✅ COMPLETADO DAY 166 — Acto II (live rotation) + Acto III (Vault fault inject) verdes
- FakeEtcdServer 5/5 + test-e2e-vault PASSED (DAY 165) + live rotation bajo tráfico confirmada (DAY 166).
- vault-fault-inject: token hijo revocado → caché RCU activa → pipeline operativo → PASSED.
- Gate de merge satisfecho: los tres actos documentados y reproducibles.

### DEBT-VAULT-RECONNECT-001 — VaultProvider retry/cache (estado desconocido)
- **Status:** ✅ CERRADA DAY 165/166 — confirmada implementación preexistente
- `get_material()` tiene caché inline: si `cached_material_.has_value()` → no toca Vault.
- `ERROR_VAULT_DOWN` → `autonomy_.on_vault_unreachable()` → AUTONOMOUS. Pipeline no muere.
- `refresh()` maneja recuperación completa: RECONCILING → NORMAL.
- El Acto III no requirió implementación nueva — el comportamiento ya existía.

"""

BACKLOG_REGLA_DAY166 = """- **REGLA PERMANENTE (DAY 166 — Consejo 8/8):** EMECAS++ tiene tres actos obligatorios: (I) arranque nominal con Vault, (II) rotación controlada con live epoch bajo tráfico, (III) Vault falla en un componente con zero downtime. Los tres actos deben ser verdes y reproducibles antes de cualquier merge enterprise a main.
- **REGLA PERMANENTE (DAY 166 — Founder):** VaultProvider caché RCU es la implementación del Acto III. El caché inline en `get_material()` garantiza que el componente siga operativo aunque Vault esté caído. El comportamiento correcto ya existía — el gate lo validó por primera vez.
"""

BACKLOG_STATUS_UPDATES = [
    # (viejo, nuevo)
    (
        "BACKLOG-EMECAS-ENTERPRISE-001:                   0% ⏳  P0 — protocolo EMECAS++ 3 actos, bloqueante de merge",
        "BACKLOG-EMECAS-ENTERPRISE-001:                 100% ✅  DAY 166 — EMECAS++ 3 actos verdes, merge a main"
    ),
    (
        "BACKLOG-CRYPTO-E2E-ROTATION-001 (FakeEtcd):     60% 🟡  DAY 165 — FakeEtcdServer 5/5 + test-e2e-vault PASSED; live rotation pendiente",
        "BACKLOG-CRYPTO-E2E-ROTATION-001:               100% ✅  DAY 166 — Live rotation Acto II+III verdes, gate completado"
    ),
    (
        "DEBT-VAULT-RECONNECT-001:                         0% ⏳  P0 — VaultProvider retry/cache estado desconocido (inspeccionar DAY 166)",
        "DEBT-VAULT-RECONNECT-001:                       100% ✅  DAY 165/166 — caché inline preexistente confirmada, Acto III no requirió código nuevo"
    ),
    (
        "DEBT-CRYPTO-NEGATIVE-TEST-001:                    0% ⏳  P0 — test negativo epoch_id incorrecto, bloqueante pre-merge",
        "DEBT-CRYPTO-NEGATIVE-TEST-001:                  100% ✅  DAY 166 — test epoch_id=0xFFFF rechazado, EMECAS++ verde"
    ),
    (
        "BACKLOG-CI-ENTERPRISE-001:                        0% ⏳  P1 post-merge (Jenkins gate enterprise)",
        "BACKLOG-CI-ENTERPRISE-001:                        0% ⏳  P1 — Jenkins gate make emecas++ (post-merge, requiere hardware FEDER)"
    ),
]


def update_backlog(text: str) -> str:
    # 1. Actualizar fecha de última actualización
    text = re.sub(
        r'\*Última actualización: DAY \d+ — \d{4}-\d{2}-\d{2}\*',
        f'*Última actualización: DAY {DAY} — {DATE}*',
        text
    )

    # 2. Insertar sección DAY 166 después del encabezado "## ✅ CERRADO DAY 165"
    marker = "## ✅ CERRADO DAY 165"
    if marker in text:
        text = text.replace(marker, BACKLOG_DAY166_SECTION + marker, 1)
    else:
        print(f"  ⚠️  Marcador '{marker}' no encontrado, insertando al inicio de cerrados")

    # 3. Insertar regla permanente DAY 166 (antes de la regla DAY 165)
    marker_regla = "- **REGLA PERMANENTE (DAY 165 — Consejo 8/8):** `epoch_id`"
    if marker_regla in text:
        text = text.replace(marker_regla, BACKLOG_REGLA_DAY166 + marker_regla, 1)

    # 4. Actualizar tabla de estado global
    for old, new in BACKLOG_STATUS_UPDATES:
        text = replace_first(text, old, new)

    # 5. Actualizar keypair activo
    text = re.sub(
        r'\*\*Keypair activo:\*\* `[a-f0-9]{64}`',
        f'**Keypair activo:** `{KEYPAIR}`',
        text
    )

    # 6. Actualizar pie de página
    text = re.sub(
        r'\*DAY \d+ — \d{4}-\d{2}-\d{2} · main @ .*\*',
        f'*DAY {DAY} — {DATE} · main @ {BRANCH}*',
        text
    )

    return text


# ─── README.md ────────────────────────────────────────────────────────────────
README_STATUS_NEW = f"""<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | {DAY} |
| Tag | {TAG} |
| Branch | {BRANCH} |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ✅ VERDE — 3 actos verdes y reproducibles (DAY 166) |
| Pipeline | 6/6 RUNNING |
| Crypto lifecycle | FASE 0 ✅ + FASE 1 ✅ + FASE 2a ✅ + FASE 2b ✅ + FASE 3 ✅ + EMECAS++ ✅ |
| Wire header epoch_id | ✅ [uint32_t][uint16_t epoch_id][2B reserved][LZ4] — 13/13 tests |
| vendor.key | ✅ Modelo B — solo en Vault dev, nunca en disco |
| ADR-045 v2 | ✅ Consejo 8/8 — implementado FASES 0-3 + EMECAS++ |
| Próximo hito | DAY {NEXT_DAY}: BACKLOG-CI-ENTERPRISE-001 (Jenkins gate) + ADR-048 F2 (NTP + community_id) |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->"""

README_HITO_DAY166 = f"""  - ✅ DAY {DAY}: **EMECAS++ 3 actos verdes · merge enterprise a main · VaultProvider caché RCU confirmado · vault-fault-inject PASSED · Zero downtime demostrado** 🎉
"""

def update_readme(text: str) -> str:
    # 1. Reemplazar bloque DAY-STATUS
    text = re.sub(
        r'<!-- DAY-STATUS -->.*?<!-- /DAY-STATUS -->',
        README_STATUS_NEW,
        text,
        flags=re.DOTALL
    )

    # 2. Actualizar keypair
    text = re.sub(
        r'\*\*Keypair activo:\*\* `[a-f0-9]{64}`',
        f'**Keypair activo:** `{KEYPAIR}`',
        text
    )

    # 3. Insertar hito DAY 166 después del hito DAY 165
    marker = f"  - ✅ DAY 165: **FASE 3 wire header epoch_id"
    if marker in text:
        idx = text.find(marker)
        # Encontrar fin de esa línea
        end = text.find("\n", idx) + 1
        text = text[:end] + README_HITO_DAY166 + text[end:]
    else:
        print("  ⚠️  Hito DAY 165 no encontrado en README, insertar manualmente")

    return text


# ─── PROMPT DAY 167 ───────────────────────────────────────────────────────────
PROMPT_DAY167 = f"""# PROMPT DE CONTINUIDAD — DAY {NEXT_DAY}
## aRGus NDR | {DATE}

---

## Estado al entrar en DAY {NEXT_DAY}

### Rama activa
`{BRANCH}` — merge enterprise completado DAY {DAY}

### EMECAS++ completo — todos los actos verdes
- test-all: ✅ (6 suites, 0 fallos)
- test-e2e-synthetic-full: ✅ delta=100/100
- test-e2e-synthetic-firewall: ✅ 546 eventos, 0 crypto_errors
- **Acto I (arranque nominal con Vault):** ✅ fingerprint estable, crypto_errors==0
- **Acto II (rotación controlada bajo tráfico):** ✅ epoch_id antes/después distintos, 0 drops
- **Acto III (vault-fault-inject token revocation):** ✅ cache RCU activa, zero downtime
- **Keypair efímero activo:** `{KEYPAIR}`

### Crypto lifecycle — todas las fases verdes
| Fase | Estado |
|------|--------|
| FASE 0 — vendor.key → Vault (Modelo B) | ✅ |
| FASE 1 — CryptoProviderHandle RCU | ✅ |
| FASE 2a — HttpEtcdRegistrar real | ✅ |
| FASE 2b — CryptoEpochCoordinator | ✅ |
| FASE 3 — Wire header epoch_id (13/13) | ✅ |
| FASE 4 — test-e2e-rotation (live Actos II+III) | ✅ |
| **EMECAS++ Enterprise (3 actos)** | ✅ CERRADO DAY {DAY} |

### Consejo de Sabios DAY {DAY} — contexto
- B1 (VaultProvider retry/cache) era gratis — caché inline preexistente confirmada por grep
- Acto III no requirió código nuevo: `get_material()` ya tenía `cached_material_.has_value()`
- `DEBT-VAULT-RECONNECT-001` cerrada sin escribir una línea de C++
- Próximo foco del Consejo: ADR-048 Fase F2 (NTP + community_id + Suricata)

---

## Deudas abiertas — ordenadas por prioridad

### P0 — ADR-048 Fase F2 prerequisitos (bloqueantes para datasets UEx)
| ID | Descripción | Estimación |
|----|-------------|-----------|
| DEBT-ARGUSPP-NTP-001 | NTP+chrony en todos los nodos. Health-check rechaza arranque si offset >1s. Gate P0 del correlation-engine. | 1 sesión |
| DEBT-ARGUSPP-COMMUNITY-ID-001 | Habilitar community_id en Suricata y Zeek desde configuración inicial. Primary key del join cross-tool. | 1 sesión |

### P1 — Post-merge CI/CD
| ID | Descripción | Estimación |
|----|-------------|-----------|
| BACKLOG-CI-ENTERPRISE-001 | Jenkins gate `make emecas++` en Jenkinsfile.dev. `agent any`. Stage Enterprise después de Unit Tests. | 1 sesión |
| DEBT-ARGUSPP-SURICATA-001 | Integrar Suricata en Vagrantfile + EMECAS. eve.json → rag-security → servidor. AppArmor obligatorio. | 2 sesiones |

### P2 — ADR-048 correlación
| ID | Descripción |
|----|-------------|
| DEBT-ARGUSPP-CORRELATION-001 | Correlation-engine v1.0 C++20. CrisisWindow disparador. Esquema Arrow con columnas opcionales 4 fuentes. |
| DEBT-ARGUSPP-ZEEK-001 | Integrar Zeek. conn/dns/ssl/files.log → servidor. community_id prerequisito. |

### P3 — No bloquea
| ID | Descripción |
|----|-------------|
| DEBT-FIREWALL-BUILD-LEGACY-001 | firewall-acl-agent/build ruta antigua (seed_client header faltante). No bloquea — build-debug funciona. |

---

## Reglas permanentes (recordatorio para DAY {NEXT_DAY})

- Edición ficheros en VM: siempre `python3 << 'PYEOF'`, nunca `sed -i` sin `-e ''` en macOS
- ZMQ slow joiner: publisher `bind()` ANTES de subscriber `connect()`
- `epoch_id` en wire header: seleccionar clave ANTES de descifrar
- `vendor.key` NUNCA en disco, NUNCA en repo — solo en Vault
- EMECAS++ tiene 3 actos. Enterprise ⊃ OSS — EMECAS++ verde implica EMECAS verde.
- NTP/chrony es P0 gate para correlation-engine (ADR-046 v3 + ADR-048)
- Gate ODR pre-merge: `make PROFILE=production all` antes de cualquier merge a main
- BACKLOG-RESEARCH-KALMAN-001.md está en docs/experiments, pendiente entrada en docs/BACKLOG.md

---

## Wire header (recordatorio)
```
[uint32_t size][uint16_t epoch_id][2B reserved][LZ4+encrypted]
  bytes 0-3      bytes 4-5         bytes 6-7     bytes 8+
```
epoch_id=0: community. epoch_id>0: enterprise.

---

## Próximos pasos sugeridos (sin orden prescriptivo)

1. **`make emecas`** — verificar que main sigue verde tras el merge
2. **BACKLOG-CI-ENTERPRISE-001** — añadir stage `make emecas++` en Jenkinsfile.dev (~30 líneas)
3. **DEBT-ARGUSPP-NTP-001** — provision.sh: instalar chrony, health-check offset >1s → exit 1
4. Consultar Consejo si el orden NTP→community_id→Suricata es el óptimo para ADR-048 Fase F2

---

*Generado al cierre de DAY {DAY} — {DATE} · main*
"""


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    root = Path(".")
    missing = [p for p in [BACKLOG_PATH, README_PATH] if not (root / p).exists()]
    if missing:
        print(f"❌ Ficheros no encontrados: {missing}")
        print("   Ejecuta el script desde la raíz del proyecto.")
        sys.exit(1)

    print("\n🔧 Actualizando BACKLOG.md…")
    backlog = read(BACKLOG_PATH)
    backlog_new = update_backlog(backlog)
    if backlog_new != backlog:
        write(BACKLOG_PATH, backlog_new)
    else:
        print("  ⚠️  BACKLOG.md sin cambios detectados — revisar manualmente")

    print("\n🔧 Actualizando README.md…")
    readme = read(README_PATH)
    readme_new = update_readme(readme)
    if readme_new != readme:
        write(README_PATH, readme_new)
    else:
        print("  ⚠️  README.md sin cambios detectados — revisar manualmente")

    print(f"\n🔧 Generando {PROMPT_PATH}…")
    PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    write(PROMPT_PATH, PROMPT_DAY167)

    print(f"""
╔════════════════════════════════════════════════════════════╗
║  ✅ Documentación DAY {DAY} generada                        ║
╚════════════════════════════════════════════════════════════╝

Ficheros actualizados:
  • docs/BACKLOG.md  — sección DAY {DAY} + status table
  • README.md        — DAY-STATUS + hito DAY {DAY}
  • {PROMPT_PATH}

Pasos siguientes:
  1. git diff docs/BACKLOG.md README.md  — revisar cambios
  2. Ajustar manualmente cualquier sección que necesite precisión
  3. git add -A && git commit -m "docs: DAY {DAY} post-merge documentation"
  4. Mañana: python3 update_day166.py → sustituir por update_day167.py

Keypair activo: {KEYPAIR}
""")


if __name__ == "__main__":
    main()