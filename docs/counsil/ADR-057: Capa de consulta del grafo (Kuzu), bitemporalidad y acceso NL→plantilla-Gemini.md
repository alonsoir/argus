Un análisis riguroso del ADR-057, aplicando el principio de **"medir, no votar"** y basándonos en las restricciones físicas y de diseño del ecosistema (Kuzu v0.11.3, Falco, arquitectura embebida).

Aquí están los puntos débiles, riesgos ocultos y vectores de fallo identificados por el Consejo, acompañados de la argumentación técnica y medible correspondiente.

---

## 1. Puntos débiles y riesgos ocultos detectados

### ⚠️ Concurrencia en Kuzu v0.11.3: El peligro del bloqueo del Engine

El ADR pospone el *smoke test* de concurrencia a la Fase 2, pero toma una decisión de diseño en la Fase 0 basada en él. En Kuzu v0.11.3, un proceso que abre la base de datos en modo escritura bloquea el archivo mediante locks del sistema operativo (`fcntl`/`flock`).

* **El punto débil:** Si la capa de consulta corre **in-process** dentro del propio thread pool del *correlation-engine*, las consultas analíticas complejas (como T1 a N saltos o T3 de agregación de scores) competirán directamente por la CPU y los recursos de memoria con el pipeline de escritura en tiempo real de `NetworkFlow`.
* **Impacto medible:** Una consulta mal acotada (ej. T1 con $n=4$ en un nodo de alta conectividad o *supernode*) puede degradar el rendimiento del *engine*, provocando caída de paquetes en el *sniffer* por contención de recursos.
* **Acción del Consejo:** Adelantar el *smoke test* de la Fase 2 a la **Fase 0**. Es crítico validar si Kuzu permite múltiples *readers* concurrentes *in-process* bajo el modelo `Connection` de la misma instancia de `Database`.

### ⚠️ El mito del "Desacople" de CLOCK-INJECTION mediante `ingested_at`

El documento afirma que `ingested_at` es totalmente ortogonal y mitiga el problema del reloj envenenado del *sniffer*. Esto es parcialmente falso desde una perspectiva forense bitemporal.

* **El punto débil:** Si el sniffer sufre una inyección de reloj y estampa un `flow_start_window` en el futuro (ej. año 2030) debido a la deuda no resuelta de `bpf_ktime_get_ns()`, y el engine lo procesa hoy estampando un `ingested_at` con fecha de 2026, la consistencia lógica del sistema bitemporal se rompe. Tendremos un registro donde el conocimiento del hecho ($T_t = 2026$) es anterior a la ocurrencia real del hecho ($T_v = 2030$).
* **Impacto medible:** Las consultas de tipo **T4 (Retro-hunt)** fallarán catastróficamente al intentar ordenar cronológicamente o correlacionar con eventos externos, ya que $T_v < T_t$ es una anomalía lógica en bases de datos bitemporales. `ingested_at` limpia el eje de transacciones, pero **no inmuniza** al grafo de la corrupción del eje de eventos.

### ❌ Explosión Combinatoria en T1 (`CORRELATES_FLOW*1..$n`)

El catálogo propone un límite de `$n \le 4$` para la navegación topológica en la plantilla T1. En análisis de grafos de red, un límite fijo de 4 saltos sin límite de *fan-out* (grado del nodo) es una bomba de tiempo.

* **El punto débil:** Si un `NetworkFlow` corresponde a un servicio centralizado (ej. DNS, NTP o un balanceador de carga), su grado de entrada/salida puede ser de miles de aristas. Elevar eso a la cuarta potencia ($O(d^n)$) provocará un desbordamiento de memoria o un cuelgue del thread de consulta.
* **Impacto medible:** El consumo de RAM de `libkuzu` escalará exponencialmente, activando el OOM (Out Of Memory) Killer de Linux sobre el *correlation-engine*.
* **Acción del Consejo:** Redefinir el parámetro. No basta con acotar los saltos ($n \le 2$ por defecto); es obligatorio parametrizar y acotar el **número máximo de vecinos expandidos por salto** (ej. `LIMIT 100`).

### ⚠️ Ambigüedad y Atascos en el Intérprete NL (TinyLlama)

El modelo propone que TinyLlama clasifique y extraiga parámetros, rechazando la petición si no alcanza un umbral de confianza.

* **El punto débil:** El rechazo duro genera fricción operativa en incidentes críticos de seguridad. Por el contrario, la devolución de múltiples opciones puede confundir al analista si las plantillas son similares (ej. T5 vs T6). Además, la extracción de parámetros (como expresiones regulares de `community_id`) mediante LLMs pequeños suele fallar o "alucinar" caracteres de la estructura del string.
* **Impacto medible:** Tasa de falsos rechazos (FRR) elevada en la interfaz de usuario, obligando al operador a abandonar la interfaz de lenguaje natural.

