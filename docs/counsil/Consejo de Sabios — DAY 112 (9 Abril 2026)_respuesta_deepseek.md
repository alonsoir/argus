## Respuesta del Consejo de Sabios – DAY 112 (9 Abril 2026)

El Consejo ha revisado el acta de DAY 112. Se valora muy positivamente la finalización de PHASE 2 y la incorporación de ADR-030/031. Sin embargo, se identifican **puntos críticos** que requieren atención antes de declarar la fase completamente cerrada. A continuación, las respuestas a las preguntas, seguidas de un análisis riguroso.

---

## Respuestas a las preguntas

### Q1-113 – ¿Merge feature/plugin-crypto → main ahora o esperar a ADR-025?

**Veredicto del Consejo:** **Merge ahora, sin ADR-025.** Unanimidad.

**Razones:**
- `main` está muy desactualizado (37+ commits). Mantenerlo así aumenta el riesgo de conflictos y dificulta la integración continua.
- PHASE 2 es un hito completo y testeado. Mergearlo ahora permite tener una base estable sobre la que aplicar ADR-025 después.
- ADR-025 (plugin signing) es un cambio sustancial (toca 6 componentes, schemas JSON, systemd, tests). Mezclarlo en el mismo PR haría la revisión más compleja y podría introducir errores no relacionados con PHASE 2.
- Si surge algún problema post-merge, es más fácil aislarlo si los cambios son atómicos.

**Acción:** Ejecutar el merge de `feature/plugin-crypto` → `main` inmediatamente después de resolver los puntos críticos que se indican abajo.

---

### Q2-113 – Secuencia de ADR-025: ¿en la misma rama o nueva rama post-merge?

**Veredicto del Consejo:** **Nueva rama post-merge.** Unanimidad.

**Razones:**
- Separación de responsabilidades: PHASE 2 es arquitectura de plugins; ADR-025 es integridad criptográfica. Son ortogonales.
- Si se implementa en la misma rama, el PR se convierte en un monolito difícil de revertir.
- Post-merge, se puede crear `feature/plugin-signing` desde `main` y trabajar de forma aislada.

**Recomendación adicional:** Aprovechar para actualizar la documentación de `BUILD.md` y `DEPLOY.md` con los nuevos pasos de provisionamiento (flag `--reset`, generación de claves Ed25519).

---

### Q3-113 – Axioma “kernel inseguro” en el paper: ¿Threat Model, Limitations o Future Work?

**Veredicto del Consejo:** **Principalmente en §Threat Model, con referencias cruzadas en §Limitations y §Future Work.** Unanimidad.

**Justificación:**
- **§Threat Model** es el lugar natural para declarar explícitamente: *“Este trabajo asume que el kernel del host puede estar comprometido. Las garantías de detección de aRGus son válidas dentro de su capa (análisis de tráfico de red), no por debajo.”* Esto define los límites del modelo de amenaza.
- **§Limitations** debe repetir el axioma como una limitación fundamental: *“Si el kernel del host es comprometido por un adversario avanzado (Mythos Preview), aRGus no puede garantizar la integridad de su propio proceso.”*
- **§Future Work** debe mencionar ADR-030 y ADR-031 como respuestas para mitigar o eliminar esa dependencia.

**Texto propuesto (aceptado con una pequeña mejora):**

> *aRGus NDR defines its detection guarantees as valid within its layer (network behavior analysis). If the host kernel is compromised by an advanced adversary — as demonstrated by Mythos Preview (Anthropic, 2026) — detection guarantees are invalidated within that host. However, network detection remains a valid defensive layer because lateral movement between hosts still traverses monitored network segments. Host hardening (ADR-030) and formal kernel verification (ADR-031) are documented as future work.*

**Mejora sugerida:** Añadir una frase explícita en §Threat Model: *“We explicitly do not assume a trusted kernel; our threat model includes the possibility of kernel compromise.”*

---

### Q4-113 – ADR-031 spike: ¿x86-64 con QEMU primero o directamente ARM64?

**Veredicto del Consejo:** **x86-64 con QEMU primero, por varias razones.** Unanimidad.

**Razones:**
- Madurez de Genode/seL4 en x86-64 es muy superior a ARM64 (documentación, ejemplos, soporte de la comunidad).
- El hardware Raspberry Pi no está disponible actualmente (BLOCKED). QEMU en x86-64 permite empezar el spike de inmediato.
- Los resultados del spike (viabilidad de libpcap, overhead de virtualización, dlopen, ZeroMQ) son en su mayoría independientes de la arquitectura. Una vez validado el concepto en x86-64, el port a ARM64 es un paso adicional (pero no trivial).
- Si el spike en x86-64 muestra que el overhead es catastrófico (>10x), se puede descartar la variante sin necesidad de tocar ARM64.

**Condición:** El informe del spike debe incluir una sección específica sobre las diferencias esperadas en ARM64 (basadas en literatura y foros de Genode). Si el spike es favorable, se procederá a repetir los experimentos en Raspberry Pi 5 cuando esté disponible.

---

## 🔴 Puntos críticos – Feedback duro pero justo

El Consejo felicita por el avance, pero **no puede aprobar el cierre de PHASE 2 ni considerar ADR-030/031 como “aprobados”** sin abordar los siguientes problemas.

