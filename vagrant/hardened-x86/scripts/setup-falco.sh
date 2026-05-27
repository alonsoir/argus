#!/usr/bin/env bash
# vagrant/hardened-x86/scripts/setup-falco.sh
# Instala Falco y carga las reglas específicas de aRGus.
# Post-Consejo DAY 133: añadidas 3 reglas nuevas (10 total).
#
# AppArmor previene. Falco detecta.
# Se ejecuta DENTRO de la hardened VM como root.
set -euo pipefail

FALCO_RULES=/etc/falco/rules.d/argus.yaml

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Falco — runtime security (post-Consejo DAY 133)         ║"
echo "║  Driver: modern_ebpf (VirtualBox compatible)             ║"
echo "╚════════════════════════════════════════════════════════════╝"

# ── Instalar Falco ────────────────────────────────────────────────────────────
if command -v falco &>/dev/null; then
    echo "  ✅ Falco ya instalado: $(falco --version 2>/dev/null | head -1)"
else
    FALCO_DEB=$(ls /vagrant/dist/vendor/falco_*.deb 2>/dev/null | head -1)
    if [ -z "$FALCO_DEB" ]; then
        echo "  ❌ ERROR: falco_*.deb not found in /vagrant"
        echo "  Ejecuta EMECAS dev: vagrant destroy -f && vagrant up && make bootstrap && make test-all"
        exit 1
    fi
    echo "  📦 Instalando desde $FALCO_DEB (offline, ADR-030 BSR)"
    FALCO_FRONTEND=noninteractive FALCO_DRIVER_CHOICE=modern_ebpf dpkg -i "$FALCO_DEB" || \
        apt-get install -f -y --no-install-recommends
    echo "  ✅ Falco instalado (offline)"
fi

# ── Configurar modern_ebpf ────────────────────────────────────────────────────
[ -f /etc/falco/falco.yaml ] && \
    sed -i 's/^driver:.*$/driver: modern_ebpf/' /etc/falco/falco.yaml 2>/dev/null || true

mkdir -p /etc/falco/rules.d

cat > "${FALCO_RULES}" << 'FALCO_RULES_EOF'
# aRGus NDR — Falco rules (DAY 133 rev.Consejo — ADR-030 Variant A)
#
# AppArmor previene accesos prohibidos.
# Falco detecta comportamiento anómalo en lo que AppArmor permite.
#
# Reglas 1-7:  originales DAY 133
# Reglas 8-10: añadidas post-Consejo DAY 133
#
# Estrategia de maduración (Gemini + Kimi):
#   Fase 1 (tuning): AppArmor complain + Falco WARNING
#   Fase 2 (estable): AppArmor enforce + Falco NOTICE
#   Fase 3 (prod):   AppArmor enforce + Falco CRITICAL

# ── Macros ────────────────────────────────────────────────────────────────────

- macro: argus_processes
  condition: proc.name in (etcd-server, sniffer, ml-detector, firewall-acl-agent, rag-ingester, rag-security)

- macro: argus_allowed_write_paths
  condition: >
    fd.name startswith /var/log/argus/ or
    fd.name startswith /etc/ml-defender/ or
    fd.name startswith /opt/argus/

- macro: argus_provisioning_processes
  condition: proc.name in (bash, sh, provision, ansible, vagrant, setup-filesystem, setup-apparmor, setup-falco, deploy-hardened)

# ── Macros estándar Falco (inline — no depender de falco_rules.yaml) ─────────
- macro: open_write
  condition: (evt.type in (open,openat,openat2) and evt.is_open_write=true and fd.typechar=f and fd.num>=0)
- macro: open_read
  condition: (evt.type in (open,openat,openat2) and evt.is_open_read=true and fd.typechar=f and fd.num>=0)
- macro: spawned_process
  condition: evt.type=execve
# ── Regla 1: Escritura fuera del patrón ───────────────────────────────────────
- rule: argus_unexpected_file_open
  desc: Un componente de aRGus escribe en una ruta fuera de su patrón
  condition: >
    argus_processes and open_write and not argus_allowed_write_paths
  output: >
    aRGus unexpected write (proc=%proc.name pid=%proc.pid path=%fd.name user=%user.name)
  priority: WARNING
  tags: [argus, filesystem, adr-030]

# ── Regla 2: Exec inesperado desde componentes ────────────────────────────────
- rule: argus_unexpected_exec
  desc: Un componente de aRGus ejecuta un binario inesperado
  condition: >
    spawned_process and
    proc.pname in (etcd-server, sniffer, ml-detector, rag-ingester, rag-security) and
    not proc.name in (sh, iptables, ipset)
  output: >
    aRGus unexpected exec (parent=%proc.pname child=%proc.name cmd=%proc.cmdline)
  priority: CRITICAL
  tags: [argus, exec, cwe-78, adr-030]

# ── Regla 3: firewall exec algo distinto de iptables/ipset ───────────────────
- rule: argus_firewall_unexpected_exec
  desc: firewall-acl-agent ejecuta algo distinto de iptables/ipset
  condition: >
    spawned_process and proc.pname = firewall-acl-agent and
    not proc.name in (iptables, iptables-save, ipset)
  output: >
    aRGus firewall unexpected exec (child=%proc.name cmd=%proc.cmdline) — CWE-78?
  priority: CRITICAL
  tags: [argus, firewall, cwe-78, adr-030]

# ── Regla 4: Shell spawn desde cualquier componente ───────────────────────────
- rule: argus_shell_spawn
  desc: Un componente de aRGus invoca una shell — casi seguro compromiso
  condition: >
    spawned_process and
    proc.pname in (etcd-server, sniffer, ml-detector, firewall-acl-agent, rag-ingester, rag-security) and
    proc.name in (bash, sh, zsh, dash, ksh)
  output: >
    CRITICAL: aRGus shell spawn (parent=%proc.pname shell=%proc.name cmd=%proc.cmdline)
  priority: CRITICAL
  tags: [argus, shell, critical, adr-030]

