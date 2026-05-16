#!/usr/bin/env python3
"""
update_day154.py — Actualiza BACKLOG.md y README.md con los cambios de DAY 154.
Ejecutar desde la raíz del repo: python3 update_day154.py
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent

# ─────────────────────────────────────────────────────────────────────────────
# BACKLOG.md
# ─────────────────────────────────────────────────────────────────────────────

def update_backlog():
    path = ROOT / "docs" / "BACKLOG.md"
    content = path.read_text()

    # 1. DEBT-FIREWALL-AUTONOMY-MODE-001 → CERRADA DAY 154
    content = content.replace(
        "DEBT-FIREWALL-AUTONOMY-MODE-001:             0% ⏳  P1 pre-FEDER (default-deny en autonomía)",
        "DEBT-FIREWALL-AUTONOMY-MODE-001:           100% ✅  CERRADA DAY 154 (FirewallAutonomyReactor)"
    )

    # 2. Añadir DEBT-FIREWALL-DENY-SELECTIVE-001 como nueva deuda P0
    new_debt = """
### DEBT-FIREWALL-DENY-SELECTIVE-001 — Regla default-deny demasiado agresiva
**Severidad:** 🔴 P0 — DAY 154 (Consejo 8/8 UNÁNIME)
**Estado:** ABIERTO — CERRAR EN DAY 155
**Componente:** `firewall-acl-agent/src/core/autonomy_reactor.cpp`

La regla actual `iptables -I INPUT 1 -j DROP` en modo AUTONOMOUS bloquea:
- Loopback (127.0.0.1) → rompe IPC interno, health checks, métricas
- Conexiones establecidas (ESTABLISHED, RELATED) → rompe sesiones activas de médicos en el HIS
- Subredes internas del hospital (imaging, monitorización, HL7, DICOM) → puede parar un quirófano
- SSH de management → deja al sysadmin fuera en momento de crisis

**Regla correcta (Kimi — orden crítico):**
```bash
iptables -I INPUT 1 -i lo -j ACCEPT --comment "argus-autonomy-lo"
iptables -I INPUT 2 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT \\
  --comment "argus-autonomy-established"
iptables -I INPUT 3 -s 10.0.0.0/8 -j ACCEPT --comment "argus-autonomy-rfc1918-a"
iptables -I INPUT 4 -s 172.16.0.0/12 -j ACCEPT --comment "argus-autonomy-rfc1918-b"
iptables -I INPUT 5 -s 192.168.0.0/16 -j ACCEPT --comment "argus-autonomy-rfc1918-c"
iptables -I INPUT 6 -j DROP --comment "argus-autonomy-deny"
```

Subnets whitelist configurables vía JSON — no hardcodeadas.
El DROP debe ser la ÚLTIMA regla de INPUT, no la primera.

**Test de cierre:** AUTONOMOUS activado → loopback responde, SSH interno funciona,
tráfico externo bloqueado → 6 tests actualizados PASSED.
**Estimación:** 1.5h DAY 155

"""
    # Insertar antes de la sección DEBT-AUTONOMY-ZMQ-EVENTS-001
    content = content.replace(
        "### DEBT-AUTONOMY-ZMQ-EVENTS-001",
        new_debt + "### DEBT-AUTONOMY-ZMQ-EVENTS-001"
    )

    # 3. Actualizar DEBT-AUTONOMY-ZMQ-EVENTS-001 con consenso del Consejo
    content = content.replace(
        "**Componente:** `CryptoAutonomyStateMachine` + ZeroMQ bus\n\nCada transición de estado",
        "**Componente:** `CryptoAutonomyStateMachine` + ZeroMQ bus\n\n**Consenso Consejo DAY 154 (7/8):** ZMQ pub/sub directo, sin polling como mecanismo principal. Solo polling reconciliador lento (60-120s) como safety net. Topic: `argus.crypto.autonomy`. Transport: `inproc://argus.autonomy` (mismo proceso) o `ipc:///run/argus/autonomy.sock`. Founder (Alonso): acuerda ZMQ como mecanismo principal.\n\nCada transición de estado"
    )

    # 4. Notas del Consejo DAY 154
    consejo_day154 = """
## 📝 Notas del Consejo de Sabios — DAY 154 (8/8)

