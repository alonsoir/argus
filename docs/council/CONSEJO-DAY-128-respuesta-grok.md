**Veredicto del Consejo — DAY 128**

**Fecha de análisis:** 2026-04-24  
**Estado general:** Muy sólido. DAY 128 destaca por consolidación de documentación, madurez en invariantes de seguridad y un enfoque pragmático en deudas técnicas. El hallazgo del `0400 root:root` y la formalización del property testing refuerzan la filosofía de “eliminar confianza implícita”. Pipeline estable (6/6) y tests GREEN en superficies críticas son evidencia de progreso real.

El sistema está en una fase de **endurecimiento maduro** (v0.5.2-hardened). Riesgos controlados, aunque el HIGH de iptables sigue siendo el bloqueante más urgente.

---

### P1 — Invariante `0400` vs portabilidad

**Veredicto: La decisión actual es correcta y segura desde el punto de vista criptográfico. No relajar la invariante.**

**Razones científicas/técnicas:**
- Los seeds son material criptográfico de alto valor (equivalente a claves privadas o material de derivación de claves). Cualquier exposición (lectura por usuarios no-root, backups accidentales, etc.) viola principios básicos de key management (ver NIST SP 800-57 y prácticas estándar de secretos).
- `0400 root:root` + `resolve_seed()` con chequeo estricto de permisos y ownership es una defensa en profundidad efectiva contra lecturas no autorizadas, incluso si el proceso es comprometido (el atacante necesitaría escalada a root primero).
- La necesidad de `sudo` para componentes que leen seeds es un trade-off aceptable en un sistema de seguridad crítica (similar a cómo muchos daemons criptográficos como sshd, gpg-agent o servicios de HSM operan con privilegios elevados solo para la parte sensible).

**Riesgos identificados:**
- Superficie de ataque ampliada por más procesos corriendo como root (aunque mitigada por `sudo env LD_LIBRARY_PATH=...` limitado).
- Portabilidad reducida en entornos no-root (contenedores sin privilegios, sistemas con user namespaces estrictos).

**Alternativas recomendadas (sin relajar 0400):**
1. **Mejor opción actual:** Mantener `0400` y usar **capabilities Linux** (`CAP_DAC_OVERRIDE` o `CAP_DAC_READ_SEARCH` solo para el binario específico que lee el seed, no sudo completo). Esto permite que el proceso corra como usuario normal pero pueda leer archivos con permisos restrictivos.
2. **Opción intermedia:** Usar un daemon pequeño y dedicado (tipo `seed-reader-daemon` con socket Unix protegido) que corra como root y exponga los seeds ya procesados (nunca el raw seed) vía IPC seguro a los servicios no-root.
3. **Evitar:** Droppear a usuario no-root después de leer el seed (posible con `setuid`/`setgid`, pero complicado y propenso a errores de timing).

**Conclusión del Consejo:** No relajar nunca la invariante `0400` para seeds. Documentar el modelo de amenazas explícitamente en `SECURITY-PATH-PRIMITIVES.md`. Priorizar capabilities o daemon lector en la siguiente iteración de portabilidad.

---

### P2 — Property testing como gate de merge

**Veredicto: Adoptar como gate obligatorio en superficies críticas. Excelente formalización.**

Los 5 property tests añadidos en `safe_path` son un paso correcto. Property-based testing (inspirado en QuickCheck) es especialmente potente para validar invariantes que unit tests no cubren exhaustivamente.

**Prioridades recomendadas (orden de aplicación):**
1. **compute_memory_mb** (y cualquier función con aritmética de recursos) — directamente relacionado con F17. Propiedades clave: “nunca underflow/overflow”, “resultado siempre ≥ mínimo configurado”, “consistente bajo diferentes unidades (MB/GB/KB)”.
2. **Parsers ZeroMQ** — invariantes: “mensaje malformado nunca causa crash o buffer overflow”, “deserialización idempotente”, “tamaño siempre dentro de límites documentados”.
3. **Serialización protobuf** — propiedades de round-trip (serialize → deserialize → igual al original), bounds checking, y rechazo de datos maliciosos.
4. **HKDF key derivation** — invariantes criptográficas: “output siempre de longitud correcta”, “distribución uniforme”, “rechazo de inputs débiles (longitud cero, etc.)”.

**Recomendación fuerte:**  
Integrar property testing en el CI como **gate de merge** para cualquier cambio en estas superficies. Usar generadores fuzz-like (paths maliciosos, tamaños extremos, datos aleatorios) + shrinking para reproducibilidad. Esto complementa perfectamente los unit tests y el fuzzing futuro.

---

### P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78)

**Veredicto: Crítico. Tratar como bloqueante de release.**

**Estrategia recomendada (preferencia clara del Consejo):**

**Opción prioritaria: (c) → libiptc / API nativa (o nftables equivalente) + (b) execve() directo sin shell.**