---

## 2. Resoluciones firmes del Consejo [CONSEJO]

Tras evaluar los puntos críticos del borrador, el Consejo emite las siguientes directrices obligatorias para la estabilización del diseño:

### 1. Concurrencia e In-Process (Sección 2.1)

* **Ratificación:** Se aprueba el modelo **in-process** por diseño de seguridad (invariante de Falco) y simplicidad de autenticación.
* **Restricción obligatoria:** Para evitar que las consultas degraden la ingesta, la capa de consulta debe ejecutarse en un **thread pool aislado y con prioridad de scheduling (nice) inferior** a los threads de mutación del grafo. Si el *smoke test* de la Fase 0 demuestra que `libkuzu` bloquea las lecturas durante un `COMMIT` de escritura masiva, se implementará un mecanismo de *Read-Write Lock* a nivel de aplicación en `cypher_builder.hpp`.

### 2. Semántica `ingested_at` y Bitemporalidad (Sección 2.2)

* **Ratificación:** Se aprueba la introducción de `ingested_at` mediante `ON CREATE SET`.
* **Enmienda de seguridad:** Se debe añadir una validación en el *engine*: si `flow_start_window` es mayor que `ingested_at` (más allá de un margen de tolerancia de sincronización de pocos segundos), el flujo se marcará con un flag de anomalía temporal `temporal_anomaly=TRUE`. Esto aislará los efectos de la vulnerabilidad CLOCK-INJECTION sin detener la ingesta.

### 3. Poda y Ajuste del Catálogo T1–T6 (Sección 2.3)

El Consejo ordena la siguiente reestructuración del catálogo de plantillas:

| Plantilla | Estado | Modificación Requerida por el Consejo |
| --- | --- | --- |
| **T1 (Vecindario)** | 🟢 Aprobada | Obligatorio añadir `LIMIT` por salto para evitar explosión topológica. $n$ máximo reducido a 2 para operadores generales. |
| **T2 (Contexto Alerta)** | 🟢 Aprobada | Mantener. Es el valor core del grafo. |
| **T3 (Densidad)** | 🟢 Aprobada | Restringir el cálculo a un subgrafo acotado por tiempo. |
| **T4 (Retro-hunt)** | 🟢 Aprobada | **Prioridad Alta.** Es la plantilla que justifica la bitemporalidad. |
| **T5 (Filtro Ventana)** | ❌ **ELIMINADA** | Violación de honestidad de diseño. Esto pertenece al plano ORO (Parquet/DuckDB). No indexar ni saturar el grafo con búsquedas secuenciales temporales de alertas. |
| **T6 (Alertas Nodo)** | 🟡 Condicional | Solo se permite si es el paso inicial para una navegación topológica (ej. anidada con T2). Si es solo para listar, se descarta a favor de ORO. |

### 4. Firma del Catálogo y Seguridad del Intérprete NL

* **Firma del Catálogo:** **Aprobada.** El catálogo de plantillas parametrizadas se compilará como un artefacto estático o JSON firmado con la clave Ed25519 del pipeline de despliegue (siguiendo la cadena de confianza de ADR-025). El *engine* se negará a cargar un catálogo cuya firma no sea válida.
* **Estrategia NL ante Ambigüedad:** Se deniega el rechazo duro inmediato. Si la confianza de TinyLlama cae por debajo del **85%**, pero se mantiene por encima del **50%**, el sistema implementará un **retorno interactivo mitigado**: presentará al operador un máximo de dos opciones pre-formateadas (ej. *"¿Quiso decir: Ver el vecindario del flujo (T1) o el contexto de la alerta (T2)?"*). Si cae por debajo del 50%, se produce un rechazo limpio con sugerencias de uso.

---

## 3. Plan de Fases Modificado (Línea Base del Consejo)

Se reorganiza el plan para priorizar la mitigación de los riesgos físicos antes de escribir código de abstracción:

* **Fase 0 (Crítica):** 1. Modificación del schema e inclusión de `ingested_at UINT64` (`ON CREATE SET`).
2. **Adelantado:** *Smoke test* real de concurrencia y estrés de `libkuzu` v0.11.3 para medir latencia de escritura mientras se ejecutan lecturas pesadas concurrently.
* **Fase 1:** Implementación del catálogo podado (T1, T2, T3, T4, T6 modificado) firmado con Ed25519 como librería interna en C++. Validación estricta de tipos en los parámetros.
* **Fase 2:** Integración de la lógica de aislamiento de hilos para consultas analíticas dentro del *engine*.
* **Fase 3:** Incorporación del clasificador TinyLlama con la lógica de umbral de confianza descrita (85% / 50% interactivo).
* **Fase 4:** Enlace con el WAL (DEBT-LABEL-WAL-001) para consultas reconstructivas históricas.

FDO Gemini