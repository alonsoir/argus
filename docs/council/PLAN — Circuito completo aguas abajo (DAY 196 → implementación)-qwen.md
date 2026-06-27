# CONSEJO DE SABIOS — REVISIÓN ADVERSARIAL PLAN DAY 196

**Estado:** Borrador bajo escrutinio  
**Postura:** Adversarial (no se ratifica sin responder objeciones)  
**Fecha escrutinio:** 2026-06-27

---

## OBJECIONES PRINCIPALES AL PLAN

### 1. **Falsa dicotomía "patrón conocido" vs "greenfield" (§7, Eslabón 1)**

El plan afirma que el medallón de correlación es *greenfield* pero reutiliza *patrones* del pipeline RAG-127. Esto es una contradicción operativa:

- **RAG-127:** firma Ed25519, CSV de 127 columnas, sin `community_id`, sin zonas bronce/plata/oro.
- **Correlation_v1:** firma HMAC-SHA256, CSV de 19 columnas, `community_id` es la clave de join, requiere zonas LZ.

**Pregunta adversarial:** ¿Qué código concreto del RAG-127 es *realmente* reutilizable sin reescritura sustancial? Si la respuesta es "solo el esqueleto `validate_roundtrip`", entonces no es reutilizar patrones, es copiar la *idea* de un test. Eso no reduce el esfuerzo de implementación en un orden de magnitud como sugiere el tono del plan.

**Exigencia:** Lista explícita de funciones/clases del RAG-127 que se importarán *tal cual* vs las que se reescribirán. Sin esto, el Eslabón 1 es una estimación de esfuerzo inflada por optimismo.

---

### 2. **Oro-como-ledger: costo de rendimiento no cuantificado (§10.2)**

El plan favorece "oro-como-ledger + join en Kuzu" citando Via Appia y reproducibilidad. Correcto en principio, pero:

- Kuzu hace join por `community_id` al materializar el grafo.
- Si hay 10M de filas en oro (aRGus + Suricata + Zeek), cada una con su `community_id`, Kuzu debe:
    1. Parsear parquet.
    2. Crear/actualizar nodos `:NetworkFlow` por `community_id`.
    3. Crear aristas `:Detection` desde cada sensor.
    4. Resolver duplicados (mismo flujo visto por múltiples sensores).

**Pregunta adversarial:** ¿Cuál es el throughput esperado de ingesta en Kuzu? Si el circuito debe procesar 100K eventos/segundo (escenario realista para Suricata+Zeek en red enterprise), ¿Kuzu aguanta el join en tiempo real, o se convierte en un batch nocturno?

**Exigencia:** Benchmark de ingesta Kuzu con dataset sintético de 1M filas con 500K `community_id` únicos. Si el throughput es <10K eventos/seg, el diseño "oro-como-ledger" obliga a arquitecturar un buffer intermedio (Kafka/Redis) que el plan no menciona.

---

### 3. **Centinela -1: ambigüedad en edge cases (§5, §10.3)**

El plan propone `-1` para numéricas ausentes, argumentando que `0` es ambiguo. Pero `-1` también lo es:

- `flow_start_sec = -1`: ¿timestamp negativo? ¿error de parsing?
- `src_port = -1`: ¿puerto no aplica (ICMP) o error?
- `ml_detector_score = -1`: ¿score negativo válido (modelo que permite negativos) o ausente?

**Pregunta adversarial:** ¿El reader C++ (`correlation_reader.parse_and_verify`) distingue entre `-1` como centinela y `-1` como valor legítimo? Si no, el centinela envenena el espacio de valores.

**Exigencia:** Especificar qué campos *nunca* pueden ser `-1` legítimamente (ej: `src_port` en TCP/UDP siempre ≥0) y cuáles *sí* (ej: `ml_detector_score` si el modelo produce negativos). Para los segundos, el centinela debe ser otro valor (ej: `NaN` en float, o un bitmask en int).

