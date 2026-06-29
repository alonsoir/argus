# ADR-019: OS Hardening y Secure Deployment

**Estado:** PROPUESTO — implementación pre-producción (post bare-metal stress test)
**Fecha:** 2026-03-22 (DAY 94)
**Autor:** Alonso Isidoro Román + Claude (Anthropic)
**Revisado por:** Consejo de Sabios — ML Defender (aRGus NDR)
**Componentes afectados:** todos — capa de infraestructura bajo el pipeline
**Depende de:** ADR-013 (provisioning), ADR-017 (plugins), ADR-018 (eBPF plugins)
**Relacionado con:** ADR-001 (deployment stack — Systemd + Ansible)

---

## Contexto

ML Defender protege hospitales, escuelas y pymes — infraestructura crítica donde
un compromiso del sistema de detección es peor que no tener detección: un atacante
que controla el detector puede cegarlo o usarlo para legitimar su actividad.

El pipeline es tan seguro como el SO que lo ejecuta. Los ADR anteriores
(013, 015, 016, 017, 018) establecen autenticación entre componentes, integridad
de programas eBPF, y keypairs por plugin. Todo ese trabajo se invalida si el
atacante puede leer `/etc/ml-defender/` porque el disco no está cifrado, o puede
modificar un binario porque AppArmor no está configurado.

Este ADR define la **capa de infraestructura** sobre la que el pipeline opera.
No sustituye ningún ADR anterior — los complementa como la roca sobre la que
se asienta la calzada romana.

**Estamos lejos de implementar esto** — el target es producción real, que requiere
primero bare-metal stress test, arXiv, y validación empírica. Se documenta ahora
porque las decisiones de provisioning (ADR-013, DAY 95-96) deben ser compatibles
con este entorno desde el principio. Un `provision.sh` que asuma acceso universal
al filesystem será difícil de adaptar a AppArmor después.

---

## Principio rector

> La seguridad no es una feature que se añade al final.
> Es una restricción que se diseña desde el principio y se implementa en capas.
> Cada capa asume que la anterior puede estar comprometida.

---

## Decisión — Stack de hardening

### Capa 1 — Cifrado de disco en reposo (LUKS2)

**Por qué:** Las claves criptográficas del pipeline (`/etc/ml-defender/`)
deben ser inaccesibles si el atacante tiene acceso físico al hardware.
En un hospital, el servidor puede estar en un armario de red sin protección
física adecuada. LUKS2 con Argon2id como KDF protege contra ataques offline.

```bash
# Durante instalación del SO (Ansible playbook)
cryptsetup luksFormat \
    --type luks2 \
    --cipher aes-xts-plain64 \
    --key-size 512 \
    --hash sha512 \
    --pbkdf argon2id \
    /dev/sda2

cryptsetup luksOpen /dev/sda2 ml_defender_root
```

**Particionado mínimo:**
```
/dev/sda1  →  /boot     (no cifrado — necesario para arranque)
/dev/sda2  →  LUKS2  →  LVM
                          ├── /          (sistema raíz)
                          ├── /var       (logs del pipeline)
                          └── /etc       (configuración + claves)
```

**Gestión de la passphrase:** El operador introduce la passphrase en el
arranque. En entornos donde el arranque desatendido es necesario (hospitales
sin personal IT 24/7), se puede usar TPM2 + PCR binding — documentado como
opción avanzada, no requisito inicial.

---

### Capa 2 — SO mínimo

**Distribución recomendada:** Debian 12 Bookworm (stable, LTS)
o Ubuntu 24.04 LTS Server — ambas bien soportadas con AppArmor.

**Principio de mínima superficie de ataque:**
```bash
# Solo lo estrictamente necesario
apt install --no-install-recommends \
    apparmor apparmor-utils \
    libsodium23 liblz4-1 \
    libzmq5 \
    protobuf-compiler \
    openssh-server \
    systemd \
    libbpf1

# Eliminar todo lo innecesario
apt purge --auto-remove \
    avahi-daemon \
    cups \
    bluetooth \
    snapd \
    whoopsie
```

**Sin entorno gráfico. Sin gestor de paquetes de usuario (snap, flatpak).
Sin servicios de red innecesarios.**

---

### Capa 3 — Política de puertos

**Todos los puertos cerrados excepto SSH.**

```bash
# ufw como frontend de iptables/nftables
ufw default deny incoming
ufw default deny outgoing
ufw allow in  22/tcp    # SSH — único canal de gestión
ufw allow out 22/tcp    # SSH saliente (para Ansible)

# Comunicación interna del pipeline — solo localhost
# Los componentes se comunican en loopback, no en interfaces externas
ufw allow in  on lo
ufw allow out on lo

ufw enable
```

**Los puertos ZeroMQ del pipeline (5570-5575) solo escuchan en loopback.**
Un componente externo no puede inyectar mensajes en el bus del pipeline
porque los sockets no están expuestos en interfaces de red externas.

```json
// sniffer.json — ejemplo correcto
"transport": {
    "bind_address": "tcp://127.0.0.1:5570"  // NOT 0.0.0.0
}
```

