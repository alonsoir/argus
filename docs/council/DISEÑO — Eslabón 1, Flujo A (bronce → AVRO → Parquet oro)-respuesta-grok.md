**Respuesta del Consejo (ratificación parcial con hechos medidos).**

El diseño del **Eslabón 1, Flujo A** es sólido, coherente con la filosofía “medir, no votar” y con las deudas pendientes del ADR-058. Cierra varias deudas importantes por construcción y mantiene el scope estrecho (solo primer salto, sin gold-plating). Procedo a responder las 3 preguntas abiertas con datos verificables.

### 1. Versión exacta de Arrow/Parquet a pinnear

**Recomendación: pinnea `=24.0.0-1` (o la última patch 24.0.x disponible en el repo oficial al momento de merge).**

**Hechos (DAY 205 → julio 2026):**
- La versión actual estable y recomendada oficialmente es **24.0.0** (lanzada ~21 abril 2026). Es la que aparece como latest en apache.org/install y en los repos APT oficiales para Bookworm.
- No existen razones técnicas fuertes para bajar a una LTS anterior (ej. 23.x o 18.x). Arrow sigue un modelo de releases frecuentes con compatibilidad fuerte del formato columnar (Arrow format 1.0+ estable desde hace años). Las rupturas ABI suelen estar bien documentadas y las APIs C++ que usarás (`arrow::Table`, Parquet writer) han sido estables en el rango 12→24.
- Beneficios de 24.0: mejoras de rendimiento en escritura Parquet, mejor soporte de logical types (útil para `timestamp-micros` en `ingested_at`), y correcciones acumuladas de bugs en memory management y I/O que son relevantes para volúmenes de eventos de red.
- Riesgo de drift: bajo si usas el repo oficial `apache-arrow-apt-source` + pin explícito en `provision.sh` (igual que se hace con Kuzu). Ejemplo:
  ```bash
  apt install -y -V libarrow-dev=24.0.0-1 libparquet-dev=24.0.0-1
  ```

**Acción recomendada:** Actualizar `provision.sh` y `Vagrantfile` con el pin antes del próximo `vagrant up` limpio. Verificar post-instalación con `dpkg -l | grep arrow` y `apt-cache policy libarrow-dev`.

Si en el futuro aparece una 25.x con regresiones graves, siempre se puede bajar el pin (el esquema Parquet es estable).

### 2. Rango unsigned de puertos (src_port / dst_port)

**Decisión recomendada: usar `int` (signed 32-bit) en el esquema AVRO + documentación explícita en el `.avsc`.**

**Razones técnicas:**
- AVRO no tiene tipos unsigned nativos en el spec (solo `int` 32-bit signed, `long` 64-bit signed). Esto es intencional y consistente en todas las implementaciones (C, C++, Java, etc.).
- Rango real de puertos (0-65535) cabe perfectamente en `int32` signed (-2^31 a 2^31-1). No hay overflow ni pérdida de información.
- En la capa C++ (`uint32_t` del proto) → simplemente casteas o static_assert al escribir. La canonicalización es trivial y reproducible.
- Alternativas (no recomendadas aquí):
    - `long` → desperdicio de espacio y complejidad innecesaria.
    - Logical type custom unsigned → sobreingeniería para este caso (puertos son un dominio muy acotado).

**Acción:** En el archivo de esquema `correlation_gold_v1.avsc` añade un campo `doc`:

```json
{
  "name": "src_port",
  "type": "int",
  "doc": "Network port (0-65535). Stored as AVRO int (signed 32-bit). Real values never exceed 65535. See proto uint32_t."
}
```

Esto cierra la asimetría sin deuda adicional. No hace falta abrir una deuda formal; es una nota de implementación estándar cuando se mapea a Avro.

### 3. Formalización del documento

**Recomendación: formalízalo como ADR numerado (ej. ADR-059 o el siguiente disponible).**

**Razones:**
- El contenido es una decisión de arquitectura concreta (lenguaje, separación de responsabilidades, esquema materializado, particionamiento) que impacta el contrato de Flujo A y varias deudas P0/P1.
- Referenciarlo desde ADR-058 es correcto, pero tener un número propio facilita trazabilidad, revisión futura y vinculación en el backlog (`BACKLOG-CIRCUIT-ARROW-MEDALLION-001`).
- Lección DAY 175/199: mejor numerar que acumular “documentos de apoyo” que luego se pierden de vista.
- Proceso: verifica el siguiente número libre contra el índice de ADRs antes de asignar.

**Estructura sugerida para el ADR:**
- Mantén la sección “Invariante rector: medir, no votar”.
- Incluye las tablas de esquema, la decisión C++/avro-c + Arrow, la tabla de deudas cerradas y las respuestas del Consejo.
- Marca como “Ratificado” una vez mergeado.

### Observaciones generales positivas / menores

- **Excelente cierre de deudas** por diseño (especialmente `DEBT-CIRCUIT-PARSER-CROSSLANG-001`, `DEBT-GOLD-NODE-DIMENSION-001`, `DEBT-EVENT-ID-FACTORY-001`). El uso de `avro-c` + Arrow C++ puro es la opción más auditable y determinista.
- Particionamiento solo por `date=` es correcto en esta etapa. Evita complejidad prematura.
- `flow_uid` materializado + `flow_start_window` + `seq_in_window` permite verificación bit-exacta futura. Muy alineado con el espíritu del proyecto.
- HMAC por fila preservado → bueno. El HMAC del artefacto Parquet completo se diseña aparte (como indicas).

**Próximos pasos sugeridos (post-ratificación):**
1. Pin de versiones + update de provision.
2. Implementar el converter C++20.
3. Pruebas de round-trip: bronce AVRO → Parquet → re-lectura y verificación de equivalencia clase D (doubles canonicalizados).
4. Medir tamaño/velocidad en volúmenes reales antes de escalar particiones.

El documento está listo para ratificación formal. Proceded con la implementación del Flujo A una vez mergeado el ADR.

Cualquier experimento adicional (benchmark Arrow writer vs alternativas, edge cases de puertos, etc.) que necesitéis, pedidlo.

FDO
GROKK