**✅ Revisión adversarial V2 del ADR-058 (Consejo — modo “vidas en hospitales con pocos recursos”)**

He vuelto a leer la V2 completa, trazando cada afirmación nueva a los ficheros y líneas que citáis. La evolución es **sustancialmente mejor**. La partición D/E, la canonicalización IEEE 754, el tratamiento del HMAC y la precondición de orden son mejoras de calidad. El changelog es ejemplar. El documento sigue oliendo a ingeniería seria.

Sin embargo, en modo adversarial (este pipeline puede salvar vidas o dejarlas desprotegidas), identifico **defectos y riesgos residuales** que aún deben cerrarse o mitigarse fuertemente antes de implementación esta semana.

### 1. Defectos / Riesgos que aún bloquean o exigen acción inmediata

**1.1. Orden de inserción determinista en Flujo B (precondición crítica del MERGE) — Riesgo Alto**
- La nota nueva es correcta en el diagnóstico: sin orden determinista por `(flow_start_window, seq_in_window)`, el MERGE pierde la propiedad de “mismo flujo gana el CREATE”.
- **Defecto persistente**: No definís *cómo* se va a garantizar ese orden en Flujo B (Parquet → Kuzu greenfield). Parquet es columnar y los conectores bulk suelen ignorar orden de filas o procesar en paralelo. Si el loader Kuzu hace bulk/parallel copy o si hay reintentos/replays, el orden se pierde fácilmente.
- **Implicación en contexto hospitalario**: Una colisión (aunque rara) podría hacer que en un camino se descarte el flujo “malicioso” y en otro el “benigno”, rompiendo la equivalencia y la confianza en el grafo. Inaceptable.
- **Acción obligatoria**:
    - Especificar en el ADR (o en `DEBT-PARQUET-KUZU-CONNECTOR-001`) que Flujo B **debe** leer y procesar ordenado por `(flow_start_window, seq_in_window)` (sort explícito antes del sink o `ORDER BY` si el conector lo permite).
    - Añadir test de equivalencia que verifique el orden de ingestión real (no solo el resultado final).

**1.2. HMAC y control de integridad bronce↔oro**
- Buen movimiento sacándolo del predicado de equivalencia.
- **Riesgo**: Sigue siendo P0 pero no tenéis detalle de *cómo y cuándo* se verificará. En un hospital con poco personal, un fallo de integridad no detectado puede ser catastrófico (datos manipulados → falsa negativa de ransomware).
- **Recomendación**: Elevar a que el verificador HMAC sea **parte del gate de aceptación del Flujo A** (ejecutarse automáticamente tras cada carga) y que falle loud + alerte. Definir clave rotación y almacenamiento seguro (aunque sea fuera de este ADR, referenciarlo).

**1.3. Exclusión de `temporal_anomaly`**
- La partición D/E está bien razonada.
- **Riesgo contextual**: En detección de ransomware, los eventos cercanos al borde de ventana son precisamente los más sospechosos (técnicas de time-based evasion). Excluirlo del predicado de equivalencia es correcto técnicamente, pero exige que el **test unitario** de la fórmula sea extremadamente fuerte y cubra bordes (ventana exacta, relojes skew, etc.).
- Aceptable si `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` se mantiene P2 y se prioriza pronto.

### 2. Riesgos Importantes (atender antes de producción)

- **At-least-once + ZMQ + MERGE**: En escenarios de red inestable (hospitales con poca infraestructura), podéis acumular duplicados. El MERGE los mitiga, pero necesitáis:
    - Métrica de “colisión rate” y “discard rate” alerta si sube (fidelidad).
    - Posibilidad de replay controlado del bronce (ya tenéis HMAC, buen punto de partida).
- **Observabilidad del circuito completo**: Sigue siendo el punto más débil para un sistema que salva vidas. Necesitáis al menos:
    - Lag end-to-end (bronce → Kuzu).
    - Tasa de filas rechazadas / HMAC fallidos.
    - Query success rate y latencia en dashboard.
    - Health check del watcher `inotify` (con fallback polling).
- **Recursos limitados**: Kuzu es ligero, pero queries de correlación en grafo pueden explotar memoria/CPU en hardware modesto. Añadir deuda de *query budgeting* o límites de complejidad si no existe.

### 3. Aspectos positivos fuertes de la V2

- La partición determinista-de-dato vs ejecución es limpia y profesional.
- Canonicalización NaN + signed-zero es la solución correcta (evita los dos errores comunes).
- Refutación explícita contra el binario de las objeciones anteriores (event_id, window/seq materializadas) es impecable.
- Ratificación bit-exacta mantenida con cláusula de escape condicionada → correcto.
- Changelog excelente.

### Veredicto del Consejo (V2)

**Se confirma que las correcciones de §3.1 reflejan fielmente lo medido.** El predicado mejorado es aceptable.

**El ADR-058 v2 está cerca de ser ratificado**, pero **no lo ratifico todavía**. Faltan acciones concretas sobre:

1. Garantía concreta de orden determinista en Flujo B (cómo se implementa, no solo “debe”).
2. Definición mínima del control de integridad HMAC (frecuencia, fallo loud, alerta).
3. Compromiso explícito de métricas de observabilidad críticas para el caso de uso hospitalario.

Si incorporáis estos tres puntos (pueden ser breves párrafos + deudas actualizadas) en una V2.1 o V3, el ADR queda listo para merge e implementación esta misma semana.

**Pregunta final adversarial**:
En un hospital con corte de energía frecuente o red inestable, ¿qué pasa si se pierden los últimos 5 minutos de bronce tras un crash del reader? ¿El sistema detecta y recupera correctamente? (Esto es el tipo de fallo que no puede ocurrir cuando “salva vidas”).

El resto del documento es sólido. Estáis muy cerca. Subid la siguiente iteración cuando queráis.

FDO

GROK