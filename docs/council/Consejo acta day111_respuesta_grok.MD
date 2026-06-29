**Consejo de Sabios — Respuesta al Acta DAY 111 (8 Abril 2026)**

Excelente día, Alonso.

El **hito arXiv:2604.04952** publicado es un logro importante. El paper menciona explícitamente el Consejo de Sabios y la metodología **Test-Driven Hardening (TDH)**, lo que refuerza la identidad del proyecto. Felicitaciones por el endorsement de Andrés Caro Lindo (UEx/INCIBE) y Sebastian Garcia (CTU Prague) — eso da credibilidad académica sólida desde el principio. El pipeline sigue en 6/6 RUNNING y PHASE 2 avanza de forma limpia a pesar del incidente de ficheros del DAY 110.

Las implementaciones de hoy (FIX-C bidireccional, FIX-D hard limit 64KB, TEST-INTEG-4c completo, PHASE 2d terminado y ADR-029 formalizado) son sólidas y coherentes con el rigor del proyecto.

### Respuestas a las preguntas para DAY 112

**Q1-112 — PHASE 2e invoke_all: ¿READONLY es correcto?**

**Sí, READONLY es definitivamente correcto en rag-security.**

**Argumento**: rag-security actúa como guardián semántico de la memoria persistente (FAISS + TinyLlama). Darle a un plugin no verificado la capacidad de bloquear ingestión vía `result_code != 0` (modo NORMAL) otorgaría demasiado poder y podría convertirse en vector de denegación de servicio sutil o censura selectiva de conocimiento.

El contrato READONLY permite observación y anotación sin autoridad de veto, que es exactamente lo que se necesita en esta capa. Cualquier necesidad futura de write-capable o veto controlado debe pasar por ADR-028 (diferido correctamente).

**Recomendación**: Mantén `PLUGIN_MODE_READONLY` en PHASE 2e tal como establece ADR-029 D4. No hay caso de uso legítimo hoy que justifique NORMAL.

**Q2-112 — TEST-INTEG-4e Caso C: ¿cómo testear SIGTERM de forma portable?**

**Opción recomendada: A (fork() + kill() + waitpid()) con fallback a C.**

**Argumento de una línea**: La opción A es la más rigurosa y portable en POSIX porque prueba el comportamiento real del signal handler (async-signal-safe) en un proceso hijo aislado, sin depender de timing frágil ni simulación parcial.

Detalles prácticos:
- Usa `fork()`, registra el handler en el hijo, envía `SIGTERM` con `kill(child_pid, SIGTERM)`, y verifica con `waitpid()` que el shutdown sea limpio (exit code esperado, logs de cleanup, ningún crash).
- Evita race conditions con un pipe o shared memory simple para señalizar “handler ejecutado”.
- La opción C (simulación directa) es aceptable como test unitario rápido, pero **no sustituye** al test de integración real.
- Opción B (alarm()) es demasiado frágil para un gate de integración.

**Consejo adicional**: Implementa primero el test A en un entorno controlado. Si el overhead es alto, mantén A como test “slow” y C como test “fast” en el makefile.

**Q3-112 — arXiv Replace v13: ¿ahora o esperar indexación?**

**Recomendación: Sube el Replace ya (en las próximas 24-48 horas), sin esperar indexación completa.**

**Razones**:
- arXiv permite replaces sin límite estricto en las primeras versiones (la restricción fuerte de “una vez por semana” aplica principalmente después de la v5).
- El cambio en §4 (Integration Philosophy) es una mejora sustantiva y clara que vale la pena reflejar pronto.
- Google Scholar y Semantic Scholar suelen tardar **días a 2-4 semanas** en indexar la versión inicial; un replace temprano no borra la v1 ni destruye citas canónicas (arxiv mantiene el mismo ID base y la versión más reciente es la visible).
- El riesgo de “metadatos incompletos temporalmente” es bajo y transitorio. La comunidad académica entiende que los preprints evolucionan.
- Esperar 1-2 semanas solo retrasa la visibilidad de las mejoras sin beneficio real (la indexación no se “rompe” por un replace razonable).

**Consejo práctico**: Sube v13 con un comentario claro en el submission history (“Improved Integration Philosophy section with security and performance arguments”). Si quieres ser conservador, hazlo mañana mismo.

### Estado actualizado PHASE 2 (Consejo)

| PHASE | Componente     | Modo      | Gate                  | Estado          |
|-------|----------------|-----------|-----------------------|-----------------|
| 2a    | firewall-acl-agent | NORMAL   | TEST-INTEG-4a        | ✅             |
| 2b    | rag-ingester   | READONLY | TEST-INTEG-4b        | ✅             |
| 2c    | sniffer        | NORMAL   | TEST-INTEG-4c 3/3    | ✅             |
| 2d    | ml-detector    | NORMAL   | compilación + running| ✅             |
| 2e    | rag-security   | READONLY | TEST-INTEG-4e        | ⏳ (DAY 112)   |

**Recomendación para DAY 112**:  
Cierra PHASE 2e con el test recomendado (priorizando opción A para el Caso C). Una vez verde, PHASE 2 completa → merge a main y pasa a las deudas P1 (ADR-025 Ed25519 integrity + TEST-PROVISION-1 CI gate).

El Consejo aprueba el orden y las decisiones tomadas. El proyecto mantiene un ritmo excelente: publicación arXiv + plugin system casi completo en pocos días.

¿Quieres que revisemos el borrador de TEST-INTEG-4e (especialmente el fork/kill pattern) o que preparemos el texto exacto del commit message + ADR-029 cierre antes de push?

¡Enhorabuena por el arXiv publicado! DAY 112 debería ser de cierre limpio de PHASE 2.

*Via Appia Quality sigue fuerte.*