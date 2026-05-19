#!/usr/bin/env bash
# =============================================================================
# update-day158-docs.sh — Actualiza BACKLOG.md y README.md tras DAY 158
# Uso: ./tools/update-day158-docs.sh  (desde la raíz del repo)
# =============================================================================
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
BACKLOG="$REPO_ROOT/docs/BACKLOG.md"
README="$REPO_ROOT/README.md"
DATE="2026-05-19"
DAY="158"
TAG="v0.9.2-day157"

echo "=== DAY $DAY — Actualizando docs ==="
echo "  BACKLOG: $BACKLOG"
echo "  README:  $README"
echo ""

# -----------------------------------------------------------------------------
# 1. BACKLOG.md — nuevas deudas ADR-046 v3
# -----------------------------------------------------------------------------
python3 << 'PYEOF'
import re, sys, os

backlog_path = os.path.join(
    os.popen("git rev-parse --show-toplevel").read().strip(),
    "docs/BACKLOG.md"
)

with open(backlog_path, "r") as f:
    content = f.read()

# -- Deudas ya existentes que no debemos duplicar --
new_debts = [
    "DEBT-ARGUSPP-NTP-001",
    "DEBT-ARGUSPP-RESOURCE-001",
    "DEBT-ARGUSPP-SURICATA-001",
    "DEBT-ARGUSPP-ZEEK-001",
    "DEBT-ARGUSPP-WAZUH-001",
    "DEBT-ARGUSPP-COMMUNITY-ID-001",
    "DEBT-ARGUSPP-CORRELATION-001",
    "DEBT-ARGUSPP-TIMEOUT-CONFIG-001",
    "DEBT-ARGUSPP-NEO4J-TTL-001",
    "DEBT-ARGUSPP-MITRE-001",
    "DEBT-ARGUSPP-BENCHMARK-001",
    "DEBT-PAPER-SYNTHETIC-001",
]

to_add = [d for d in new_debts if d not in content]
if not to_add:
    print("  [BACKLOG] Todas las deudas ADR-046 v3 ya presentes. Sin cambios.")
    sys.exit(0)

# -- Bloque a insertar --
block = """
---

## ADR-046 v3 — aRGus++ Multi-Source Pipeline (DAY 158)

> Aprobado Consejo 8/8. Supersede ADR-046 v1 y v2.
> Principio rector: **la crisis es la ventana de correlación**.
> Disparadores múltiples (aRGus/Suricata/Zeek/Wazuh).
> community_id como primary key de correlación cross-tool.
> Secuencia: v1.0 (aRGus only) → v1.1 (+ Suricata) → v1.2 (+ Zeek) → v2.0 (+ Wazuh + Neo4j).

| ID | Descripción | Prioridad | Estado |
|---|---|---|---|
| DEBT-ARGUSPP-NTP-001 | NTP+chrony en todos los nodos. Health-check rechaza arranque si offset >1s. Gate P0 del correlation-engine. | P0 | OPEN |
| DEBT-ARGUSPP-COMMUNITY-ID-001 | Habilitar community_id en Suricata y Zeek desde configuración inicial. Primary key del join cross-tool. | P0 en v1.1 | OPEN |
| DEBT-ARGUSPP-SURICATA-001 | Integrar Suricata en Vagrantfile + EMECAS. eve.json → rag-security → servidor. | P1 | OPEN |
| DEBT-ARGUSPP-ZEEK-001 | Integrar Zeek en Vagrantfile + EMECAS. conn/dns/ssl/files.log → servidor. | P1 | OPEN |
| DEBT-ARGUSPP-CORRELATION-001 | Implementación C++20 correlation-engine v1.0. Disparador aRGus + buffer + flush Parquet. Esquema Arrow con columnas opcionales para 4 fuentes desde v1.0. | P1 | OPEN |
| DEBT-ARGUSPP-TIMEOUT-CONFIG-001 | Mapa source_wait_timeout configurable por JSON (argus:5s, suricata:10s, zeek:20s, wazuh:90s). crisis_idle_timeout:120s separado. late_arrival:true para Wazuh tardío. | P1 en v1.0 | OPEN |
| DEBT-ARGUSPP-NEO4J-TTL-001 | TTL + compactación + cold storage Neo4j. Prerequisito de producción real. Grafo puede crecer explosivamente sin esto. | P1 pre-producción | OPEN |
| DEBT-ARGUSPP-RESOURCE-001 | Medir CPU/RAM/disco de las 4 fuentes en RPi5 y N100 bajo carga MITRE. Prerequisito para definir tiers de despliegue. | P1 con hardware | OPEN |
| DEBT-ARGUSPP-MITRE-001 | mitre-generator + Atomic Red Team. Ver ADR-047 (pendiente redacción). | P1 post-hardware | OPEN |
| DEBT-ARGUSPP-BENCHMARK-001 | Re-ejecutar BACKLOG-BENCHMARK-CAPACITY-001 con las 4 fuentes activas. | P1 post-hardware | OPEN |
| DEBT-ARGUSPP-WAZUH-001 | Wazuh agent en edge + manager en servidor central. P2 post-medición de recursos en hardware físico. | P2 | OPEN |
| DEBT-PAPER-SYNTHETIC-001 | Sección paper v24: curva F1 vs ratio académico/sintético. Refs: Arp et al.[2022], Wagner et al.[2022], Sommer&Paxson[2010]. | P2 | OPEN |

**ADR-047 pendiente:** mitre-generator — orquestador de experimentos MITRE ATT&CK para ground truth reproducible. Consenso 8/8 Consejo DAY 158.

**Nota arquitectónica (DAY 158):** Cada herramienta genera su propio Parquet con su propio esquema.
El esquema final en Neo4j es aditivo. No se puede predefinir el esquema de Suricata/Zeek/Wazuh
hasta que se integren. community_id es el pegamento entre esquemas distintos.
Los timeouts del correlation-engine controlan cuánto espera el servidor a que converjan las señales
una vez abierta la CrisisWindow — no controlan el período de recolección del edge (que es continuo).
Una CrisisWindow es un registro de evento, no un dataset de entrenamiento. Los datasets de
entrenamiento se acumulan de cientos/miles de CrisisWindows a lo largo de días/semanas (ADR-040).
"""

