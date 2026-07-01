# Revisión adversarial ADR-058 v2

**Modo:** adversario. **Supuesto operativo:** este pipeline detecta ransomware en hospitales con pocos recursos. Un falso negativo mata. Un falso positivo desvía recursos críticos de la UCIs. La cadena de custodia del dato desde el sensor hasta el dashboard no admite puntos ciegos.

**Resumen ejecutivo:** La v2 es una mejora sustancial sobre la v1. La partición D/E, la guarda canónica NaN/-0.0, la reubicación del HMAC y las refutaciones contra el binario son trabajo de primera categoría. No obstante, he identificado **2 puntos que necesitan resolución antes de sellar** y **4 puntos que no bloquean pero que en un contexto de vida o muerte merecen traza explícita en este ADR** (no en deuda futura — aquí, donde el siguiente implementador los va a leer).

---

## Bloqueantes (requieren resolución antes de sellar)

### B1. Bit-exacto en doubles asume mismo parser text→double — y el converter es greenfield con lenguaje sin especificar

**Dónde:** §3.1, nota de igualdad de scores.

**El ADR dice:** *"ambos caminos parten del mismo double — el de parse_double sobre el mismo bronce CSV (Camino 0 y Flujo A leen el mismo texto; la degradación texto→double, si la hay, es idéntica en ambos y se cancela en el predicado)"*.

**El problema:** Esta afirmación es cierta SOLO si ambos caminos usan la misma implementación de parsing texto→double. Camino 0 usa C++ (`correlation_reader.cpp` con `std::from_chars` / `locale::classic()`). El converter Flujo A es **greenfield** — su lenguaje no está especificado en este ADR. La propia nota de encoding dice *"si es Python, los vectores golden congelados"* admitiendo que Python es una posibilidad real.

Si el converter es Python:
- C++ `std::from_chars` garantiza *correct rounding* (C++17, IEEE 754).
- Python `float()` delega a `PyOS_string_to_double` → `strtod()` del C library del sistema, que **no siempre** implementa correct rounding (depende de la libc — musl sí, glibc histórico no en todos los bordes).
- Resultado: para ciertos valores en los bordes de precisión (subnormales, cadenas con >17 dígitos significativos), ambos lados pueden producir bit patterns distintos a partir del mismo texto. El predicado `==` falla **sin que exista bug en el converter**.

La cláusula de escape ε no cubre este caso: está condicionada a *"cuantización inevitable y documentada del converter"* (AVRO→Parquet→double). Una divergencia de parsing texto→double no es cuantización del converter — es divergencia de runtime entre lenguajes. El análisis de tipos del ADR (AVRO double = Parquet DOUBLE = IEEE 754 binary64) es correcto para el tramo AVRO→Kuzu, pero el tramo CSV→double es el eslabón no analizado.

**No mecaniza "medir, no votar":** El invariante rector exige trazar a `fichero:línea`. El análisis de tipos traza el tramo Avro→Parquet→Kuzu. El tramo CSV→double del converter no tiene `fichero:línea` porque el converter no existe. Se está votando (asumiendo same-parsing) sin medir.

**Propuesta de resolución (cualquiera basta):**
1. **Especificar el lenguaje** del converter Flujo A en este ADR. Si es C++ y reusa `parse_double`, B1 cae.
2. **Si es cross-language,** añadir una nota explícita: *"El bit-exacto en scores está condicionado a que el converter use un parser text→double con correct rounding equivalente a `std::from_chars` C++17. Si el converter es Python, el gate DAY 198 incluye un paso previo: parsear todos los doubles del bronce con ambos runtimes y medir `max|d_cpp - d_python|`. Si > 0 ULP, se deriva ε_parse de esa medición."*
3. **Eliminar el parsing de texto como variable:** transportar los doubles en el bronce en formato hex IEEE 754 (`0x1.fp+3`) que ambos lados parsean sin ambigüedad. (Invasivo — probablemente no vale la pena.)

**Veredicto:** No se puede ratificar un predicado bit-exacto con un eslabón no analizado. No es re-litigación de bit-exacto (ratificado) — es ampliar el análisis de tipos al tramo que falta.

---

### B2. "Aristas coinciden" es ambiguo: ¿subconjunto o igualdad de conjuntos?

**Dónde:** §3.1, línea del predicado: *"aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)"*

**El problema:** "Coinciden" no es una especificación. Tiene dos lecturas:

- **Lectura débil (subconjunto):** ∀ arista ∈ C0 → ∃ arista equivalente ∈ AB. Si AB tiene aristas EXTRA, el predicado pasa.
- **Lectura fuerte (igualdad de conjuntos):** set(aristas)_C0 == set(aristas)_AB. Bidireccional.