> "DAY 154 — ADR-045 VaultClient decomposition completa. DEBT-FIREWALL-AUTONOMY-MODE-001 cerrada.
>
> **Hitos técnicos:**
> `ICryptoDeriver` + `HkdfCryptoDeriver`: 6 tests (determinismo, aislamiento family/index, seed inválido → nullopt, fingerprint).
> `IEtcdRegistrar` + `StubEtcdRegistrar`: 4 tests. VaultClient por composición completa (4º ctor). 7 tests common/.
> `FirewallAutonomyReactor`: AUTONOMOUS/DEGRADED → default-deny, NORMAL → lift. Executor inyectable. 6 tests. 48/48 firewall tests.
> EMECAS: bootstrap ✅ | test-all ✅ | hardened-full ✅ | check-prod-all ✅.
>
> **Consenso P1 — ZMQ directo (7/8 + Founder):**
> No polling como mecanismo principal. `TransitionCallback` ya definido en `crypto_autonomy.h` — el cableado es mínimo. Latencia 30s inaceptable en entorno ransomware activo. Añadir polling reconciliador 60-120s solo como safety net. Topic: `argus.crypto.autonomy`. Transport: `inproc://` si mismo proceso, `ipc://` si procesos separados. ChatGPT: 'Polling → race windows → comportamiento no determinista → debugging infernal en fail-closed systems.'
>
> **Consenso P2 — Default-deny SELECTIVO (8/8 UNÁNIME):**
> La regla actual `-I INPUT 1 -j DROP` es INCORRECTA para hospitales. Eleva a P0 DAY 155.
> Kimi: 'Un `vagrant up` en un laptop no sufre. Un hospital sí.' DROP en posición 1 rompe loopback → IPC interno del propio NDR queda ciego. Orden correcto: lo → ESTABLISHED → RFC1918 → DROP. Subnets whitelist configurables vía JSON.
>
> **Consenso P3 — HWM primero (8/8):**
> Sin HWM explícito, benchmarks no son reproducibles. Throughput alto con 50% drops silenciosos es una mentira. Medir tres estados: steady, failure, recovery.
>
> **Consenso P4 — ISP después (8/8):**
> `DEBT-CAPTURE-BACKEND-ISP-001` espera a post-benchmark. Reactor con señal real es P0 funcional; ISP es P2 de calidad.
>
> **ChatGPT — transición arquitectónica:**
> 'El sistema ya no es solo un NDR. Empieza a comportarse como una plataforma resiliente distribuida. Propagación de estado, reconciliación, persistencia, backpressure y recovery semantics son ahora más importantes que añadir features nuevas.'
>
> **Nueva deuda registrada:**
> `DEBT-FIREWALL-DENY-SELECTIVE-001` (P0, DAY 155): regla actual puede paralizar hospital en autonomía.
>
> 'No estamos comparando herramientas — estamos construyendo el sistema que protege a los que no tienen escudo.' — Founder · DAY 154"
> — Consejo de Sabios (8/8) · DAY 154 · v0.8.0-adr045

"""
    # Insertar antes de las notas del Consejo de Sabios DAY 151
    content = content.replace(
        "## 📝 Notas del Consejo de Sabios — DAY 151",
        consejo_day154 + "## 📝 Notas del Consejo de Sabios — DAY 151"
    )

    # 5. Estado global — marcar DAY 154
    content = content.replace(
        "DEBT-AUTONOMY-ZMQ-EVENTS-001:             0% ⏳  P1 (transiciones sin eventos ZMQ)",
        "DEBT-FIREWALL-DENY-SELECTIVE-001:          0% ⏳  P0 DAY 155 (regla actual rompe hospitales)\nDEBT-AUTONOMY-ZMQ-EVENTS-001:             0% ⏳  P1 DAY 155 (ZMQ pub/sub directo)"
    )

    content = content.replace(
        "ADR-045 VaultClient Decomposition:        0% ⏳  DAY 153+ (IVaultTransport + ICacheManager primero)",
        "ADR-045 VaultClient Decomposition:      100% ✅  CERRADA DAY 154 — v0.8.0-adr045"
    )

    content = content.replace(
        "DEBT-FIREWALL-AUTONOMY-MODE-001:             0% ⏳  P1 pre-FEDER (default-deny en autonomía)",
        "DEBT-FIREWALL-AUTONOMY-MODE-001:           100% ✅  CERRADA DAY 154 (FirewallAutonomyReactor)"
    )

    # 6. Fecha última actualización
    content = content.replace(
        "*DAY 151 — 14 Mayo 2026 · main @ 9e692a4e*",
        "*DAY 154 — 16 Mayo 2026 · main @ v0.8.0-adr045*"
    )

    path.write_text(content)
    print("✅ BACKLOG.md actualizado")


# ─────────────────────────────────────────────────────────────────────────────
# README.md
# ─────────────────────────────────────────────────────────────────────────────

def update_readme():
    path = ROOT / "README.md"
    content = path.read_text()

    # 1. Tag activo y estado
    content = content.replace(
        "**Tag activo:** `v0.8.0-day151` | **Branch activa:** `main`",
        "**Tag activo:** `v0.8.0-adr045` | **Branch activa:** `main`"
    )

    # 2. Keypair (sin cambios en DAY 154, se mantiene)

    # 3. Hitos DAY 154
    hitos_154 = """### Hitos DAY 154 🎉