---

### Capa 4 — AppArmor — un perfil por componente y por plugin

**Por qué AppArmor y no SELinux:** AppArmor usa perfiles por ruta de binario,
más fácil de escribir y mantener para un equipo pequeño. SELinux es más potente
pero su curva de aprendizaje es prohibitiva sin un equipo de seguridad dedicado.
Para los targets de despliegue (hospitales, escuelas), AppArmor es el balance
correcto entre seguridad y mantenibilidad.

**Perfil por componente — ejemplo sniffer:**

```
# /etc/apparmor.d/usr.lib.ml-defender.sniffer
#include <tunables/global>

/usr/lib/ml-defender/sniffer {
    #include <abstractions/base>

    # Binario propio
    /usr/lib/ml-defender/sniffer  mr,

    # Solo sus propias claves — no puede leer las de ml-detector
    /etc/ml-defender/sniffer/**   r,

    # Solo su configuración
    /etc/ml-defender/sniffer/sniffer.json  r,

    # Logs propios
    /vagrant/logs/lab/sniffer.log  w,

    # Plugins autorizados — solo los declarados en su JSON
    /usr/lib/ml-defender/plugins/libplugin_ja4_v1.so  mr,
    /usr/lib/ml-defender/plugins/libplugin_dns_dga_v1.so  mr,

    # eBPF — necesita acceder a interfaces de red
    capability net_admin,
    capability sys_admin,  # solo para carga eBPF/XDP — scoped
    network,

    # ZeroMQ — solo loopback
    network tcp,
    /run/ml-defender/sniffer.sock  rw,

    # Denegar explícitamente
    deny /etc/ml-defender/ml-detector/**  r,
    deny /etc/ml-defender/firewall/**     r,
    deny /proc/*/mem                      r,
    deny /sys/kernel/debug/**             r,
}
```

**Perfil por plugin — ejemplo libplugin_ja4:**

```
# /etc/apparmor.d/usr.lib.ml-defender.plugins.libplugin_ja4_v1.so
/usr/lib/ml-defender/plugins/libplugin_ja4_v1.so {
    #include <abstractions/base>

    # Solo su propio JSON de contrato
    /etc/ml-defender/plugins/ja4_v1.json  r,

    # Sin acceso a red directa — depende del sniffer
    deny network,

    # Sin acceso a otros secrets
    deny /etc/ml-defender/**  r,
}
```

**Un plugin no puede leer las claves de otro plugin ni del componente host.**
Si un plugin está comprometido, AppArmor limita el blast radius al propio plugin.

---

### Capa 5 — Kernel hardening (sysctl)

```bash
# /etc/sysctl.d/99-ml-defender.conf

# Deshabilitar IP forwarding (el pipeline no es un router)
net.ipv4.ip_forward = 0
net.ipv6.conf.all.forwarding = 0

# Protección contra SYN flood (ironía proteger el detector de SYN floods)
net.ipv4.tcp_syncookies = 1

# Deshabilitar IPv6 si no se usa
net.ipv6.conf.all.disable_ipv6 = 1

# Deshabilitar ICMP redirect
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Protección contra martian packets
net.ipv4.conf.all.log_martians = 1

# Deshabilitar core dumps (evitar leak de claves en memoria)
kernel.core_pattern = |/bin/false
fs.suid_dumpable = 0

# Restringir acceso a dmesg (información del kernel)
kernel.dmesg_restrict = 1

# Restringir acceso a kptr (punteros del kernel)
kernel.kptr_restrict = 2

# Protección ptrace — solo procesos padre pueden usar ptrace
kernel.yama.ptrace_scope = 1
```

---

### Capa 6 — SSH hardening

SSH es el único canal de entrada. Debe ser lo más restrictivo posible.

```
# /etc/ssh/sshd_config.d/ml-defender.conf

# Solo autenticación por clave — no passwords
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no

# Solo el usuario de gestión del pipeline
AllowUsers ml-defender-admin

# Timeout agresivo
LoginGraceTime 30
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2

# Deshabilitar features innecesarias
X11Forwarding no
AllowTcpForwarding no
AllowAgentForwarding no
PermitTunnel no

# Solo cifrados modernos
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org
```

---

## Compatibilidad con provision.sh (ADR-013)

`provision.sh` debe diseñarse desde el principio para ser compatible con
este entorno endurecido. Implicaciones concretas:

**1. Paths de claves fijos y conocidos:**
```bash
# provision.sh escribe en paths que AppArmor permite
/etc/ml-defender/{componente}/          # claves de componentes
/etc/ml-defender/plugins/              # claves de plugins userspace
/etc/ml-defender/ebpf-plugins/         # claves de plugins eBPF

# chmod obligatorio tras cada escritura
chmod 0600 /etc/ml-defender/*/          # privadas y HMACs
chmod 0644 /etc/ml-defender/*_public*   # públicas
```

**2. El script se ejecuta como root, una única vez, bajo SSH:**
```bash
ssh ml-defender-admin@hospital-server \
    "sudo /opt/ml-defender/scripts/provision.sh"
```

