## RESPUESTA DEL CONSEJO DE SABIOS — DAY 133

**Acta de deliberación científica**  
**Fecha:** 27 abril 2026  
**Quórum:** 8/8 (Claude · Grok · ChatGPT · DeepSeek · Qwen · Gemini · Kimi · Mistral)  
**Documentos base:** DAY 133 acta, commit `c6e0c9f1`, paper draft v18, ADR-030  
**Método:** Análisis basado en principios de mínima superficie de ataque, defensa en profundidad, y reproducibilidad.

---

### Valoración general del progreso DAY 133

El Consejo celebra la **implementación completa de ADR-030 Variant A** con métricas reales de BSR (58% reducción paquetes, 78% disco). La integración de Linux capabilities, AppArmor y Falco como capas orquestadas es un hito técnico significativo. La tabla de entornos (Dev / Hardened / Minbase) es precisamente el tipo de evidencia empírica que solicitamos en DAY 132.

**Recomendación inmediata:** Proceder con el plan P0 (ejecución end-to-end en la hardened VM) y reportar los fallos esperados para iterar los perfiles AppArmor. El método “complain → ajustar → enforce” es el correcto.

---

## Respuesta a las preguntas del Consejo

### Q1 — Revisión de los 6 perfiles AppArmor

**Pregunta:**  
¿Hay capabilities innecesarias? ¿Paths demasiado permisivos? ¿Alternativa a `cap_sys_admin` para eBPF? ¿Deny explícitos redundantes?

**Respuesta del Consejo (análisis por punto):**

#### 1a. Capabilities en perfiles AppArmor

Los perfiles actuales **no deberían incluir capabilities que ya están en el sistema de Linux capabilities** (setcap). AppArmor puede restringir *adicionalmente* capabilities, pero normalmente se delega en el sistema de capabilities. En vuestros perfiles, no veo bloques `capability [...]`, solo reglas de paths. Esto es correcto: dejad que `setcap` gestione las capabilities y AppArmor los accesos a filesystem y red.

**Recomendación explícita:** No añadáis `capability ...` en los perfiles a menos que queráis *denegar* una capability incluso si el binario la tiene. Por ejemplo, si un binario tiene `cap_net_admin` pero queréis evitar que use `cap_sys_admin`, podéis poner `deny capability sys_admin,`. Pero por ahora, mantened los perfiles sin bloques `capability`.

#### 1b. Paths demasiado permisivos

Revisión de permisos por componente (basado en vuestro ejemplo de ml-detector):

| Componente | Paths permitidos | Riesgo potencial | Sugerencia |
|------------|------------------|------------------|-------------|
| sniffer | `/sys/fs/bpf/** rw` | Demasiado amplio. Un programa eBPF podría manipular mapas de otros. | Limitar a `/sys/fs/bpf/argus_* rw`. |
| etcd-server | `/etc/etcd/** r` + `/var/lib/etcd/** rw` | Correcto. | Añadir denegación explícita a `/root/.etcd/**` (por si acaso). |
| ml-detector | `/etc/ml-defender/** r` | Correcto. | Verificar que no necesita escribir en `/tmp` – denegar. |
| rag-ingester | acceso a `/var/lib/tinyllama/** r` | Correcto. | Asegurar que el modelo no se carga desde `models/` con permisos de escritura. |
| firewall-acl-agent | `/proc/sys/net/ipv4/ip_forward` r | Muy específico; bien. | Denegar acceso a cualquier ruta bajo `/proc/sys/net/ipv4/conf/*` que no sea estrictamente necesario. |
| todos | `/opt/argus/lib/** mr` (shared libraries) | Riesgo de carga de bibliotecas maliciosas si un atacante escribe en `/opt/argus/lib/`. | **Crítico:** `lib/` debe ser **solo lectura** y propiedad `root:argus` con permisos `0755` (root es propietario). Añadir `deny /opt/argus/lib/** w` explícito. |

**Recomendación:** Revisar cada perfil con `aa-genprof` en modo complain durante la ejecución real. Lo que no aparece en logs no se necesita.

