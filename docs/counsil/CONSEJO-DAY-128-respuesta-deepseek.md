## Respuesta del Consejo de Sabios — DAY 128

**Modelos consultados:** Claude, Grok, ChatGPT, DeepSeek, Qwen, Gemini, Kimi, Mistral  
**Consenso alcanzado en:** 2026-04-24

---

### P1 — Invariante `0400` vs portabilidad

**Riesgos identificados:**
- `sudo` generalizado amplía la superficie de ataque si un componente malicioso logra ejecutarse bajo `sudo` (por ejemplo, a través de una inyección de LD_PRELOAD o manipulación de `LD_LIBRARY_PATH`).
- Posible confusión operacional: algunos componentes arrancan con `sudo`, otros no. La documentación de operaciones debe ser explícita.
- En entornos contenerizados, `sudo` puede no estar disponible o requerir configuración extra (política `sudoers`).

**Alternativas que preservan `0400` sin `sudo` generalizado:**
1. **Proceso dedicado `seed-helper`** con privilegios mínimos (`CAP_DAC_OVERRIDE` o `CAP_DAC_READ_SEARCH`) que expone una API Unix socket. Los componentes no privilegiados piden el seed mediante `SCM_RIGHTS` (paso de fd). Esto evita `sudo` en los componentes principales.
2. **Usar `fscrypt` o `encfs`** con una clave derivada de TPM – los seeds permanecen cifrados en disco, se descifran en un proceso aislado al arranque.
3. **Cambiar el propietario a un grupo dedicado (`seed-readers`)** y permisos `0440`. La invariante se mantiene en `040` (sin escritura para nadie) pero se relaja la exclusividad `root:root`. Si el modelo de amenaza permite que procesos no-root del grupo accedan, es aceptable siempre que el grupo esté estrictamente controlado.

**Recomendación:**  
Mantener `sudo` actual por simplicidad, pero documentar como **requisito de seguridad no negociable** y planificar a medio plazo la migración a helper con `CAP_DAC_READ_SEARCH`. Esto reduce la huella de `sudo` a un solo binario bien auditado.

---

### P2 — Property testing como gate de merge

**Superficies prioritarias (ordenadas por criticidad + complejidad):**

1. **`compute_memory_mb` (F17)** – Ya identificada. Operaciones aritméticas con enteros de sistema (proporciones, límites). **Tests necesarios:** invariantes de redondeo, no desbordamiento, rangos válidos (ej: `compute_memory_mb(0.95, total_mb)` nunca excede total_mb).
2. **Parsers ZeroMQ (multipart messages)** – Decodificación de marcos, límites de tamaño, caracteres nulos embebidos. **Propiedades:** `encode(decode(x)) == x` para todos los mensajes válidos; decode rechaza inputs malformados sin crash.
3. **Serialización protobuf** – Especialmente después de actualizaciones de esquema. **Propiedad:** `serialize(deserialize(m)) == m` para todos los mensajes, incluyendo campos `optional` y `repeated`.
4. **HKDF key derivation** – Con vectores conocidos (RFC 5869) y propiedades criptográficas: `extract(salt, IKM)` produce salida pseudorandom; `expand(PRK, info, L)` es determinista e inyectiva en `info`.
5. **Módulo de rate limiting (`TokenBucket`)** – Propiedades de conservación de tokens, ausencia de desbordamiento en 64-bit, corrección de tiempo.

**Recomendación:**  
Hacer property testing obligatorio para **cualquier función que reciba entrada externa no confiable** (network, ficheros, user input) o que realice aritmética de seguridad (memoria, timeouts). Integrar en CI con `make test-property` y bloquear merge si falla. Los 5 tests actuales son un buen comienzo; añadir `compute_memory_mb` como siguiente paso inmediato.

---

### P3 — `DEBT-IPTABLES-INJECTION-001` (CWE-78)

**Análisis de opciones:**

