## DeepSeek — Retroalimentación DAY 102

Enhorabuena por completar ADR-012 PHASE 1b en todos los componentes. 25/25 tests es un nuevo récord que refleja la madurez del sistema. Respondo a las tres preguntas.

---

### Q1 — Makefile rag alignment: ¿refactorizar ahora o deuda?

**Recomendación:** **Refactorizar ahora, pero con un alcance mínimo: alinear `rag-build` al patrón estándar (cmake + `$(CMAKE_FLAGS)`) sin tocar el resto de inconsistencias.**

**Razonamiento:**
- La inconsistencia actual hace que `rag-build` ignore `PROFILE` (siempre Release) y rompe la uniformidad. En la fase previa a arXiv, es mejor que todos los componentes se construyan con el mismo mecanismo para evitar sorpresas (ej: tests de rendimiento con diferentes optimizaciones).
- El esfuerzo es pequeño (1‑2 horas) y se puede hacer como parte de DAY 103.
- Las otras inconsistencias (`rag-attach`, tests no incluidos en `test-components`, `build-unified`) son de menor prioridad; se pueden documentar como deuda técnica para PHASE 2, siempre que `make rag-build` funcione correctamente y `rag-attach` no sea necesario para los experimentos del paper.

**Acción concreta:** En DAY 103, modifica la receta `rag-build` para que use el mismo patrón que `firewall` (cmake directo con `$(CMAKE_FLAGS)`). Deja pendiente `rag-attach` y la inclusión en `build-unified` para después de arXiv, si acaso.

---

### Q2 — Estructura de §6.X (PAPER-ADR022)

**Recomendación:** La estructura propuesta es correcta y completa. El título “Pedagogical Case Study” es adecuado, pero sugiero un pequeño ajuste para reflejar que es un caso *extraído del desarrollo real*.

**Propuesta de título:**  
`6.X HKDF Context Symmetry: A Case Study in Test-Driven Hardening`

**Pequeños refinamientos:**
- En **6.X.1**, añadir una frase que explique por qué el error pasó desapercibido inicialmente (los tests unitarios de cifrado funcionaban porque usaban el mismo contexto en ambos lados; el error solo emergió en integración).
- En **6.X.3**, mencionar explícitamente que TEST-INTEG-3 es parte de la suite de regresión (CI) y que su propósito es capturar futuras regresiones en el mismo patrón.
- En **6.X.4**, añadir una frase que conecte con el valor de la metodología del Consejo: el error fue identificado por la diversidad de revisores y formalizado como test antes de la corrección.

La subsección debe ser breve (una página en el preprint), pero lo suficientemente autocontenida para que un lector entienda por qué es un ejemplo relevante.

---

### Q3 — Orden de prioridades P1 para DAY 103+

**Recomendación:**
1. **Makefile rag alignment** (1‑2h) — para que todos los componentes sigan el mismo patrón y no haya sorpresas.
2. **PAPER-ADR022 §6** (2‑3h) — es contenido del paper que debe estar afinado antes de la sumisión.
3. **BARE-METAL stress test** (1 día) — este es el único resultado empírico que falta para la versión final. Depende de disponibilidad de hardware. Si el hardware está accesible, conviene hacerlo antes de pulir detalles menores del paper, porque puede revelar nuevos cuellos de botella que modifiquen las conclusiones.
4. **PAPER-FINAL métricas DAY 102** (1h) — se puede hacer en paralelo.
5. **DOCS-APPARMOR** (2‑3d) — útil pero no bloqueante para arXiv. Se puede documentar en el paper como “work in progress” o “future work”.

**Justificación:**
- Los ítems 1 y 2 son de baja incertidumbre y rápido cierre.
- El stress test en bare-metal es el experimento que puede cambiar la narrativa del paper (cuello de botella real, rendimiento máximo). Si se demora demasiado, podría retrasar la sumisión. Idealmente, ejecútalo antes de dar por finalizado el preprint.
- Los perfiles AppArmor son valiosos para despliegue, pero no son necesarios para la aceptación en arXiv.

**Secuencia sugerida:**
- DAY 103: Makefile rag alignment + empezar PAPER-ADR022.
- DAY 104: Terminar PAPER-ADR022 y coordinar bare-metal (si el hardware está listo).
- DAY 105‑106: Ejecutar bare-metal stress test y actualizar paper con resultados.
- DAY 107: Revisión final y envío a arXiv.

---

### Comentario adicional

El nuevo test TEST-PLUGIN-INVOKE-1 es un ejemplo perfecto de la metodología TDH: se escribió para validar el contrato de invocación antes de que el plugin-loader se desplegara en todos los componentes. Eso también merece una mención en el paper (quizás en la misma subsección §6.X).

Enhorabuena por el día 102. El proyecto está en su mejor momento para la sumisión.

— DeepSeek, miembro del Consejo de Sabios