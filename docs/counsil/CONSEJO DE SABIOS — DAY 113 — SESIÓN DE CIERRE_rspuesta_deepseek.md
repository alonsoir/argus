## Respuesta del Consejo de Sabios – DAY 113 (10 Abril 2026)

El Consejo reconoce el intenso trabajo realizado en ADR-025 y en el paper. Sin embargo, **hay dos omisiones críticas** que invalidan la pretensión de “PHASE 2 completa” y deben ser corregidas antes de cualquier merge a `main`. A continuación, el análisis duro pero justo.

---

## 🔴 Puntos críticos – No negociables

### 1. TEST-INTEG-4d para ml-detector sigue sin existir

En DAY 112 el Consejo exigió explícitamente: *“Implementar test_integ_4d.cpp para ml-detector … antes de declarar PHASE 2 cerrada”*. En el acta de DAY 113 se listan `4a+4b+4c+4e` pero **no 4d**. El `make test` dice 11/11, pero esos son 4 tests de integración antiguos + 7 de signing. **No hay evidencia de que ml-detector haya sido probado con el plugin loader.**

**Esto es inaceptable.** Sin TEST-INTEG-4d, la fase ml-detector no está validada. El pipeline puede fallar silenciosamente en producción.

**Exigencia inmediata:**
- Implementar `test_integ_4d.cpp` siguiendo el patrón de 4c (tres casos: NORMAL con payload, modificación de campo read‑only, `result_code != 0`).
- Ejecutarlo y documentar el resultado.
- Incluirlo en `make plugin-integ-test` y en el CI.
- **No se autoriza ningún merge a `main` hasta que 4d esté verde.**

### 2. Async-signal-safety de `shutdown()` no ha sido revisada

El DAY 112 también se señaló que `shutdown()` no es async-signal-safe según POSIX. En el acta de DAY 113 no hay ninguna mención a que se haya corregido o justificado. El código `plugin_loader.cpp` no se muestra, pero la implementación de ADR-025 pudo haber introducido más llamadas no seguras (ej. `dlclose`, `free`, logging).

**Exigencia:**
- Revisar `plugin_loader.cpp` y asegurar que `shutdown()` solo realiza operaciones async-signal-safe: cambiar un `std::atomic<bool>` y, como mucho, llamar a `close()` sobre fds.
- Si necesita liberar memoria o cerrar bibliotecas, hacerlo en un hilo aparte o en un `atexit` normal, nunca desde el signal handler.
- Documentar en ADR-029 (o en una nota de código) la lista exacta de funciones llamadas desde el handler.
- Añadir una prueba con `fork+kill` (Opción A recomendada) que ejecute valgrind o sanitizers para detectar comportamientos indefinidos.

Mientras esto no esté resuelto, **el signal handler es un riesgo de deadlock/corrupción**.

---

## Respuesta a las preguntas (una vez solventados los puntos críticos)

### Q1 – Merge ahora o esperar a `--reset`?

**Veredicto:** **Merge ahora** (después de corregir 4d y signal safety), sin esperar a `--reset`.

**Razones:**
- `--reset` es una operación administrativa de rotación de claves, no necesaria para el funcionamiento base. La deuda técnica está aceptablemente documentada.
- La rama actual es estable y contiene valor sustancial (firma de plugins). Mantenerla abierta mucho tiempo genera divergencia.
- El merge permite desbloquear el trabajo en PHASE 3 o ADR-026 sobre una base común.

**Condición:** El `--reset` debe estar registrado como **deuda prioridad P1** en `BACKLOG.md` con un plan para implementarlo en los siguientes 7-10 días naturales.

---

### Q2 – `provision.sh --reset` (D11): ¿ahora o diferir?

**Veredicto:** **Diferir, pero con alta prioridad (P1) y plazo concreto.**

**Argumentos:**
- No es bloqueante para la funcionalidad principal (la clave actual es válida y segura).
- Sin embargo, la rotación de claves es una práctica de seguridad necesaria para entornos de producción a largo plazo. Sin ella, el operador no puede revocar una clave comprometida.
- La implementación es acotada (unos 100-150 líneas en bash más la lógica de mover archivos).

**Recomendación:**
- Crear una issue/tarea específica para `--reset` con deadline **antes del inicio de PHASE 3**.
- Aceptar el merge actual sin ella, pero no cerrar ADR-025 hasta que esté implementada.

