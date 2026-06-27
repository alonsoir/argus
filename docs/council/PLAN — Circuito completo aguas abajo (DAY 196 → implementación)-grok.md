**Consejo de Sabios — Respuesta adversarial (miembro crítico)**

No palmaditas. El plan tiene estructura, ambición controlada y buena higiene de deudas. Eso es lo positivo. Ahora lo duro.

### Evaluación general del plan
El enfoque “medir primero, optimizar después” (circuito verde con un motor antes de todo) es **correcto**. Optimizar ciego es la raíz de la mayoría de fracasos en estos sistemas. La separación estricta AdapterSpec (comportamiento) vs correlation_v1 (dato) también es sana y corrige el desmadre DAY 194.

**Problemas estructurales serios que veo:**

1. **Complejidad innecesaria y proliferación de capas custom.**  
   Están construyendo otro medallón Parquet/Arrow propio cuando ya existe uno en `scripts/parquet/`. La “dualidad” que documentan es una bandera roja de deuda arquitectónica. Dos pipelines de bronce→oro con reglas de centinela, tipos y validación distintas es mantenimiento caro y fuente futura de bugs sutiles.

2. **Dependencia excesiva de CSV posicional + HMAC como fuente de verdad.**  
   CSV de 19 columnas sin header es frágil. Un campo añadido o movido rompe todo downstream. El HMAC mitiga corrupción pero no migra bien. En producción real (no Vagrant), esto duele. Entiendo la decisión “JSON is the law” y bronce PRESERVA, pero el formato concreto es cuestionable.

3. **Rotación de ficheros y follow.**  
   El DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001 es más grave de lo que parece. En entornos distribuidos o con reinicios, un engine que se quede pegado a un fichero viejo es silencioso y mortal. Vigilar directorio + orden lexicográfico/temporal es obligatorio. El “lanzador recalcula” también falla si hay lag o reinicios.

4. **Wazuh y el problema del dominio mixto (flow vs host).**  
   Tienen razón en no forzar `host_key` como `community_id`. Esa mentira envenena el grafo. Pero postergar la decisión de esquema hasta antes de implementarlo es riesgoso. Si Wazuh es relevante, resuélvanlo ya o asuman que el primer circuito será incompleto.

### Respuestas directas a las preguntas del Consejo (sección 10)

**1. Formato de salida del adapter → Ratifico B.**  
Cada motor escribe `correlation_v1` a bronce. Es lo más simple y mantiene bronce como PRESERVA. El envelope protobuf era vaporware, elimínenlo formalmente en la enmienda v1.1. **Aprobado.**

**2. Forma del oro: join en Arrow vs join en Kuzu.**  
**Lean: oro-como-ledger + join en Kuzu.**  
Razones adversariales:
- Kuzu está diseñado precisamente para grafos con propiedades y joins multi-arista. Forzar el wide-table en Arrow duplica trabajo y pierde flexibilidad (Wazuh por IP, staleness diferente por fuente, detecciones múltiples sobre mismo flow).
- Reproducibilidad: el ledger Parquet por sensor es más fácil de auditar y recomputar que un mega-wide-table.
- Performance: joins en Kuzu sobre community_id (ya validado) deberían ser rápidos. Si no lo son, el problema es tamaño de datos o modelado, no la capa.
- Solo si tienen un consumidor analítico fuerte que odie grafos, consideren oro-como-join como vista materializada secundaria.

**3. Centinela numérico.**  
**-1 en CSV.** Es la menor mala opción. `0` es ambiguo (score válido, puerto 0 existe en algunos contextos). `UNKNOWN` en numérico rompe el reader actual. La semántica downstream debe ser clara: `-1` o `UNKNOWN` → `null` en Arrow + interpretación explícita en grafo (“no aplica” o “no reportado por este sensor”). Confirmado.

**4. Rotación/follow.**  
Engine vigila **directorio** y consume los ficheros más nuevos por `<source_sensor>`. El lanzador recalculando datado es frágil. Implementen un watcher simple o polling con inotify (Linux). Este punto es P0 antes de producción.

**5. Wazuh.**  
Contrato host-domain separado o `correlation_v2` con `host_key` opcional. Prefiero v2 con campo opcional + HMAC sobre columnas presentes (o HMAC null-safe). Romper el sellado de 19 columnas es inevitable si Wazuh importa. Decídanlo ahora.

**6. Andrés.**  
Stub con contrato negativo total. No contaminen el diseño principal hasta tener datos reales.

### Preguntas duras adicionales (Consejo adversario)

- **¿Por qué no usan un sistema de mensajería real (Kafka, Pulsar, o incluso NATS) para el backbone en vez de ZMQ custom everywhere?** ZMQ es excelente para low-latency punto a punto, pero el ecosistema de exactly-once, schema registry, replay, monitoring y operadores es pobre. Están reinventando mucho.
- **¿Cuál es el SLO real de staleness end-to-end?** Zeek ~5 min, Wazuh diferente, aRGus en tiempo real. Si el dashboard/Kuzu necesita consistencia, tienen un problema de ventanas temporales que no resuelven solo con community_id.
- **Error handling y backpressure.** ¿Qué pasa cuando el correlation-engine se cae o Kuzu se pone lento? ¿Los writers acumulan? ¿Los adapters bloquean? At-least-once está bien, pero sin límites de retry + DLQ van a perder datos o ahogarse.
- **Testing.** ¿Tienen golden tests para roundtrip completo correlation_v1 → Parquet → Kuzu → consulta Cypher? Sin eso, el “circuito verde” será ilusión.
- **Seguridad del HMAC.** ¿Clave rotación? ¿Por sensor? ¿Audit de quién puede escribir en bronce?

### Recomendaciones concretas antes de mergear nada
- Eslabón 0 (config JSON) primero, obligatorio.
- Terminar el medallón greenfield **mínimo viable** solo para aRGus.
- Validar E2E con datos sintéticos + inyección de fallos (HMAC malo, campos faltantes, rotación).
- Documentar explícitamente las dos capas Parquet (RAG vs Correlación) y por qué coexisten.
- Abrir las deudas como issues antes de escribir código.

El plan es viable pero huele a “construimos nuestro propio mini-data-mesh”. Asegúrense de que la complejidad añadida realmente compre valor medible (el microscopio del que hablan) y no solo más código bonito.

El Consejo espera ver evidencias de las verificaciones §8 y el circuito verde con aRGus antes de aprobar el resto. Sin eso, es solo papel.

Próxima ronda cuando tengan mediciones reales. Sin piedad.

FDO

GROK