# ── Regla 5: Binario del pipeline modificado en runtime ───────────────────────
- rule: argus_binary_modified
  desc: Un binario del pipeline aRGus modificado en runtime — violación BSR (ADR-039)
  condition: >
    open_write and fd.name startswith /opt/argus/bin/ and
    not argus_provisioning_processes
  output: >
    CRITICAL: aRGus BSR violation — binary modified (proc=%proc.name path=%fd.name user=%user.name)
  priority: CRITICAL
  tags: [argus, integrity, adr-039, bsr]

# ── Regla 6: seed.bin accedido por proceso ajeno ─────────────────────────────
- rule: argus_seed_accessed_by_wrong_process
  desc: Un seed.bin es accedido por un proceso que no pertenece al pipeline
  condition: >
    open_read and fd.name glob "/etc/ml-defender/*/seed.bin" and
    not argus_processes and not argus_provisioning_processes
  output: >
    CRITICAL: aRGus seed.bin unexpected access (proc=%proc.name path=%fd.name user=%user.name)
  priority: CRITICAL
  tags: [argus, crypto, seeds, adr-025]

# ── Regla 7: Raw socket desde non-sniffer ────────────────────────────────────
- rule: argus_unexpected_raw_socket
  desc: Componente no-sniffer abre un raw socket
  condition: >
    evt.type = socket and evt.arg.domain in (AF_PACKET, PF_PACKET) and
    proc.name in (ml-detector, rag-ingester, rag-security, etcd-server)
  output: >
    aRGus non-sniffer opened raw socket (proc=%proc.name pid=%proc.pid)
  priority: WARNING
  tags: [argus, network, adr-030]

# ── Regla 8 (nuevo Consejo): Modificación de config en runtime ───────────────
# Detecta tampering silencioso de los JSONs que controlan el pipeline
- rule: argus_config_modified_unexpected
  desc: Fichero de config de aRGus modificado por proceso no autorizado
  condition: >
    open_write and fd.name startswith /etc/ml-defender/ and
    not argus_provisioning_processes and not proc.name = etcd-server
  output: >
    CRITICAL: aRGus config tampered (proc=%proc.name path=%fd.name user=%user.name)
  priority: CRITICAL
  tags: [argus, config, integrity, adr-030]

# ── Regla 9 (nuevo Consejo): Sustitución de modelo o plugin ──────────────────
# Un rename de .so o .gguf en runtime puede ser sustitución maliciosa
- rule: argus_model_or_plugin_replaced
  desc: Modelo ML o plugin de aRGus reemplazado en runtime
  condition: >
    evt.type = rename and
    (fd.name glob "/opt/argus/plugins/*.so" or
     fd.name glob "/opt/argus/models/*.gguf" or
     fd.name glob "/opt/argus/models/*.onnx") and
    not argus_provisioning_processes
  output: >
    CRITICAL: aRGus model/plugin replaced at runtime (proc=%proc.name src=%fd.name user=%user.name)
  priority: CRITICAL
  tags: [argus, integrity, plugins, bsr, adr-025]

# ── Regla 10 (nuevo Consejo): Modificación de perfil AppArmor ────────────────
# Si un atacante modifica los perfiles AA, toda la capa de prevención cae
- rule: argus_apparmor_profile_modified
  desc: Perfil AppArmor de aRGus modificado — invalida toda la capa de prevención
  condition: >
    open_write and fd.name glob "/etc/apparmor.d/argus.*" and
    not argus_provisioning_processes
  output: >
    CRITICAL: aRGus AppArmor profile tampered (proc=%proc.name path=%fd.name user=%user.name)
  priority: CRITICAL
  tags: [argus, apparmor, critical, adr-030]

# ── Regla 11 (DEBT-PROD-APT-SOURCES-INTEGRITY-001 DAY 135): apt sources modificados ──
# Modificar sources.list en producción es el vector clásico de supply-chain attack
- rule: argus_apt_sources_modified
  desc: Fichero apt sources modificado en VM de producción — posible supply-chain attack
  condition: >
    open_write and
    (fd.name = /etc/apt/sources.list or
     fd.name glob "/etc/apt/sources.list.d/*") and
    not argus_provisioning_processes
  output: >
    CRITICAL: apt sources tampered in production (proc=%proc.name path=%fd.name user=%user.name)
  priority: CRITICAL
  tags: [argus, supply-chain, apt, adr-030]

FALCO_RULES_EOF

echo "  ✅ ${FALCO_RULES}: $(wc -l < ${FALCO_RULES}) líneas (11 reglas)"

# ── Validar y arrancar ────────────────────────────────────────────────────────
falco --validate "${FALCO_RULES}" 2>/dev/null && echo "  ✅ Sintaxis OK" || \
    echo "  ⚠️  Validación falló — revisar manualmente"

systemctl enable falco 2>/dev/null || true
systemctl restart falco 2>/dev/null || true

sleep 2
systemctl is-active falco &>/dev/null && \
    echo "  ✅ Falco: RUNNING (11 reglas argus)" || \
    echo "  ⚠️  Falco no arrancó — journalctl -u falco"

echo ""
echo "── Estrategia de maduración ──"
echo "  Fase 1 (tuning): prioridad WARNING — no alertas bloqueantes"
echo "  Fase 2 (estable): subir a NOTICE tras 30 min sin FP"
echo "  Fase 3 (prod): CRITICAL — investigación obligatoria"
echo ""
echo "✅ setup-falco completado (11 reglas — DAY 135 +apt-sources-integrity)"