Tras el provisioning, la cuenta de admin puede desactivarse o limitarse
a operaciones de lectura. Las claves generadas son estables hasta
re-provisioning explícito.

**3. Re-provisioning explícito para actualizaciones:**
Actualizar un plugin (v1 → v2) requiere ejecutar provision.sh de nuevo.
No hay actualizaciones silenciosas — el operador es consciente de cada
cambio en las credenciales del sistema.

---

## Ansible playbook — estructura

```yaml
# playbooks/deploy_ml_defender.yml
---
- name: Deploy ML Defender (aRGus NDR)
  hosts: ml_defender_nodes
  become: yes

  roles:
    - role: base_os_hardening      # sysctl, paquetes mínimos, ufw
    - role: apparmor_profiles      # perfiles por componente y plugin
    - role: ssh_hardening          # sshd_config
    - role: ml_defender_install    # binarios, configs, systemd units
    - role: ml_defender_provision  # provision.sh — keypairs y seeds
    - role: ml_defender_start      # systemctl enable + start

  vars:
    ml_defender_version: "{{ lookup('env', 'ML_DEFENDER_VERSION') }}"
    luks_passphrase:     "{{ vault_luks_passphrase }}"  # Ansible Vault
```

Las contraseñas y passphrases viajan en **Ansible Vault** — nunca en texto
claro en el playbook ni en el inventario.

---

## Modelo de amenaza cubierto

| Amenaza | Mitigación |
|---|---|
| Acceso físico al servidor | LUKS2 — disco inaccesible sin passphrase |
| Malware que lee /etc/ml-defender/ | AppArmor — solo el proceso autorizado puede leer sus propias claves |
| Plugin malicioso que escalona privilegios | AppArmor por plugin — blast radius limitado |
| Inyección de mensajes ZeroMQ desde red | ufw — puertos ZMQ solo en loopback |
| Brute force SSH | PasswordAuthentication no + MaxAuthTries 3 |
| Leak de claves vía core dump | kernel.core_pattern + fs.suid_dumpable = 0 |
| Rootkit via módulo kernel | ADR-016 (kernel-telemetry) + kernel.dmesg_restrict |
| Compromiso de plugin eBPF | ADR-015 + ADR-018 — HMAC + keypairs |
| Actualización silenciosa de binario | AppArmor mr (map+read, no write) en binarios |

---

## Lo que este ADR NO cubre

- **TPM2 + PCR binding** para arranque desatendido — opción avanzada,
  requiere hardware compatible, documentar como extensión futura
- **Secure Boot** — importante pero requiere gestión de claves de arranque,
  fuera del scope inicial
- **Auditoría centralizada (auditd → SIEM)** — relevante en enterprise,
  ENT-7 (OpenTelemetry + Grafana) lo contempla
- **Gestión de certificados X.509** — el pipeline usa ZMQ CURVE y ChaCha20,
  no TLS/X.509; si en el futuro se añade TLS, este ADR se actualiza
- **Multi-nodo HA** — ADR-001 descartó K8s; HA es enterprise territory

---

## Consecuencias

**Positivas:**
- El pipeline es tan seguro como puede ser en el hardware objetivo sin
  infraestructura enterprise (HSM, PKI dedicada, SIEM)
- AppArmor por plugin hace que el blast radius de un plugin comprometido
  sea mínimo — no puede leer claves de otros componentes
- LUKS protege las claves en reposo — un atacante con acceso físico
  no puede extraer el material criptográfico del disco
- Compatible con el target de despliegue (hospitales, escuelas, pymes)
  sin requerir personal de seguridad especializado para operar

**Negativas / limitaciones:**
- LUKS requiere intervención manual en cada arranque (passphrase)
  a menos que se use TPM2 — trade-off aceptado en esta fase
- AppArmor en modo enforce puede romper cosas inesperadamente durante
  el desarrollo — usar aa-complain primero, enforce después de validación
- La superficie de mantenimiento crece: además del pipeline, hay perfiles
  AppArmor que actualizar cuando cambia un binario o se añade un plugin

**Modo de transición:**
```
Desarrollo (ahora):    sin AppArmor enforce, sin LUKS
Pre-producción:        AppArmor en modo complain — observar, no bloquear
Producción:            AppArmor en modo enforce + LUKS
```

---

## Referencias

- ADR-001: Deployment Stack (Systemd + Ansible) — este ADR complementa
- ADR-013: Seed Distribution — provision.sh debe ser compatible
- ADR-015: eBPF Program Integrity — AppArmor complementa la verificación HMAC
- ADR-017: Plugin Interface Hierarchy — perfiles AppArmor por plugin
- ADR-018: eBPF Kernel Plugin Loader — CAP_BPF confinado por AppArmor
- CIS Benchmark Debian/Ubuntu — referencia para hardening de SO
- NIST SP 800-123: Guide to General Server Security

---

*Co-authored-by: Alonso Isidoro Román + Claude (Anthropic)*
*Consejo de Sabios — ML Defender (aRGus NDR)*
*DAY 94 — 22 marzo 2026*