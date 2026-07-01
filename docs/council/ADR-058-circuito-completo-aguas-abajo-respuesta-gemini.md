Estimado Lead Developer y miembros del Consejo,

Tras analizar minuciosamente el **ADR-058** bajo el principio rector de *"medir, no votar"*, el panel identifica **dos grietas críticas de diseño** que podrían sabotear la implementación de esta semana si no se mitigan inmediatamente. No son cuestiones de preferencia, sino fallas lógicas y sistémicas en los bordes de la equivalencia y la concurrencia.

---

## 1. El punto ciego del `MERGE` secuencial vs. paralelo (Falla de Equivalencia)

El ADR asume en la sección 3.1 que la colisión de `flow_uid` es inocua para el predicado porque ambos caminos usan `MERGE` con `ON CREATE SET` únicamente, asumiendo que "ambos perderán el mismo flujo".

> **La falla:** Esto solo es cierto si el orden de inserción en Kuzu es **estrictamente idéntico y determinista** en ambos caminos.

* **Camino 0:** Es un `ifstream` secuencial sobre el CSV de bronce. El orden de inserción está dictado por el orden físico de las líneas del fichero.
* **Flujo A+B:** Pasa por Avro y Parquet. La ingesta desde Parquet a Kuzu (Eslabón 2) suele optimizarse mediante lecturas paralelas, particionado o cargas en bloque (*bulk load*).

Si el orden de inserción cambia debido al paralelismo o al procesamiento de bloques en el Flujo B, ante una colisión de `flow_uid`, el flujo que ganará el `ON CREATE SET` en el Flujo A+B será **distinto** al que ganó en el Camino 0. El predicado de equivalencia de propiedades (`props_identidad` y `props_veredicto`) **romperá en el test de integración**, no por un bug del converter, sino por una condición de carrera de arquitectura.

**Mitigación inmediata:** El predicado debe evaluar si existen colisiones registradas antes de fallar el test, o el Flujo B debe garantizar un ordenamiento estricto por `(window, seq_in_window)` antes de la fase de inserción en Kuzu.

---

## 2. La trampa cross-language en la exactitud de bits del `double`

La decisión de exigir una igualdad `BIT-EXACTA` por defecto en los scores (colores 14-16) es teóricamente robusta pero altamente peligrosa si el **Flujo A** se implementa en un ecosistema distinto (Python/Go/Rust) al del **Camino 0** (C++20).

* El Camino 0 usa `std::from_chars` en `cypher_builder.hpp`.
* Si el convertidor del Flujo A utiliza librerías nativas de Python (`float()`), `fast_float`, o el parser interno de un framework de Avro, el algoritmo de parsing de cadena-a-flotante puede diferir en el **último bit de la mantisa** (ULP) para ciertos valores límite, aun siendo ambos IEEE 754 binary64.
* Adicionalmente, si en C++ se compila con banderas como `-ffast-math` (común en módulos `ml-detector`), el orden de las operaciones floating-point destruye la bit-exactitud cross-platform.

**Mitigación inmediata:** Ratificar la igualdad bit-exacta **solo si** se garantiza que ambos caminos comparten exactamente el mismo binario de parsing de texto (ej. si el convertidor del Flujo A invoca la misma lógica C++ compilada), o bien degradar el control a un `std::bit_cast<uint64_t>` permitiendo una tolerancia máxima de $\pm1 \text{ ULP}$ antes de forzar la cláusula de escape de $\varepsilon$.

---

## 3. Vulnerabilidad en la "Guarda NaN" mediante `memcmp`

El texto propone usar `memcmp` de los 8 bytes para validar la igualdad del patrón de bits en caso de `NaN`.

* En IEEE 754, un `NaN` no es un único valor: está el bit de signo y la carga útil (*payload*). Los compiladores y serializadores de diferentes lenguajes suelen alterar el *payload* del `NaN` (pasando de *Signaling NaN* a *Quiet NaN*) al serializar a formatos de disco como Avro o Parquet.
* Un `memcmp` crudo fallará si el Flujo A normaliza el `NaN` a `0x7ff8000000000000` pero el parser de Kuzu o el lector de Parquet genera `0xfff8000000000000` (diferencia de signo).

**Mitigación inmediata:** El predicado de validación en el test debe usar explícitamente `std::isnan(a) && std::isnan(b)` en lugar de comparaciones binarias crudas para los estados de indefinición del modelo ML inerte.

---

¿Desea el Consejo que formalicemos la enmienda para obligar al Flujo B a ordenar por secuencia antes del sumidero de Kuzu, neutralizando así el riesgo del `MERGE` desincronizado?

FDO GEMINI