---

### 4. **Wazuh: decisión de esquema diferida sin plan de contingencia (§4, §10.5)**

El plan identifica que Wazuh no cabe en `correlation_v1` (sin `host_key`) y propone dos opciones:
- (a) Extender a `correlation_v2` (rompe sellado de 19 columnas).
- (b) Contrato host-domain aparte con sink propio.

Pero no evalúa el costo de (b): dos esquemas paralelos, dos pipelines de ingesta, dos conjuntos de tests, dos documentos de contrato. Esto es deuda arquitectónica, no solución.

**Pregunta adversarial:** ¿Por qué no extender `correlation_v1` a 20 columnas (añadir `host_key` como col 19, HMAC recalculado sobre 0-18)? El "sellado de 19 columnas" es una convención, no una ley física. Romperla ahora (con un solo motor host-domain) es más barato que mantener dos esquemas para siempre.

**Exigencia:** Análisis de costo-beneficio: (a) `correlation_v2` de 20 columnas vs (b) contrato host-domain separado. Incluir: esfuerzo de implementación, esfuerzo de mantenimiento a 12 meses, riesgo de desync entre esquemas.

---

### 5. **ZMQ PUB/SUB: riesgos de slow-joiner y backpressure no mitigados (§7.1, §9)**

El plan cita la regla slow-joiner (PUB `bind()` antes que SUB `connect()`) pero no aborda:

- **Message loss en slow-joiner:** Si el SUB se conecta tarde, pierde los primeros mensajes. ¿Cómo se garantiza at-least-once (§3.1)?
- **Backpressure:** Si el engine consume más lento de lo que los adapters producen, el buffer de ZMQ crece sin límite. ¿Hay HWM (high-water mark)? ¿Qué pasa cuando se satura?
- **Reconexión:** Si el engine cae y se reinicia, ¿los adapters reenvían eventos pendientes, o se pierden?

**Pregunta adversarial:** El plan dice "transporte interno SIEMPRE ZeroMQ PUB/SUB con regla slow-joiner" pero no especifica cómo se resuelve at-least-once en un transporte que *por diseño* puede perder mensajes. ¿Hay un mecanismo de ack/retry, o se asume que la pérdida es aceptable?

**Exigencia:** Especificar: (a) HWM en PUB y SUB; (b) estrategia de reconexión (¿replay desde checkpoint?); (c) qué pasa si se pierde un evento (¿se detecta por gap en `native_event_id`? ¿se alerta?).

---

### 6. **Rotación de ficheros: soluciones propuestas tienen trade-offs ocultos (§9, §10.4)**

El plan identifica el problema (writer rota diario, engine sigue un fichero) y propone dos opciones:
- (a) Engine vigila directorio (sigue el fichero más nuevo).
- (b) Lanzador recalcula path datado.

Pero no evalúa:
- **(a) Race condition:** Si el writer está escribiendo en `2026-06-27.csv` y el engine lo lee, ¿qué pasa si a medianoche el writer rota a `2026-06-28.csv`? ¿El engine pierde los últimos eventos del día anterior, o los lee dos veces?
- **(b) Acoplamiento:** El lanzador debe conocer la lógica de rotación del writer. Si el writer cambia a rotación horaria, el lanzador debe actualizarse.

**Pregunta adversarial:** ¿Por qué no usar un mecanismo estándar como `inotify` (Linux) o `ReadDirectoryChangesW` (Windows) para que el engine detecte nuevos ficheros sin polling? O mejor: ¿por qué no eliminar la rotación diaria y usar un único fichero con append, truncado por tamaño (logrotate)?

**Exigencia:** Evaluar tres opciones: (a) engine vigila directorio con `inotify`; (b) lanzador recalcula path; (c) fichero único con rotación por tamaño. Incluir: complejidad de implementación, riesgo de pérdida de eventos, acoplamiento entre componentes.

---