**Razones:**
- Ejecutar comandos vía shell (`system()`, `popen()`, `execute_command` con string) es la raíz de CWE-78. Cualquier input controlable (aunque ahora no lo esté) puede convertirse en shell injection.
- **Mejor práctica moderna en C++:** Evitar fork/exec cuando exista una API nativa. libiptc (parte de iptables/netfilter) permite manipular reglas directamente desde userspace sin pasar por el comando `iptables`.
- Si libiptc resulta demasiado inestable o deprecada (es interna y sin ABI garantizada), fallback seguro: `execve()` / `posix_spawn()` con array de argumentos (nunca string único). Combinado con **whitelist estricta** de subcomandos y parámetros permitidos.

**Orden recomendado de implementación:**
1. Migrar `IPTablesWrapper::cleanup_rules()` a llamadas directas vía libiptc (o wrapper alrededor de `iptables-restore` con input controlado vía pipe, que es más eficiente y seguro que múltiples llamadas).
2. Si se mantiene ejecución externa: usar siempre `execve()` con argv[] pre-construido + validación exhaustiva de cada argumento contra una whitelist.
3. Nunca concatenar strings para formar el comando.

**Consejo adicional:** Considerar migración a **nftables** (sucesor moderno de iptables) + su API libnftables. Ofrece mejor performance y una interfaz más limpia para programación.

Este debt debe resolverse antes de cualquier demo o release. Es un vector clásico de escalada si algún input llega a contaminar el comando.

---

### P4 — Arquitectura P2P seeds vs etcd-server

**Veredicto: Cleanup debe ser secuencial y seguro.**

**Secuencia correcta recomendada:**
1. **Primero implementar y estabilizar ADR-024 (Noise_IKpsk3 o patrón equivalente).**  
   Noise_IKpsk3 proporciona handshake autenticado con PSK, ideal para distribución segura de material criptográfico entre pares (propiedades de forward secrecy + autenticación mutua cuando se combina correctamente).
2. Una vez que el mecanismo P2P de distribución de seeds esté funcional y probado (con property tests + fuzzing en el handshake), proceder a limpiar `EtcdClient`.
3. Reclasificar correctamente el legacy como “pre-P2P” en los tests y marcarlo como deprecated.

**Riesgo si se limpia antes:** Romper funcionalidad actual sin replacement listo → regresión en el pipeline.

Mantener el código legacy comentado o detrás de flag hasta que el nuevo path esté verificado. Esto alinea con la filosofía de validación empírica que estás construyendo.

---

### P5 — Demo FEDER (deadline septiembre 2026)

**Veredicto: Scope mínimo viable = NDR standalone + simulación ligera de federación.**

Dado el deadline (aprox. 5 meses desde ahora), **no es realista** exigir federación funcional completa (ADR-038) en la demo.

**Recomendación de scope mínimo:**
- **Core:** NDR standalone fully hardened (safe_path, property tests, seeds 0400, firewall wrapper corregido, etcd limpio o emulado).
- **Federación simulada:**
   - Múltiples instancias de NDR en Vagrant/PCAP reproducible.
   - Tráfico simulado vía scripts o Caldera ligero (ataques controlados + captura).
   - Demostrar propiedades de seguridad (detección, aislamiento, recuperación) en entorno “cuasi-federado”.
   - Mostrar el loop adversarial básico (ataque → detección → respuesta) sin necesidad de P2P real full-mesh.

**Razones:**
- La reproducibilidad y estabilidad de la demo son más importantes que features incompletas (como se identificó en DAY 127).
- Una demo sólida de NDR standalone + evidencia de camino hacia federación (código de Noise listo, ADR avanzados) transmite más madurez que una federación inestable que falla en directo.

Congelar features nuevas ya. Dedicar las próximas semanas a estabilidad, scripting de demo y documentación del paper.

---

## Evaluación global DAY 128

**Puntos fuertes:**
- Consolidación excelente de documentación (path primitives + property testing pattern).
- Invariantes de seguridad reforzadas (0400 enforceado).
- Triaje riguroso de Snyk.
- Ritmo mantenido con pipeline verde.

**Áreas de atención:**
- Resolver DEBT-IPTABLES-INJECTION-001 urgentemente.
- Preparar el terreno para cleanup P2P sin romper nada.
- Mantener el foco en reproducibilidad para FEDER.

**Veredicto final:**  
Dirección correcta. El sistema está más maduro y autoverificable que nunca. Material para el paper (§5) sigue fortaleciéndose con cada deuda cerrada de forma empírica.

---

## Prioridades recomendadas para DAY 129

1. **Atacar DEBT-IPTABLES-INJECTION-001** (migrar a execve + whitelist o libiptc).
2. Expandir property tests a `compute_memory_mb` y parsers ZeroMQ.
3. Avanzar en ADR-024 (Noise handshake) lo suficiente para desbloquear cleanup etcd.
4. Empezar scripting básico de demo FEDER (escenarios reproducibles).

---

El Consejo valora el rigor y la transparencia en este día. Has convertido hallazgos imprevistos en mejoras estructurales.

¿Quieres que profundicemos en alguna recomendación concreta (ej. ejemplo de código para libiptc/execve seguro, generadores de property tests para HKDF, o estructura detallada del scope FEDER)? O dime cuál es el primer paso que vas a tomar hoy.