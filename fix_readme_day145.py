#!/usr/bin/env python3
"""
fix_readme_day145.py — Actualiza README.md de estado DAY 138 → DAY 145.
Ejecutar desde la raíz del repo: python3 fix_readme_day145.py
macOS-safe: no usa sed -i.
"""

from pathlib import Path

README = Path("README.md")

def r(old, new, content):
    if old not in content:
        print(f"⚠️  ANCHOR NO ENCONTRADO:\n  {repr(old[:80])}")
        return content
    return content.replace(old, new, 1)

content = README.read_text(encoding="utf-8")

# ── 1. Badge Hardened (v0.6.0 → v0.7.0) ─────────────────────────────────────
content = r(
    "[![Hardened](https://img.shields.io/badge/Security-v0.6.0--hardened__variant__a-brightgreen)]()",
    "[![Hardened](https://img.shields.io/badge/Security-v0.7.0--variant__b-brightgreen)]()",
    content
)

# ── 2. Badge AppArmor (6/6 → 7/7) ────────────────────────────────────────────
content = r(
    "[![AppArmor](https://img.shields.io/badge/AppArmor-6%2F6_enforce-brightgreen)]()",
    "[![AppArmor](https://img.shields.io/badge/AppArmor-7%2F7_enforce-brightgreen)]()",
    content
)

# ── 3. Añadir badge IRP si no existe ─────────────────────────────────────────
if "IRP-argus--network--isolate" not in content:
    content = r(
        "[![TDH](https://img.shields.io/badge/Methodology-Test_Driven_Hardening-purple)](https://github.com/alonsoir/test-driven-hardening)",
        "[![TDH](https://img.shields.io/badge/Methodology-Test_Driven_Hardening-purple)](https://github.com/alonsoir/test-driven-hardening)\n[![IRP](https://img.shields.io/badge/IRP-argus--network--isolate_ADR--042-red)]()",
        content
    )

# ── 4. Bloque de estado (línea con tag + branch) ──────────────────────────────
content = r(
    "✅ `main` is tagged `v0.6.0-hardened-variant-a`. Branch activa: `feature/variant-b-libpcap` — ADR-029 Variant B pipeline completo (DAY 138).\n**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**",
    "✅ `main` is tagged `v0.7.0-variant-b`. Branch activa: `main` — ADR-029 Variant A vs B x86 completado (DAY 145). Paper v19 publicado.\n**PRE-PRODUCTION: do not deploy in hospitals until ACRL (DEBT-PENTESTER-LOOP-001) is complete.**",
    content
)

# ── 5. Cabecera estado actual ─────────────────────────────────────────────────
content = r(
    "## Estado actual — DAY 138 (2026-05-01)",
    "## Estado actual — DAY 145 (2026-05-08)",
    content
)

# ── 6. Tag activo + branch activa ────────────────────────────────────────────
content = r(
    "**Tag activo:** `v0.6.0-hardened-variant-a` | **Branch activa:** `feature/variant-b-libpcap` @ `da1badf7`",
    "**Tag activo:** `v0.7.0-variant-b` | **Branch activa:** `main`",
    content
)

# ── 7. Paper version ──────────────────────────────────────────────────────────
content = r(
    "**Paper:** arXiv:2604.04952 · Draft v18 (Cornell procesando)",
    "**Paper:** arXiv:2604.04952 · Draft v19 (ADR-029 Variant A vs B)",
    content
)

# ── 8. Pipeline status ────────────────────────────────────────────────────────
content = r(
    "- 6/6 componentes RUNNING — validado EMECAS DAY 138 ✅\n- `make test-all`: ALL TESTS COMPLETE (9/9 sniffer, incluyendo 8 tests Variant B)\n- `make sniffer && make sniffer-libpcap`: ambos ✅ sin warnings nuevos",
    "- 6/6 componentes RUNNING — validado EMECAS DAY 145 ✅\n- `make test-all`: ALL TESTS COMPLETE (65/65 PASSED — 0 FAILED) ✅\n- `make PROFILE=production all`: Gate ODR — ALL COMPONENTS BUILT ✅\n- `make argus-network-isolate-test`: dry-run PASSED ✅",
    content
)

