He revisado a fondo la v2 del ADR-058. La trazabilidad a `fichero:línea` es excelente y la mayoría de las correcciones están bien medidas. Sin embargo, en un sistema que debe sostener vidas en hospitales con pocos recursos, cualquier ambigüedad o suposición no validada es un riesgo inaceptable. A continuación, expongo los defectos remanentes que he encontrado, ordenados por criticidad para la seguridad del paciente.

---

## 1. El predicado de equivalencia **no cubre las aristas de las relaciones** con el mismo rigor que los nodos

La cláusula de equivalencia para las relaciones dice:

> *aristas {ALERT_ABOUT, TELEMETRY_ABOUT, CORRELATES_FLOW} coinciden (con method/confidence)*

Pero **no especifica el predicado concreto para esa coincidencia**. ¿Basta con que existan las mismas aristas entre los mismos nodos? ¿Se comparan sus propiedades `method` y `confidence` de forma bit-exacta? ¿Qué pasa si una arista se crea con `method` ligeramente diferente en un camino y en otro por un error de serialización?  
La partición D/E no incluye estas propiedades de arista; se asume que son deterministas-de-dato, pero no está medido ni afirmado explícitamente.  
**Riesgo en hospital:** Una arista con `confidence` divergente puede hacer que el dashboard muestre una relación como "alta confianza" en un camino y "baja confianza" en otro. Si el personal clínico toma decisiones basadas en ese grafo (p. ej., aislar un dispositivo médico), una diferencia no detectada puede llevar a una falsa sensación de seguridad o a un bloqueo innecesario.  
**Acción requerida:** Definir explícitamente el predicado de igualdad de aristas (al menos `(src_label, src_pk, dst_label, dst_pk, edge_label, method, confidence)` con igualdad bit-exacta, y justificar si `confidence` es determinista-de-dato — debería serlo si sale del join determinista, pero debe trazarse).

---

## 2. El orden determinista en Flujo B se decreta, pero no se especifica cómo se garantiza en el converter

Se introduce la **precondición de orden de inserción determinista** para la robustez ante colisión `flow_uid`:

> *Decreto: el Flujo B inserta en orden determinista por (flow_start_window, seq_in_window) antes del sink Kuzu*

Pero el converter **Flujo B (Parquet → Kuzu)** es greenfield y no se detalla cómo se logrará ese orden. Parquet no garantiza orden de lectura a menos que se ordene explícitamente. Si el converter lee el archivo Parquet con un iterador que no respeta un orden, o si el Parquet se genera en paralelo y las filas no están ordenadas por `(window, seq)`, el orden de inserción en Kuzu **no será determinista**, y la precondición se romperá sin que el test de equivalencia pueda distinguirlo de un bug real.  
**Riesgo en hospital:** La colisión `flow_uid` es rara pero posible (diferentes nodos con misma ventana). Si el orden no es determinista, un incidente de seguridad real podría generar un flujo que, bajo un orden, se descarta, y bajo otro, sobrescribe al benigno. Podría ocultar un flujo malicioso en el dashboard.  
**Acción requerida:** Añadir en §3.1 o en una nota de implementación cómo el Flujo B garantiza el orden (p. ej., `ORDER BY flow_start_window, seq_in_window` en la consulta de lectura del Parquet, o un paso de ordenación explícito). Esto debe ser verificable en el test de equivalencia.

---

## 3. La partición D/E no incluye las propiedades de las relaciones, ni `flow_start_sec`/`flow_start_nano`

La tabla de partición solo lista propiedades de nodos. ¿Qué pasa con `flow_start_sec` y `flow_start_nano`? ¿Se almacenan en Kuzu? Revisando: en el grafo, la tabla `NetworkFlow` tiene `flow_start_window` pero no `flow_start_sec`/`nano` (según el schema). Sin embargo, el oro-ledger **sí** tendrá esas columnas (son parte del contrato de 19 columnas). Para la equivalencia en Kuzu no aplican, pero entonces la comparación de `props_identidad` no incluye esos campos. ¿Es eso correcto? Parece que sí. Pero la tabla de partición debería aclarar que `flow_start_sec`/`nano` **no están en Kuzu** (como `hmac`), y por tanto no van al predicado. Es un punto menor, pero para un sistema crítico es mejor ser explícito.

