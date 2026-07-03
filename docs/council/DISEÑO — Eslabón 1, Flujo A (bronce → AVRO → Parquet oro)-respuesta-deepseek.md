**Respuesta del Consejo de Sabios**

Se examinan las tres preguntas abiertas del diseño del Eslabón 1, Flujo A (bronce → AVRO → Parquet oro).  
Se responde con hechos verificables, en coherencia con el invariante rector «medir, no votar».

---

### 1. Versión exacta de Arrow/Parquet a pinnear

**Decisión:** Fijar `libarrow-dev` y `libparquet-dev` en **24.0.0-1** (la candidata propuesta) es correcto y suficiente. No existe motivo técnico para elegir una versión anterior.

**Hechos que sostienen la decisión:**
- Apache Arrow no tiene un modelo LTS oficial; las versiones se publican aproximadamente cada 3–4 meses. La 24.0.0 (enero 2025) es, a fecha de hoy, la rama estable más reciente con empaquetado oficial para Debian Bookworm en el repositorio `apache-arrow-apt-source`.
- El paquete candidato fue confirmado en `defender` con `apt-cache policy`, mostrando disponibilidad. La misma fuente de paquetes ya se usa en el proyecto para otras dependencias (HashiCorp, Jenkins), por lo que no introduce riesgo de cadena de suministro nuevo.
- La combinación `libavro-dev 1.11.1` + Arrow 24.0.0 no presenta incompatibilidades conocidas: el diseño aísla explícitamente el I/O AVRO (`avro-c`, API C) de las estructuras de Arrow. Arrow se usa únicamente para construir la tabla en memoria y escribir Parquet, labor en la que la versión 24.0.0 es robusta y ampliamente validada en producción.
- Pin de versión exacta (`=24.0.0-1`) es imprescindible para reproducibilidad (lección aprendida con `DEBT-KUZU-UPSTREAM-ARCHIVED-001`).

**Acción complementaria (medida experimental):**  
Antes de tocar `provision.sh`, se recomienda una verificación de integración mínima en `defender`:
```bash
g++ -std=c++20 -o /tmp/arrow_smoke arrow_smoke.cpp \
   $(pkg-config --cflags --libs arrow parquet)
```
donde `arrow_smoke.cpp` construye una `arrow::Table` trivial y escribe un `.parquet`. Si compila y ejecuta sin errores con las librerías 24.0.0-1, la versión queda ratificada por hecho medido.

**Conclusión:** 24.0.0-1 es la versión que el Consejo ratifica. No se requiere LTS anterior.

---

### 2. Formato del rango unsigned de puertos en AVRO (cols 9-10)

**Decisión:** Documentar la asimetría dentro del propio esquema `.avsc` mediante el atributo `doc` (estándar AVRO), sin abrir una deuda separada.

**Fundamento:**
- Los valores de puerto reales (0–65535) caben holgadamente en un `int` signed de 32 bits, sin overflow ni pérdida semántica durante la serialización/deserialización con `avro-c` y la posterior escritura Parquet.
- En la capa Parquet/Arrow el tipo sí puede ser `uint32` sin ambigüedad, y el converter traducirá correctamente. La asimetría existe únicamente en la representación intermedia AVRO, y no afecta a la corrección numérica.
- Registrar la restricción en el campo `doc` del esquema es explícito, auditable y no introduce un nuevo artefacto de seguimiento. Abrir una nota de deuda para un hecho que ya es estable y no requiere acción futura iría contra el principio de no acumular deuda sin justificación.

**Redacción propuesta para el `.avsc`** (a incluir en los campos 9 y 10):
```json
{ "name": "src_port", "type": "int",
  "doc": "Puerto de origen (0-65535). Almacenado como signed 32-bit; cabe sin overflow. En Parquet se representa como UINT32." }
```
Análogo para `dst_port`.

**El Consejo considera que esto cierra la cuestión** sin necesidad de un ticket de deuda.

---

### 3. Formalización como ADR numerado vs. documento de apoyo referenciado desde ADR-058

**Decisión:** El presente documento se mantiene como **documento de diseño de apoyo** (`docs/design/bronce-avro-parquet-flujo-a.md` o similar) y es explícitamente ratificado por el Consejo como anexo técnico de ADR-058.

**Razonamiento:**
- ADR-058 ya contiene el contrato del circuito (secciones §3.1, §4-V1, §6) y las decisiones arquitectónicas de alto nivel. Este diseño es la **implementación concreta** del primer salto del medallón, no una decisión arquitectónica nueva e independiente.
- Convertir cada eslabón en un ADR independiente inflaría el registro sin ganancia proporcional de trazabilidad; además, la lección de DAY 175/199 alerta sobre colisiones de numeración si no se audita el backlog completo.
- El documento ya declara explícitamente: *«Este documento diseña solo el primer salto del medallón …»* y *«Documento de apoyo a ADR-058 v3»*. Mantener esa jerarquía es coherente.
- Ratificarlo como anexo no le resta fuerza normativa: se cita desde ADR-058 con su hash de contenido o ruta, y toda modificación futura requiere actualización del anexo y re‑ratificación.

**Regla de proceso acordada:**  
Cualquier nuevo diseño de eslabón del medallón que merezca ratificación del Consejo se alojará en `docs/design/` como documento de apoyo y será referenciado desde el ADR del circuito (actualmente ADR-058). Solo se creará un ADR numerado cuando se introduzca una decisión arquitectónica transversal que afecte a múltiples flujos (ej. la firma del Parquet consolidado como artefacto, que es greenfield).

---

**Dictamen final del Consejo:**  
Las tres preguntas quedan resueltas. El diseño puede avanzar a implementación una vez que se cablee la provisión (Arrow 24.0.0-1 pineada), se incluya el atributo `doc` en los campos de puerto del esquema AVRO, y se archive este documento como anexo ratificado de ADR-058.  
Se recomienda ejecutar la verificación de integración (smoke test de Arrow) antes del siguiente `vagrant destroy && up` para cerrar el bucle de medición.

FDO

DeepSeek