# ── 9. Hitos DAY 138 → reemplazar por bloque DAY 138-145 ────────────────────
content = r(
    "### Hitos DAY 138 🎉\n- **DEBT-CAPTURE-BACKEND-ISP-001 CERRADA** — commit `1a7f723a`. `CaptureBackend` a 5 métodos puros. Métodos eBPF en `EbpfBackend`. Consejo 5-2-1 → implementado.\n- **DEBT-VARIANT-B-PCAP-IMPL-001 CERRADA** — commits `22df0099` + `da1badf7`. Pipeline completo `pcap_dispatch → proto → LZ4 → ChaCha20 → ZMQ`. Wire format idéntico a Variant A. 8/8 tests PASSED.\n- **DEBT-VARIANT-B-CONFIG-001 REGISTRADA** — JSON propio pendiente. Campos multihilo hardcodeados en binario.\n- **Consejo 8/8 DAY 138** — 7 preguntas, veredictos unánimes: ODR P0 bloqueante, dontwait correcto, nft -f transaccional, seL4 no diseñar ahora.",
    "### Hitos DAY 145 🎉\n- **ADR-029 Variant A vs B x86** — libpcap ~2× eBPF en VirtualBox virtio (artefacto SKB mode). Equivalencia funcional confirmada.\n- **Bootstrap múltiple** — `bootstrap-x86-ebpf` + `bootstrap-x86-libpcap`. `bootstrap` = alias de A.\n- **pipeline-status** distingue Variant A/B + detecta invariant violation.\n- **Relay targets** — resumen inline por velocidad + rutas log + nota MTU en banner.\n- **Paper v19** — §6 ADR-029, §10.9, §11.17, §12, abstract actualizado.\n- **Failed packets (2,630):** artefacto fijo pcap CTU-13 Neris — frames jumbo MTU VirtualBox. No son errores del pipeline.\n\n### Hitos DAY 143-144 🎉\n- **DEBT-IRP-NFTABLES-001 CERRADA** — IRP completo: config → disparo → fork()+execv() → AppArmor 7/7 enforce → 12/12 tests.\n- **DEBT-IRP-SIGCHLD-001 CERRADA** — SA_NOCLDWAIT. SigchldTest.NoZombiesAfterNForks PASSED.\n- **DEBT-IRP-AUTOISO-FALSE-001 CERRADA** — isolate.json única fuente de verdad. 5 tests PASSED.\n- **DEBT-IRP-BACKUP-DIR-001 CERRADA** — /run/argus/irp/. AppArmor + provision.sh actualizados.\n- **Gate ODR production SUPERADO** — 3 ODR violations reales detectadas y corregidas bajo -flto.",
    content
)