En un pipeline de vida o muerte, la lectura déil es insuficiente: si Flujo A+B produce aristas fantasma (relaciones que no existen en Camino 0), el grafo tiene correlaciones falsas. Un falso positivo en el dashboard puede hacer que un clínico pierda horas investigando una amenaza inexistente mientras el ransomware opera.

La ambigüedad es peligrosa porque un implementador razonable podría leer "coinciden" como "las que tiene C0, AB las tiene" (subconjunto) y escribir un test unidireccional.

**Propuesta:** Reemplazar "coinciden" por la especificación exacta:

```
∧ set((type, from_uid, to_eid, method, confidence))_C0 
   == set((type, from_uid, to_eid, method, confidence))_AB
```

(O la tupla que identifique unívocamente cada arista según el schema real.)

**Veredicto:** Bloqueante por ambigüedad en el predicado — el núcleo del ADR. Corrección de una línea.

---

## Significativos para vida o muerte (no bloquean el ADR, pero necesitan traza aquí)

### S1. `temporal_anomaly` excluida del predicado → hueco de cobertura en señal de detección primaria

**Dónde:** §3.1 partición D/E, `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` (P2).

**La exclusión está justificada** para el predicado de equivalencia (deriva de `ingested_at`, es determinista-de-ejecución, bien trazado a `cypher_builder.hpp:86`). No se cuestiona.

**El riesgo es diferente:** `temporal_anomaly` es un **booleano de detección** — marca flujos que llegan fuera de su ventana temporal esperada, un patrón típico de exfiltración lenta. El P2 lo deriva a un test unitario de la fórmula `(window, ingested_at) → bool`. Pero un unit test verifica que la fórmula es correcta dado un input — **no verifica que el converter Flujo A+B produzca el input correcto**.

Escenario de fallo no cubierto: el converter Flujo A lee el bronce, pero al escribir al grafo reemplaza `ingested_at` con el timestamp de procesamiento del Parquet (no con el del bronce). La fórmula da `true` o `false` correctamente para el input que recibe — pero el input es wrong. El unit test pasa. La detección en producción falla silenciosamente.

**Propuesta:** Añadir al gate (no al predicado §3.1, pero sí al test de aceptación del circuito) una verificación de **procedencia de `ingested_at`**: dado un bronce con timestamps conocidos, verificar que `ingested_at` en el grafo Flujo A+B es coherente con las filas del bronce (p.ej., monotónico con el orden de filas, o dentro de una banda esperada del timestamp de la fila bronce). No es bit-exacto — es coherencia de origen. Esto puede hacerse con un mock clock inyectado en el test.

**Veredicto:** No bloquea el ADR. Pero sugeriría elevar `DEBT-CIRCUIT-TEMPORAL-ANOMALY-PARITY-001` de P2 a P1 y ampliar su alcance en la descripción para incluir verificación de procedencia, no solo de fórmula.

---

### S2. ON CREATE ONLY = primera-escritura-gana: limitación sellada sin anotación explícita

**Dónde:** §2 corolario 5 (at-least-once), §4 V7 (MERGE, 0 ON MATCH SET).

**El comportamiento es correcto para equivalencia** (ambos caminos lo hacen igual, la v2 lo trazó bien). No se cuestiona.

**Lo que falta es una anotación de consciencia:** ON CREATE ONLY significa que si el mismo `flow_uid` se re-ingresa con datos corregidos (p.ej., score actualizado por un detector ML post-circuito, que es el supuesto operativo DEBT-RANSOMWARE-ML-HEAD-INERT-001), el grafo **conserva la primera versión y descarta la actualización silenciosamente**. Esto no es un bug de equivalencia — es una limitación de la semántica de escritura que el ADR sella como correcta para ambos caminos.

Un implementador post-circuito que diseñe el mecanismo de re-cualificación ML necesita saber que el grafo tiene semántica de primera-escritura-gana. Si no está anotado aquí, puede asumir upsert semántico y diseñar sobre una premisa falsa.

**Propuesta:** Añadir a §4 V7 (o §2 corolario 5) una nota:

> **Limitación sellada:** ON CREATE ONLY = semántica de primera-escritura-gana. Las actualizaciones de scores/clasificación post-ingesta (cuando se active la re-cualificación ML) requieren un mecanismo separado — ON MATCH SET, versión temporal por flow_uid, o re-ingesta con flow_uid distinto. Esta limitación es consciente y se aborda en el diseño post-circuito, no en este ADR.

