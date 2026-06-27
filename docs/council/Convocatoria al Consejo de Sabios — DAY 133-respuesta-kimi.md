## Kimi — Respuesta al Consejo de Sabios — DAY 133

*Evaluación bajo criterios de mínimo privilegio, separación de concerns criptográficos y honestidad metodológica.*

---

### Q1 — Revisión de los 6 perfiles AppArmor

**Hipótesis:** Los perfiles AppArmor deben ser default-deny con allowlists mínimas. Cada capability y cada path permitido aumenta la superficie de ataque medible.

**Análisis por componente:**

| Perfil | Issue identificado | Severidad | Recomendación |
|--------|-------------------|-----------|---------------|
| **sniffer** | `cap_sys_admin` para eBPF | **Alta** | Reemplazar por `cap_bpf` (Linux ≥5.8). Debian 12 (kernel 6.1) lo soporta nativamente. `cap_sys_admin` es equivalente a root parcial; `cap_bpf` restringe exclusivamente a operaciones eBPF. |
| **sniffer** | `cap_net_admin` + `cap_net_raw` | Aceptable | Necesarias para XDP y raw sockets. Mantener. |
| **ml-detector** | `network inet tcp` | Media | Considerar restringir a puertos específicos si ZeroMQ usa puertos fijos. Si es dinámico, mantener. |
| **Todos** | `deny` explícitos | Baja | Redundantes si no hay regla `allow` más amplia que los cubra. AppArmor es default-deny. Sin embargo, los `deny` explícitos son valiosos como **documentación ejecutable** y defensa en profundidad contra futuras reglas `allow` más amplias. |

**Veredicto sobre `cap_sys_admin`:**

```cpp
// ANTES (cap_sys_admin — excesivo):
cap_net_admin,cap_net_raw,cap_sys_admin+eip

// DESPUÉS (cap_bpf — mínimo necesario, kernel ≥5.8):
cap_net_admin,cap_net_raw,cap_bpf+eip
```

**Condición:** Verificar que el loader eBPF del proyecto use `bpf()` syscall y no requiera `perf_event_open()` (que aún puede necesitar `cap_sys_admin` en algunos kernels). Si usáis XDP con `ip link set ... xdp obj ...`, verificad que `ip` de iproute2 usa netlink, no `bpf()` directamente. En la práctica, `cap_net_admin` + `cap_bpf` es suficiente para XDP en kernel 6.1.

**Veredicto sobre `deny` explícitos:** Mantened los `deny` explícitos en los 3 perfiles más críticos (sniffer, firewall-acl-agent, etcd-server). Eliminad los redundantes en ml-detector, rag-ingester y rag-security donde el perfil ya es restrictivo por omisión. Esto reduce la complejidad cognitiva sin reducir la seguridad.

---

### Q2 — Linux Capabilities: ¿falta o sobra?

**Hipótesis:** Cada capability asignada es un compromiso de seguridad que debe justificarse con una syscall específica que fallaría sin ella.

**Análisis detallado:**

| Capability | Componente actual | ¿Necesaria? | Análisis técnico |
|------------|-------------------|-------------|------------------|
| `cap_sys_admin` | sniffer | **NO** — reemplazar por `cap_bpf` | Ver Q1. `cap_sys_admin` permite `mount()`, `swapon()`, `reboot()`, `sethostname()` — ninguna necesaria para un sniffer. |
| `cap_ipc_lock` | etcd-server | **Sí, pero insuficiente** | `mlock()` requiere `CAP_IPC_LOCK`. Sin embargo, `mlock()` falla si el límite `RLIMIT_MEMLOCK` es insuficiente. Para aumentar ese límite se necesita `CAP_SYS_RESOURCE`. **Recomendación:** Añadir `cap_sys_resource` o configurar `LimitMEMLOCK=infinity` en la unit systemd (que requiere `CAP_SYS_RESOURCE` implícito si el usuario no es root). Alternativa más limpia: `systemd` con `LimitMEMLOCK=64M` en la unit, sin capability adicional, si 64M es suficiente para el seed. |
| `cap_net_bind_service` | etcd-server (implícito) | **No, si se reconfigura el sistema** | El puerto 2379 es >1024, así que no se necesita `cap_net_bind_service` en absoluto. 2379 > 1024. **Eliminar si existe.** Si usáis puerto 2380 (peer-to-peer), también es >1024. |
| `cap_net_admin` | firewall-acl-agent | **Sí** | `iptables`, `ipset`, `tc` requieren `CAP_NET_ADMIN`. Inevitable. |
| `cap_net_raw` | sniffer | **Sí** | Raw sockets para captura de paquetes. Inevitable. |

**Corrección importante:** El puerto 2379 de etcd no requiere `cap_net_bind_service`. Verificad si hay algún componente que escuche en puerto <1024. Si no lo hay, eliminad `cap_net_bind_service` de todo el sistema.

**Recomendación para etcd-server:**