### 7. **Andrés stub: contrato negativo sin mecanismo de resolución (§4, §10.6)**

El plan mantiene a Andrés como stub con "contrato negativo" (5 incógnitas pendientes). Pero no especifica:
- ¿Quién es responsable de resolver las incógnitas?
- ¿Hay un deadline para resolverlas, o el stub puede permanecer indefinidamente?
- ¿Qué mecanismo asegura que, cuando Andrés tenga datos reales, el stub se reemplace con un adapter real?

**Pregunta adversarial:** Un stub con "contrato negativo" es deuda técnica que se olvida. ¿Qué garantía hay de que no se convierta en un "TODO: resolver Andrés" que permanece en el código por 2 años?

**Exigencia:** Asignar ownership (¿equipo de Andrés? ¿equipo de plataforma?), deadline (¿Q3 2026?), y mecanismo de tracking (¿ticket en Jira? ¿issue en GitHub?). Si no hay ownership ni deadline, el stub debe eliminarse del plan hasta que haya datos reales.

---

### 8. **Dashboard de consulta: especificación incompleta (§7, Eslabón 3)**

El plan menciona "Cypher primero; NL-only admin después" pero no especifica:
- ¿Qué tecnología? (Neo4j Browser, custom web app, CLI?)
- ¿Qué SLA de consulta? (¿<1s para queries simples? ¿<10s para joins complejos?)
- ¿Quién construye el dashboard? (¿equipo de plataforma? ¿equipo de producto?)
- ¿Qué queries debe soportar? (¿listar flujos por community_id? ¿buscar amenazas por IP? ¿retro-hunt histórico?)

**Pregunta adversarial:** Un dashboard sin especificación es un scope creep garantizado. ¿Cómo se mide el éxito del Eslabón 3 si no hay criterios de aceptación?

**Exigencia:** Especificar: (a) tecnología (recomendación: Neo4j Browser para MVP, custom app después); (b) 5 queries críticas que debe soportar el MVP; (c) SLA de consulta (p95 < 2s); (d) ownership (equipo de plataforma).

---

## RESPUESTAS A LAS PREGUNTAS DEL §10

### 1. **A vs B (formato de salida del adapter): Ratificado con condición**

**Decisión:** B (cada motor escribe `correlation_v1` a bronce).  
**Condición:** El plan debe especificar cómo se garantiza que todos los adapters producen `correlation_v1` compatible. ¿Hay un test de conformidad (contract test) que valide que un adapter nuevo produce filas válidas? Si no, el "contrato" es solo documentación, no verificación.

**Exigencia:** Implementar `adapter-conformance-test` que: (a) genera 100 eventos sintéticos; (b) los pasa por el adapter; (c) valida que la salida es `correlation_v1` válido (19 columnas, HMAC correcto, centinelas correctos). Sin este test, no se puede afirmar que el contrato se respeta.

---

### 2. **Forma del oro: oro-como-ledger con benchmark obligatorio**

**Decisión:** Oro-como-ledger + join en Kuzu.  
**Condición:** Benchmark de ingesta Kuzu (ver objeción 2). Si el throughput es <10K eventos/seg, el diseño debe revisarse para incluir un buffer intermedio.

---

### 3. **Centinela numérico: -1 con excepciones documentadas**

**Decisión:** `-1` para numéricas ausentes, **excepto**:
- `ml_detector_score` / `fast_detector_score` / `overall_threat_score`: si el modelo produce negativos, el centinela es `NaN` (float) o un valor fuera de rango (ej: `-9999.0`).
- `flow_start_sec` / `flow_start_nano`: si el timestamp puede ser negativo (edge case), el centinela es `0` (asumiendo que `0` no es un timestamp válido en este contexto).

**Exigencia:** Documentar en el contrato `correlation_v1` qué campos permiten valores negativos legítimos y cuál es su centinela.

---

### 4. **Rotación/follow: engine vigila directorio con inotify**

