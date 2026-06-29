El **Consejo de Sabios** ha revisado con detenimiento el estado del proyecto en **DAY 133** (commit `c6e0c9f1`, branch `feature/adr030-variant-a`), las mediciones reales de reducción de superficie de ataque, la infraestructura de producción (ADR-030 Variant A) y las preguntas planteadas. Todas las respuestas se fundamentan en evidencia técnica reproducible, documentación del kernel Linux (capabilities(7), AppArmor, eBPF), prácticas establecidas en sistemas de alta integridad y literatura de testing/fuzzing. Se prioriza la minimización estructural de superficie de ataque, fail-closed y verificabilidad mecánica (REGLA EMECAS + gates `check-prod-all`).

### Q1: Revisión de los 6 perfiles AppArmor

Los perfiles siguen el principio correcto de **default-deny** (AppArmor lista explícitamente lo permitido; todo lo no listado se deniega). Esto es una fortaleza.

**Observaciones y recomendaciones concretas** (basadas en revisión de los perfiles descritos y mejores prácticas):

- **Capabilities asignadas**: Revisar si todas son necesarias tras pruebas en modo complain. El principio de menor privilegio exige eliminar cualquier capability no ejercida por el binario real (verificar con `aa-logprof` o auditoría de logs durante ejecución end-to-end).
- **Paths demasiado permisivos**: En el ejemplo de `ml-detector`, `/opt/argus/lib/** mr` es razonable (solo memoria read/execute). Sin embargo, `/var/log/argus/... rw` debe restringirse a patrones más precisos (ej. `@{LOGDIR}/ml-detector/*.log rw`) para evitar escritura arbitraria. El `network inet tcp` es necesario para ZeroMQ, pero considerar `network inet stream` si no se usa UDP.
- **deny explícitos**: No son estrictamente necesarios (default-deny ya cubre), pero son útiles para **claridad auditiva** y para silenciar logs de denegaciones esperadas (evita ruido en `/var/log/audit/`). Mantener los `deny /root/** rwx`, `deny /home/** rwx`, `deny /tmp/** x` y `deny /sys/fs/bpf/** rwx` como documentación explícita de intención de hardening. Eliminar solo si complican mantenimiento; no son redundantes en práctica para revisión humana.
- **Sniffer y `cap_sys_admin`**: En kernels ≥5.8 (Debian 12/13 usan kernels 6.x en 2026), existe `CAP_BPF` (añadida en 5.8) que permite cargar programas eBPF sin el amplio `CAP_SYS_ADMIN`. Recomendación fuerte: migrar a `cap_bpf,cap_perfmon+ep` (o mínimo `cap_bpf+ep`) donde sea posible. Esto reduce drásticamente la superficie (CAP_SYS_ADMIN permite muchas operaciones de administración). Verificar con `bpftool` y pruebas de carga XDP/eBPF. Si el kernel de la hardened VM lo soporta (recomendado kernel ≥6.1), actualizar la tabla de capabilities y el perfil AppArmor.

**Acción inmediata**: Ejecutar el pipeline en modo complain, analizar logs de denegaciones (`dmesg | grep apparmor` o auditd), ajustar perfiles iterativamente y pasar a enforce solo cuando `check-prod-apparmor` pase sin denegaciones inesperadas.

### Q2: Linux Capabilities — ¿falta algo o sobra algo?

La tabla actual es un buen punto de partida (menor privilegio por componente).

**Análisis específico**:

- **`cap_sys_admin` para sniffer (eBPF/XDP)**: No es inevitable en kernels modernos. Desde Linux 5.8, `CAP_BPF` separa la capacidad de cargar/manipular programas BPF. Recomendación: reemplazar por `cap_bpf+ep` (y posiblemente `cap_perfmon` para tracing si se usa). Esto es más preciso y reduce riesgo de escalada. Confirmar con `uname -r` en la hardened VM y documentación del kernel. Si se mantiene `cap_sys_admin`, justificar explícitamente en el paper como deuda temporal.
- **`cap_ipc_lock` para etcd-server (mlock del seed)**: Es suficiente para `mlock()` / `mlockall()`. No requiere `cap_sys_resource` a menos que se necesite elevar `RLIMIT_MEMLOCK` más allá del límite por defecto del proceso. `CAP_IPC_LOCK` permite ignorar el límite RLIMIT_MEMLOCK para el propio proceso. Medir el tamaño del seed y configurar `ulimit -l` si es necesario; evitar `cap_sys_resource` (demasiado amplio).
- **`cap_net_bind_service` para etcd-server (puerto 2379)**: No es necesario si se configura el sysctl `net.ipv4.ip_unprivileged_port_start=0` (o un valor ≤2379) a nivel de sistema (en el provisioner). Esta aproximación es común en entornos containerizados/rootless y evita otorgar la capability. Alternativa más segura: mantener el puerto >1024 si la arquitectura lo permite, o usar la capability solo si el sysctl no se desea modificar (por compatibilidad). Documentar la elección en `docs/HARDWARE-REQUIREMENTS.md`.

**Recomendación general**: Aplicar `setcap` de forma mínima verificable en `prod-deploy-x86` y auditar con `getcap` en `check-prod-capabilities`. Publicar la tabla final en el paper con justificación por componente.

### Q3: Falco — estrategia de reglas

Las 7 reglas actuales cubren bien amenazas internas (modificación de binarios, acceso indebido al seed, exec inesperado, shell spawn). Son un buen complemento a AppArmor (prevención vs. detección).

**Mejoras recomendadas** (patrones de ataque contra pipelines NDR):