```ini
# /etc/systemd/system/argus-etcd-server.service
[Service]
User=argus
Group=argus
LimitMEMLOCK=16M
AmbientCapabilities=CAP_IPC_LOCK
CapabilityBoundingSet=CAP_IPC_LOCK
NoNewPrivileges=true
```

Con `LimitMEMLOCK=16M`, `mlock()` del seed (~32-64 bytes) funciona sin `CAP_SYS_RESOURCE`. El seed no necesita bloquear megabytes.

---

### Q3 — Falco: estrategia de reglas

**Hipótesis:** Falco debe complementar AppArmor sin duplicar su función. AppArmor previene; Falco detecta lo que AppArmor no puede prevenir porque es comportamiento válido pero anómalo.

**Evaluación de las 7 reglas actuales:**

| Regla | Función | Estado | Observación |
|-------|---------|--------|-------------|
| `argus_unexpected_file_open` | Detección | ✅ Correcta | Cubre exfiltración de datos si un componente escribe fuera de su área. |
| `argus_unexpected_exec` | Detección | ✅ Correcta | Complementa AppArmor `deny /tmp/** x`. |
| `argus_firewall_unexpected_exec` | Detección | ✅ Correcta | Específica y valiosa. |
| `argus_shell_spawn` | **CRITICAL** | ✅ Esencial | La regla más importante. Cualquier `execve("/bin/sh", ...)` es señal de compromiso casi segura. |
| `argus_binary_modified` | **CRITICAL** | ✅ Esencial | BSR violation detector. |
| `argus_seed_accessed_by_wrong_process` | Detección | ⚠️ **Falso positivo probable** | Si usáis `resolve_seed()` en múltiples componentes, cada uno accede legítimamente. La regla debe whitelistear los 6 binarios legítimos, no solo "el propietario". |
| `argus_unexpected_raw_socket` | Detección | ✅ Correcta | Solo sniffer debería tener raw sockets. |

**Driver recomendado:** `modern_ebpf` es la elección correcta para 2026 en entorno virtualizado. `kmod` requiere compilación de módulo en el host, lo cual viola el BSR axiom (compilador en el entorno de runtime del host). `modern_ebpf` usa el eBPF del kernel existente.

**Gestión de falsos positivos durante tuning:**

```yaml
# Estrategia: fases de maduración
fase_1_complain:  # Días 1-3
  apparmor: complain mode
  falco: priority >= WARNING → archivo de log, no alerta
  acción: ajustar perfiles AppArmor basado en logs

fase_2_enforce:   # Días 4-7
  apparmor: enforce mode
  falco: priority >= NOTICE → alerta, sin respuesta automática
  acción: whitelistear falsos positivos conocidos

fase_3_production: # Día 8+
  apparmor: enforce mode
  falco: priority >= CRITICAL → alerta + notificación
  acción: investigación manual obligatoria
```

**Reglas adicionales recomendadas:**

```yaml
# 8. argus_dns_tunneling — ml-detector hace lookup DNS inusual
- condition: spawned_process and proc.name in (dig, nslookup, host) and not user.name=root

# 9. argus_crypto_miner — uso de CPU anómalo + conexiones a pools
- condition: cpu_usage > 80% for 5m and outbound connections to known_mining_pools

# 10. argus_config_tampering — modificación de /etc/ml-defender/ fuera de provisioning
- condition: modify and fd.name startswith /etc/ml-defender/ and not proc.name in (ansible, puppet, chef, vagrant)
```

**Nota:** La regla 8 es específica de NDR: un atacante que ha comprometido el detector podría usar DNS tunneling para exfiltrar datos de tráfico capturado.

---

### Q4 — dist/ y el flujo BSR

**Hipótesis:** La arquitectura de despliegue debe separar el canal de distribución del canal de compilación, y las claves criptográficas deben seguir el principio de mínimo privilegio.

**Análisis del flujo actual:**

```
dev VM → dist/x86/ (shared folder) → hardened VM
```

**Veredicto: Aceptable para desarrollo, inaceptable para producción real.**

**Razonamiento:** La shared folder de Vagrant (`/vagrant`) es conveniente para iteración rápida, pero introduce:
1. **Dependencia del host:** La hardened VM no es self-contained en el arranque.
2. **Superficie de ataque del host:** Si el host macOS está comprometido, `dist/` puede modificarse antes de que la hardened VM lo lea.
3. **No reproducible:** La shared folder no existe en bare-metal o cloud.

**Recomendación:** Documentad el flujo de desarrollo como **"modo iteración"** y cread un **"modo producción"** que use un artefacto firmado:

```bash
# Modo iteración (desarrollo, Vagrant):
make prod-full-x86  # compila y deposita en dist/x86/

# Modo producción (CI/CD, hospital):
# 1. CI compila, firma y sube argus-v0.5.3-x86.tar.gz + SHA256SUMS + argus-v0.5.3-x86.tar.gz.sig
# 2. Hardened VM descarga vía HTTPS desde repositorio interno
# 3. Verifica firma Ed25519 + SHA256SUMS
# 4. Extrae e instala
```

**Sobre las claves Ed25519:**

