# Convocatoria al Consejo de Sabios — DAY 133
*aRGus NDR — arXiv:2604.04952 — 27 Abril 2026*

---

## Contexto del proyecto

**aRGus NDR** es un sistema open-source de Network Detection and Response en C++20,
diseñado para hospitales, escuelas y municipios que no pueden permitirse ciberseguridad
empresarial. Pipeline de 6 componentes: eBPF/XDP sniffer → ml-detector (RandomForest
embebido + ONNX) → firewall-acl-agent → rag-ingester → rag-security (TinyLlama local).

**Métricas validadas:** F1=0.9985, Recall=1.0000, FPR=0.0002% sobre CTU-13 Neris.
**Paper:** arXiv:2604.04952 — Draft v18 (hoy).
**Metodología:** TDH (Test-Driven Hardening) + Consejo de Sabios (8 modelos).
**Repositorio:** github.com/alonsoir/argus — branch `feature/adr030-variant-a`

---

## Lo que se completó en DAY 133

### 1. REGLA EMECAS — Verde desde las 05:10
```
vagrant destroy -f && vagrant up && make bootstrap && make test-all
→ 6/6 RUNNING | TEST-INTEG-SIGN 7/7 PASSED | ALL TESTS COMPLETE
```
Fallo pre-existente conocido (no regresión): `rag-ingester test_config_parser` 1/8.

### 2. Paper Draft v18 — §6.12 con métricas reales

Mediciones realizadas esta mañana sobre VMs recién provisionadas
(`debian/bookworm64`, misma base box):

| Environment | Packages | Disk used | Compilers present |
|---|---|---|---|
| Dev VM | 719 | 5.9 GB | gcc, g++, clang, cmake, build-essential |
| Hardened VM (ADR-030 Var. A) | 304 | 1.3 GB | **NONE** (`check-prod-no-compiler`: OK) |
| Minbase target† | ~100 | ~0.4 GB | NONE |

†Estimado para `debootstrap --variant=minbase`. El suelo de ~250 paquetes viene de la
base Vagrant (systemd, SSH, Perl, Python, qemu-utils), no del provisioning de aRGus.
Deuda documentada: DEBT-PROD-FS-MINIMIZATION-001.

**Reducción:** 58% en paquetes (719→304), 78% en disco (5.9→1.3 GB).
**BSR verificado mecánicamente:** `check-prod-no-compiler` devuelve OK.

### 3. ADR-030 Variant A — Infraestructura de producción (commit `c6e0c9f1`)

#### 3a. Makefile — nuevos targets de producción
```makefile
# Gestión de la hardened VM
hardened-up / halt / destroy / ssh

# Pipeline BSR completo
prod-build-x86        # compila con -O3 -march=native -DNDEBUG -flto
prod-collect-libs     # recolecta solo librerías runtime (sin -dev)
prod-sign             # Ed25519 sobre cada binario y plugin (reutiliza ADR-025)
prod-checksums        # SHA256SUMS sobre dist/x86/
prod-deploy-x86       # instala en /opt/argus/, aplica setcap, sin SUID
prod-full-x86         # orquesta todo lo anterior

# Provisioning de la hardened VM (se ejecuta una vez)
hardened-provision-all  # filesystem + AppArmor + Falco

# Gates de seguridad (se ejecutan en hardened VM)
check-prod-no-compiler   # BSR: dpkg + PATH, dos capas
check-prod-apparmor      # 6 perfiles en enforce mode
check-prod-capabilities  # setcap correcto en sniffer y firewall
check-prod-permissions   # ownership y modos de /opt/argus/, etc.
check-prod-falco         # servicio activo y reglas cargadas
check-prod-all           # todos los gates anteriores
```

#### 3b. Decisión de diseño — Linux Capabilities (no root completo)

| Componente | Capabilities | Justificación |
|---|---|---|
| sniffer | `cap_net_admin,cap_net_raw,cap_sys_admin+eip` | XDP/eBPF + dual NIC |
| firewall-acl-agent | `cap_net_admin+eip` | iptables/ipset |
| etcd-server | `cap_ipc_lock+eip` | mlock() del seed en RAM |
| ml-detector | ninguna | corre como `argus` no-root real |
| rag-ingester | ninguna | corre como `argus` no-root real |
| rag-security | ninguna | corre como `argus` no-root real |

Usuario del sistema: `argus` — `--system --no-create-home --shell /usr/sbin/nologin`.