**Decisión:** Engine vigila directorio con `inotify` (Linux) para detectar nuevos ficheros.  
**Razón:** Elimina el acoplamiento con el lanzador y evita race conditions (el engine solo lee ficheros que el writer ha cerrado).

**Exigencia:** Implementar `inotify` con filtro `IN_CLOSE_WRITE` (solo notifica cuando el writer cierra el fichero, no cuando lo abre). Fallback a polling (1s) si `inotify` no está disponible.

---

### 5. **Wazuh: correlation_v2 de 20 columnas**

**Decisión:** Extender `correlation_v1` a 20 columnas (añadir `host_key` como col 19, HMAC recalculado sobre 0-18).  
**Razón:** Más barato mantener un esquema de 20 columnas que dos esquemas paralelos. El "sellado de 19 columnas" es una convención, no una ley.

**Exigencia:** Implementar migración: (a) writer produce `correlation_v2` (20 columnas); (b) reader acepta tanto v1 (19 cols) como v2 (20 cols) por `schema_version` (col 0); (c) HMAC se recalcula sobre 0-18 en v2.

---

### 6. **Andrés: eliminar stub hasta que haya datos reales**

**Decisión:** Eliminar a Andrés del plan hasta que haya repo/datos.  
**Razón:** Un stub sin ownership ni deadline es deuda técnica que se olvida. Cuando Andrés tenga datos reales, se re-introduce en el plan con contrato definido.

**Exigencia:** Cerrar el ticket de Andrés. Cuando el equipo de Andrés tenga datos reales, abre un nuevo ticket con: (a) naturaleza del motor; (b) transporte; (c) presencia de `community_id`; (d) clave de join; (e) staleness SLO.

---

## VERIFICACIONES PENDIENTES OBLIGATORIAS (§8)

Antes de implementar cualquier eslabón, el plan debe resolver:

1. **[POR VERIFICAR] §8.1:** ¿El converter RAG-127 está en uso en producción?  
   **Acción:** Ejecutar `ps aux | grep generate_parquet` y revisar logs de cron/systemd. Si está en uso, el Eslabón 1 debe coordinarse con el equipo de RAG para no romperlo.

2. **[POR VERIFICAR] §8.2:** ¿Writer y reader resuelven al mismo path?  
   **Acción:** Ejecutar los comandos `grep` propuestos y validar que `bronze_root` en JSON coincide con `--bronze` en el engine. Si no, el Eslabón 0 debe incluir un test de integración que falle si los paths no coinciden.

3. **[POR VERIFICAR] §8.3:** ¿De qué lee Kuzu hoy?  
   **Acción:** Revisar `correlation-engine/src/main.cpp` para confirmar que no hay una segunda ruta de ingesta. Si la hay, el Eslabón 2 debe re-apuntar ambas rutas al medallón.

---

## CONCLUSIÓN DEL CONSEJO

**Estado del plan:** **NO RATIFICADO** — requiere responder las 8 objeciones principales y las 6 exigencias de las preguntas del §10.

**Próximos pasos:**
1. Resolver las 3 verificaciones pendientes (§8).
2. Responder las 8 objeciones con evidencia (benchmarks, análisis de costo-beneficio, especificaciones).
3. Re-someter al Consejo con las respuestas incorporadas.

**Advertencia:** El plan tiene buena estructura y separación de responsabilidades, pero subestima la complejidad de:
- Implementar un medallón LZ desde cero (no es "reutilizar patrones").
- Hacer join en Kuzu a alto throughput (requiere benchmark).
- Migrar de FS-drop a ZMQ PUB/SUB sin perder eventos (requiere mecanismo de ack/retry).

Sin resolver estos puntos, el "circuito verde" será verde en el papel, pero rojo en producción.

---

**Firmado:**  
*Consejo de Sabios — División de Escrutinio Adversarial*  
*2026-06-27*

FDO

QWEN