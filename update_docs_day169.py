#!/usr/bin/env python3
"""
update_docs_day169.py — aRGus NDR
=================================================================
Actualiza docs/BACKLOG.md y README.md desde el estado DAY 166
hasta DAY 169, cubriendo el retraso documental de tres días:

  DAY 167 — NTP/chrony (DEBT-ARGUSPP-NTP-001 P0) + correlation-engine
            scaffold (ADR-048 F2) + BACKLOG-CI-ENTERPRISE-001
            (Jenkins gate make emecas++). Merge a main 7b45feca.
  DAY 168 — Vagrantfile multi-VM: Suricata 7.0.10 + Zeek 8.2.0 +
            Wazuh 4.x en ml_defender_gateway_lan (192.168.100.0/24).
            community-id habilitado en Suricata y Zeek.
            Merge a main 21642e87.
  DAY 169 — Día de arquitectura. ADR-046 v4 + AdapterSpec v1 cerrados.
            Separación de planos. ADR-050 pendiente (seis vectores).
            community_id en aRGus (protobuf + sniffer) ABIERTO P0.

PROPIEDADES:
  * Idempotente: cada inserción comprueba un centinela antes de aplicar.
    Se puede ejecutar N veces sin duplicar contenido.
  * No usa sed. Lectura/escritura con Python (regla macOS del proyecto).
  * --dry-run para previsualizar sin escribir.
  * Backup .bak antes de tocar nada (salvo en --dry-run).

USO (desde la raíz del repo en macOS):
    python3 update_docs_day169.py --dry-run     # previsualizar
    python3 update_docs_day169.py               # aplicar
=================================================================
"""

import argparse
import shutil
import sys
from pathlib import Path

# ─── Parámetros del día ──────────────────────────────────────────────────────
DAY        = 169
DATE       = "2026-05-29"
OLD_TAG    = "v1.0.0-day166"
NEW_TAG    = "v1.0.0-day166"   # main no re-taggea cada día; 167/168 fueron merges directos
MAIN_SHA   = "21642e87"        # main tras merge DAY 168

# ─── Utilidades ──────────────────────────────────────────────────────────────

class Patcher:
    """Aplica reemplazos e inserciones idempotentes sobre un fichero de texto."""

    def __init__(self, path: Path, dry_run: bool):
        self.path = path
        self.dry_run = dry_run
        self.text = path.read_text(encoding="utf-8")
        self.original = self.text
        self.log = []

    def replace_once(self, old: str, new: str, label: str):
        """Reemplaza la PRIMERA aparición de `old`. Idempotente: si `new`
        ya está presente y `old` no, no hace nada."""
        if new in self.text and old not in self.text:
            self.log.append(f"  · SKIP (ya aplicado): {label}")
            return
        if old not in self.text:
            self.log.append(f"  ! AVISO (anclaje no encontrado): {label}")
            return
        self.text = self.text.replace(old, new, 1)
        self.log.append(f"  ✓ replace: {label}")

    def insert_after(self, anchor: str, block: str, sentinel: str, label: str):
        """Inserta `block` justo después de `anchor`. Idempotente vía `sentinel`:
        si `sentinel` ya está en el texto, no inserta."""
        if sentinel in self.text:
            self.log.append(f"  · SKIP (ya insertado): {label}")
            return
        if anchor not in self.text:
            self.log.append(f"  ! AVISO (anclaje no encontrado): {label}")
            return
        self.text = self.text.replace(anchor, anchor + block, 1)
        self.log.append(f"  ✓ insert: {label}")

    def commit(self):
        changed = self.text != self.original
        print(f"\n── {self.path} ──")
        for line in self.log:
            print(line)
        if not changed:
            print("  (sin cambios)")
            return
        if self.dry_run:
            print("  [dry-run] no se escribe nada")
            return
        backup = self.path.with_suffix(self.path.suffix + ".bak")
        shutil.copy2(self.path, backup)
        self.path.write_text(self.text, encoding="utf-8")
        print(f"  → escrito. Backup en {backup.name}")


# ─── BACKLOG.md ──────────────────────────────────────────────────────────────

