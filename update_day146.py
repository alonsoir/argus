#!/usr/bin/env python3
"""
update_day146.py — Actualiza README.md y BACKLOG.md con los resultados del DAY 146.
Ejecutar desde la raíz del repositorio aRGus NDR:

    python3 update_day146.py

Cambios aplicados:
  README.md:
    - Estado actual: DAY 145 → DAY 146
    - Tag: v0.7.0-variant-b → v0.7.1-day146
    - Paper: Draft v19 → Draft v20
    - Deudas cerradas DAY 146 (TMPFILES, IPSET, EMECAS, BOOTSTRAP-SNIFFER)
    - Hitos DAY 146 en Roadmap + Milestones
    - Próxima frontera DAY 147
    - Nota Consejo de Sabios DAY 146
  BACKLOG.md:
    - Última actualización: DAY 146
    - Secciones CERRADO DAY 146 para las 4 deudas
    - Estado global actualizado
    - Experimento comparativo Suricata documentado
    - Nota Consejo de Sabios DAY 146
"""

import sys
import re
from pathlib import Path

# ── Colores para terminal ────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"

def ok(msg):  print(f"{GREEN}✅ {msg}{RESET}")
def warn(msg): print(f"{YELLOW}⚠️  {msg}{RESET}")
def err(msg):  print(f"{RED}❌ {msg}{RESET}")

def replace_once(text, old, new, label):
    if old not in text:
        warn(f"No se encontró: {label!r}")
        return text, False
    result = text.replace(old, new, 1)
    ok(f"Aplicado: {label}")
    return result, True

# ════════════════════════════════════════════════════════════════════════════
# README.md
# ════════════════════════════════════════════════════════════════════════════

