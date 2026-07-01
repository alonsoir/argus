He analizado la V2 del ADR-058 con el rigor que merece el contexto (salvar vidas en hospitales con pocos recursos). Las correcciones medidas son sólidas, pero persisten defectos críticos que deben resolverse antes de implementación.

---

## **DEFECTOS CRÍTICOS (P0) — Bloqueantes para implementación**

### 1. **Precondición de orden determinista NO verificada contra el binario**

**Sección afectada:** §3.1, nota "Precondición de la robustez"

**El problema:** El ADR afirma que "Flujo B inserta en orden determinista por `(flow_start_window, seq_in_window)` antes del sink Kuzu" y que "el test de equivalencia asume y verifica esta precondición". **Pero no hay medición que lo demuestre.**

**Por qué es crítico:**
- Camino 0 procesa el CSV bronce en **orden de líneas** (ifstream secuencial)
- Si el CSV bronce **no está ordenado** por `(window, seq)`, entonces Camino 0 y Flujo B procesan en órdenes **distintos**
- Ante colisión de `flow_uid`, **flujos diferentes ganan el `ON CREATE SET`** en cada camino
- El predicado de equivalencia **rompe por arquitectura, no por bug del converter**

**Acción requerida (medir, no votar):**
```bash
# Verificar si el bronce actual está ordenado
head -n 10000 bronze.csv | awk -F',' '{print $5, $6}' | sort -c
```
- Si **está ordenado**: documentar la precondición como invariante del contrato bronce (no solo del Flujo B)
- Si **no está ordenado**: el Flujo B debe aplicar `sort` antes del sink, **y** el test debe verificar que ambos caminos producen el mismo orden de inserción
- En ambos casos: añadir verificación automática en CI que falle si el bronce diverge del orden esperado

**Sin esta medición, la "robustez a colisión" es una afirmación no verificada.**

---

### 2. **Punto de canonicalización NaN/`-0.0` no especificado**

**Sección afectada:** §3.1, nota "Guarda de comparación"

**El problema:** El ADR dice "ambos caminos deben canonicalizar **antes** de comparar" pero **no especifica dónde** ocurre la canonicalización:
- ¿En el converter Flujo A (al escribir AVRO/Parquet)?
- ¿En el conector Parquet→Kuzu (al leer)?
- ¿En el test de equivalencia (al comparar)?
- ¿En los tres puntos?

**Por qué es crítico:**
- Si solo se canonicaliza en el **test**, el grafo Kuzu contendrá valores **no-canónicos** (NaN con payloads arbitrarios, `-0.0` y `+0.0` mezclados)
- Si se canonicaliza en el **converter**, se pierde información (¿importa distinguir signaling vs quiet NaN para debugging?)
- Si se canonicaliza en **ambos**, hay duplicación de lógica y riesgo de divergencia

**Acción requerida:**
- Especificar el punto único de canonicalización (recomendación: **converter Flujo A**, al escribir AVRO)
- Documentar que el test asume grafos ya canónicos (no canonicaliza al comparar)
- Añadir test unitario que verifique: mismo input → mismo patrón canónico en AVRO
- Decisión explícita: ¿se preservan los payloads de NaN o se colapsan a un único patrón? (Para hospitales, recomiendo colapsar: simplifica debugging)

**Sin esta especificación, "una sola regla canónica" es una intención, no un diseño.**

---

### 3. **Estrategia de testing del predicado no especificada**

**Sección afectada:** §3.1 (predicado completo)

**El problema:** El predicado de equivalencia es complejo (sets, propiedades, aristas, bit-exacto en doubles), pero **no hay plan de testing**:
- ¿Qué framework? (pytest + hypothesis? Google Test? Custom?)
- ¿Qué dataset? (golden data? generado? edge cases?)
- ¿Cuánto tarda? (¿ejecutable en CI?)
- ¿Qué cobertura? (¿100% de columnas? ¿solo críticas?)

**Por qué es crítico:**
- "Medir, no votar" exige que el test sea **ejecutable y repetible**
- Sin estrategia, el test puede ser frágil, lento, o no cubrir casos críticos (ICMP, NaN, colisiones)
- Para hospitales, el test debe ser **confiable**: no puede fallar por flaky tests

**Acción requerida:**
- Añadir sección §3.3 "Estrategia de testing" con:
    - Framework: pytest + pandas (para manipulación de grafos) + hypothesis (property-based)
    - Dataset: golden data de 1000 flujos (incluyendo edge cases: ICMP, NaN, colisiones)
    - Criterio: 100% de coincidencia en propiedades D (determinista-de-dato)
    - Performance: < 5 min para 1000 flujos (ejecutable en CI)
    - Edge cases: test específico para colisión `flow_uid` (verificar que ambos caminos descartan el mismo flujo)

**Sin esta estrategia, el predicado es una especificación no verificable.**

---

## **DEFECTOS IMPORTANTES (P1) — Críticos en contexto de hospitales**

### 4. **Recovery ante fallos no especificado**

**Contexto:** Hospitales con pocos recursos → hardware limitado, operadores no expertos, alta disponibilidad requerida.

