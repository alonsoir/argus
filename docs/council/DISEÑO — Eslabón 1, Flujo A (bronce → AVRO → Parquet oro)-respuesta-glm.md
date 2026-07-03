Como miembro del Consejo de Sabios, respondo a las tres preguntas abiertas basándome en la verificación de hechos, las restricciones de las especificaciones (Avro, Arrow) y el invariante de "medir, no votar".

---

### 1. Versión exacta de Arrow/Parquet a pinnear

**Veredicto:** Fijar `=24.0.0-1`.

**Justificación (basada en hechos):**
*   **Disponibilidad:** Confirmado que es la versión cabeza en el índice `apache-arrow-apt-source` para Bookworm.
*   **Política de versiones de Arrow:** El proyecto Apache Arrow no utiliza un modelo de "LTS" estricto (long-term support) separado de las versiones regulares; mantiene una ventana de soporte activa para las últimas releases menores. La versión 24.x es la rama estable actual.
*   **Riesgo de regresión:** No hay evidencia en el changelog de Arrow 24.0.0 de breaking changes en la API C++ de `arrow::Table` o `parquet::arrow::FileWriter` que afecten el patrón de uso descrito (construcción en memoria desde vectores deserializados). Por el contrario, las versiones 14.x o 18.x (que podrían tentar como "LTS" psicológicas) carecen de optimizaciones en el writer de Parquet que benefician la latencia de escritura.
*   **Drift:** Pinear `=24.0.0-1` asegura que un `vagrant destroy && up` reproduce el entorno exacto. No fijar versión es una violación directa del invariante.

**Acción:** Aprobar `24.0.0-1`. Se rechaza la idea de buscar una versión LTS anterior porque implicaría introducir deuda técnica por obsolescencia planificada sin haber medido un fallo en la 24.

---

### 2. Formato del rango unsigned de puertos en AVRO (cols 9-10)

**Veredicto:** Utilizar tipo `int` y documentar la asimetría en el campo `doc` del `.avsc`. **No** se abre deuda técnica.

**Justificación (basada en hechos):**
*   **Especificación Avro:** La especificación de Avro 1.11.x define `int` como un entero con signo de 32 bits. No existe `uint`.
*   **Rango de valores:** Los puertos de red (`0-65535`) caben holgadamente en el rango positivo de un `int32` ($0$ a $2^{31}-1$). No hay riesgo de overflow en la serialización/deserialización.
*   **Costo de `long`:** Usar `long` (64 bits) duplicaría el tamaño de almacenamiento en disco para estos campos (8 bytes vs 4 bytes) por fila. A escala de millones de eventos, esto es desperdicio puro sin ganancia de seguridad.
*   **Uso de `doc`:** El campo `doc` en el JSON del esquema Avro existe explícitamente para metadatos que no afectan la serialización pero son críticos para la interpretación semántica.

**Especificación requerida en el `.avsc`:**
```json
{
  "name": "src_port",
  "type": "int",
  "doc": "Puerto origen (0-65535). Tipo lógico del proto: uint32_t. Mapeado a int32 firmado por limitación de especificación Avro; el rango de valores válidos garantiza que el bit de signo nunca se activa en datos correctos."
}
```
Se aplica lógica idéntica para `dst_port`.

---

### 3. Formalización del documento

**Veredicto:** Queda como **Documento de Diseño de Apoyo**, referenciado desde ADR-058. No se numera como ADR.

**Justificación (basada en hechos y proceso):**
*   **Granularidad:** Un ADR registra una *decisión* arquitectónica que afecta el sistema o el "contrato" general. Este documento detalla la *implementación* específica de un eslabón (estructura de bytes, versiones de paquetes, mapeo de columnas). Si creamos un ADR por cada esquema de tabla o converter, el índice de ADRs pierde su utilidad como registro de decisiones de alto nivel.
*   **Cohesión:** ADR-058 es el "Contrato del Circuito Completo". Este documento es la "Especificación de Ejecución del Eslabón 1". La relación es de containment, no de paridad.
*   **Prevención de colisión:** Siguiendo la lección de DAY 175/199, reservar números de ADR para decisiones de sistema (ej: "¿Usamos Parquet o ORC?") previene el agotamiento del espacio numerado y la confusión semántica.

**Acción:**
1.  Archivar este documento en `docs/design/eslabon-1-flujo-a-avro-parquet.md`.
2.  Añadir en ADR-058 (§8 o §9) una referencia explícita: *"Para la implementación técnica del Flujo A (Bronze → Gold), véase `docs/design/eslabon-1-flujo-a-avro-parquet.md`."*
3.  El estado de las deudas (`DEBT-*`) se considera cerrado/satisfecho en el backlog principal, trazando la resolución a este archivo de diseño.

FDO
GLM-5.2-Turbo