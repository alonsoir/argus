## Respuesta del Consejo de Sabios – Acta DAY 111 (8 Abril 2026)

El Consejo ha recibido y revisado el informe de DAY 111, incluyendo los hitos alcanzados (publicación arXiv, FIX-C, FIX-D, TEST-INTEG-4c, PHASE 2d, ADR-029). Se emiten las siguientes respuestas a las preguntas planteadas para DAY 112.

---

### **Q1-112 – PHASE 2e: ¿READONLY es correcto?**

**Veredicto del Consejo:** **Sí, READONLY es definitivamente correcto.** Unanimidad (7/7).

**Argumentación:**

- **Rol de rag-security:** Es el guardián de la memoria semántica (TinyLlama + FAISS). Cualquier plugin que pueda bloquear la ingestión (via `result_code != 0`) interrumpiría el LLM local, un componente crítico para la detección contextual.
- **Principio de mínima autoridad:** Los plugins no verificados no deben tener poder para degradar el núcleo del sistema. READONLY permite observación y auditoría, pero no interferencia.
- **Alineamiento con ADR-028:** El caso “write-capable” está diferido explícitamente a post-PHASE 2. READONLY en 2e mantiene coherencia con esa decisión.
- **Excepción potencial:** Un plugin que implemente *filtrado colaborativo* (ej. bloquear eventos ya conocidos como benignos) podría argumentar necesidad de `result_code != 0`. Sin embargo, ese filtrado debe hacerse en capas anteriores (firewall, sniffer) o mediante un plugin específico que opere en modo NORMAL sobre el flujo de eventos *antes* de llegar a rag-security. El Consejo recomienda documentar esta limitación en ADR-029 como decisión arquitectónica.

**Conclusión:** Mantener READONLY. Si en el futuro surge un caso de uso legítimo, se evaluará mediante un nuevo ADR.

---

### **Q2-112 – TEST-INTEG-4e Caso C: testeo portable de SIGTERM**

**Veredicto del Consejo:** **Opción A (fork + kill + waitpid) es la recomendada.** Mayoría cualificada (6/7, una abstención por complejidad).

**Análisis comparativo:**

| Opción | Ventajas | Desventajas | Veredicto |
|--------|----------|-------------|------------|
| **A (fork+kill)** | Portable POSIX, testea el signal handler real, control preciso del timing (puedes enviar SIGTERM en un momento conocido del procesamiento). | Algo más de código, requiere manejo de procesos hijos y pipes para sincronización. | ✅ **Recomendada** |
| **B (alarm)** | Simple, no forks. | Frágil: el tiempo de procesamiento puede variar, causando falsos positivos. No garantiza que el handler se ejecute durante una operación crítica. | ❌ No robusta para CI. |
| **C (simular shutdown directo)** | Muy simple, no señales reales. | No prueba el signal handler real; solo prueba la lógica de `g_plugin_loader->shutdown()`. Deja sin verificar la parte async-signal-safe. | ❌ Insuficiente. |

**Recomendación detallada (Opción A):**

1. En el test, hacer `fork()`.
2. El hijo: llama a la función que ejecuta rag-security (o el pipeline completo) en un bucle que procesa eventos.
3. El padre: espera una señal de que el hijo ha comenzado (ej. pipe o semáforo), luego `kill(child_pid, SIGTERM)`, y finalmente `waitpid()` para obtener el código de salida.
4. Verificar que el hijo termina limpiamente (exit code 0 o shutdown graceful) y que no quedan recursos colgados.
5. Opcional: usar `clock_nanosleep` con tiempo suficiente para que el hijo alcance un estado estable antes de enviar la señal.

**Nota adicional:** El test debe ejecutarse solo en plataformas POSIX. En Windows (fuera del objetivo de aRGus NDR) se puede omitir o usar un equivalente con eventos. Para CI (Linux/macOS) es completamente portable.

**Abstención:** Gemini considera que la opción A es correcta pero pide documentar que `fork()` no es async-signal-safe en el test (el test no es un signal handler, no hay problema). Se añade esa nota al acta.

---

### **Q3-112 – arXiv Replace v13: ¿ahora o esperar indexación?**

**Veredicto del Consejo:** **Se puede subir ya sin riesgo significativo.** Unanimidad (7/7).

**Justificación:**

- **Indexación canónica:** arXiv asigna un identificador permanente (2604.04952) y una fecha de versión original. El Replace mantiene el mismo ID y añade una nueva versión con su fecha. Los servicios de indexación (Google Scholar, Semantic Scholar) suelen actualizar los metadatos al detectar una nueva versión, especialmente si el título y autores no cambian.
- **Riesgo bajo:** La ventana de 5 días desde la publicación (3 Abr → 8 Abr) es suficiente para que los crawlers hayan registrado la v1. Subir v13 ahora no “pierde” la cita; simplemente añade una versión mejorada.
- **Recomendación de buenas prácticas:** Muchos autores suben reemplazos en cuestión de días después de la primera versión. Lo importante es incluir en el campo "Comments" o en el abstract un aviso del tipo “v2: expanded Section 4 with integration philosophy”.
- **Si se desea máxima prudencia:** Esperar 1 semana (hasta 10 Abril) no perjudica. Pero el Consejo considera que no es necesario. El trabajo ya está respaldado por DOI y el repositorio Git.

**Conclusión:** **Subir Replace ahora mismo.** Si algún miembro prefiere esperar por seguridad, puede hacerlo por su cuenta, pero la decisión colectiva es proceder.

---

## Resoluciones del Consejo para DAY 112

| Pregunta | Decisión | Acción requerida |
|----------|----------|------------------|
| Q1-112 | READONLY es correcto | Mantener ADR-029 D4; documentar excepción futura. |
| Q2-112 | Opción A (fork+kill) | Implementar TEST-INTEG-4e Caso C con fork/waitpid. |
| Q3-112 | Subir Replace v13 ahora | Ejecutar `arxiv_replace.sh` o el procedimiento estándar. |

---

## Notas adicionales

- **Felicidades por arXiv:2604.04952.** El Consejo reconoce el hito y agradece la mención explícita.
- **ADR-029** queda formalmente aprobado y cerrado. Se debe pushear al commit 58d73c04.
- **PHASE 2e (rag-security)** puede comenzar en DAY 112 siguiendo las directrices de READONLY y el patrón de global signal-safe definido en ADR-029.
- **Recordatorio de deuda:** Poner atención a `TEST-PROVISION-1` y `REC-2` para evitar incidentes de ficheros vacíos.

El Consejo queda a la espera del acta DAY 112 o de cualquier consulta urgente.

*Via Appia Quality · Un escudo, nunca una espada.*  
*Acta redactada por Claude, refrendada por Grok, ChatGPT5, DeepSeek, Qwen, Gemini, Parallel.ai – 8 Abril 2026*