def patch_backlog(dry_run: bool):
    path = Path("docs/BACKLOG.md")
    if not path.exists():
        print(f"! No existe {path} — ¿estás en la raíz del repo?")
        return
    p = Patcher(path, dry_run)

    # 1) Fecha de cabecera
    p.replace_once(
        "*Última actualización: DAY 166 — 2026-05-27*",
        f"*Última actualización: DAY {DAY} — {DATE}*",
        "cabecera fecha",
    )

    # 2) Bloque CERRADO DAY 167-168-169 al principio de la zona de cierres.
    #    Se inserta justo antes del primer "## ✅ CERRADO DAY 166".
    cerrado_block = """## ✅ CERRADO DAY 168

### Vagrantfile multi-VM — Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x
- **Status:** ✅ COMPLETADO DAY 168 — merge a main `21642e87`
- Cuatro VMs en `ml_defender_gateway_lan` (192.168.100.0/24), `autostart: false`:
  - `defender` 192.168.100.1 — aRGus NDR completo (primary)
  - `suricata` 192.168.100.10 — Suricata 7.0.10, AF_PACKET, community-id:yes, PROMISC
  - `zeek` 192.168.100.11 — Zeek 8.2.0, community-id-v1, PROMISC
  - `wazuh` 192.168.100.12 — Wazuh 4.x manager running, NTP OK
  - `client` 192.168.100.50 — tcpreplay + nmap/hydra/sqlmap/atomic-red-team
- 50.248 reglas ET Open cargadas en Suricata.
- `WAZUH_MANAGER_PASSWORD` eliminado del Vagrantfile (fix de seguridad).

### DEBT-ARGUSPP-COMMUNITY-ID-001 — community_id en Suricata + Zeek (PARCIAL)
- **Status:** 🟡 60% DAY 168 — configuración hecha, falta aRGus
- community-id habilitado en Suricata (`community-id: yes`) y Zeek (`community-id-v1`).
- **PENDIENTE (P0, DAY 169+):** campo `community_id` en el contrato protobuf y
  cálculo en el sniffer de aRGus. El ID NO viene por defecto en aRGus — Suricata,
  Zeek y Wazuh lo traen de fábrica, aRGus no.
- **Catch crítico (Kimi):** el `community_id` del sniffer debe ser idéntico byte a byte
  al de Zeek/Suricata para la misma 5-tupla. Canonicalización: `proto` numérico (6/17),
  no string (`"tcp"`); orden de endpoints normalizado. Si difiere, el join cross-tool
  falla en silencio — es el mismo bug de endianness que cazamos al principio.

### REGLAS PERMANENTES nuevas DAY 168
- **REGLA PERMANENTE (DAY 168):** Nunca `set -e` en provisions del Vagrantfile.
  Usar `|| true` (no bloqueante) o `|| { exit 1; }` (bloqueante explícito).
- **REGLA PERMANENTE (DAY 168):** El fix de DNS (`chattr +i /etc/resolv.conf`)
  SIEMPRE después de instalar chrony — chrony reescribe resolv.conf al arrancar.
- **REGLA PERMANENTE (DAY 168):** Nunca `cat << 'EOF'` anidado dentro de un
  heredoc `<<-SHELL` en el Vagrantfile — usar `printf`. El anidamiento rompe el parser.

## ✅ CERRADO DAY 167

### DEBT-ARGUSPP-NTP-001 — NTP+chrony en todos los nodos (P0)
- **Status:** ✅ COMPLETADO DAY 167 — merge a main `7b45feca`
- chrony instalado y configurado en todos los nodos del pipeline.
- Health-check rechaza el arranque si el offset NTP es >1s.
- Gate P0 del correlation-engine: `community_id` es inútil sin timestamps sincronizados
  entre las cinco fuentes (aRGus/Suricata/Zeek/Wazuh).

### correlation-engine scaffold (ADR-048 F2)
- **Status:** ✅ COMPLETADO DAY 167 — andamiaje inicial
- Esqueleto C++20 del correlation-engine con `source_wait_timeout` por fuente
  (argus 5s / suricata 10s / zeek 20s / wazuh 90s) y `crisis_idle_timeout` 120s.
- Esquema Arrow con columnas opcionales para las 4 fuentes desde v1.0.

### BACKLOG-CI-ENTERPRISE-001 — Jenkins gate make emecas++
- **Status:** ✅ COMPLETADO DAY 167 — 11 pasadas Jenkins hasta verde
- Stage `make emecas++` en `Jenkinsfile.dev`: tras Unit Tests, antes de Build .deb.
- Precondición: Vault dev activo (`make vault-dev-start`).
- Fallo del Acto I, II o III → pipeline rojo, no merge.
- `package-deb` y `deploy-vagrant-test` marcados como deferred (skip) en dev.
- Fix `pkill -x etcd-server` (self-match SIGTERM, Fase 5).
- Deudas registradas: DEBT-PACKAGE-DEB-001 (deferred), DEBT-DEPLOY-VAGRANT-001
  (deferred), KNOWN-FAIL-VM-PERF-001 (documentado), DEBT-XGBOOST-HEADERS-001
  (headers desde pip + fallback curl en Vagrantfile).

"""
    p.insert_after(
        "## ✅ CERRADO DAY 166",
        "",  # no-op anchor protection; real insert below
        sentinel="## ✅ CERRADO DAY 168",
        label="(guard) bloque cierres 167/168",
    )
    # La inserción real: anteponer el bloque antes del marcador DAY 166.
    p.replace_once(
        "## ✅ CERRADO DAY 166",
        cerrado_block + "## ✅ CERRADO DAY 166",
        "bloque CERRADO DAY 167+168",
        )

    # 3) Sección de arquitectura DAY 169 + deudas nuevas abiertas.
    #    Se inserta antes de la "## 🔑 Decisiones de diseño consolidadas".
    arquitectura_block = """## 🏛️ DAY 169 — Día de arquitectura

**Estado:** rama de arquitectura. Sin merge de código de pipeline — trabajo de diseño.

- **ADR-046 v4 — APROBADO.** Cuarta iteración del Multi-Source Pipeline. Refina la
  separación de planos: plano de datos (telemetría cruda por fuente) vs plano de
  correlación (CrisisWindow + community_id como pegamento) vs plano de decisión.
- **AdapterSpec v1 — CERRADO.** Contrato formal del adaptador por fuente: cómo cada
  motor (Suricata/Zeek/Wazuh) entrega su Parquet con su esquema propio y cómo el
  correlation-engine lo une de forma aditiva vía `community_id`.
- **Separación de planos** consolidada como principio de diseño.
- **ADR-050 — PENDIENTE de redacción.** Los seis vectores de ataque de la sesión MITRE,
  el bootstrap de la víctima y la corrección criptográfica del canal de telemetría.
  Se redactará como hicimos con ADR-046 (borrador → Consejo).

### DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 — community_id nativo en aRGus (P0)
**Severidad:** 🔴 P0 — gate del dataset federado
**Estado:** ABIERTO — DAY 169
**Componente:** `protobuf/network_security.proto` + `sniffer`

community_id viene de fábrica en Suricata, Zeek y Wazuh, pero NO en aRGus.
Trabajo pendiente:
1. `protobuf/network_security.proto`: añadir campo `community_id` (string, field ~20).
   protobuf3 backwards-compatible — campos nuevos no rompen componentes existentes.
2. `sniffer`: calcular community_id (SHA1 de la 5-tupla:
   src_ip + dst_ip + src_port + dst_port + proto).
3. Propagar por el pipeline: sniffer → ml-detector → correlation-engine.

**Catch crítico (Kimi — gate real):** la canonicalización debe ser idéntica byte a byte
a la de Zeek/Suricata para la misma 5-tupla. `proto` como número (6/17), no string;
orden de endpoints normalizado (menor primero). Si difiere, el join cross-tool falla
en silencio. Verificación obligatoria: misma 5-tupla → mismo community_id en las 4
herramientas, comparado a mano antes de declararlo cerrado.

**Test de cierre:** misma 5-tupla inyectada → community_id idéntico en aRGus, Suricata
y Zeek. Diff byte a byte = 0.

### ADR-050 — Sesión MITRE + corrección cripto telemetría (PENDIENTE redacción)
**Estado:** ⏳ BORRADOR PENDIENTE — DAY 169
**Contenido a redactar:** seis vectores de ataque de la sesión MITRE controlada,
bootstrap de las dos víctimas, corrección criptográfica del canal de telemetría.
Flujo: borrador → Consejo de Sabios → aprobación → implementación.

"""
    p.insert_after(
        "## 🔑 Decisiones de diseño consolidadas",
        "",
        sentinel="## 🏛️ DAY 169 — Día de arquitectura",
        label="(guard) arquitectura DAY 169",
    )
    p.replace_once(
        "## 🔑 Decisiones de diseño consolidadas",
        arquitectura_block + "## 🔑 Decisiones de diseño consolidadas",
        "sección arquitectura DAY 169",
        )

    # 4) Footer
    p.replace_once(
        "*DAY 166 — 2026-05-27 · main @ main*",
        f"*DAY {DAY} — {DATE} · main @ {MAIN_SHA}*",
        "footer fecha/sha",
    )

    p.commit()