- **ADR-045 VaultClient decomposition COMPLETA** — `ICryptoDeriver` + `HkdfCryptoDeriver` (6 tests), `IEtcdRegistrar` + `StubEtcdRegistrar` (4 tests). VaultClient por composición con 4º ctor inyectable. 7 tests common/. v0.8.0-adr045.
- **DEBT-FIREWALL-AUTONOMY-MODE-001 CERRADA** — `FirewallAutonomyReactor`: AUTONOMOUS/DEGRADED → `iptables -I INPUT 1 argus-autonomy-deny DROP`, NORMAL → `iptables -D INPUT`. Executor inyectable (testable sin root). 6 tests. 48/48 firewall tests verdes.
- **Fix EMECAS** — `crypto_deriver.h` y `etcd_registrar.h` añadidos al install target. `test_auto_isolate` T6 corregido para `-Werror` en production build.
- **Consejo 8/8** — ZMQ directo para señal autonomía (P0 DAY 155). Default-deny actual INCORRECTA para hospitales → `DEBT-FIREWALL-DENY-SELECTIVE-001` P0 DAY 155.
- **EMECAS:** bootstrap ✅ | test-all ✅ | hardened-full ✅ | check-prod-all ✅.

"""
    content = content.replace(
        "### Hitos DAY 149 🎉",
        hitos_154 + "### Hitos DAY 149 🎉"
    )

    # 4. Tabla de deudas — añadir nueva + actualizar existentes
    content = content.replace(
        "| DEBT-FIREWALL-AUTONOMY-MODE-001 | 🔴 P1 pre-FEDER | Firewall default-deny en autonomía extendida |",
        "| DEBT-FIREWALL-AUTONOMY-MODE-001 | ✅ CERRADA DAY 154 | FirewallAutonomyReactor |\n| DEBT-FIREWALL-DENY-SELECTIVE-001 | 🔴 P0 DAY 155 | Regla actual rompe hospitales — selectiva |"
    )

    # 5. Milestones — añadir DAY 154
    milestone_154 = "- ✅ DAY 154: **ADR-045 VaultClient decomposition · DEBT-FIREWALL-AUTONOMY-MODE-001 CERRADA · 48/48 tests · v0.8.0-adr045** 🎉\n"
    content = content.replace(
        "- ✅ DAY 151: **ICryptoProvider",
        milestone_154 + "- ✅ DAY 151: **ICryptoProvider"
    )

    # 6. Próxima frontera
    content = content.replace(
        "1. **EMECAS protocolo** — `vagrant destroy -f && vagrant up && make bootstrap && make test-all`\n2. **Integrar etcd-server con VaultClient**",
        "1. **EMECAS protocolo** — `vagrant destroy -f && vagrant up && make bootstrap && make test-all`\n2. **DEBT-FIREWALL-DENY-SELECTIVE-001 P0** — regla default-deny selectiva (loopback + ESTABLISHED + RFC1918)\n3. **DEBT-AUTONOMY-ZMQ-EVENTS-001** — ZMQ pub/sub `argus.crypto.autonomy` (inproc/ipc)\n4. **BACKLOG-ZMQ-TUNING-001** — HWM + Linger en todos los sockets"
    )

    path.write_text(content)
    print("✅ README.md actualizado")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔧 Actualizando BACKLOG.md y README.md — DAY 154")
    update_backlog()
    update_readme()
    print("")
    print("📋 Próximos pasos:")
    print("  git add docs/BACKLOG.md README.md")
    print("  git checkout -b docs/day154-backlog-readme")
    print("  git commit -m 'DAY 154: BACKLOG + README — ADR-045 cerrado, DEBT-FIREWALL-DENY-SELECTIVE-001 P0'")
    print("  git push origin docs/day154-backlog-readme")
    print("  gh pr create --base main --head docs/day154-backlog-readme \\")
    print("    --title 'DAY 154: BACKLOG + README actualizados' \\")
    print("    --body 'ADR-045 cerrado. DEBT-FIREWALL-AUTONOMY-MODE-001 cerrada. DEBT-FIREWALL-DENY-SELECTIVE-001 P0 registrada.'")