**El problema:** No hay mención de:
- ¿Qué pasa si Kuzu se corrompe?
- ¿Qué pasa si el circuito falla a mitad de procesamiento?
- ¿Se puede reconstruir el grafo desde el oro-ledger?
- ¿Hay backup/restore?

**Por qué es crítico:**
- Si el grafo se corrompe y no hay recovery, el dashboard queda ciego
- Para hospitales, esto puede significar **no detectar un ataque en curso**
- Operadores no expertos necesitan procedimientos claros

**Acción requerida:**
- Añadir sección §10 "Recovery y continuidad" con:
    - Procedimiento de reconstrucción: oro-ledger → Flujo B → Kuzu (idempotente por MERGE)
    - Backup automático del grafo Kuzu (snapshot diario)
    - Procedimiento de restore: documentado y probado
    - Test de recovery: ejecutar en CI (corromper Kuzu, reconstruir, verificar equivalencia)

---

### 5. **Observabilidad no especificada**

**Contexto:** Operadores no expertos necesitan monitoreo simple.

**El problema:** No hay mención de:
- Métricas del circuito (throughput, latency, error rate)
- Alertas por fallos (reader caído, writer lento, ZMQ queue llena)
- Logs estructurados para debugging

**Por qué es crítico:**
- Sin observabilidad, los fallos pasan desapercibidos hasta que causan impacto
- Para hospitales, la detección temprana de fallos es crucial

**Acción requerida:**
- Añadir sección §11 "Observabilidad" con:
    - Métricas: Prometheus + Grafana (throughput, latency, queue depth)
    - Alertas: umbral de error rate > 1%, queue depth > 1000, latency > 1s
    - Logs: estructurados (JSON), con `flow_uid` para tracing
    - Dashboard: health check del circuito (verde/amarillo/rojo)

---

### 6. **Performance requirements no especificados**

**Contexto:** Hospitales con hardware limitado.

**El problema:** No hay mención de:
- ¿Cuántos flujos/segundo debe soportar?
- ¿Cuál es la latencia aceptable (bronce → dashboard)?
- ¿Cuánto tarda el test de equivalencia?

**Por qué es crítico:**
- Si el circuito es más lento que la generación de flujos, se acumulan colas
- Para detección en tiempo real, la latencia debe ser acotada
- Hardware limitado exige optimización

**Acción requerida:**
- Añadir sección §12 "Performance" con:
    - Throughput mínimo: 1000 flujos/segundo (ajustar según caso de uso)
    - Latencia máxima: < 5s (bronce → dashboard)
    - Test de carga: ejecutar en CI con dataset de 100k flujos
    - Benchmark: medir en hardware objetivo (¿ARM? ¿x86 de bajo costo?)

---

## **DEFECTOS SECUNDARIOS (P2) — Importantes pero no bloqueantes**

### 7. **Backpressure en ZMQ diferido**

**Sección afectada:** §6, deuda `DEBT-ZMQ-DELIVERY-GUARANTEE-001`

**El problema:** Se declara "gold-plating" y se difiere, pero para hardware limitado, el backpressure es **crítico**:
- Sin HWM (high-water mark), ZMQ puede consumir memoria ilimitada
- Sin política de drop/block, el sistema puede colapsar bajo carga

**Acción requerida:**
- Especificar HWM mínimo (ej: 10000 mensajes)
- Especificar política: block (no drop) para garantizar at-least-once
- Documentar que esto se implementa en Eslabón 1 (no greenfield)

---

### 8. **Portabilidad de inotify diferida**

**Sección afectada:** §5 (Eslabón 0)

**El problema:** `inotify` es Linux-only. Para despliegues en contenedores con volúmenes NFS/SMB, no funciona.

**Acción requerida:**
- Documentar limitación: "requiere Linux con filesystem local"
- Proveer fallback: polling con `stat()` cada 1s (más lento, pero portable)
- O restringir explícitamente el despliegue: "solo Linux + ext4/xfs"

---

## **RECOMENDACIÓN AL CONSEJO**

**No ratificar aún.** La V2 es mejor que la V1, pero los defectos P0 son bloqueantes:

1. **Precondición de orden determinista**: medir contra el binario (¿el bronce está ordenado?)
2. **Punto de canonicalización**: especificar dónde ocurre
3. **Estrategia de testing**: añadir §3.3 con framework, dataset, criterios

**Acción propuesta:**
- Resolver P0 con 1 día de trabajo (mediciones + documentación)
- Resolver P1 con 2 días adicionales (recovery, observabilidad, performance)
- Re-someter a ratificación con estos puntos cerrados

**El ADR está ~90% completo.** Con 3 días de trabajo adicional, puede quedar sólido para implementación. El contexto de hospitales con pocos recursos no permite improvisar: cada defecto no resuelto es un riesgo para pacientes.

**Nota final:** Las objeciones de "gold-plating" (schema evolution, key management, RBAC, retention, rollback) se declinan correctamente en este ADR. No son defectos del circuito, sino trabajo post-FEDER. Pero los P0/P1 que identifico **sí son del circuito** y deben resolverse ahora.

FDO

QWEN