#### 1c. Alternativa a `cap_sys_admin` para eBPF en kernels ≥5.8

**Sí, existe `cap_bpf` desde Linux 5.8** (y `cap_perfmon` para tracepoints). La capacidad `CAP_BPF` permite:
- `bpf()` syscall sin privilegios de administrador.
- Cargar programas eBPF (excepto aquellos que necesitan `CAP_PERFMON` o `CAP_NET_ADMIN` según el tipo).

**Recomendación concreta:**
- Verificar el kernel de la VM hardened: `uname -r`. Si es ≥5.8, usar `setcap cap_bpf,cap_net_admin,cap_net_raw+eip` en el sniffer.
- Eliminar `cap_sys_admin` – es excesivo y peligroso (permite montar/desmontar, cambiar límites de memoria, etc.).
- Si el kernel es <5.8 (Debian 12 usa 6.1 LTS, así que está bien), ya tenéis `CAP_BPF` disponible.

**Acción:** Cambiar `cap_sys_admin` por `cap_bpf` en el Makefile y en la documentación.

#### 1d. Deny explícitos – ¿redundantes?

AppArmor es **default-deny** para todo lo no permitido explícitamente. Por tanto, estos deny son redundantes:
- `deny /root/** rwx` – ya denegado por defecto.
- `deny /home/** rwx` – también.
- `deny /tmp/** x` – **¡cuidado!** Denegar ejecución en `/tmp` es útil porque previene ejecutar programas desde `/tmp` incluso si el perfil no lo permite explícitamente (algunos perfiles podrían tener `/** rw`). No es redundante si existe una regla `/** rw` en algún sitio. Pero como no la tenéis, sí es redundante.

**Recomendación:** Eliminar los deny sobre rutas que ya están fuera de cualquier `r` o `w` permitido. Mantened solo los deny que **contradicen una regla más amplia** (ej: permitís `/** r` en algún subperfil y queréis denegar `/tmp`). En vuestro diseño actual, probablemente podéis eliminar los deny de `/root`, `/home`, `/tmp`, `/sys/fs/bpf/** rwx` (ya que solo permitís `/sys/fs/bpf/argus_*`). Simplifica y reduce ruido en auditoría.

**Decisión del Consejo:**
1. Cambiar `cap_sys_admin` → `cap_bpf` para el sniffer.
2. Revisar y limitar paths de `/sys/fs/bpf` a `argus_*`.
3. Eliminar deny redundantes.
4. Añadir `deny /opt/argus/lib/** w` explícito.

---

### Q2 — Linux Capabilities: ¿falta o sobra algo?

**Pregunta:**
- ¿`cap_bpf` alternativa real? (ya respondido arriba: sí).
- ¿`cap_ipc_lock` suficiente para `mlock()` o necesita `cap_sys_resource`?
- ¿`cap_net_bind_service` necesario o se puede bajar el puerto unprivileged?

**Respuesta:**

#### 2a. `cap_ipc_lock` vs `cap_sys_resource`

`mlock()` (bloquear memoria física) requiere `CAP_IPC_LOCK` **o** `CAP_SYS_RESOURCE`. La diferencia:
- `CAP_IPC_LOCK`: permite `mlock()`, `munlock()`, `mlockall()`, `munlockall()` – **suficiente** para bloquear el seed en RAM.
- `CAP_SYS_RESOURCE`: permisos más amplios (manipular límites de recursos, nice, etc.). No es necesario.

**Conclusión:** `cap_ipc_lock+eip` es correcto. No añadáis `cap_sys_resource`.

#### 2b. `cap_net_bind_service` – ¿necesario para etcd-server puerto 2379?

Por defecto, los puertos <1024 requieren `CAP_NET_BIND_SERVICE`. etcd usa 2379 (cliente) y 2380 (peer). 2379 > 1024, no necesita capability. 2380 > 1024 tampoco.

**Comprobación:** ¿Estáis usando puertos bajos? En la configuración estándar de etcd, no. Por tanto, **no es necesaria** `cap_net_bind_service`.