---

## 4. La guarda canónica para NaN y -0.0 introduce una transformación sutil que debe ser idéntica en ambos caminos

Se propone canonicalizar NaN a un patrón fijo (`0x7ff8000000000000`) y `-0.0` a `+0.0`. Esto es correcto. Sin embargo, surge un riesgo: en C++, el converter Camino 0 no realiza esa canonicalización hoy; el sink de Kuzu escribe los doubles tal como vienen del parseo. Si el parser de C++ produce `-0.0` a partir de `"-0.0"` en el CSV, y el converter Flujo A (en Python o Java) hace la canonicalización, entonces ambos grafos divergirán en el patrón de bits del double almacenado, pero el predicado de equivalencia (que aplica la canonicalización) los considerará iguales. Eso es un falso positivo: **los grafos en disco son diferentes**, lo que afecta a cualquier otra herramienta que lea de Kuzu sin canonicalizar (p. ej., un dashboard que compare scores).  
**Riesgo en hospital:** Si el dashboard o un sistema de monitorización compara scores con `==` en una consulta Cypher, podría ver diferencias inexplicables entre entornos (desarrollo vs producción) y generar confusión o falsas alarmas.  
**Acción requerida:** El predicado debe exigir que **ambos caminos escriban el double en Kuzu tras aplicar la misma canonicalización**. Es decir, la canonicalización no debe ser solo para la comparación del test, sino parte de la escritura en el grafo. De lo contrario, el test pasará pero los grafos serán bit-distintos. Si no se quiere modificar Camino 0, se debe documentar como deuda (`DEBT-CANONICAL-DOUBLE-SINK-001`) y justificar por qué no es crítico.

---

## 5. Duplicados en el oro por entrega at-least-once: el ADR aún no aborda el impacto

La v1 mencionaba ZMQ PUSH/PULL at-least-once. La revisión anterior señaló que el oro-ledger podría contener duplicados y eso rompe la unicidad esperada. La v2 no añade ninguna deuda ni aclaración al respecto. En §2 corolario 6 se habla de HMAC por fila, pero un duplicado tendría el mismo HMAC y contenido, invalidando la verificabilidad (¿cuál es la fila canónica?).  
**Riesgo en hospital:** Si se usa el ledger para auditoría forense, un duplicado puede hacer que un evento parezca haber ocurrido dos veces, llevando a decisiones incorrectas sobre el aislamiento de un dispositivo. Además, el replicar el grafo desde el ledger podría introducir el mismo flujo dos veces, y aunque MERGE lo descarte, la mera existencia de duplicados en el oro es una corrupción semántica.  
**Acción requerida:** Crear al menos una deuda P1 (`DEBT-GOLD-DEDUP-AT-LEAST-ONCE-001`) que capture la necesidad de deduplicación en el oro (por ejemplo, añadiendo un offset de Kafka o un identificador único de publicación). Mientras no se implemente, el oro no es confiable como source-of-truth inmutable.

---

## 6. Escritura atómica en bronce: el Eslabón 0 sigue sin detallar cómo se garantiza con append

El Eslabón 0 propone “escritura atómica `.tmp → rename` + cierre por tiempo absoluto”. En un archivo de log que crece durante horas, escribir atómicamente cada línea con rename es inviable. La interpretación más plausible es atomicidad en la rotación (al cambiar de día, se cierra el fichero y se renombra). Pero el texto no lo aclara, y el watcher `inotify`/`IN_CLOSE_WRITE` está pensado para detectar cuando el writer cierra el fichero tras escribir un bloque. Si el writer escribe muchas líneas y luego cierra, el reader podría leer un archivo parcial.  
**Riesgo en hospital:** Una lectura parcial durante un incidente podría causar que el dashboard muestre solo una fracción de los flujos, ocultando un ataque en curso.  
**Acción requerida:** Especificar claramente la estrategia de atomicidad: ¿se escribe en un archivo temporal durante el día y se renombra al final del día? ¿O se asume que el reader solo lee archivos completos del día anterior? Esto afecta a la latencia y a la integridad de la información en tiempo real. Debe quedar explícito.

