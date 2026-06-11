Análisis del Consejo de Sabios sobre ADR-057.  
Se revisan a continuación los puntos débiles identificados, con argumentación basada en información comprobable y medible, en coherencia con el principio rector del proyecto: *medir, no votar*.

---

## 1. Viabilidad y soporte de Kuzu v0.11.3

**Debilidad crítica:**  
El ADR hace depender toda la capa de consulta de Kuzu, pero menciona “no fiarse de la doc de un repo archivado”. Si el repositorio de Kuzu está efectivamente archivado (sin mantenimiento activo), el proyecto asume un riesgo técnico alto:

- Posibles bugs no corregidos, especialmente en concurrencia o corrupción del `.kuzu`.
- Ausencia de parches de seguridad.
- Inviabilidad de escalar o migrar si el formato se vuelve obsoleto.

**Evidencia medible necesaria antes de cualquier ratificación:**
- Estado real del repositorio de Kuzu (¿archivado, mantenido, fork comunitario?).
- Prueba de regresión del comportamiento esperado (smoke test dialecto, manejo de errores, integridad tras cierre abrupto).
- Evaluación de alternativas si Kuzu demuestra no ser sostenible (por ejemplo, DuckDB con extensión de grafos, o SQLite con modelo propio, aunque se perdería Cypher nativo).

**Recomendación del Consejo:**  
No se puede asumir Kuzu como base firme sin verificar su estado de mantenimiento. El ADR debería incluir un enlace al commit exacto, licencia y plan de contingencia si el proyecto está abandonado. Esta verificación debe ser previa a cualquier otra decisión.

---

## 2. Modelo de concurrencia y acceso al fichero Kuzu

**Debilidad actual:**  
La decisión de capa *in-process* se apoya en tres argumentos: lock del `.kuzu`, regla Falco y autenticación. Sin embargo, el propio ADR reconoce que no se ha medido si Kuzu soporta un segundo proceso en modo `READ_ONLY`. El argumento del lock es, por tanto, una hipótesis, no un hecho comprobado.

Además, la regla Falco que alerta de cualquier lector externo es un control operacional que se puede adaptar de forma precisa (p. ej., excepción para un proceso lector firmado y con hash verificado), sin debilitar la seguridad si se diseña adecuadamente.

**Medición requerida:**
- Smoke test de concurrencia: ¿`Database::open(path, READ_ONLY)` desde otro proceso simultáneamente con un escritor en el engine?
- Comportamiento bajo estrés (múltiples lectores concurrentes, impacto en la escritura).
- Evaluación coste/beneficio de un servicio lector externo (operadores que solo leen) frente a acoplar toda consulta al engine.

**Recomendación:**  
La ratificación del default *in-process* debe condicionarse al resultado de estas mediciones. Si se permite `READ_ONLY`, el Consejo no ve argumentos técnicos irrefutables para cerrar la puerta a un servicio externo, especialmente si simplifica el consumo de dashboards o la integración con sistemas de monitorización. Mientras no se midan los resultados, se mantiene la incertidumbre.  
*[CONSEJO] No ratifica aún el default in-process hasta disponer de los datos de concurrencia (Fase 2, pero ésta debería ejecutarse antes de la Fase 1).*

---

## 3. Completitud de la bitemporalidad y semántica del catálogo T4

**Debilidad identificada:**  
La solución bitemporal propuesta es parcial:
- El grafo captura el *transaction-time* de primera ingestión (`ingested_at`), pero **no el estado histórico del conocimiento**.
- La consulta T4 (“Retro‑hunt de IOC”) descrita como *“devolver TODOS los flujos que lo presentan, con su flow_start_window y su ingested_at”* es útil, pero **no responde a “¿qué sabíamos a las 03:00?”**, que exigiría una foto del grafo en ese instante.
- Esa capacidad depende completamente de `DEBT-LABEL-WAL-001`, deuda abierta sin fecha de cierre.

**Verificación:**
- Revisar el enunciado exacto de T4: si el caso de uso real es solo “muéstrame los flujos conocidos hasta ahora junto con cuándo los conocimos”, entonces es correcto y debe aclararse en el ADR que no es un *point-in-time* query.
- Si se promete un *retro‑hunt* bitemporal genuino, el catálogo está sobrevendiendo una funcionalidad aún no implementada.

**Recomendación:**  
El Consejo sugiere renombrar T4 como “Visión temporal plana de flujos por comunidad” y añadir una futura plantilla T7 (dependiente del WAL) que sí ejecute reconstrucción histórica.  
*[CONSEJO] Ratifica `ingested_at` con semántica `ON CREATE SET` (coste cero ahora), pero insta a aclarar la limitación en el catálogo y a ligar explícitamente T7 a la deuda del WAL.*

---

## 4. Viabilidad del NL→plantilla con TinyLlama

**Riesgos no medidos:**
- **Clasificación de plantillas:** No se presenta ninguna métrica de precisión de TinyLlama para esta tarea. Un clasificador débil forzará rechazos en exceso o mapeará erróneamente preguntas críticas.
- **Extracción de parámetros:** El ADR indica que el modelo extraerá parámetros tipados (ej. `community_id` con formato `1:...=`). Esta tarea de *slot-filling* es significativamente más compleja que la clasificación y puede inducir errores silenciosos si el identificador es mal transcrito. La validación por tipo no detecta fallos semánticos (e.g., `community_id` legal pero incorrecto para la intención del usuario).
- **Umbral de confianza y comportamiento ante ambigüedad:** Queda a decisión del Consejo, pero sin datos es imposible establecer un umbral adecuado.