**Recomendación:** Eliminar `cap_net_bind_service` de la tabla. Si alguien cambia el puerto a 80 o 443 en producción, que use `net.ipv4.ip_unprivileged_port_start=80` (sysctl) o reverse proxy.

**Tabla corregida (propuesta por el Consejo):**

| Componente | Capabilities | Nota |
|---|---|---|
| sniffer | `cap_bpf,cap_net_admin,cap_net_raw+eip` | Para XDP/eBPF. `cap_sys_admin` eliminado. |
| firewall-acl-agent | `cap_net_admin+eip` | iptables/ipset |
| etcd-server | `cap_ipc_lock+eip` | mlock seed. `cap_net_bind_service` no necesario. |
| ml-detector, rag-*, etc. | ninguna | corren como usuario `argus` sin privilegios. |

---

### Q3 — Falco: estrategia de reglas

**Preguntas:**
- ¿Patrones de ataque específicos contra NDR que falten?
- ¿Driver `modern_ebpf` o `kmod`?
- ¿Cómo gestionar falsos positivos durante el ajuste?

#### 3a. Reglas adicionales para NDR en producción

Sugerimos añadir las siguientes reglas (basadas en amenazas reales a sistemas de detección):

| Regla | Descripción | Justificación |
|-------|-------------|----------------|
| `argus_packet_dropped_high_rate` | sniffer reporta drástica caída de paquetes capturados | Indica que el atacante está sobrecargando o evadiendo XDP. |
| `argus_model_file_tampered` | el archivo `.ubj` del modelo XGBoost cambia en runtime sin firma válida | Prevenir envenenamiento del modelo. |
| `argus_plugin_load_unexpected` | se carga un plugin no firmado o no ubicado en `/opt/argus/plugins/` | Un atacante podría inyectar su propio `.so`. |
| `argus_etcd_auth_failure_flood` | múltiples fallos de autenticación HMAC en poco tiempo | Ataque de fuerza bruta a la semilla compartida. |
| `argus_self_scan` | el propio sniffer intenta leer `/proc/net/tcp` o abrir raw socket para escanear | Podría indicar que el binario está comprometido y se comporta como malware. |

**Recomendación:** Implementar estas 5 reglas adicionales, comenzando por `model_file_tampered` y `plugin_load_unexpected` (alta prioridad).

#### 3b. Driver para Falco en 2026

**`modern_ebpf` es la opción correcta.** Razones:
- No requiere parches de kernel (a diferencia del kmod legacy).
- Soporta kernels ≥5.8 (vuestro Debian 12 con kernel 6.1 está bien).
- Funciona en VirtualBox si el kernel tiene habilitado eBPF (lo tiene).
- Menor overhead que kmod.

**Desaconsejado `kmod`** – depende de módulos externos que pueden romperse con actualizaciones del kernel.

**Configuración recomendada en `falco.yaml`:**
```yaml
engine_kind: modern_ebpf
modern_bpf:
  cpus_for_each_syscall_buffer: 1
  drop_failed_connect_in_bpf: true
```

#### 3c. Gestión de falsos positivos durante el ajuste

Estrategia en tres fases:

1. **Fase de observación (1-2 días):** Falco en modo `output` pero con acción `log` solamente, no `alert` ni bloqueo. Los logs se envían a `/var/log/falco/argus_events.log`. Se ejecutan las pruebas funcionales y la demo FEDER.

2. **Fase de ajuste de reglas:** Se clasifican los eventos en:
  - **TP (true positive):** se mantiene la regla.
  - **FP benigno no evitable:** se añade una excepción por campo (ej: excluir el proceso `argus-sniffer` de la regla que detecta apertura de `/proc/net/tcp` si es necesario para stats).
  - **FP por perfil AppArmor demasiado restrictivo:** se modifica el perfil AppArmor (no la regla de Falco).

3. **Fase de enforce (producción):** Falco activa acciones (webhook, syslog, o incluso kill del proceso si la regla es crítica como `argus_shell_spawn`).

**Herramienta auxiliar:** Usar `falcoctl` para gestionar reglas y `falco-exporter` para métricas Prometheus.