# ── 10. Tabla deuda técnica abierta ──────────────────────────────────────────
content = r(
    """### Deuda técnica abierta

| Deuda | Prioridad | Target |
|-------|-----------|--------|
| DEBT-COMPILER-WARNINGS-CLEANUP-001 (ODR P0) | 🔴 Alta — bloqueante | DAY 139+ |
| DEBT-VARIANT-B-CONFIG-001 | 🔴 Alta | pre-FEDER |
| DEBT-IRP-NFTABLES-001 | 🔴 Alta | pre-FEDER |
| DEBT-IRP-QUEUE-PROCESSOR-001 | 🔴 Alta | post-merge |
| DEBT-JENKINS-SEED-DISTRIBUTION-001 | 🔴 Alta | pre-FEDER |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | 🔴 Alta | pre-FEDER |
| DEBT-SEEDS-SECURE-TRANSFER-001 | 🔴 Alta | post-FEDER |
| DEBT-PCAP-CALLBACK-LIFETIME-DOC-001 | 🟢 Baja | trivial |
| DEBT-KEY-SEPARATION-001 | 🟡 Media | post-FEDER |
| DEBT-ADR040-001..012 | ⏳ | post-FEDER |
| DEBT-ADR041-001..006 | ⏳ | pre-FEDER |

### Próxima frontera — DAY 139
1. EMECAS obligatorio
2. `DEBT-COMPILER-WARNINGS-CLEANUP-001` sub-tarea ODR (P0 bloqueante — Consejo 8/8 unánime)
3. O: `DEBT-VARIANT-B-CONFIG-001` (JSON propio + hardcoding + test e2e)
4. Según decisión: `DEBT-IRP-NFTABLES-001` o `DEBT-CRYPTO-MATERIAL-STORAGE-001`""",
    """### Deuda técnica abierta

| Deuda | Prioridad | Target |
|-------|-----------|--------|
| DEBT-IRP-TMPFILES-001 | 🟡 P1 | post-merge (tmpfiles.d reboot) |
| DEBT-IRP-IPSET-TMP-001 | 🟡 P1 | post-merge (ipset_wrapper /tmp) |
| DEBT-EMECAS-VERIFICATION-001 | 🟢 P2 | post-merge (README devs) |
| DEBT-IRP-FLOAT-TYPES-001 | 🟡 P1 | pre-FEDER (tipos score float/double) |
| DEBT-IRP-PROB-CONJUNTA-001 | 🟡 P1 | post-FEDER (señal conjunta) |
| DEBT-ETCD-HA-QUORUM-001 | 🔴 P0 | post-FEDER (OBLIGATORIO) |
| DEBT-IRP-QUEUE-PROCESSOR-001 | 🔴 Alta | post-merge |
| DEBT-JENKINS-SEED-DISTRIBUTION-001 | 🔴 Alta | pre-FEDER |
| DEBT-CRYPTO-MATERIAL-STORAGE-001 | 🔴 Alta | pre-FEDER |
| DEBT-MUTEX-ROBUST-001 | 🟡 P1 | post-FEDER |
| DEBT-ADR040-001..012 | ⏳ | post-FEDER |
| DEBT-ADR041-001..006 | ⏳ | pre-FEDER |

### Próxima frontera — DAY 146+
1. DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot
2. DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
3. Diseño experiment-comparative (aRGus + Suricata + Zeek como cooperadores)
4. Abrir feature/adr029-variant-c-arm64 scope definido""",
    content
)

# ── 11. Tabla de resultados validados — añadir filas ADR-029 ─────────────────
content = r(
    "| **Variant B tests** | **8/8 PASSED** | DAY 138 — unit/integ/stress/regression |",
    """| **Variant B tests** | **9/9 PASSED** | DAY 142 — buffer=8MB verificado |
| **ADR-029 Variant A eBPF (VBox)** | **~10 Mbps / 9,178 pps** | DAY 145 — techo virtio SKB mode |
| **ADR-029 Variant B libpcap (VBox)** | **~19 Mbps / 17,614 pps** | DAY 145 — ~2× eBPF en virtio |
| **IRP cycle** | **PASS** | NORMAL→ISOLATED→ROLLBACK→NORMAL DAY 142 |

> **Nota ADR-029 — Failed packets (2,630):** Artefacto fijo del pcap CTU-13 Neris. Frames jumbo que superan el MTU 1500 de VirtualBox (`errno=90 EMSGSIZE`). Conteo idéntico en los 6 runs — confirma origen en el fichero, no en el pipeline. El sniffer nunca ve esos frames. **No son errores del pipeline.**""",
    content
)

# ── 12. Linux Capabilities — añadir argus-network-isolate ────────────────────
content = r(
    "| ml-detector, rag-ingester, rag-security | none |",
    "| argus-network-isolate | `cap_net_admin` (AppArmor enforce — DAY 143) |\n| ml-detector, rag-ingester, rag-security | none |",
    content
)