**Mediciones necesarias antes de la Fase 3:**
- Conjunto de evaluación etiquetado de ≥200 preguntas en lenguaje natural, cubriendo todas las plantillas y variaciones.
- Métricas: *accuracy* de clasificación (top-1 y top-3), *precision/recall* de extracción de parámetros clave, tasa de falsos positivos en consultas que deberían ser rechazadas.
- Prueba de estrés con *adversarial examples* (inyección de comandos, preguntas fuera de dominio) para verificar que no hay escape a Cypher libre.

**Recomendación:**  
El Consejo no puede fijar un umbral de confianza sin estos datos. Se propone un prototipo ligero en la Fase 3 con evaluación empírica y, solo tras alcanzar un acuerdo sobre métricas mínimas (p.ej., ≥95 % de top-1 exacto y extracción correcta de identificadores en ≥90 % de casos), incorporar la capa NL al flujo productivo.  
*[CONSEJO] Pospone la decisión sobre umbral y comportamiento hasta tener resultados medibles; recomienda mantener la interfaz de plantillas manual (Fase 1) como alternativa robusta mientras tanto.*

---

## 5. Firma del catálogo (Ed25519)

**Debilidad de sobre-ingeniería:**  
La firma criptográfica de las plantillas solo tiene sentido si el catálogo se carga dinámicamente desde una fuente externa o modificable. Si las plantillas se compilan dentro del binario del engine y se despliegan como parte de su integridad, la firma añade complejidad sin mejorar la seguridad (el binario ya debería estar firmado o su hash verificado).
- ¿Se prevé cargar plantillas en caliente sin recompilar?
- Si es así, el modelo de firma debe definir una cadena de confianza y revocación, no solo una clave.

**Medición:**  
Determinar si el catálogo será estático (embebido) o dinámico. Si es estático, eliminar la firma y confiar en la integridad del binario. Si es dinámico, especificar el flujo completo de actualización y verificación.

**Recomendación:**  
*[CONSEJO] Solicita aclarar el modelo de despliegue del catálogo antes de ratificar la necesidad de firma. Si no es dinámico, se elimina la complejidad; si lo es, se debe medir la latencia y la cadena de confianza, no solo mencionar ADR-025.*

---

## 6. Ordenación de fases y dependencias ocultas

**Riesgo de secuenciación:**
- La Fase 2 (smoke de concurrencia Kuzu) se coloca después de la Fase 1 (plantillas in-process). Si el smoke test demostrara que un servicio lector externo es viable y deseable, el esfuerzo de integrar las plantillas dentro del engine podría haberse malgastado.
- La Fase 4 (informe forense “a fecha de”) depende de `DEBT-LABEL-WAL-001`, que no tiene plazo. La solución bitemporal completa queda así en el aire.

**Propuesta medible:**  
Invertir el orden:
1. Smoke de concurrencia (0.5 días) y verificación de estado de Kuzu antes de escribir una sola plantilla.
2. Decidir entonces la arquitectura de consulta (in-process o servicio).
3. Implementar `ingested_at` (Fase 0) y plantillas (Fase 1) sobre la decisión firme.
4. Desarrollar el NL con prototipo medible (Fase 3).

**Recomendación:**  
*[CONSEJO] Exige que las mediciones de viabilidad de Kuzu y su concurrencia se completen antes de comprometer recursos en las Fases 1 y 3.*

---

## 7. Otros puntos de medición

- **Rendimiento de las plantillas sobre datos sintéticos representativos** (Fase 1): tiempos de respuesta, uso de memoria, explosión de vecindarios con `$n=4`. Acotación quizás insuficiente.
- **Integridad de `ingested_at`**: verificar que el reloj NTP-disciplinado del engine no tiene deriva significativa (medir con `ntpq -p` en ventanas de carga).
- **Evolución del schema**: si aparecen nuevos tipos de nodos, el catálogo y el clasificador NL requerirán actualización. Medir el coste de mantenimiento planificado.

---

## Conclusión del Consejo (sumario de puntos débiles y condiciones)

1. **Kuzu**: Se debe confirmar su estado de mantenimiento y someterlo a pruebas de estrés básicas. Sin esto, el ADR reposa sobre un cimiento incierto.
2. **Concurrencia**: El argumento del lock no está verificado; el default in‑process no puede ratificarse sin el smoke test. Se recomienda adelantarlo y, si procede, reconsiderar un servicio lector externo.
3. **Bitemporalidad**: `ingested_at` es correcto y barato ahora. La plantilla T4 debe acotar su alcance real para no prometer consultas históricas que dependen de deuda no resuelta.
4. **NL→plantilla**: Sin datos de precisión de TinyLlama en clasificación y extracción de parámetros, no se puede fijar umbral ni aprobar el diseño. Se requiere un prototipo con métricas.
5. **Firma del catálogo**: Debe justificarse con un modelo de despliegue dinámico; si el catálogo es estático, la firma sobra.
6. **Fases**: Reordenar para reducir riesgo de retrabajo: medir Kuzu/concurrencia primero, luego decidir arquitectura.

El Consejo está listo para re‑evaluar estos puntos cuando se aporten los resultados medibles solicitados.

FDO
DEEPSEEK