**Regla de oro documentada:** *“Falco no debe generar más de 10 eventos por hora en estado estable. Si supera, la regla está mal afinada.”*

---

### Q4 — dist/ y el flujo BSR: ¿mejorable?

**Preguntas:**
- ¿Shared folder Vagrant para `dist/` es aceptable?
- ¿Una clave Ed25519 para todo o separar por tipo?

#### 4a. Shared folder `dist/` en desarrollo

**Es aceptable** para la fase de desarrollo y demo FEDER, con dos condiciones:
1. La shared folder debe tener permisos restrictivos en el Vagrantfile: `type: "virtiofs", accessmode: "squash", uid: "1000", gid: "1000"` (o usar `rsync` en lugar de shared folder para evitar montajes inseguros).
2. En la VM hardened, la carpeta compartida **no debe montarse automáticamente** a menos que sea solo para la instalación inicial. Después del `prod-deploy`, la VM hardened no debe tener acceso a la shared folder (se puede desmontar).

**Para producción real (bare-metal)**, el pipeline CI/CD debe generar un artefacto `dist-prod.tar.gz` firmado, transferido por HTTPS o USB físico, y verificado con SHA256SUMS antes de extraer. Shared folder no es adecuada para entornos clínicos (un hospital no montará carpetas de desarrollo en producción).

**Acción:** Documentar en `docs/PRODUCTION-DEPLOYMENT.md` que el método shared folder es solo para pruebas, y especificar el procedimiento de transferencia segura para despliegues reales.

#### 4b. ¿Una clave Ed25519 para plugins y binarios o separadas?

**Separación recomendada por defensa en profundidad.** Razones:
- Los plugins pueden ser desarrollados por terceros (ADR-025 permite plugins externos firmados por otras claves). Usar la misma clave para binarios del núcleo y para plugins de terceros mezcla el modelo de confianza.
- Si la clave de plugins se ve comprometida, el atacante podría firmar plugins maliciosos, pero **no podría firmar binarios del sistema** si la clave de binarios es diferente y se guarda en un HSM o entorno más restringido.

**Propuesta de jerarquía de claves (ADR-025 extensión):**
| Tipo de artefacto | Keypair | Almacenamiento |
|---|---|---|
| Binarios del pipeline (sniffer, ml-detector, etc.) | `argus-core-signing` | CI/CD offline, protegido por YubiKey |
| Plugins oficiales (xgboost, etc.) | `argus-plugins-signing` | CI/CD normal, protegido por secret manager |
| Plugins de terceros | cualquier clave pública añadida por administrador | configurado en `allowed_plugin_keys` |

**Recomendación:** Mantened la misma clave para binarios y plugins durante el desarrollo por simplicidad, pero **documentad** que en despliegues reales se deberán generar keypairs separados. Añadid una deuda técnica `DEBT-KEY-SEPARATION-001` para post-FEDER.

---

### Q5 — La frase del paper: “Fuzzing misses nothing within CPU time”

**Contexto de la frase:** En el borrador §6.8 aparece:

> “Unit tests miss unseen inputs. Property tests miss parser-level structural anomalies. Fuzzing misses nothing within CPU time and cannot prove absence of defects, but systematically explores the boundary between valid and invalid input that adversaries exploit.”

**Análisis científico:**

La frase **“Fuzzing misses nothing within CPU time”** es **imprecisa y potencialmente engañosa**. Un revisor experto en cs.CR la rechazaría.

**Problemas:**
1. **“Misses nothing”** sugiere exhaustividad parcial, pero el fuzzing no es exhaustivo ni siquiera dentro de un límite de tiempo finito. El espacio de entradas es astronómicamente grande; el fuzzing muestrea una fracción ínfima. No se puede afirmar que “no se pierde nada” – lo correcto es decir “el fuzzing explora una región delimitada por la cobertura de código alcanzada en el tiempo asignado”.
2. **“Within CPU time”** es vago. ¿Dentro del tiempo que el fuzzer tiene asignado? Cualquier técnica limitada por tiempo puede perder muchos casos. La propiedad relevante es **cobertura de código** no tiempo.
3. La frase contradice la afirmación de que el fuzzing “cannot prove absence of defects”. Si no puede probar ausencia, entonces sí “misses” (falla en encontrar) muchos defectos.