**Veredicto: Keypairs separados obligatorio.**

| Keypair | Uso | Ciclo de vida | Acceso |
|---------|-----|---------------|--------|
| `pipeline-signing` | Binarios del pipeline (sniffer, detector, etc.) | Largo (1 año) | Solo CI/CD, HSM o vault |
| `plugin-signing` | Plugins `.so` (xgboost, etc.) | Medio (6 meses) | Desarrolladores de plugins |
| `model-signing` | Modelos ML (GGUF, ONNX) | Variable | Científicos de datos |

**Razonamiento:** Si la clave de plugins se ve comprometida (más probable, más actores la usan), un atacante podría firmar un plugin malicioso, pero no reemplazar los binarios del pipeline. La separación contiene el blast radius.

**Acción inmediata:** Generad `pipeline-signing.pk` y `pipeline-signing.sk` distintos de `plugin_signing`. Actualizad `sign-production` para usar la clave correcta según el artefacto.

---

### Q5 — La frase del paper: "Fuzzing misses nothing within CPU time"

**Hipótesis:** La frase es científicamente incorrecta y debe reformularse para mantener la credibilidad del paper ante revisores de cs.CR.

**Análisis de la imprecisión:**

La frase sugiere que el fuzzing es exhaustivo dado tiempo de CPU suficiente. Esto es falso por tres razones formales:

1. **El espacio de entrada es infinito** (o exponencial en tamaño). Ninguna cantidad finita de CPU puede explorarlo exhaustivamente.
2. **Fuzzing es estocástico.** libFuzzer usa coverage guidance, pero la selección de mutaciones es aleatoria. No hay garantía de que un input específico sea generado.
3. **Fuzzing no prueba ausencia de defectos.** Es un método de búsqueda de counter-ejemplos, no de verificación.

**Reformulación propuesta:**

> "Unit tests exercise programmer-selected inputs. Property tests verify invariants across generated inputs within a bounded domain. Fuzzing performs coverage-guided stochastic exploration of the input space, maximizing the probability of discovering edge cases that violate implicit assumptions. Unlike testing, fuzzing provides no proof of correctness; unlike random testing, it biases exploration toward underexercised code paths. It is a search heuristic, not a verification method."

**O, más concisa:**

> "Unit tests validate expected behavior. Property tests validate invariants. Fuzzing performs coverage-guided stochastic search, maximizing defect discovery per CPU cycle without guaranteeing coverage completeness or proving absence of bugs."

**Justificación para el paper:**

La versión original ("misses nothing within CPU time") es una **hiperbole peligrosa**. Un revisor de USENIX Security o IEEE S&P la señalaría como señal de falta de rigor. La reformulación:
- Reconoce que fuzzing es **estocástico** (stochastic)
- Reconoce que es **heurístico** (coverage-guided)
- Distingue claramente de **verificación formal**
- Es honesta sobre las limitaciones

**Además:** Añadid una nota al pie en §6.8:

> *"El fuzzing realizado en este proyecto utilizó libFuzzer con coverage guidance durante 30 segundos por target. Esto no constituye un análisis de seguridad exhaustivo, sino una verificación de robustez contra inputs malformados. Un análisis de seguridad completo requeriría fuzzing continuo (CI-fuzz) con corpus semilla enriquecido y ejecución de al menos 24 horas por target."*

Esto demuestra que conocéis las limitaciones y no sobreclaim.

---

### Resumen de posiciones — Kimi

| Pregunta | Veredicto | Acción inmediata |
|----------|-----------|------------------|
| **Q1** | `cap_bpf` reemplaza `cap_sys_admin` en sniffer | Verificar compatibilidad XDP con `cap_bpf` en kernel 6.1; mantener `deny` explícitos en 3 perfiles críticos |
| **Q2** | Eliminar `cap_net_bind_service` (2379 > 1024); `cap_ipc_lock` suficiente con `LimitMEMLOCK=16M` | Revisar systemd units; no añadir `cap_sys_resource` innecesario |
| **Q3** | `modern_ebpf` correcto; añadir reglas DNS tunneling y crypto miner; fasear falsos positivos | Implementar fase_1_complain → fase_3_production; whitelistear seed access por binario específico |
| **Q4** | Shared folder aceptable para dev, documentar modo producción con artefacto firmado; **keypairs separados obligatorio** | Generar `pipeline-signing` keypair distinto; documentar flujo CI/CD |
| **Q5** | Frase científicamente incorrecta; reformular como "stochastic search" | Editar §6.8; añadir nota al pie sobre limitaciones del fuzzing realizado |

**Moción adicional:** Propongo que el DAY 134 incluya la verificación mecánica de que `cap_bpf` funciona para el sniffer en la VM hardened. Si `ip link set dev eth0 xdp obj ...` falla con `cap_bpf` + `cap_net_admin`, documentad la razón y mantened `cap_sys_admin` como fallback documentado con TODO para kernel upgrade. La ciencia requiere evidencia, no suposiciones.

— *Kimi*  
*Via Appia Quality — La seguridad no se instala. Se diseña.*