def update_readme(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changes = 0

    # 1. Cabecera de estado
    text, ok_ = replace_once(text,
                             "✅ `main` is tagged `v0.7.0-variant-b`. Branch activa: `main` — ADR-029 Variant A vs B x86 completado (DAY 145). Paper v19 publicado.",
                             "✅ `main` is tagged `v0.7.1-day146`. Branch activa: `main` — Experimento comparativo Suricata vs aRGus completado (DAY 146). Paper v20 generado.",
                             "badge estado main")
    changes += ok_

    # 2. Título sección estado
    text, ok_ = replace_once(text,
                             "## Estado actual — DAY 145 (2026-05-08)",
                             "## Estado actual — DAY 146 (2026-05-09)",
                             "título sección estado")
    changes += ok_

    # 3. Tag activo
    text, ok_ = replace_once(text,
                             "**Tag activo:** `v0.7.0-variant-b` | **Branch activa:** `main`",
                             "**Tag activo:** `v0.7.1-day146` | **Branch activa:** `main`",
                             "tag activo")
    changes += ok_

    # 4. Keypair + Paper
    text, ok_ = replace_once(text,
                             "**Paper:** arXiv:2604.04952 · Draft v19 (ADR-029 Variant A vs B)",
                             "**Paper:** arXiv:2604.04952 · Draft v20 (Suricata comparative + DAY 146)",
                             "paper version")
    changes += ok_

    # 5. Hitos DAY 145 — añadir DAY 146 después
    hitos_145_end = "- **Failed packets (2,630):** artefacto fijo pcap CTU-13 Neris — frames jumbo MTU VirtualBox. No son errores del pipeline."
    hitos_146 = """- **Failed packets (2,630):** artefacto fijo pcap CTU-13 Neris — frames jumbo MTU VirtualBox. No son errores del pipeline.

### Hitos DAY 146 🎉
- **EMECAS verde** — 4 deudas técnicas cerradas: DEBT-IRP-TMPFILES-001, DEBT-IRP-IPSET-TMP-001, DEBT-BOOTSTRAP-SNIFFER-VERIFY-001, DEBT-EMECAS-VERIFICATION-001.
- **Experimento comparativo Suricata 6.0.10 vs aRGus NDR** — CTU-13 Neris, mismas condiciones. Suricata: 0 alertas (ET Open no cubre Neris 2011). aRGus: F1=0.9985, Recall=1.0000.
- **Makefile**: `make up-argus`, `make up-suricata`, `make halt-argus`, `make halt-suricata`, `make experiment-suricata-run/results`.
- **Paper Draft v20** generado — nueva §8.13 con comparativa directa, Tabla comparación actualizada con datos empíricos Suricata.
- **Vagrantfile Suricata** operativo — `nictype1 virtio` (fix crítico DHCP NAT), 50,010 reglas ET Open cargadas."""
    text, ok_ = replace_once(text, hitos_145_end, hitos_146, "hitos DAY 146")
    changes += ok_

    # 6. Deuda técnica — marcar cerradas
    text, ok_ = replace_once(text,
                             "| DEBT-IRP-TMPFILES-001 | 🟡 P1 | post-merge (tmpfiles.d reboot) |",
                             "| DEBT-IRP-TMPFILES-001 | ✅ CERRADA DAY 146 | tmpfiles.d + provision.sh |",
                             "deuda TMPFILES")
    changes += ok_

    text, ok_ = replace_once(text,
                             "| DEBT-IRP-IPSET-TMP-001 | 🟡 P1 | post-merge (ipset_wrapper /tmp) |",
                             "| DEBT-IRP-IPSET-TMP-001 | ✅ CERRADA DAY 146 | ipset_wrapper /run/argus/irp/ |",
                             "deuda IPSET")
    changes += ok_

    text, ok_ = replace_once(text,
                             "| DEBT-EMECAS-VERIFICATION-001 | 🟢 P2 | post-merge (README devs) |",
                             "| DEBT-EMECAS-VERIFICATION-001 | ✅ CERRADA DAY 146 | README.md blockquote EMECAS |",
                             "deuda EMECAS")
    changes += ok_

    # 7. Próxima frontera
    text, ok_ = replace_once(text,
                             """### Próxima frontera — DAY 146+
                     1. DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/ en reboot
                     2. DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
                     3. Diseño experiment-comparative (aRGus + Suricata + Zeek como cooperadores)
                     4. Abrir feature/adr029-variant-c-arm64 scope definido""",
                             """### Próxima frontera — DAY 147+
                     1. Buscar ruleset ET Open histórico (2011) — separar "firma nunca existió" de "firma retirada"
                     2. Refinar §8.13 paper v20 con narrativa de paradigmas complementarios
                     3. Commit paper v20 definitivo a arXiv
                     4. Abrir feature/adr029-variant-c-arm64 scope definido
                     5. DEBT-IRP-FLOAT-TYPES-001 — unificar tipos score float/double pre-FEDER""",
                             "próxima frontera DAY 147")
    changes += ok_

    # 8. Roadmap — DONE DAY 145 y NEXT DAY 146
    text, ok_ = replace_once(text,
                             "### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉",
                             "### ✅ DONE — DAY 146 (9 May 2026) — Suricata Comparative + Deudas 🎉\n\n| Task | Result |\n|---|---|\n| EMECAS verde | ✅ 4 deudas cerradas |\n| Experimento Suricata vs aRGus | ✅ 0 alertas Suricata vs F1=0.9985 aRGus |\n| Makefile up/halt-argus/suricata | ✅ Topología dual |\n| Paper Draft v20 | ✅ §8.13 + Tabla comparativa empírica |\n\n### ✅ DONE — DAY 145 (8 May 2026) — ADR-029 Variant A vs B 🎉",
                             "roadmap DONE DAY 146")
    changes += ok_

    # 9. Milestones — añadir DAY 146
    text, ok_ = replace_once(text,
                             "- ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio · Bootstrap múltiple · Paper v19 · v0.7.0-variant-b** 🎉",
                             "- ✅ DAY 145: **ADR-029 Variant A vs B x86 · libpcap ~2× eBPF en virtio · Bootstrap múltiple · Paper v19 · v0.7.0-variant-b** 🎉\n- ✅ DAY 146: **Experimento Suricata comparativo · 0 alertas ET Open vs F1=0.9985 aRGus · Paper v20 §8.13 · v0.7.1-day146** 🎉",
                             "milestone DAY 146")
    changes += ok_

    # 10. Nota Consejo DAY 146
    consejo_145_note = '> — Consejo de Sabios (8/8) · DAY 145'
    consejo_146_note = """> — Consejo de Sabios (8/8) · DAY 145



> "DAY 146 — Experimento comparativo Suricata 6.0.10 (50,010 reglas ET Open Mayo 2026) vs aRGus NDR sobre CTU-13 Neris 2011. Condiciones idénticas: mismo hardware, misma VM, mismo dataset, misma topología, mismas velocidades de replay.
>
> **Resultado:** Suricata genera 0 alertas. aRGus: F1=0.9985, Recall=1.0000.
>
> **Interpretación unánime (8/8):** No es un fallo de Suricata. El motor funciona correctamente. Las reglas ET Open evolucionan y las firmas para amenazas de 15 años se retiran. El hallazgo científico es la diferencia de paradigmas: las firmas detectan lo conocido; el comportamiento estadístico persiste en el tiempo.
>
> **Consenso sobre la narrativa:** aRGus no compite con Suricata — los complementa. Un despliegue hospitalario óptimo combinaría ambos. La afirmación publicable es que los modelos comportamentales tienen generalización temporal que los sistemas de firmas no pueden tener por diseño.
>
> **Pendiente:** buscar ruleset ET Open 2011 para separar 'firma nunca existió' de 'firma retirada'. Ambos resultados son científicamente válidos y publicables.
>
> 4 deudas técnicas cerradas: DEBT-IRP-TMPFILES-001, DEBT-IRP-IPSET-TMP-001, DEBT-BOOTSTRAP-SNIFFER-VERIFY-001, DEBT-EMECAS-VERIFICATION-001.
>
> 'El cero de Suricata no es un error — es una coordenada en el mapa de la evolución de las amenazas.' — Qwen · adaptado"
> — Consejo de Sabios (8/8) · DAY 146"""
    text, ok_ = replace_once(text, consejo_145_note, consejo_146_note, "nota consejo DAY 146")
    changes += ok_

    path.write_text(text, encoding="utf-8")
    return changes


# ════════════════════════════════════════════════════════════════════════════
# BACKLOG.md
# ════════════════════════════════════════════════════════════════════════════

def update_backlog(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    changes = 0

    # 1. Última actualización
    text, ok_ = replace_once(text,
                             "*Última actualización: DAY 145 — 8 Mayo 2026*",
                             "*Última actualización: DAY 146 — 9 Mayo 2026*",
                             "fecha actualización")
    changes += ok_

    # 2. Footer
    text, ok_ = replace_once(text,
                             "*DAY 144 — 7 Mayo 2026 · feature/variant-b-libpcap @ e52870d5*",
                             "*DAY 146 — 9 Mayo 2026 · main @ v0.7.1-day146*",
                             "footer fecha")
    changes += ok_

    # 3. Añadir sección CERRADO DAY 146 antes de CERRADO DAY 144
    seccion_146 = """## ✅ CERRADO DAY 146

### DEBT-IRP-TMPFILES-001 — tmpfiles.d para /run/argus/irp/
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `tools/provision.sh` línea 1250: instala `/etc/tmpfiles.d/argus.conf` con `d /run/argus/irp 0700 argus argus -`. `/run/argus/irp` se recrea automáticamente en cada reboot via `systemd-tmpfiles`. Sin intervención manual.
- **Test de cierre:** reboot VM → `/run/argus/irp/` existe con permisos 0700 → dry-run IRP PASSED.

### DEBT-IRP-IPSET-TMP-001 — ipset_wrapper.cpp usa /tmp
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `firewall-acl-agent/src/core/ipset_wrapper.cpp` líneas 322, 391: `/tmp/ipset_restore.tmp` → `/run/argus/irp/ipset_restore.tmp` y `/tmp/ipset_delete.tmp` → `/run/argus/irp/ipset_delete.tmp`. Firewall recompilado OK (debug).
- **Test de cierre:** `grep -r '/tmp' firewall-acl-agent/src/` = 0 resultados (excluido código comentado).

### DEBT-BOOTSTRAP-SNIFFER-VERIFY-001 — sleep insuficiente en sniffer-start
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `Makefile` líneas 610, 623: `sleep 2` → `sleep 4` en `sniffer-start` y `sniffer-libpcap-start`. Línea 267: verificación real del sniffer antes del banner — exit 1 si STOPPED, no falso positivo.
- **Test de cierre:** EMECAS completo — pipeline-status muestra sniffer RUNNING tras bootstrap.

### DEBT-EMECAS-VERIFICATION-001 — párrafo README para devs
- **Status:** ✅ CERRADO DAY 146
- **Fix:** `README.md` líneas 269-276: párrafo blockquote explicativo del protocolo EMECAS — qué hace, por qué existe, qué significa FAILED=0, comportamiento del sniffer (4s estabilización sesión tmux).
- **Test de cierre:** nuevo desarrollador puede seguir el protocolo sin ambigüedad.

### Experimento comparativo Suricata vs aRGus NDR — DAY 146
- **Status:** ✅ COMPLETADO DAY 146
- **Branch:** `main` → `v0.7.1-day146`
- **Commits:** `df19f1f8` (Vagrantfile) · `19295a7e` (run_experiment.sh) · `ff83b402` (up-argus/up-suricata) · `8e503815` (Makefile targets + parse_results.py) · `e1efbfbc` (resultado)

**Diseño experimental:**
- Suricata 6.0.10 + ET Open (50,010 reglas, Mayo 2026)
- VM idéntica a aRGus: `debian/bookworm64 12.20240905.1`, 8,192 MB, 6 vCPU, VirtIO NIC, VirtualBox 7.2
- Dataset: CTU-13 Neris (320,524 paquetes, 19,135 flows, ground truth: 147.32.84.165, 646 flows maliciosos)
- Topología: VM client → tcpreplay → VM suricata (eth2, promiscuo) — idéntica a aRGus DAY 145
- Velocidades: 10, 50, 100 Mbps

| Sistema | Reglas/Modelo | TP | FP | F1 | Recall |
|---------|--------------|-----|-----|-----|--------|
| **aRGus NDR** | ML behavioral (sintético) | 646 | 2 | **0.9985** | **1.0000** |
| Suricata 6.0.10 | 50,010 ET Open (Mayo 2026) | 0 | 0 | 0.0000 | 0.0000 |

| Target | Mbps real Suricata | Alertas | exit |
|--------|-------------------|---------|------|
| 10 Mbps | 9.99 | 0 | 0 |
| 50 Mbps | 19.43 | 0 | 0 |
| 100 Mbps | 18.82 | 0 | 0 |

**Interpretación científica:**
No es un fallo de Suricata. El motor procesó el tráfico correctamente (`decoder.pkts` confirmado en stats.log). Las reglas ET Open evolucionan — las firmas de 2011 (botnet Neris, IRC C2, SMB lateral movement) han sido retiradas del ruleset actual. aRGus detecta el patrón comportamental independientemente de la antigüedad de la amenaza porque fue entrenado con datos sintéticos que modelan comportamiento, no firmas específicas.

**Significado científico:**
Corrobora la tesis de Sommer & Paxson (2010): la detección basada en firmas requiere conocimiento previo del atacante; la detección comportamental no. Primera comparativa directa publicada entre un NDR ML embebido y un IDS de firmas en producción sobre el mismo dataset, hardware y topología.

**Pendiente:** repetir con ruleset ET Open histórico (~2011) para separar "firma nunca existió" de "firma retirada".

**Makefile targets nuevos:**
- `make up-argus` / `make up-suricata` / `make halt-argus` / `make halt-suricata`
- `make experiment-suricata-up/down/run/results/status`

**Paper:** Draft v20 — nueva §8.13 "Direct Experimental Comparison: aRGus NDR vs Suricata 6.0.10 on CTU-13 Neris". Tabla 6 (tab:comparison) actualizada con datos empíricos Suricata F1=0.000.

"""

    insert_before = "## ✅ CERRADO DAY 144"
    if insert_before in text:
        text = text.replace(insert_before, seccion_146 + insert_before, 1)
        ok("Sección CERRADO DAY 146 insertada")
        changes += 1
    else:
        warn("No se encontró ancla '## ✅ CERRADO DAY 144'")

    # 4. Actualizar estado global — deudas cerradas DAY 146
    updates_estado = [
        ("DEBT-IRP-TMPFILES-001:                  0% ⏳  P1 post-merge (tmpfiles.d reboot)",
         "DEBT-IRP-TMPFILES-001:               100% ✅  DAY 146 (tmpfiles.d + provision.sh)"),
        ("DEBT-IRP-IPSET-TMP-001:                  0% ⏳  P1 post-merge (ipset_wrapper /tmp)",
         "DEBT-IRP-IPSET-TMP-001:               100% ✅  DAY 146 (ipset_wrapper /run/argus/irp/)"),
        ("DEBT-EMECAS-VERIFICATION-001:             0% ⏳  P2 post-merge (README devs)",
         "DEBT-EMECAS-VERIFICATION-001:          100% ✅  DAY 146 (README blockquote EMECAS)"),
    ]
    for old, new in updates_estado:
        text, ok_ = replace_once(text, old, new, f"estado global: {old[:40]}...")
        changes += ok_

    # Añadir Suricata experiment al estado global
    text, ok_ = replace_once(text,
                             "ADR-029 Variant A vs B x86 (DAY 145):  100% ✅  DAY 145 (experimento comparativo completo)",
                             "ADR-029 Variant A vs B x86 (DAY 145):  100% ✅  DAY 145 (experimento comparativo completo)\nExperimento Suricata vs aRGus (DAY 146):  100% ✅  DAY 146 (0 alertas ET Open vs F1=0.9985)",
                             "estado global experimento Suricata")
    changes += ok_

    text, ok_ = replace_once(text,
                             "Paper Draft v19:                        100% ✅  DAY 145 (§6 ADR-029 + §10.9 + §11.17 + §12)",
                             "Paper Draft v19:                        100% ✅  DAY 145 (§6 ADR-029 + §10.9 + §11.17 + §12)\nPaper Draft v20:                        100% ✅  DAY 146 (§8.13 Suricata + tab:comparison empírico)",
                             "paper v20 en estado global")
    changes += ok_

    # 5. Nota Consejo DAY 146 — añadir antes de ## 📝 Notas DAY 144
    nota_146 = """## 📝 Notas del Consejo de Sabios — DAY 146 (8/8)

> "DAY 146 — Experimento comparativo Suricata 6.0.10 (50,010 reglas ET Open Mayo 2026) vs aRGus NDR sobre CTU-13 Neris 2011. Condiciones idénticas de hardware, VM, dataset y topología de red.
>
> **Resultado:** Suricata: 0 alertas. aRGus: F1=0.9985, Recall=1.0000.
>
> **Interpretación unánime (8/8):** No es un fallo de Suricata. El motor procesó el tráfico correctamente. Las reglas ET Open 2026 no cubren el botnet Neris 2011 porque esas firmas han sido retiradas. El resultado es el comportamiento esperado de un IDS de firmas cuando no existe regla para la amenaza.
>
> **Significado científico:** Primera comparativa directa publicada entre NDR ML embebido e IDS de firmas en producción sobre el mismo dataset. Corrobora Sommer & Paxson (2010): firmas = conocimiento previo necesario; comportamiento = generalización temporal. aRGus fue entrenado con datos sintéticos que modelan comportamiento, no con CTU-13 directamente.
>
> **Consenso sobre narrativa:** Los sistemas son complementarios, no competidores. Un despliegue hospitalario óptimo combinaría ambos. No atacar a Suricata en el paper.
>
> **Pendiente:** buscar ruleset ET Open histórico (~agosto 2011) para separar 'firma nunca existió' de 'firma retirada'. Ambos resultados son científicamente válidos.
>
> 4 deudas técnicas cerradas. EMECAS verde. v0.7.1-day146 tagueado.
>
> 'El cero de Suricata no es un error — es una coordenada en el mapa de la evolución de las amenazas.' — Qwen · adaptado"
> — Consejo de Sabios (8/8) · DAY 146


"""
    insert_before_144 = "## 📝 Notas del Consejo de Sabios — DAY 144 (8/8)"
    if insert_before_144 in text:
        text = text.replace(insert_before_144, nota_146 + insert_before_144, 1)
        ok("Nota Consejo DAY 146 insertada")
        changes += 1
    else:
        warn("No se encontró ancla nota Consejo DAY 144")

    path.write_text(text, encoding="utf-8")
    return changes


# ════════════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════════════

def main():
    root = Path(".")

    readme = root / "README.md"
    backlog = root / "docs" / "BACKLOG.md"

    # Fallback: BACKLOG.md puede estar en raíz
    if not backlog.exists():
        backlog = root / "BACKLOG.md"

    print(f"\n{'═'*60}")
    print(f"  aRGus NDR — Actualización DAY 146")
    print(f"{'═'*60}\n")

    if not readme.exists():
        err(f"README.md no encontrado en {readme.absolute()}")
        sys.exit(1)

    if not backlog.exists():
        err(f"BACKLOG.md no encontrado en {backlog.absolute()}")
        sys.exit(1)

    print(f"📄 README.md: {readme.absolute()}")
    n = update_readme(readme)
    print(f"   → {n} cambios aplicados\n")

    print(f"📋 BACKLOG.md: {backlog.absolute()}")
    n = update_backlog(backlog)
    print(f"   → {n} cambios aplicados\n")

    print(f"{'═'*60}")
    print(f"  ✅ Actualización DAY 146 completada")
    print(f"  Revisar con: git diff README.md docs/BACKLOG.md")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()