# ─── README.md ───────────────────────────────────────────────────────────────

def patch_readme(dry_run: bool):
    path = Path("README.md")
    if not path.exists():
        print(f"! No existe {path} — ¿estás en la raíz del repo?")
        return
    p = Patcher(path, dry_run)

    # 1) Encabezado de estado
    p.replace_once(
        "## Estado actual — DAY 166 (2026-05-27)",
        f"## Estado actual — DAY {DAY} ({DATE})",
        "encabezado estado",
    )

    # 2) Tabla DAY-STATUS (entre los comentarios HTML). Reemplazo del bloque entero.
    old_status = """<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | 166 |
| Tag | v1.0.0-day166 |
| Branch | main |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ✅ VERDE — 3 actos verdes y reproducibles (DAY 166) |
| Pipeline | 6/6 RUNNING |
| Crypto lifecycle | FASE 0 ✅ + FASE 1 ✅ + FASE 2a ✅ + FASE 2b ✅ + FASE 3 ✅ + EMECAS++ ✅ |
| Wire header epoch_id | ✅ [uint32_t][uint16_t epoch_id][2B reserved][LZ4] — 13/13 tests |
| vendor.key | ✅ Modelo B — solo en Vault dev, nunca en disco |
| ADR-045 v2 | ✅ Consejo 8/8 — implementado FASES 0-3 + EMECAS++ |
| Próximo hito | DAY 167: BACKLOG-CI-ENTERPRISE-001 (Jenkins gate) + ADR-048 F2 (NTP + community_id) |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->"""
    new_status = f"""<!-- DAY-STATUS -->
| Campo | Valor |
|---|---|
| DAY | {DAY} |
| Tag | {NEW_TAG} |
| Branch | main @ {MAIN_SHA} |
| EMECAS++ OSS | ✅ verde — test-all + test-e2e-synthetic-full + test-e2e-synthetic-firewall |
| EMECAS++ Enterprise | ✅ VERDE — 3 actos + Jenkins gate (DAY 167) |
| Pipeline | 6/6 RUNNING |
| NTP/chrony | ✅ DEBT-ARGUSPP-NTP-001 — health-check rechaza offset >1s (DAY 167) |
| correlation-engine | 🟡 scaffold ADR-048 F2 (DAY 167) |
| Multi-VM | ✅ Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x en 192.168.100.0/24 (DAY 168) |
| community_id | 🟡 Suricata+Zeek configurados · aRGus protobuf+sniffer PENDIENTE P0 (DAY 169) |
| Arquitectura | ✅ ADR-046 v4 + AdapterSpec v1 (DAY 169) · ADR-050 pendiente |
| Próximo hito | community_id nativo en aRGus (protobuf+sniffer) + ADR-050 |
| Gate UEx/INCIBE | Datasets de valor científico (no deadline duro) |
<!-- /DAY-STATUS -->"""
    p.replace_once(old_status, new_status, "tabla DAY-STATUS")

    # 3) Hitos DAY 167/168/169 — insertar antes de "### Hitos DAY 163 🎉"
    hitos_block = """### Hitos DAY 169 🏛️
- **Día de arquitectura.** `ADR-046 v4` aprobado (Multi-Source Pipeline, separación de planos). `AdapterSpec v1` cerrado (contrato del adaptador por fuente). `ADR-050` pendiente de redacción (seis vectores de la sesión MITRE + corrección cripto telemetría).
  - **DEBT-ARGUSPP-COMMUNITY-ID-ARGUS-001 abierta (P0)** — community_id nativo en aRGus: campo en protobuf + cálculo SHA1 de la 5-tupla en el sniffer. Catch de Kimi: canonicalización idéntica byte a byte a Zeek/Suricata o el join cross-tool falla en silencio.

### Hitos DAY 168 🎉
- **Vagrantfile multi-VM** — Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x + client en `ml_defender_gateway_lan` (192.168.100.0/24, `autostart: false`). community-id habilitado en Suricata y Zeek. 50.248 reglas ET Open. `WAZUH_MANAGER_PASSWORD` eliminado (fix seguridad). Merge a main `21642e87`.
  - **3 reglas permanentes nuevas** — nunca `set -e` en provisions (usar `|| true` / `|| { exit 1; }`); DNS fix `chattr +i` SIEMPRE tras chrony; nunca heredoc `cat << 'EOF'` anidado en `<<-SHELL` (usar `printf`).

### Hitos DAY 167 🎉
- **DEBT-ARGUSPP-NTP-001 CERRADA (P0)** — chrony en todos los nodos, health-check rechaza arranque si offset >1s. Gate del correlation-engine: community_id es inútil sin timestamps sincronizados.
  - **correlation-engine scaffold (ADR-048 F2)** — esqueleto C++20 con `source_wait_timeout` por fuente y `crisis_idle_timeout` 120s.
  - **BACKLOG-CI-ENTERPRISE-001 CERRADA** — stage `make emecas++` en Jenkinsfile.dev (11 pasadas hasta verde). Vault dev como precondición. Acto I/II/III rojo → no merge. Merge a main `7b45feca`.

"""
    p.insert_after(
        "### Hitos DAY 163 🎉",
        "",
        sentinel="### Hitos DAY 169 🏛️",
        label="(guard) hitos 167/168/169",
    )
    p.replace_once(
        "### Hitos DAY 163 🎉",
        hitos_block + "### Hitos DAY 163 🎉",
        "hitos DAY 167+168+169",
        )

    # 4) Tabla de milestones — añadir entradas 167/168/169 tras la línea DAY 166
    p.insert_after(
        "  - ✅ DAY 166: **EMECAS++ 3 actos verdes · merge enterprise a main · VaultProvider caché RCU confirmado · vault-fault-inject PASSED · Zero downtime demostrado · Tag v1.0.0-day166** 🎉",
        "\n  - ✅ DAY 167: **DEBT-ARGUSPP-NTP-001 (P0) · correlation-engine scaffold ADR-048 F2 · BACKLOG-CI-ENTERPRISE-001 Jenkins gate · merge main 7b45feca** 🎉"
        "\n  - ✅ DAY 168: **Vagrantfile multi-VM Suricata 7.0.10 + Zeek 8.2.0 + Wazuh 4.x · community-id Suricata/Zeek · 3 reglas permanentes · merge main 21642e87** 🎉"
        "\n  - ✅ DAY 169: **Día de arquitectura · ADR-046 v4 + AdapterSpec v1 · separación de planos · ADR-050 pendiente · community_id nativo aRGus P0 abierto** 🏛️",
        sentinel="✅ DAY 167: **DEBT-ARGUSPP-NTP-001",
        label="milestones 167/168/169",
    )

    # 5) Reemplazar la línea "🔜 DAY 167" del bloque milestones por "🔜 DAY 170"
    p.replace_once(
        "  - 🔜 DAY 167: **BACKLOG-CI-ENTERPRISE-001 (Jenkins gate `make emecas++`) + ADR-048 F2 (DEBT-ARGUSPP-NTP-001 + DEBT-ARGUSPP-COMMUNITY-ID-001) + DEBT-ARGUSPP-SURICATA-001**",
        "  - 🔜 DAY 170: **community_id nativo en aRGus (protobuf + sniffer, canonicalización Kimi) + ADR-050 borrador + RSS bajo carga (pipeline+client+tcpreplay) + DEBT-ARGUSPP-SURICATA-001 (eve.json → correlation-engine)**",
        "próximo hito 170",
    )

    p.commit()


# ─── main ────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Actualiza docs a DAY 169")
    ap.add_argument("--dry-run", action="store_true",
                    help="previsualiza sin escribir")
    args = ap.parse_args()

    print(f"aRGus NDR — actualización documental DAY {DAY} ({DATE})")
    print(f"Modo: {'DRY-RUN (sin escritura)' if args.dry_run else 'APLICAR'}")

    patch_backlog(args.dry_run)
    patch_readme(args.dry_run)

    print("\nHecho.")
    if not args.dry_run:
        print("Verifica con:  git diff docs/BACKLOG.md README.md")
        print("Backups creados: docs/BACKLOG.md.bak  README.md.bak")


if __name__ == "__main__":
    main()