# ── 13. Build profiles table — añadir si falta ───────────────────────────────
if "PROFILE=production" not in content:
    content = r(
        "### Workflow diario (REGLA EMECAS)",
        """### Build Profiles

| Profile | Flags | Cuándo usarlo |
|---------|-------|---------------|
| `debug` (**default**) | `-g -O0` | Desarrollo diario |
| `production` | `-O3 -flto -march=native -DNDEBUG` | ODR verification, capacity benchmarks |
| `tsan` | `-fsanitize=thread -g -O1` | Race conditions |
| `asan` | `-fsanitize=address,undefined -g -O1` | Memory errors |

```bash
make all                        # debug (default)
make PROFILE=production all     # ODR check via LTO — gate pre-merge obligatorio
```

### Workflow diario (REGLA EMECAS)""",
        content
    )

# ── 14. IRP section — añadir si no existe ────────────────────────────────────
if "argus-network-isolate" not in content:
    content = r(
        "## Hardened Deployment (ADR-030 Variant A)",
        """## 🛡️ Incident Response Protocol — ADR-042

`argus-network-isolate` — binario C++20 que aísla una interfaz via nftables en 6 pasos transaccionales.
Disparado por `firewall-acl-agent` cuando: `threat_score >= 0.95 AND event_type IN (ransomware, lateral_movement, c2_beacon)`.
**Por defecto:** `auto_isolate: false` — habilitar explícitamente tras configurar whitelist.

```bash
make argus-network-isolate-build   # compilar
make argus-network-isolate-test    # dry-run en eth1
```

## Hardened Deployment (ADR-030 Variant A)""",
        content
    )

# ── 15. Roadmap DONE section ─────────────────────────────────────────────────
content = r(
    "### ✅ DONE — DAY 138 (1 May 2026) — ADR-029 Variant B pipeline 🎉\n- [x] DEBT-CAPTURE-BACKEND-ISP-001 CERRADA — `CaptureBackend` 5 métodos puros\n- [x] DEBT-VARIANT-B-PCAP-IMPL-001 CERRADA — pipeline pcap → proto → LZ4 → ChaCha20 → ZMQ\n- [x] Suite 8 tests Variant B — 8/8 PASSED en make test-all\n- [x] `PcapCallbackData` — mecanismo callback sin friend/miembros públicos\n- [x] Wire format idéntico a Variant A — ml-detector recibe ambos sin modificación\n- [x] Consejo 8/8 DAY 138 — 7 veredictos, ODR P0 bloqueante confirmado",
    """### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉

| Task | Result |
|---|---|
| EMECAS ritual | ✅ 65/65 PASSED |
| PCAP relay x86 eBPF (Variant A) | ✅ ~10 Mbps, 320,524 pkts, exit=0 |
| PCAP relay x86 libpcap (Variant B) | ✅ ~19 Mbps, 320,524 pkts, exit=0 |
| Merge feature/variant-b-libpcap → main | ✅ v0.7.0-variant-b |
| Bootstrap múltiple (x86-ebpf / x86-libpcap) | ✅ Makefile actualizado |
| Paper Draft v19 | ✅ §6 ADR-029, §10.9, §11.17, §12 |

### ✅ DONE — DAY 143-144 — IRP completo + ODR gate 🎉
- [x] DEBT-IRP-NFTABLES-001 CERRADA — IRP completo, AppArmor 7/7 enforce, 12/12 tests
- [x] DEBT-IRP-SIGCHLD-001 CERRADA — SA_NOCLDWAIT
- [x] DEBT-IRP-AUTOISO-FALSE-001 CERRADA — isolate.json única fuente de verdad
- [x] DEBT-IRP-BACKUP-DIR-001 CERRADA — /run/argus/irp/
- [x] Gate ODR production PASSED — 3 violations reales corregidas bajo -flto

### ✅ DONE — DAY 138-142 — ADR-029 Variant B pipeline 🎉
- [x] DEBT-CAPTURE-BACKEND-ISP-001 CERRADA — `CaptureBackend` 5 métodos puros
- [x] DEBT-VARIANT-B-PCAP-IMPL-001 CERRADA — pipeline pcap → proto → LZ4 → ChaCha20 → ZMQ
- [x] DEBT-VARIANT-B-BUFFER-SIZE-001 CERRADA — pcap_create()+pcap_set_buffer_size()
- [x] DEBT-VARIANT-B-MUTEX-001 CERRADA (Nivel 1) — exclusión mutua via tmux
- [x] Suite 9 tests Variant B — 9/9 PASSED""",
    content
)

