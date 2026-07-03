El Consejo ha revisado el borrador del diseño para el Eslabón 1 (Flujo A). En estricto cumplimiento del invariante rector (*medir, no votar*) y basándonos en la especificación técnica de las librerías y las mejores prácticas de ingeniería de datos, se emiten las siguientes ratificaciones y respuestas a las preguntas abiertas.

### 1. Versión exacta de Arrow/Parquet a pinnear

**Ratificación:** Se aprueba pinnear la versión más reciente verificada, **`=24.0.0-1`**. No se debe retroceder a una LTS anterior.

**Fundamento técnico (medido, no supuesto):**
*   **Estabilidad de ABI en el repositorio oficial:** El repositorio oficial de Apache Arrow (`apache-arrow-apt-source`) garantiza la compatibilidad binaria (ABI) dentro de una misma versión mayor. El paquete `libarrow-dev=24.0.0-1` tiene una dependencia estricta y transitiva del paquete de runtime correspondiente a esa ABI (ej. `libarrow2400`). Pinnear el paquete `-dev` en el `provision.sh` congela automáticamente el runtime, eliminando el riesgo de *drift*.
*   **Ciclo de releases de Arrow:** Apache Arrow libera una versión mayor cada mes. Una "LTS anterior" en el ecosistema Arrow simplemente significa una versión de hace 3 o 4 meses, sin beneficios de estabilidad a largo plazo (como los que ofrecería una LTS de Ubuntu o Debian), pero con la desventaja de perder correcciones de bugs y optimizaciones de Parquet.
*   **Acción requerida:** En `provision.sh`, la instrucción debe ser explícita: `apt-get install -y libarrow-dev=24.0.0-1 libparquet-dev=24.0.0-1`.

### 2. Formato del rango unsigned de puertos en AVRO (cols 9-10)

**Ratificación:** Se debe utilizar el tipo primitivo **`int`** de AVRO y documentar la asimetría en el campo `doc` del esquema. **No se abre ninguna deuda técnica por esto.**

**Fundamento técnico (basado en la especificación AVRO):**
*   **Especificación AVRO:** La especificación oficial de Apache Avro define los tipos primitivos como `null`, `boolean`, `int` (32-bit signed), `long` (64-bit signed), `float`, `double`, `bytes` y `string`. **AVRO no posee tipos primitivos `unsigned` ni `uint16`**.
*   **Capacidad matemática:** El rango de un puerto TCP/UDP es `0-65535`. Un entero con signo de 32 bits (`int` en AVRO) soporta hasta `2,147,483,647`. Por lo tanto, todos los valores de puerto caben perfectamente sin ningún riesgo de *overflow* ni pérdida de precisión. Usar `long` sería un desperdicio de espacio y procesamiento; usar `bytes` o `fixed` rompería la ergonomía del Parquet resultante.
*   **Acción requerida:** En el archivo `.avsc`, las columnas 9 y 10 se definirán como `"type": "int"`. Se añadirá el campo `"doc"` para dejar la trazabilidad explícita: `"doc": "Port number (0-65535). Avro lacks unsigned primitives; stored as signed 32-bit int per specification."`. Esto cierra la duda por diseño, sin generar deuda.

### 3. Formalización como ADR numerado vs. documento de diseño de apoyo

**Ratificación:** Este documento debe permanecer como **documento de diseño de apoyo (Specification/Design Doc)** y **no** formalizarse como un ADR numerado independiente. Debe ser referenciado desde ADR-058.

**Fundamento técnico (basado en el patrón ADR de Michael Nygard y arquitectura de software):**
*   **Separación de Decisiones vs. Especificaciones:** Un ADR (Architecture Decision Record) está diseñado para capturar el *Contexto*, la *Decisión* y las *Consecuencias* de una elección arquitectónica de alto nivel (ej. "Usaremos C++20 con libavro/libarrow para el Flujo A, particionando por fecha"). Incluir el mapeo exacto de 24 columnas, los tipos AVRO y las reglas de canonicalización dentro de un ADR viola el principio de separación de responsabilidades documentales.
*   **Riesgo de "ADR Bloat" (Inflación del ADR):** Si el esquema AVRO/Parquet sufre un cambio menor (ej. añadir una columna 24 o cambiar el tipo de un campo), el ADR tendría que ser modificado, alterando el registro histórico de una decisión que en sí misma no cambió (la decisión de usar C++20 y Parquet sigue siendo válida).
*   **Acción requerida:**
    1. Guardar este documento como `docs/design/flow-a-bronze-to-gold-spec.md`.
    2. En ADR-058, añadir un enlace en la sección de "Referencias" o "Documentación de soporte" apuntando a este archivo.
    3. Esto mantiene el ADR-058 enfocado en el *por qué* y el *qué* arquitectónico, mientras que este documento gestiona el *cómo* a nivel de contrato de datos, permitiendo que el esquema evolucione (con su propio versionado) sin manchar el historial de decisiones arquitectónicas.

---

**Conclusión del Consejo:**
El diseño presentado es sólido, respeta la jerarquía de determinismo (clases D y E) y aplica correctamente la doctrina de "medir, no votar". Con los tres ajustes de ratificación detallados arriba (pin de versión, tipo `int` documentado en AVRO, y formato de documento de apoyo), el Eslabón 1 queda **APTO PARA IMPLEMENTACIÓN**.

Se procede a cerrar el estado de BORRADOR.

FDO
qwen