---

### Q3 – Próxima prioridad: ¿PHASE 3 o ADR-026?

**Veredicto:** **PHASE 3 primero.** (Unanimidad)

**Justificación:**
- **PHASE 3** (hardening del pipeline: systemd, AppArmor básico, CI gate) es **requisito previo** para cualquier despliegue real, incluso en pruebas. Sin él, los componentes pueden morir silenciosamente o ser vulnerables a ataques locales (LD_PRELOAD, etc.).
- **ADR-026** (Fleet Telemetry + XGBoost) es una funcionalidad nueva y ambiciosa. Requiere diseño adicional, entrenamiento de modelos y pruebas. No tiene sentido añadir complejidad sobre una base que aún no es robusta en producción.
- El paper actual ya tiene suficiente contribución con PHASE 2 + ADR-025. ADR-026 puede ser material para una segunda versión del paper o un follow-up.

**Plan sugerido:**
1. Completar PHASE 3 (estimación 1-2 semanas).
2. Una vez PHASE 3 estable, abordar ADR-026.
3. ADR-030/031 siguen en backlog, sin prioridad inmediata.

---

### Q4 – DEBT-TOOLS-001: ¿P3 es correcto?

**Veredicto:** **Sí, P3 es adecuado** (pero con matices).

**Razones:**
- Los synthetic injectors son herramientas de desarrollo y prueba, no parte del pipeline de producción.
- Su falta de integración con el plugin loader no afecta la corrección del sistema real, solo la representatividad de los stress tests.
- **Sin embargo**, si se planea usar esos injectors para medir rendimiento o para validar el comportamiento bajo carga (por ejemplo, para el paper), entonces deberían subir a P2.

**Recomendación:**
- Documentar explícitamente en la descripción de DEBT-TOOLS-001 que los injectors actuales **no** validan la ruta de plugins.
- Si en el futuro se usan para benchmarks públicos, actualizar la deuda a P2.

---

### Q5 – Párrafo Glasswing/Mythos: ¿tono correcto?

**Veredicto:** **El tono es adecuado, pero puede mejorarse en precisión y humildad científica.**

**Observaciones:**
- La redacción actual es algo deferente (“sophisticated reasoning”, “depth previously requiring specialized human expertise”). Es correcto para un paper cs.CR, pero podría ser más neutral: simplemente constatar el hecho sin calificativos valorativos.
- Es importante no sobrevender el impacto: Mythos Preview es una capacidad de investigación, no una amenaza generalizada. El paper debe evitar dar la impresión de que “las IA ya pueden hackear cualquier kernel”.

**Texto alternativo sugerido (más neutral):**

> *This paper was written and submitted in April 2026, shortly after the public disclosure of Anthropic’s Glasswing project and its Mythos Preview capability. Mythos Preview demonstrated autonomous identification of kernel privilege escalation vulnerabilities in Linux, illustrating the increasing sophistication of AI-assisted security analysis. We explicitly discuss the implications of such capabilities on the threat model of network-based detection systems (see §Threat Model).*

**Además:** Asegurarse de que el párrafo no está en §Related Work sino en una sección de motivación o contexto (quizás la introducción). Related Work debería citar trabajos previos, no anuncios de prensa.

**Recomendación final:** Mantenerlo, pero moverlo a la Introducción o a una nota contextual, no a Related Work.

---

## Resumen de acciones obligatorias antes del merge a `main`

| Ítem | Acción | Estado actual | Plazo |
|------|--------|---------------|-------|
| 1 | Implementar TEST-INTEG-4d para ml-detector | ❌ No hecho | Inmediato |
| 2 | Revisar async-signal-safety de `shutdown()` | ❌ No revisado | Inmediato |
| 3 | Añadir test con fork/kill para signal handler | ❌ No hecho | Inmediato |
| 4 | Corregir párrafo Glasswing (opcional, no bloqueante) | ⚠️ Mejorable | Antes del arXiv Replace |

Una vez cumplidos 1, 2 y 3, el Consejo autorizará el merge de `feature/plugin-integrity-ed25519` → `main`.

Mientras tanto, **no se acepta la afirmación de “PHASE 2 completa”** ni se considera estable la rama.

---

*“La verdad por delante, siempre” – también cuando duele.*  
El Consejo espera la rectificación en DAY 114.

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta redactada: 10 Abril 2026*