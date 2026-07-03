# Dictamen del Consejo de Sabios — Eslabón 1, Flujo A

He revisado el documento con la atención que merece un diseño que toca el corazón del circuito. A continuación, mi respuesta a cada una de las tres preguntas explícitas, con hechos verificables donde es posible y juicio fundado donde no.

---

## 1. Versión de Arrow/Parquet a pinnear

**Dictamen: pinna `libarrow-dev=24.0.0-1` / `libparquet-dev=24.0.0-1` explícitamente.**

No hay razón técnica para retroceder a una LTS anterior. Arrow 24.x es estable, y la política del proyecto ("medir, no votar") favorece la versión que ya has medido en `defender`. Pinna con `=` en `provision.sh`, igual que hiciste con Kuzu.

**Hecho verificable que añade peso:** Arrow 24.0.0 usa Parquet format 2.6 internamente, que es backward-compatible con lectores 12.x+. Si en el futuro necesitas downgrade por alguna razón, los archivos escritos con 24.0.0 seguirán legibles. No es un one-way door.

**Nota de implementación:** en `provision.sh`, instala `apache-arrow-apt-source` primero (sin pin, es solo el repo), luego pinna la versión exacta de los paquetes binarios:

```bash
apt-get install -y -V libarrow-dev=24.0.0-1 libparquet-dev=24.0.0-1
```

Si el índice del repo de Arrow hace downgrade de versión en el futuro, `apt-get` fallará en lugar de traer drift silencioso. Eso es el comportamiento deseado.

---

## 2. Formato del rango unsigned de puertos (cols 9-10)

**Dictamen: documenta la asimetría en el esquema AVRO con un `doc` field, no abras deuda menor.**

Los puertos reales (0-65535) caben sin overflow en `int` signed de 32 bits. El riesgo no es técnico, es semántico: un lector futuro del esquema podría asumir que `int` implica negativos permitidos.

Añade en el `.avsc`:

```json
{
  "name": "src_port",
  "type": "int",
  "doc": "Unsigned uint32_t del proto. Rango válido: 0-65535. Valores >= 2^31 son reservados para extensión futura."
}
```

Esto cierra la pregunta sin deuda. Si alguna fuente futura (Suricata/Zeek) genera un campo que sí necesita el rango completo de `uint32_t`, ese será un cambio de esquema consciente, no una sorpresa.

---

## 3. ¿Formalizar como ADR numerado o documento de apoyo?

**Dictamen: queda como documento de apoyo referenciado desde ADR-058, sin número propio.**

Razones:

- El alcance es un *sub-diseño* del Flujo A, ya trazado en ADR-058 §3.1, §4-V1, §6. No introduce una decisión arquitectónica nueva; detalla una que ya existe.
- La lección del DAY 175/199 (colisión de numeración) pesa. El backlog de ADRs del proyecto ya tiene `ADR-024`, `ADR-026`, `ADR-027`, `ADR-058`. Añadir `ADR-059` por un sub-diseño crea ruido en el índice.
- El formato "Consejo de Sabios" que ya usas (`DISEÑO — Eslabón 1, Flujo A`) es suficientemente explícito. La trazabilidad se mantiene vía el campo `Relacionado:`.

**Excepción futura:** si el Flujo A se desglosa en múltiples documentos de diseño (por ejemplo, cuando llegue `BACKLOG-CIRCUIT-ARROW-MEDALLION-001` y la unificación cross-sensor), entonces sí conviene un ADR-0XX que actúe como índice del medallón completo. Hoy no.

---

## Observaciones adicionales del Consejo (no solicitadas, pero pertinentes)

### Sobre la separación `avro-c` / Arrow C++

La decisión es sólida. Arrow C++ tiene soporte AVRO vía `arrow::dataset`, pero es experimental y depende de una build con `ARROW_WITH_AVRO=ON`, que no está garantizada en los paquetes Debian. Tu patrón (C library wrappada en C++20, auditable, sin binding intermedio) es el mismo que justificó `CorrelationWriter` con OpenSSL. Coherencia arquitectónica.

### Sobre la canonicalización de doubles (cols 14-16)

Confirmo que tu estrategia (NaN → quiet `0x7ff8000000000000`, `-0.0` → `+0.0`) en el punto único de escritura es la única forma de hacer `EQUIV(Camino0, FlujoA+B)` bit-exacta. En C++20, `std::bit_cast<uint64_t>` desde `<bit>` es la herramienta correcta para inspeccionar el patrón de bits sin UB. No uses `reinterpret_cast` para esto.

### Sobre `DEBT-GOLD-INTEGRITY-HMAC-001`

Preservar `hmac_row` como columna (col 18) satisface la integridad por fila. La firma del Parquet consolidado como artefacto que mencionas en §4 es un diseño aparte — y correctamente lo dejas fuera de este documento. Cuando llegue, no reutilices el firmador Ed25519 de `scripts/parquet/`; un HMAC-SHA256 con clave derivada del nodo es más apropiado para un artefacto de almacenamiento que para un mensaje de red.

---

**Estado de este dictamen:** listo para ratificación. Si el Consejo está de acuerdo, el siguiente paso es cablear `libavro-dev` y `libarrow-dev=24.0.0-1` / `libparquet-dev=24.0.0-1` en `provision.sh` con los pines explícitos, y generar el `.avsc` con el `doc` field en los puertos.
FDO
KIMI