# ── 16. NEXT section ──────────────────────────────────────────────────────────
content = r(
    "### 🔜 NEXT — DAY 139\n\n| Priority | Task |\n|---|---|\n| 🔴 P0 BLOQUEANTE | `DEBT-COMPILER-WARNINGS-CLEANUP-001` — sub-tarea ODR (UB en C++20) |\n| 🔴 P0 | `DEBT-VARIANT-B-CONFIG-001` — sniffer-libpcap.json propio + test e2e |\n| 🔴 P0 | `DEBT-IRP-NFTABLES-001` — argus-network-isolate con nft -f transaccional |\n| 🟡 P1 | `DEBT-CRYPTO-MATERIAL-STORAGE-001` — prototipo HashiCorp Vault |",
    """### 🔜 NEXT — DAY 146+

| Priority | Task |
|---|---|
| 🟡 P1 | DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot |
| 🟡 P1 | DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp |
| 🟡 P1 | Diseño experiment-comparative (aRGus + Suricata + Zeek como cooperadores) |
| 🟡 P1 | Abrir feature/adr029-variant-c-arm64 scope definido |
| 🟢 P2 | DEBT-EMECAS-VERIFICATION-001 — párrafo README para devs |""",
    content
)

# ── 17. Milestones ────────────────────────────────────────────────────────────
content = r(
    "- ✅ DAY 138: **ISP cerrado · pipeline Variant B completo · 8/8 tests · Consejo 8/8** 🎉\n- 🔜 DAY 139: **ODR cleanup P0 · DEBT-VARIANT-B-CONFIG-001 · IRP nftables**",
    """- ✅ DAY 138: **ISP cerrado · pipeline Variant B completo · 8/8 tests · Consejo 8/8** 🎉
- ✅ DAY 140: **192→0 warnings · -Werror activo · ODR limpio** 🎉
- ✅ DAY 141: **DEBT-VARIANT-B-CONFIG-001 · sniffer-libpcap.json · emails FEDER** 🎉
- ✅ DAY 142: **IRP pasos 1-6 · buffer=8MB · mutex Nivel 1 · Consejo 8/8** 🎉
- ✅ DAY 143: **DEBT-IRP-NFTABLES-001 sesión 3/3 CERRADA — IRP completo · AppArmor 7/7 · 12 tests** 🎉
- ✅ DAY 144: **3 deudas P0 IRP cerradas · Gate ODR production · 65/65 tests** 🎉
- ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio · Bootstrap múltiple · Paper v19 · v0.7.0-variant-b** 🎉
- 🔜 DAY 146+: **DEBT-IRP-TMPFILES-001 · DEBT-IRP-IPSET-TMP-001 · experiment-comparative · ARM64 scope**""",
    content
)

# ── 18. arXiv badge / paper section ──────────────────────────────────────────
content = r(
    "**Published:** 3 April 2026 · **Draft v18** (Cornell procesando) · MIT license",
    "**Published:** 3 April 2026 · **Draft v19** (ADR-029 Variant A vs B) · MIT license",
    content
)

README.write_text(content, encoding="utf-8")
print("✅ README.md actualizado (DAY 138 → DAY 145)")
print("\nVerificar:")
print("  grep -n 'DAY 145\\|v0.7.0\\|v19\\|DAY 146' README.md | head -20")
print("\nSiguiente:")
print("  git add README.md")
print("  git commit -m 'fix: README.md DAY 138 → DAY 145 (git checkout --ours cogió versión incorrecta)'")
print("  git push origin main:refs/heads/feature/fix-readme-day145")
print("  # Abrir PR y mergear")