### 1. Falta TEST-INTEG-4d para ml-detector

En la tabla de PHASE 2, `ml-detector` aparece como “compilación limpia” pero **sin ningún test de integración**. El `make plugin-integ-test` solo muestra 4a, 4b, 4c, 4e. **¿Dónde está 4d?**

El mandato del Consejo desde DAY 109 era que cada fase debe tener su TEST-INTEG-X antes de darla por completa. Sin 4d, **PHASE 2 no está completa (4/5, no 5/5).**

**Exigencia:**
- Implementar `test_integ_4d.cpp` para ml-detector siguiendo el patrón de 4c (casos: NORMAL con payload, modificación de campos read-only, result_code != 0).
- Ejecutar y pasar el test antes de declarar PHASE 2 cerrada.
- El merge a `main` debe incluir este test.

### 2. Async-signal-safety de `shutdown()` en ADR-029

El ADR-029 D2 dice que el signal handler solo llama a `write()`, `shutdown()`, `raise()`. Pero **`shutdown()` no es una función async-signal-safe** según POSIX (la lista oficial incluye `_exit()`, `signal()`, `raise()`, `write()`, `read()`, `close()`, `pipe()`, `dup2()`, `fcntl()` con F_SETFD, `fstat()`, `getpid()`, `gettimeofday()`, `sleep()`, `usleep()`, `wait()`, `waitpid()`, y algunas más – `shutdown()` **no está en esa lista**).

Si `g_plugin_loader->shutdown()` hace algo más que establecer el puntero a nullptr (por ejemplo, llamar a `dlclose()`, `free()`, `munmap()`, o cualquier función que no sea async-signal-safe), el comportamiento es **indefinido** y puede causar deadlock o corrupción de memoria.

**Exigencia:**
- Revisar la implementación de `shutdown()` en `plugin_loader.cpp`. Debe ser extremadamente simple: solo cambiar un estado atómico y, si es necesario, cerrar fds con `close()` (que sí es async-signal-safe).
- **No** llamar a `dlclose()` ni liberar memoria desde el signal handler.
- Documentar claramente en ADR-029 qué funciones son seguras y por qué.
- Añadir un test (opción A de Q2-112) que envíe SIGTERM durante el procesamiento y verifique que no hay corrupción (valgrind o sanitizers).

### 3. ADR-030 y ADR-031: “aprobados” prematuramente

El Consejo, en su revisión anterior (9 Abril 2026), **no aprobó los ADR sin condiciones**. Se emitieron observaciones que debían ser incorporadas antes de cerrarlos. El acta de DAY 112 dice “aprobados por el Consejo en sesión DAY 109 (5/5 unanimidad)” – pero esa sesión no ocurrió con ese resultado. **Esto es un error de registro.**

**Estado real:**
- ADR-030: **Aceptado en principio, pendiente de incorporar las mejoras sugeridas** (kernel version fallback, secure boot en Raspberry Pi, flags ARM64, caveat XDP).
- ADR-031: **Aceptado como RESEARCH, pendiente de spike técnico y de incorporar la nota sobre comparación con libpcap nativo.**

**Exigencia:**
- Modificar ambos ADR según las recomendaciones del Consejo (ver respuesta anterior).
- Subir los cambios a `docs/adr/` y actualizar `BACKLOG.md` con el estado correcto (ACEPTADO con condiciones, no simplemente “aprobado”).
- No marcar como “cerrados” hasta que las condiciones se cumplan.

### 4. Integridad de los tests: ¿se ejecutaron realmente?

El acta afirma `make plugin-integ-test: 4a+4b+4c+4e PASSED`. Sin embargo, no se adjunta ningún log ni evidencia. Dado el incidente anterior de ficheros vacíos, el Consejo recomienda **publicar los logs de CI** (o al menos un resumen verificado) en el acta.

**Recomendación:** Incluir en el acta un enlace a la ejecución de CI (GitHub Actions o similar) o pegar el output de `make plugin-integ-test` como bloque de código.

---

## Resumen de acciones obligatorias antes del merge a `main`

| Ítem | Acción | Responsable | Plazo |
|------|--------|-------------|-------|
| 1 | Implementar TEST-INTEG-4d para ml-detector | Alonso | Antes del merge |
| 2 | Revisar async-signal-safety de `shutdown()` y corregir si es necesario | Alonso | Antes del merge |
| 3 | Actualizar ADR-030 y ADR-031 con las observaciones del Consejo | Alonso | Antes de cerrar los ADR (no bloquea merge) |
| 4 | Publicar log de CI para `plugin-integ-test` | Alonso | En el acta DAY 112 (corregida) |

Una vez realizados 1, 2 y 4, el Consejo **autoriza el merge** de `feature/plugin-crypto` → `main`.

---

## Conclusión

El trabajo de DAY 112 es sólido en muchos aspectos, pero la falta de test para ml-detector y la posible vulnerabilidad en el signal handler son **problemas graves** que deben corregirse. La honestidad intelectual exige reconocer estas deficiencias antes de cantar victoria.

*“La verdad por delante, siempre”* – también cuando duele.

El Consejo espera la actualización de DAY 113 con las correcciones.

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta redactada: 9 Abril 2026*