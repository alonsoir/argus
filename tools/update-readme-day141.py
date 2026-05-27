#!/usr/bin/env python3
# update-readme-day141.py — ejecutar desde la raíz del repo
# python3 tools/update-readme-day141.py

import re

with open('README.md', 'r') as f:
    content = f.read()

# ── 1. Estado actual — DAY (número) ──────────────────────────────────────────
content = re.sub(
    r'## Estado actual — DAY \d+ \(\d{4}-\d{2}-\d{2}\)',
    '## Estado actual — DAY 141 (2026-05-04)',
    content
)

# ── 2. Branch y commit ───────────────────────────────────────────────────────
content = content.replace(
    "feature/variant-b-libpcap` @ `f2852de2`",
    "feature/variant-b-libpcap` @ `63a37d9d`"
)

# ── 3. Tabla de deuda técnica — DEBT-COMPILER-WARNINGS → cerrada ─────────────
content = content.replace(
    "| DEBT-COMPILER-WARNINGS-CLEANUP-001 (ODR P0) | 🟡 En curso — 192→67 warnings | DAY 140 |",
    "| DEBT-VARIANT-B-BUFFER-SIZE-001 | 🔴 P1 | pre-FEDER (pre-benchmark ARM64) |\n| DEBT-VARIANT-B-MUTEX-001 | 🔴 P1 | pre-FEDER (Nivel 1 script) |"
)

content = content.replace(
    "| DEBT-VARIANT-B-CONFIG-001 | 🔴 Alta | pre-FEDER |",
    ""
)

content = content.replace(
    "| DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 | 🟢 Baja | trivial |",
    ""
)

# ── 4. Hitos DAY 139/140 → marcar ✅ y añadir DAY 141 ───────────────────────
content = content.replace(
    "- ✅ DAY 140: **192→0 warnings · -Werror activo · ODR limpio con LTO · Jenkinsfile skeleton · THIRDPARTY-MIGRATIONS.md** 🎉\n- 🔜 DAY 141: **DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 · DEBT-VARIANT-B-CONFIG-001 · emails Andrés Caro**",
    "- ✅ DAY 140: **192→0 warnings · -Werror activo · ODR limpio con LTO · Jenkinsfile skeleton · THIRDPARTY-MIGRATIONS.md** 🎉\n- ✅ DAY 141: **DEBT-VARIANT-B-CONFIG-001 · sniffer-libpcap.json · exclusión mutua · emails FEDER** 🎉\n- 🔜 DAY 142: **DEBT-IRP-NFTABLES-001 sesión 1 · DEBT-VARIANT-B-BUFFER-SIZE-001**"
)

# ── 5. Próxima frontera ───────────────────────────────────────────────────────
content = re.sub(
    r'### Próxima frontera — DAY \d+.*?(?=\n---|\n## )',
    """### Próxima frontera — DAY 142
1. EMECAS obligatorio
2. `DEBT-IRP-NFTABLES-001` — sesión 1/3 (argus-network-isolate, nftables transaccional)
3. `DEBT-VARIANT-B-BUFFER-SIZE-001` — pcap_create()+pcap_set_buffer_size()
4. `DEBT-VARIANT-B-MUTEX-001` — script exclusión mutua Nivel 1

""",
    content,
    flags=re.DOTALL
)

with open('README.md', 'w') as f:
    f.write(content)

print("✅ README.md actualizado — DAY 141")