**Veredicto:** No bloquea. Una nota de 3 líneas previene un diseño incorrecto futuro.

---

### S3. La cláusula de caducidad §3.2 no tiene mecanismo de fallo automático

**Dónde:** §3.2.

**El ADR dice:** al activar `DEBT-JOIN-CONFIDENCE-001`, el predicado "debe revisarse."

**El riesgo:** "Debe revisarse" es un proceso humano. Si alguien activa el join adaptativo sin revisar el predicado, el test de equivalencia sigue pasando (compara solo el subconjunto determinista, que sigue siendo igual). El test da verde cuando debería dar rojo. En un hospital, esto es un falso negativo del gate de calidad.

**Propuesta:** Añadir al test una guarda que verifique el estado de `DEBT-JOIN-CONFIDENCE-001`. Si el código del join tiene un branch condicional (p.ej. `if adaptive_confidence`), el test falla con: *"Predicado §3.1 caducado — cláusula §3.2 activada. Resolver DEBT-JOIN-CONFIDENCE-001 antes de pasar el gate."* Esto mecaniza la caducidad y la hace infalible.

**Veredicto:** No bloquea. Guarda de seguridad barata para un riesgo real de deslizamiento.

---

### S4. Verificación de la precondición de orden determinista: aclarar qué "verifica" significa

**Dónde:** §3.1, decreto: *"el test de equivalencia asume y verifica esta precondición."*

**El problema:** "Asume y verifica" es circular si la verificación es el propio test de equivalencia (si el test falla, no sabes si es por orden incorrecto o por bug del converter). Si la verificación es un test separado (p.ej., interceptar output del connector antes del sink y verificar orden), no es circular.

La distinción importa en producción: un fallo del gate ambiguamente diagnóstico bloquea un despliegue correcto o deja pasar un bug real.

**Propuesta:** Aclarar en una frase: *"Verificación = test independiente previo al de equivalencia: interceptar las sentencias Cypher del connector Flujo B y verificar que el orden de INSERT/MERGE es (flow_start_window ASC, seq_in_window ASC). Si este test no pasa, el de equivalencia no se ejecuta."*

**Veredicto:** No bloquea — la precondición es correcta como decreto. Solo necesita desambiguación de la verificación.

---

## Menores

### S5. Código de prioridad `F4` sin definir

§2 nota: `DEBT-ARGUSPP-WAZUH-001 (F4, OPEN)`. `F4` no aparece definido en este ADR ni se referencia una escala. En un pipeline de vida o muerte, un código de prioridad opaco puede llevar a que un operador trate una deuda como baja cuando es crítica. Eliminar la referencia a F4 o definir la escala.

### S6. Aparente contradicción P1 / "antes del Eslabón 1"

§2 corolario 3: *"Decisión sube antes del Eslabón 1."* §6: `DEBT-HOST-DOMAIN-CONTRACT-001` clasificada como **P1**. Si bloquea Eslabón 1, ¿no es P0? Probablemente significa "P1 dentro del alcance del Eslabón 1" (no P0 global), pero la tabla de §6 no tiene esa granularidad. Una nota aclaratoria evita confusión.

---

## Lo que está bien (para balance)

- **Partición D/E:** Hallazgo genuino. Ninguno de los 8 modelos lo vio en la v1. Bien trazado a `fichero:línea`.
- **Guarda canónica NaN/-0.0:** Precisa y correcta. La mayoría de equipos usaría `memcmp` o `==` crudo y tendría bugs latentes en producción. La elección de un único patrón quiet NaN como canonicalización es la solución derecha.
- **Reubicación de HMAC:** La corrección es exacta — un campo con 0 hits en `schema.cypher` no puede estar en un predicado sobre la proyección Kuzu. DeepSeek tuvo razón y la v2 lo incorporó limpiamente.
- **Refutaciones contra el binario:** Las tres objeciones caídas (`event_id`=col 2, window/seq materializadas, scores DOUBLE en schema) están bien documentadas con traza. Esto es "medir, no votar" en acción.
- **Changelog trazado a revisor:** Estándar de trazabilidad que rara vez se ve. Permite auditoría de qué modelo dijo qué y qué pasó después.

---

## Veredicto global

**Condicionado a resolución de B1 y B2.** B1 requiere una frase que anote la condición del parser o especifique el lenguaje. B2 requiere reemplazar "coinciden" por la especificación de igualdad de conjuntos. Ambas son correcciones de <5 líneas que no tocan la forma del oro ni bit-exacto.

Con esas dos correcciones, **confirmo** que las correcciones de §3.1 reflejan fielmente lo medido, y el ADR puede cerrar.

FDO

GLM