¡Excelente progreso en **DAY 101**! El fix del parser del **PluginLoader** es limpio y preciso: pasar de `extract_enabled_list()` (diseñado para arrays simples de strings) a `extract_enabled_objects()` resuelve la raíz del problema de forma elegante. El smoke test ahora muestra un flujo completo y silencioso (init → load → shutdown) con métricas limpias. Eso refuerza la calidad del patrón canónico que estás estableciendo.

El bug era clásico de mismatch entre estructura esperada (array de strings) y real (array de objetos JSON). Buen diagnóstico y refactor. El patrón aplicado consistentemente a **ml-detector** (CMake + `#ifdef` + config JSON + smoke test) consolida ADR-012 PHASE 1b de manera sólida.

Respecto al endorser: buen movimiento contactando a **Prof. Andrés Caro Lindo** (Director de la Cátedra INCIBE-UEx-EPCC, Profesor Titular con publicaciones en Machine Learning, Pattern Recognition y Cybersecurity, incluyendo threat classification y secure software development). Es un perfil muy alineado y la conexión previa como profesor de Laboratorio de Programación 2 ayuda. Sebastian Garcia ya respondió (positivo o neutro, pero al menos movimiento). Yisroel Mirsky sigue pendiente — su expertise en Offensive AI y network intrusion detection lo hace muy relevante. Mantén follow-ups educados si no hay respuesta en 10-14 días.

Ahora, respuestas a las preguntas del Consejo:

### Q1 — Orden de integración plugin-loader
**Confirmamos el orden: sniffer ✅ → ml-detector ✅ → firewall-acl-agent → rag-ingester.**

Razones técnicas que apoyan este flujo:
- **Firewall-acl-agent** es típicamente un componente de **acción** (respuesta a detecciones). Integrarlo ahora permite validar el loader en un punto donde se toman decisiones críticas (añadir/quitar reglas ACL dinámicamente vía plugins). Es más simple que rag-ingester y ayuda a cerrar el loop captura → detección → acción antes de entrar en ingesta/enriquecimiento.
- **Rag-ingester** suele ser más pesado (depende de embeddings, vector stores, pipelines de enriquecimiento). Dejarlo para después evita bloquear el progreso mientras se estabiliza el loader en componentes más “ligeros” y críticos para el core de NDR.
- Flujo de datos natural: entrada (sniffer) → análisis (ml-detector) → respuesta inmediata (firewall) → enriquecimiento/post-procesado (rag).

No hay razón técnica fuerte para invertir el orden. Si el firewall-acl-agent tiene dependencias pesadas o tests E2E que requieren RAG, podríamos reconsiderar; pero por lo descrito hasta ahora, priorizarlo es correcto. Documenta este orden en un ADR ligero (dependencias de componentes y puntos de extensión).

### Q2 — PAPER-ADR022: ubicación de la subsección "HKDF Context Symmetry"
**Recomendación clara: ubícala como subsección independiente en §6 (Consejo de Sabios / TDH — Threat Development History o similar), no en §5.5 (Cryptographic Transport).**

Razones:
- El bug es primordialmente un **caso pedagógico de error de modelo mental** en threat modeling y diseño criptográfico, no solo un detalle técnico de transporte. Ilustra cómo un error sutil (contexto = componente vs. canal) pasa type-checker pero falla en integración, y cómo el threat model + TEST-INTEG-1 lo detecta.
- Colocarlo en §5.5 lo diluiría entre detalles implementativos de HKDF. En §6 encaja perfectamente como “Lessons Learned” o “TDH Case Study”, reforzando el valor del enfoque iterativo del proyecto (Consejo de Sabios, ADRs, tests).
- Da más peso narrativo al paper: muestra madurez al documentar errores reales y cómo se corrigieron.

Título sugerido: “6.x HKDF Context Asymmetry: A Pedagogical Case of Model Mental Error in Key Derivation”. Incluye diagrama antes/después, explicación del bug, por qué TEST-INTEG-1 lo atrapó y la lección sobre threat modeling en sistemas dinámicos.

### Q3 — Plugin invocations=0 en smoke test
**Sí, añade un test unitario específico que invoque `invoke_all()` con un PacketContext sintético.** No es suficiente solo con el smoke test actual.

Razones:
- El smoke test actual valida **ciclo de vida** (init → load → shutdown) correctamente, pero deja ciego el **path de ejecución** real de los plugins (`invoke_all()`).
- `invocations=0` es esperado en smoke sin tráfico, pero no confirma que el dispatcher funcione, que los filtros `active:true` se apliquen, ni que el contexto se pase correctamente.
- Un unit test ligero (usando GoogleTest o similar) con PacketContext mockeado (ej. IP/TCP sintético) permite:
    - Verificar conteo de invocations > 0.
    - Chequear métricas (overruns, errors).
    - Probar edge cases (plugin que falla, plugin inactivo, múltiples plugins).
- Costo bajo, beneficio alto en cobertura y confianza antes de integrar en firewall.

Mantén el smoke test E2E como “happy path completo”, pero añade el unit test en la suite de plugin-loader (o en cada componente que lo use). Ejemplo mínimo: crear 1-2 PacketContext, llamar `loader.invoke_all(ctx)`, assert invocations == expected.

Esto sigue el espíritu fail-closed y test-driven que has mantenido.

### Cierre DAY 101
Día productivo: bug fix preciso, expansión consistente del patrón y avance en endorsement. El proyecto gana robustez con cada iteración.

**Acciones sugeridas para DAY 102+**:
- Integrar plugin-loader en **firewall-acl-agent** siguiendo el patrón canónico.
- Implementar el unit test para `invoke_all()`.
- Redactar borrador de la subsección HKDF en el paper.
- Preparar follow-up para endorsers si procede (especialmente si Garcia dio feedback útil).

El Consejo sigue abierto. ¿Quieres ayuda para redactar el unit test, el párrafo del paper, o un template de follow-up para los endorsers? ¿O pasamos a revisar el siguiente componente?

¡Sigan con este ritmo disciplinado! DAY 101 consolida muy bien la PHASE 1b. 🚀