#### 3c. AppArmor — 6 perfiles en enforce mode

Un perfil por componente en `security/apparmor/`. Principio: solo lo
absolutamente imprescindible. Ejemplo del más restrictivo (ml-detector):

```
# Puede:
/opt/argus/lib/**            mr   (sus librerías)
/etc/ml-defender/ml-detector/** r (su config)
/var/log/argus/ml-detector/** rw  (sus logs)
network inet tcp                   (ZeroMQ)

# Denegado explícitamente:
deny /root/** rwx
deny /home/** rwx
deny /tmp/**  x
deny /sys/fs/bpf/** rwx
deny /opt/argus/bin/sniffer x     (no puede ejecutar otros componentes)
```

#### 3d. Filesystem layout en la hardened VM

```
/opt/argus/
    bin/     0750 argus:argus  — binarios (0550)
    lib/     0755 root:argus   — runtime libs
    plugins/ 0755 root:argus   — plugins firmados
    models/  0750 argus:argus  — TinyLlama GGUF

/etc/ml-defender/
    [component]/  0750 argus:argus
        seed.bin  0400 argus:argus  ← solo-lectura por su propietario
    plugins/  0750 root:argus
        plugin_signing.pk  0444 root:argus

/var/log/argus/
    [component]/  0750 argus:argus

/tmp    → tmpfs noexec,nosuid,nodev,size=128M
/var/tmp → tmpfs noexec,nosuid,nodev,size=64M
```

#### 3e. Falco — 7 reglas específicas de aRGus

Falco complementa AppArmor: AA **previene** accesos prohibidos;
Falco **detecta** comportamiento anómalo aunque AA lo permita.

Reglas implementadas:
1. `argus_unexpected_file_open` — escritura fuera del patrón esperado
2. `argus_unexpected_exec` — exec inesperado desde componentes
3. `argus_firewall_unexpected_exec` — firewall exec algo distinto de iptables/ipset
4. `argus_shell_spawn` — cualquier componente invoca una shell (CRITICAL)
5. `argus_binary_modified` — binario modificado en runtime (CRITICAL, BSR)
6. `argus_seed_accessed_by_wrong_process` — seed.bin accedido por proceso ajeno
7. `argus_unexpected_raw_socket` — non-sniffer abre raw socket

---

## Plan DAY 134

### P0 — Ejecutar el pipeline real (primera vez end-to-end)

```bash
# 1. Provisionar la hardened VM
make hardened-up
make hardened-provision-all
# → setup-filesystem + setup-apparmor + setup-falco

# 2. Compilar y desplegar
make prod-full-x86
# → prod-build-x86 → prod-collect-libs → prod-sign → prod-checksums → prod-deploy-x86

# 3. Verificar gates de seguridad
make check-prod-all
# → check-prod-no-compiler
# → check-prod-apparmor  (¿los 6 perfiles en enforce?)
# → check-prod-capabilities (¿setcap correcto?)
# → check-prod-permissions (¿ownership y modos?)
# → check-prod-falco (¿servicio activo?)
```

**Expectativa realista:** van a fallar cosas. Los perfiles AppArmor son una primera
aproximación — necesitan ajuste iterativo contra el comportamiento real de los
binarios. El flujo correcto es:

```
Modo complain → observar logs → ajustar → modo enforce → check-prod-all
```

### P1 — Tabla de fuzzing §6.8 (DEBT-PAPER-FUZZING-METRICS-001)

Métricas reales del fuzzing ya ejecutado (DAY 130):

```
| Target              | Runs  | Crashes | Corpus | Time |
| validate_chain_name | 2.4M  | 0       | 67     | 30s  |
| validate_filepath   | ?     | 0       | ?      | ?    |
| safe_exec           | ?     | 0       | ?      | ?    |
```

Recuperar métricas exactas del DAY 130 y añadirlas al paper §6.8.

### P2 — Commit de documentación DAY 133→134

```bash
git add docs/  # prompt continuidad DAY 134
git commit -m "docs: DAY 133 completado — ADR-030 Var A infra + paper v18"
git push origin feature/adr030-variant-a
```

---

## Preguntas al Consejo — DAY 133

### Q1: Revisión de los 6 perfiles AppArmor

Los perfiles están en `security/apparmor/`. Revisar especialmente:

- ¿Hay capabilities que hemos asignado que no son necesarias?
- ¿Hay paths de acceso en los perfiles que son demasiado permisivos?
- El sniffer tiene `cap_sys_admin` para cargar programas eBPF. ¿Existe una
  alternativa más restrictiva en kernels modernos (≥5.8)?
- ¿Los `deny` explícitos son necesarios si AppArmor es default-deny?
  (Sí en algunos casos, no en otros — ¿cuáles son redundantes?)

### Q2: Linux Capabilities — ¿falta algo o sobra algo?

La tabla de capabilities por componente está arriba. Preguntas:

- ¿`cap_sys_admin` para eBPF es inevitable, o en kernel ≥5.8 hay alternativa
  con `cap_bpf` (disponible desde Linux 5.8)?
- ¿`cap_ipc_lock` para etcd-server es suficiente para `mlock()`, o necesita
  también `cap_sys_resource` para el límite de memoria bloqueada?
- ¿`cap_net_bind_service` para etcd-server (puerto 2379) es necesario,
  o con sysctl `net.ipv4.ip_unprivileged_port_start` se puede bajar el umbral?

### Q3: Falco — estrategia de reglas

Las 7 reglas actuales son una primera aproximación. Preguntas:

- ¿Hay patrones de ataque específicos contra pipelines NDR en producción
  que deberíamos cubrir y no hemos cubierto?
- ¿El driver recomendado para Falco en 2026 es `modern_ebpf` o `kmod`?
  (Hemos elegido `modern_ebpf` para compatibilidad con VirtualBox.)
- ¿Cómo gestionar los falsos positivos de Falco durante el periodo de
  ajuste de los perfiles AppArmor, sin deshabilitar las alertas?

### Q4: dist/ y el flujo BSR — ¿algo que mejorar?

El flujo actual es:
```
dev VM compila → dist/x86/ (shared folder) → hardened VM instala
```

Preguntas:
- ¿Es aceptable que `dist/x86/` esté en la shared folder de Vagrant
  durante el desarrollo, sabiendo que en producción será un artefacto
  de un pipeline CICD?
- ¿La firma Ed25519 de los binarios con la misma clave que los plugins
  (ADR-025) es arquitectónicamente correcta, o deberían ser keypairs
  separados (uno para plugins, otro para binarios de pipeline)?

### Q5: La frase del paper — "Fuzzing misses nothing within CPU time"

Esta frase aparece en §6.8 del paper. El founder no la entiende bien.

Por favor, explicad qué significa con precisión científica, por qué es
imprecisa o incorrecta, y proponed una reformulación que sea:
- Científicamente honesta
- Comprensible para un revisor de cs.CR de arXiv
- Consistente con la literatura de fuzzing (libFuzzer, AFL++)

El contexto completo de la frase en el paper:

> "Unit tests miss unseen inputs. Property tests miss parser-level
> structural anomalies. Fuzzing misses nothing within CPU time and
> cannot prove absence of defects, but systematically explores the
> boundary between valid and invalid input that adversaries exploit."

---

## Deudas abiertas post-DAY 133

| ID | Descripción | Prioridad |
|---|---|---|
| DEBT-PAPER-FUZZING-METRICS-001 | Métricas reales §6.8 + reformular frase | 🔴 P0 |
| DEBT-PROD-APT-SOURCES-INTEGRITY-001 | SHA-256 sources.list en boot, fail-closed | 🔴 P1 |
| DEBT-PROD-FS-MINIMIZATION-001 | Imagen minbase x86+ARM (post-FEDER) | ⏳ |
| DEBT-DEBIAN13-UPGRADE-001 | Upgrade path Debian 12→13 | ⏳ post-FEDER |

---

## Reglas permanentes (recordatorio)

- **REGLA EMECAS:** `vagrant destroy -f && vagrant up && make bootstrap && make test-all`
- **main:** sagrado. Solo entra lo que pasa REGLA EMECAS en VM destruida.
- **AppArmor es la primera línea de defensa**, Falco la segunda.
- **JSON es la ley.** No hardcoded values.
- **Fail-closed.** En caso de duda, rechazar.
- **Método científico puro.** Medir y publicar lo que salga. Sin adornar.

---

*DAY 133 — 27 Abril 2026 · commit c6e0c9f1 · feature/adr030-variant-a*
*"Un escudo que aprende de su propia sombra."*
*"La superficie de ataque mínima no es una aspiración. Es una decisión de diseño."*