# Insertar antes del último separador o al final
if "## ADR-046 v3" not in content:
    content = content.rstrip() + "\n" + block + "\n"
    with open(backlog_path, "w") as f:
        f.write(content)
    print(f"  [BACKLOG] Añadidas {len(to_add)} deudas ADR-046 v3.")
else:
    print("  [BACKLOG] Bloque ADR-046 v3 ya presente.")
PYEOF

# -----------------------------------------------------------------------------
# 2. README.md — actualizar estado del proyecto
# -----------------------------------------------------------------------------
python3 << 'PYEOF'
import os, re

repo_root = os.popen("git rev-parse --show-toplevel").read().strip()
readme_path = os.path.join(repo_root, "README.md")

with open(readme_path, "r") as f:
    content = f.read()

# Línea de estado DAY actual
day_line_old = re.search(r'\*\*DAY activo[^*]*\*\*[^\n]*', content)
day_line_new = "**DAY activo:** 158 | **Tag:** v0.9.2-day157 | **Branch:** main"

if day_line_old:
    content = content[:day_line_old.start()] + day_line_new + content[day_line_old.end():]
    print("  [README] Línea DAY actualizada.")
else:
    print("  [README] No se encontró línea DAY — busca manualmente.")

# Bloque de estado si existe
status_marker = "<!-- DAY-STATUS -->"
status_block = f"""<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 158 |
| Tag | v0.9.2-day157 |
| Branch | main |
| EMECAS | ✅ Verde (19-05-2026) |
| Pipeline | 6/6 RUNNING |
| ADR-046 | v3 aprobado Consejo 8/8 |
| Próximo hito | DEBT-ARGUSPP-SURICATA-001 |
| Deadline FEDER | 22-09-2026 |
<!-- /DAY-STATUS -->"""

if "<!-- DAY-STATUS -->" in content and "<!-- /DAY-STATUS -->" in content:
    content = re.sub(
        r'<!-- DAY-STATUS -->.*?<!-- /DAY-STATUS -->',
        status_block,
        content,
        flags=re.DOTALL
    )
    print("  [README] Bloque DAY-STATUS actualizado.")
elif "<!-- DAY-STATUS -->" not in content:
    # Insertar después del primer h2
    content = re.sub(
        r'(## [^\n]+\n)',
        r'\1\n' + status_block + '\n',
        content,
        count=1
    )
    print("  [README] Bloque DAY-STATUS insertado.")

# ADR-046 v3 en la tabla de ADRs si existe
if "ADR-046" in content and "v3" not in content.split("ADR-046")[1][:100]:
    content = content.replace(
        "ADR-046",
        "ADR-046 v3"
    )
    print("  [README] ADR-046 actualizado a v3.")

with open(readme_path, "w") as f:
    f.write(content)

print("  [README] Guardado.")
PYEOF

# -----------------------------------------------------------------------------
# 3. Verificación final
# -----------------------------------------------------------------------------
echo ""
echo "=== Verificación ==="
echo "Deudas ADR-046 v3 en BACKLOG:"
grep -c "DEBT-ARGUSPP" "$BACKLOG" || echo "  0 (revisar)"
echo ""
echo "Estado en README:"
grep -A2 "DAY-STATUS" "$README" | head -5 || echo "  No encontrado"
echo ""
echo "=== Ficheros modificados ==="
git diff --stat HEAD -- docs/BACKLOG.md README.md
echo ""
echo "Para commitear:"
echo "  git add docs/BACKLOG.md README.md"
echo "  git commit -m 'docs(day158): ADR-046 v3 debts + status update'"
echo "  git push origin main"
PYEOF