| Opción | Ventajas | Desventajas |
|--------|----------|--------------|
| **(a) Whitelist de comandos** | Sencillo, bajo impacto | Requiere mantener lista; aún vulnerable si la whitelist es demasiado amplia (ej: permitir `-A` pero no sanitizar cadenas). |
| **(b) `execve()` directo sin shell** | Elimina shell metacharacters (`;`, `\|`, `` ` ``). Mejor práctica general. | Debes construir `argv` correctamente. Todavía vulnerable a argumentos maliciosos si no validas cada argumento. |
| **(c) `libiptc`** | No hay fork/exec, seguridad máxima. | Complejo; depende de `libiptc` (no siempre instalada). Cambios en iptables requieren recompilación. |

**Estrategia recomendada (defensa en profundidad):**
1. **Inmediato (fix crítico):** Usar `execvp()` con `argv` explícito, **nunca** pasar por `system()` o `popen()`.  
   Ejemplo:
   ```cpp
   char *argv[] = {"iptables", "-D", chain, rule, nullptr};
   execvp(argv[0], argv);
   ```
2. **Validación estricta de entrada:** Whitelist de caracteres permitidos (alfanumérico, `-`, `_`, `.`, `:`, `/`) y rechazar cualquier otro.
3. **Lista blanca de comandos** – Solo aceptar `"-A"`, `"-D"`, `"-I"`, `"-L"`, `"-F"` (y posiblemente `"-t"` para tabla).
4. **A largo plazo:** Evaluar `libnftables` (sucesor de iptables) con API en C, que permite manipulación directa sin fork/exec.

**Plan de acción:**  
Crear una función `sanitize_iptables_args()` que valida cada argumento contra regex `^[a-zA-Z0-9_./:-]+$` y usa `execve()`. Implementar **hoy** y aplicar a `cleanup_rules()`.

---

### P4 — Arquitectura P2P seeds vs etcd-server

**Secuencia correcta de cleanup:**

**No se debe limpiar `EtcdClient` antes de tener ADR-024 funcional.** La razón:
- El código legado `EtcdClientHmacTest` todavía se ejecuta (aunque no bloqueante). Si eliminas la capacidad de leer seeds del FS antes de que el nuevo Noise_IKpsk3 esté operativo, el sistema podría quedar en un estado híbrido donde algunos componentes esperan seeds vía etcd y otros vía P2P.

**Secuencia recomendada:**
1. **Completar ADR-024 (Noise_IKpsk3)** e integrarlo en pipelines de bootstrap.
2. **Migración gradual:**
   - Añadir flag `--use-legacy-etcd-seed` (default false).
   - En los componentes que hoy usan `EtcdClient`, primero intentar obtener seed vía P2P (ADR-024), si falla y flag legacy true, usar `resolve_seed()`.
3. **Verificar en VM nueva** que con flag legacy=false todo funciona.
4. **Eliminar `EtcdClient` del código** y sus tests asociados.
5. **Eliminar `resolve_seed()`** (o moverlo exclusivamente a `bootstrap` para generar el seed inicial).

**Riesgo si se hace antes:** Regresión silenciosa en escenarios de red aislada donde P2P aún no está maduro. La deuda `DEBT-ETCDCLIENT-LEGACY-SEED-001` no es bloqueante; etiquetar como `backlog` post-ADR-024.

---

### P5 — Demo FEDER (deadline 22 septiembre 2026)

**Recomendación por consenso:**

**Scope mínimo viable para la demo FEDER = NDR standalone con capacidad de demostrar “federación simulada”.**

**Justificación:**  
La federación real (ADR-038) implica descubrimiento dinámico de pares, consenso distribuido, reconciliación de estado. Desarrollar, probar y estabilizar todo esto antes de septiembre 2026 es **arriesgado** (6 meses).

**Propuesta concreta:**
- **Sí obligatorio:**
   * NDR funcionando en un solo nodo con todas las capacidades (detección, RAG, API, reglas).
   * Interfaz de usuario/web que muestre “federación” simulada: dos instancias NDR independientes que comparten indicadores vía un script de import/export manual.
   * Documentación clara de cómo se federaría en la arquitectura final (ADR-038).
- **No obligatorio (postergable):**
   * Descubrimiento automático.
   * Replicación en tiempo real.
   * Tolerancia a particiones.

**Ventajas:**
- Cumple el objetivo político de mostrar “federación” (interoperabilidad entre dominios administrativos).
- Reduce el riesgo de no entregar nada.
- Permite iterar sobre ADR-038 con calidad después de la demo.

**Alternativa si hay recursos adicionales:**  
Implementar **federación minimalista** usando gossip sobre mensajes firmados (sin consenso complejo) – se puede hacer en 2-3 meses. Pero el Consejo recomienda la opción segura: NDR standalone + simulator.

---

## Acuerdos vinculantes

1. **`0400` se mantiene** con documentación de `sudo` como requisito. Se crea issue para helper `seed-helper` (prioridad baja).
2. **Property testing** obligatorio para nuevas funciones críticas. Añadir `compute_memory_mb` inmediatamente.
3. **Fijar `DEBT-IPTABLES-INJECTION-001`** usando `execvp()` + validación whitelist. Deadline: 7 días.
4. **No eliminar `EtcdClient`** hasta que ADR-024 esté completo y validado en VM.
5. **Demo FEDER scope:** NDR standalone + simulación de federación. Comunicar a stakeholders antes de 15 de mayo.

---

**El Consejo declara el DAY 128 como exitoso en consolidación y discovery técnico.** Los property tests y la taxonomía de `safe_path` son activos duraderos. La deuda de inyección iptables debe resolverse con urgencia.

*Firmado por los 8 modelos en consenso.*