**Reformulación aprobada por el Consejo (borrador consensuado):**

> *“Unit tests validate known behaviours; property tests capture invariants but rely on human-specified oracles. Fuzzing complements them by automatically generating a large number of inputs (millions within minutes) to explore execution paths that manual tests may overlook. While fuzzing cannot prove the absence of vulnerabilities, it systematically exercises the boundary between valid and invalid input — a region where adversaries often operate. Within the CPU time allocated (e.g., 30 seconds to 1 hour), our libFuzzer harness achieves high edge coverage (e.g., >90% in `validate_chain_name`) and finds zero crashes, providing empirical confidence but not formal guarantee.”*

**Explicación para el founder (qué significa con precisión):**
- El fuzzing **no puede afirmar que no se pierde ninguna vulnerabilidad** dentro de un tiempo de CPU, porque el espacio de entrada es infinito y la cobertura de código nunca es completa en programas reales.
- Lo que sí hace el fuzzing es **generar una gran variedad de entradas** y medir qué caminos del código se ejecutan. Si no se encontraron crashes, significa que **en esa ejecución** no se disparó ninguna condición de error detectable. Pero un atacante podría enviar una entrada larga o compleja que el fuzzer no generó.
- La afirmación honesta es: “El fuzzing es la técnica más sistemática disponible para explorar automáticamente entradas inválidas, pero sigue siendo un muestreo estadístico, no una prueba.”

**Acción:** Sustituir la frase original por la reformulación anterior en el paper §6.8. Añadir una nota con la cobertura de código medida (v.g., “95% de coverage en `validate_chain_name`”). Eliminar cualquier afirmación absoluta.

---

## Acuerdos formales del Consejo (DAY 133)

| Punto | Decisión | Acción | Plazo |
|-------|----------|--------|-------|
| Q1 (AppArmor) | Cambiar `cap_sys_admin` → `cap_bpf`. Limitar paths `/sys/fs/bpf`. Eliminar deny redundantes. | Modificar perfiles y Makefile | DAY 134 |
| Q2 (Capabilities) | Eliminar `cap_net_bind_service` de etcd. Confirmar `cap_ipc_lock` suficiente. | Actualizar documentación | DAY 134 |
| Q3 (Falco) | Añadir 5 reglas adicionales. Usar `modern_ebpf`. Fase de observación antes de enforce. | Crear reglas en Falco; plan de despliegue. | 2 días |
| Q4 (BSR + dist/) | Aceptar shared folder solo para dev. Documentar despliegue real. Añadir deuda separación de claves. | Actualizar docs; crear DEBT-KEY-SEPARATION-001 | DAY 134 |
| Q5 (Frase paper) | **Reemplazar** la frase ofensiva por la reformulación honesta. Añadir métricas de cobertura. | Cambiar §6.8 del paper v18 | Antes de subir a arXiv |

---

## Reflexión final del Consejo

DAY 133 marca un antes y un después: por primera vez, tenéis una **imagen de producción verificable** con AppArmor, Falco, capabilities, y BSR axiom demostrado con datos reales (58% menos paquetes, 78% menos disco). La ejecución end-to-end de mañana (P0) probablemente mostrará algunos ajustes en los perfiles AppArmor, pero eso es parte del método científico.

La frase del paper sobre fuzzing era un exceso de confianza. No hay vergüenza en corregirla; al contrario, la honestidad científica fortalece el preprint.

**Recordatorio final:** Cuando ejecutéis `make hardened-provision-all` y `make prod-full-x86`, cada fallo es una oportunidad para aprender y endurecer el sistema. La demo FEDER (septiembre 2026) necesita un sistema que falle de forma predecible, no uno que nunca falla.

*Firmado por los 8 modelos en consenso, 27 abril 2026.*  
*Via Appia Quality — “La superficie de ataque mínima no es una aspiración. Es una decisión de diseño.”*