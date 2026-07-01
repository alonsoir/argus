**✅ Revisión del ADR-058 por el Consejo (simulada).**

He leído el documento completo con atención, trazando cada afirmación a las secciones que citas. El ADR está **muy maduro**, con un nivel de rigor ("medir, no votar") superior a la media de lo que veo en proyectos reales. La estructura, el gate DAY 198 con 9 verificaciones byte-trazadas y la filosofía de equivalencia son excelentes. Aun así, identifico **defectos/riesgos** y oportunidades de endurecimiento antes de mergear e implementar esta semana.

### 1. Defectos / Riesgos Críticos (atender antes de implementación)

**1.1. Cláusula de caducidad (§3.2) débil**
- Decís correctamente que al activar `DEBT-JOIN-CONFIDENCE-001` (join no-determinista) el predicado de equivalencia se rompe por diseño.
- **Defecto**: No definís *qué* subconjunto determinista queda ni cómo se monitorizará la divergencia cuando eso ocurra.  
  **Recomendación fuerte**: Añadir al predicado una métrica de "drift rate" (porcentaje de nodos/aristas que difieren entre Camino 0 y Flujo A+B) que se exponga en Prometheus/observabilidad *desde el primer día*. Esto convierte la caducidad en algo observable, no en una bomba silenciosa.

**1.2. HMAC por fila heredado de bronce (§2.6 y §3.1)**
- Muy buena decisión.
- **Riesgo no mencionado**: ¿Qué pasa si el converter Flujo A modifica aunque sea un byte de una columna no usada en el grafo (ej. un campo de debug, un timestamp de ingestión, etc.)? El HMAC fallaría y bloquearía todo legítimamente, pero el grafo seguiría siendo semánticamente equivalente.  
  **Propuesta**: O bien (a) el HMAC se calcula solo sobre las columnas que realmente entran al grafo (whitelist explícita), o (b) se mantiene el HMAC full-row y se añade un segundo campo `hmac_graph_relevant` para el subconjunto usado en Kuzu. Prefiero (a) por simplicidad.

**1.3. flow_start_window materializado (V1)**
- Decisión correcta.
- **Defecto pequeño**: No especificás el tipo exacto y la precisión (¿`uint64_t` micros desde epoch? ¿`string` ISO? ¿`int64` con unidad explícita?). Esto afecta compresión Parquet y queries futuras.  
  **Acción**: Fijar en el ADR el tipo físico (`uint64` micros UTC) y justificar por qué no se usa `TIMESTAMP` de Parquet (coherencia con bucketing del hash).

### 2. Riesgos Importantes (P1)

- **ZMQ PUSH/PULL at-least-once (§2.5)**: Bien elegido. ¿Tenéis *back-pressure* explícito y high-water marks configurados? Si el consumidor Kuzu se atrasa, ¿el writer bronce se bloquea o tira mensajes? Definir política de *circuit breaker* o *shedding* antes de producción.
- **MERGE sin ON MATCH SET (§3.1 y V7)**: Robusto a colisiones (buen análisis). Pero implica que actualizaciones de propiedades de un flow (ej. nuevo score cuando llega más telemetría) **no se propagan**. ¿Es aceptable por ahora? Documentar explícitamente como trade-off temporal (aceptable mientras ML-head esté inerte).
- **NaN handling**: Buena guarda. Asegurarse que el converter Flujo A use el mismo patrón de quiet-NaN que C++ (no signalling-NaN). Añadir test unitario con payload que contenga NaN.

### 3. Mejoras / Clarificaciones Recomendadas

1. **Predicado de equivalencia**:
    - Añadir explícitamente que también se verifica cardinalidad total de nodos y aristas (no solo sets). Evita el caso patológico de duplicados compensados.
    - Documentar el comando exacto o script que ejecuta el diff (idealmente algo reproducible con `kuzu` CLI + scripts de hash de export).

2. **Eslabón 0 (crítico esta semana)**:
    - El watcher `inotify`/`IN_CLOSE_WRITE` es correcto pero frágil en entornos container/NFS. Considerar alternativa o complemento con polling + `stat()` mtime como fallback.
    - Escritura atómica `.tmp` → rename es correcta.

3. **Deudas**:
    - `DEBT-GOLD-INTEGRITY-HMAC-001` debería ser P0 (no P? en tu lista). Es parte del core del oro.
    - Añadir una deuda nueva: `DEBT-CIRCUIT-OBSERVABILITY-001` (métricas de latencia y throughput por etapa + lag entre bronce y Kuzu).

4. **Wazuh / host_domain_v1**:
    - La separación es correcta. Asegurarse que el contrato `DEBT-HOST-DOMAIN-CONTRACT-001` incluya `agent_id`, `ip`, `method` (dhcp/static/nat), `confidence` y `valid_from/valid_to` (bitemporalidad Kuzu).

### 4. Preguntas Rápidas al Consejo (para cerrar hoy)

- ¿Estáis cómodos con **at-least-once** + idempotencia vía MERGE, o queréis exactly-once (más complejo con ZMQ)?
- ¿El dashboard leerá directamente de Kuzu o seguirá habiendo proyecciones wide-table? (el ADR dice "proyecciones co-iguales" — confirmar que no se introduce oro oculto en dashboard).
- ¿Tenéis volumen de prueba representativo (millones de flows) para validar performance del Flujo B (Parquet→Kuzu) antes de ratificar?

### Veredicto del Consejo

**Ratifico la igualdad BIT-EXACTA por defecto** en los 3 scores double tal como propones (con ε solo como escape medida y documentada). El predicado queda sólido.

El ADR está **listo para merge** con las correcciones de sección 1 (especialmente HMAC scope y tipo de `flow_start_window`) y la observabilidad añadida. Es uno de los ADRs mejor escritos y más medidos que he revisado.

Si queréis, subid la versión con los cambios propuestos y os hago una segunda pasada rápida.

¿Implementáis Eslabón 0 esta misma semana? Puedo ayudar a revisar el código del watcher/rotation si lo abrís.

¡Buen trabajo equipo! Esto ya huele a producción.

FDO

GROK