---

## 7. `temporal_anomaly` excluida, pero su fórmula usa `ingested_at`, que es per-fila y no determinista: correcto. Sin embargo, ¿hay riesgo de que otros campos calculados dependan de `ingested_at` sin ser detectados?

Se ha identificado `temporal_anomaly` como dependiente de `ingested_at`. ¿Existen otros? Por ejemplo, ¿`seq_in_window` se calcula en el reader basándose en el orden de llegada de las filas? Si el orden de lectura del bronce no es determinista (múltiples archivos, múltiples hilos), `seq_in_window` podría variar entre caminos. El ADR no menciona cómo se asigna `seq_in_window` en el reader. Debería medirse.  
**Riesgo:** Si `seq_in_window` no es determinista-de-dato sino que depende del orden de procesamiento, la partición D/E es incorrecta y el predicado fallará sin bug.  
**Acción:** Medir en `correlation_reader.cpp` o `main.cpp` cómo se asigna `seq_in_window`. Si se deriva del orden en el CSV, es determinista (el CSV es una secuencia). Si depende del orden de inserción en un mapa interno, podría no serlo. Verificar y documentar.

---

## 8. El ADR no menciona cómo se maneja la ingesta de múltiples archivos de bronce (rotación diaria) para la equivalencia

El Camino 0, hoy, solo lee un único archivo de bronce (el actual). Flujo A+B procesará todo el histórico. El test de equivalencia debe definir sobre qué conjunto de datos se ejecuta: ¿solo el archivo de hoy? ¿Todo el directorio? Si es solo el archivo actual, ¿cómo se garantiza que ambos caminos ven exactamente el mismo contenido cuando el writer sigue escribiendo? Se necesita un snapshot común.  
**Riesgo:** Si el test se ejecuta mientras el writer sigue añadiendo líneas, el Camino 0 podría ver una línea más que Flujo A (que procesa hasta un cierto punto), y el test fallaría sin bug.  
**Acción:** Definir que el test de equivalencia se ejecuta sobre un **conjunto de archivos cerrados** (día anterior) o sobre un snapshot inmutable. Debe ser explícito.

---

## 9. La cláusula de caducidad (§3.2) no detalla qué dispara exactamente la activación de `DEBT-JOIN-CONFIDENCE-001`

Se dice "join adaptativo / no-determinista". ¿Quién decide cuándo se activa? ¿Un cambio en la configuración? ¿Se espera que sea un flag? Si se activa sin que el equipo de guardia lo sepa, el predicado se romperá y las alertas de equivalencia empezarán a sonar. En un hospital, eso puede llevar a desactivar el sistema de monitoreo justo cuando más se necesita.  
**Acción:** Añadir que la activación de ese join será explícita y bajo control de configuración versionada, con un período de solapamiento donde ambos modos sean comparables.

---

## Conclusión

La v2 ha corregido los defectos más graves, pero aún quedan puntos críticos para un sistema que salva vidas:
1. **Predicado de aristas sin concretar** (potencial divergencia no detectada).
2. **Orden determinista en Flujo B no implementado** (riesgo de no equivalencia por carrera).
3. **Canonicalización de doubles no garantizada en ambos sinks** (grafos bit-distintos).
4. **Duplicados en el oro sin tratar** (corrupción de la fuente de verdad).
5. **Atomicidad y snapshot para el test** no definidos.

Estos defectos no impiden continuar con la implementación, pero deben ser abordados como deudas explícitas o especificaciones adicionales **antes de poner el sistema en producción en un hospital**. Recomiendo incorporar las acciones indicadas y, si se desea, elevar la criticidad de algunas deudas a P0 (especialmente la deduplicación y el orden determinista).

¿Procedemos a redactar una v3 con estas inclusiones o se prefiere diferir como tickets? Estoy listo para seguir en modo adversarial hasta que el diseño sea lo más sólido posible.

FDO

DEEPSEEK