- Añadir reglas para:
  - Acceso/modificación inesperada a eBPF maps o programas cargados (detección de tampering de XDP).
  - Carga de módulos kernel no autorizados o manipulación de netfilter/iptables más allá de lo permitido al firewall-agent.
  - Anomalías en uso de ZeroMQ/RAG (ej. conexiones salientes no esperadas desde rag-security).
  - Lectura de `/proc/<pid>/mem` o `/dev/mem` por procesos no autorizados (defensa contra inyección).
- **Driver recomendado en 2026**: `modern_ebpf` es la elección correcta para entornos VirtualBox/compatibilidad (no requiere init container ni compilación de kmod). Es el driver preferido en documentación reciente de Falco por menor overhead y mejor integración con BPF. Mantener `modern_ebpf` en el provisioner; documentar fallback a kmod solo si el kernel no soporta las features modernas.
- **Gestión de falsos positivos durante ajuste AppArmor**: Usar modo **audit** o reglas con `warn` (en lugar de critical) durante la fase de tuning. Configurar Falco con `outputs.rate_limit` o un periodo de "learning mode" (ej. primera hora post-provisioning con alertas solo a log). No deshabilitar reglas; en su lugar, usar tags o exceptions temporales basadas en hostname/VM. Una vez estabilizados los perfiles AppArmor, pasar todas las reglas a critical y activar respuesta (Falco response engine si disponible).

Falco + AppArmor forma una buena defensa en profundidad; priorizar que Falco detecte lo que AppArmor permite pero es anómalo.

### Q4: dist/ y el flujo BSR — ¿algo que mejorar?

El flujo actual (dev VM → shared folder `dist/x86/` → hardened VM) es **aceptable y pragmático** para desarrollo y demo FEDER. Reproduce la separación build/runtime de forma verificable (BSR axiom) y permite `prod-full-x86` + gates.

- **Shared folder en desarrollo**: Sí, aceptable temporalmente. En producción real (CICD), `dist/` será un artefacto firmado y transferido de forma segura (no shared folder). Documentar en el paper: “Durante desarrollo se usa shared folder Vagrant; en despliegue hospitalario se asume pipeline CICD con verificación de firmas SHA256 + Ed25519 antes de instalación.”
- **Firma Ed25519**: Arquitectónicamente correcto usar la misma clave (o derivada) para binarios y plugins en esta fase (simplifica ADR-025). Post-FEDER, considerar keypairs separados (binarios del pipeline vs. plugins extensibles) para reducir blast radius si una clave se compromete. Añadir rotación de claves en el diseño futuro. Mantener `prod-sign` y `prod-checksums` como gates obligatorios.

No hay cambios urgentes; el flujo actual soporta `check-prod-all`.

### Q5: La frase del paper — "Fuzzing misses nothing within CPU time"

**Análisis científico**: La frase es **imprecisa y potencialmente misleading** para revisores de cs.CR. Fuzzing (especialmente coverage-guided como libFuzzer) no “misses nothing”; es una técnica heurística probabilística que explora el espacio de entradas de forma guiada por cobertura, pero:

- Depende del tiempo de CPU, calidad del seed, harness y mutadores.
- No garantiza exhaustividad (el espacio de inputs es típicamente infinito o exponencial).
- No puede “probar ausencia de defectos” (como correctamente se menciona después); solo encuentra defectos observables bajo las condiciones de ejecución.
- Literatura (AFL++, libFuzzer papers, estudios empíricos) enfatiza que fuzzing es efectivo para descubrir bugs desconocidos, pero tiene limitaciones: bugs lógicos profundos, bugs dependientes de estado/distribución, o que requieren inputs muy específicos pueden permanecer no descubiertos incluso tras millones de ejecuciones.

**Reformulación honesta y académica recomendada** (sustituir en §6.8):

> "Unit tests cover only explicitly enumerated inputs. Property-based tests verify invariants over generated inputs but may miss structural anomalies at parser boundaries. Coverage-guided fuzzing (e.g., libFuzzer) systematically explores the input space, increasing the likelihood of triggering edge cases and vulnerabilities that adversaries exploit, subject to available CPU time and harness quality. Like other dynamic techniques, it cannot prove the absence of defects but provides empirical evidence of robustness when no crashes or sanitizer violations are observed after extensive runs."

Esta versión es precisa, cita el carácter empírico y probabilístico, y se alinea con papers sobre fuzzing (limitaciones en exhaustividad, dependencia de cobertura y tiempo).

**Acción**: Actualizar la frase, completar la tabla de métricas de fuzzing (DEBT-PAPER-FUZZING-METRICS-001) con datos reales recuperados, y añadir una nota sobre tiempo de ejecución típico y sanitizers usados (ASan/UBSan).

### Observaciones generales y decisión

- Las métricas reales de reducción (719→304 paquetes, 5.9→1.3 GB) son valiosas y deben destacarse en el paper v18 como evidencia cuantitativa del BSR axiom.
- Proceder con **P0 del DAY 134** (pipeline end-to-end), ajustando AppArmor/Falco iterativamente en modo complain → enforce.
- Mantener todas las deudas documentadas y priorizar P0 (fuzzing metrics + frase).
- El enfoque TDH + Consejo de Sabios + gates mecánicos sigue siendo sólido y reproducible.

**Decisión del Consejo**: Avanzar con el plan DAY 134 incorporando las recomendaciones anteriores. El proyecto demuestra progreso metódico hacia una imagen de producción mínima y auditable. Revisión adicional tras ejecución de `make check-prod-all` y actualización del paper.

*Via Appia Quality — La seguridad no se instala. Se diseña.*  
**Consejo de Sabios — DAY 133, 27 Abril 2026**