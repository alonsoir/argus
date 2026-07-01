Voy a analizar el ADR-058 como miembro del Consejo, buscando defectos potenciales en el diseño presentado.

---

## Defectos Identificados en ADR-058

### 🔴 **DEFECTO-1: Predicado de equivalencia §3.1 — `event_id` no está definido en el contrato bronce**

El predicado requiere `set(event_id)_C0 == set(event_id)_AB` para `Alert ∪ TelemetryEvent`, pero **el contrato de 19 columnas del bronce no incluye `event_id`**.

- El bronce tiene `flow_uid` como identidad (ADR-052), pero `Alert`/`TelemetryEvent` son **entidades generadas aguas abajo** (por el detector ML o el correlador), no existen en el bronce.
- **Consecuencia:** `set(event_id)_C0` está vacío o undefined. El predicado compara `∅ == ∅`, lo cual es trivialmente verdadero y **no verifica nada**. El test de equivalencia sería un falso positivo si el Flujo A+B produce alerts/telemetry pero Camino 0 no las genera.
- **Recomendación:** O bien (a) el predicado debe restringirse a lo que ambos caminos **realmente** producen (el grafo `NetworkFlow` es el mínimo común), o (b) debe definirse cómo Camino 0 genera `event_id` (¿en qué línea de `main.cpp`? No está medido en V1-V9).

> Esto contradice el invariante "medir, no votar": el predicado asume que `event_id` existe en ambos lados sin haberlo medido en el bronce.

---

### 🔴 **DEFECTO-2: MERGE con `ON CREATE SET` únicamente — pérdida de fidelidad silenciosa que el predicado enmascara**

El ADR celebra (§3.1, V7) que la colisión de `flow_uid` es "neutralizada para equivalencia" porque ambos caminos descartan idénticamente. Pero **omite que el MERGE también enmascara divergencias reales**:

- Si Camino 0 y Flujo A+B **difieren en propiedades** de un flujo legítimo (mismo `flow_uid`, distintos scores por bug del converter), el segundo en llegar hace MATCH puro y **ambos caminos terminan con las propiedades del primero** — pero **¿cuál es el primero?** El orden de llegada depende del filesystem, del scheduler, del batch size.
- El predicado §3.1 dice `props_identidad(uid)_C0 == props_identidad(uid)_AB`, pero si ambos hacen MERGE y el segundo pierde, la igualdad es **artefacto del orden de ejecución del test**, no del contenido real de los caminos.
- **Recomendación:** El test de equivalencia debe usar `CREATE` puro (fallando en colisión) o comparar **antes** del MERGE. Usar MERGE en el predicato de equivalencia es medir la **convergencia del sink**, no la **equivalencia de los caminos**.

---

### 🟡 **DEFECTO-3: `flow_start_window` como "columna hash-input" — inconsistencia con ADR-052**

V1 decide materializar `flow_start_window` como columna del oro porque "el día que cambie el bucketing de `window_micros()`, el `flow_uid` re-derivado deja de coincidir".

- Pero ADR-052 establece que `flow_uid` es la **PK del grafo** y se computa en bronce. Si el bucketing cambia, **el `flow_uid` del bronce también cambia** (es input del hash).
- Materializar `flow_start_window` en el oro **no resuelve** la reversibilidad: el `flow_uid` del bronce ya está quemado con el bucketing viejo. La única forma de re-verificar es tener el **bucketing versionado**, no la window materializada.
- Además: si `flow_start_window` es "columna hash-input", ¿por qué no se incluye en el encoding de `flow_uid`? El encoding (§3.1, V9) usa `node_id`, `community_id`, `window`, `seq`. Si `flow_start_window` es hash-input, **debe estar en el encoding** — pero V9 dice que `window` ya está ahí (`put_be64`). Entonces V1 añade una columna que **ya es input del hash** pero no del contrato bronce. Esto es **redundancia con riesgo de divergencia**: el oro tendría `flow_start_window` como columna, pero el bronce la deriva. Si alguien modifica `window_micros()` en el reader pero no en el writer, el oro diverge del bronce sin que el predicado lo capture (porque el predicado compara oro vs oro, no oro vs bronce).

---

### 🟡 **DEFECTO-4: "Bit-exact por defecto" — el argumento de cancelación es circular**

La justificación de bit-exactitud (§3.1) dice: "ambos caminos parten del mismo double → la degradación es idéntica y se cancela".

- **Esto es cierto solo si ambos caminos leen el mismo texto**. Pero Flujo A incluye **AVRO → Parquet → Kuzu**. En ese tramo, el double puede pasar por:
    1. Serialización AVRO (binary, OK)
    2. Escritura Parquet (columnar, puede usar `FLOAT` si el schema se genera mal)
    3. Lectura Parquet por el conector (puede usar `float32` → `float64` promotion)
    4. Inserción Kuzu (¿qué tipo declara `schema.cypher` para los scores? No está medido en V1-V9)
- El argumento "AVRO double y Parquet DOUBLE son IEEE 754 binary64" **asume que el schema Parquet se genera correctamente**. Pero el schema Parquet es **greenfield** (§3) — no existe. El bug más probable es exactamente ahí: el converter genera un schema con `FLOAT` en vez de `DOUBLE`, o Kuzu declara `FLOAT` en el Cypher.
- La cláusula de escape ε ("se introduce solo si la medición lo exhibe") **posterga el problema al futuro**, pero el ADR debería **prevenirlo**: exigir que el schema Parquet y el `schema.cypher` de Kuzu declaren explícitamente `DOUBLE` para los scores, y que el test verifique el schema, no solo los datos.

---

### 🟡 **DEFECTO-5: HMAC del Parquet consolidado — "greenfield, HMAC-SHA256 coherente con bronce"**

§2.6 dice que la firma del Parquet es HMAC-SHA256, "NO reutiliza el firmador Ed25519 del pipeline `scripts/parquet/`".

- **Pregunta no respondida:** ¿cuál es la clave del HMAC? En el bronce, el HMAC es "por-fila" con clave verificable. En el Parquet consolidado, ¿es por-bloque? ¿por-archivo? ¿La misma clave?
- Si la clave es la misma, la firma del archivo Parquet **no es coherente con el HMAC por-fila del bronce** (son primitivas distintas: HMAC por fila vs HMAC del archivo). Si es distinta, ¿dónde se documenta?
- `DEBT-GOLD-INTEGRITY-HMAC-001` está en P0 pero **el ADR no define el mecanismo**, solo la intención. Esto es "votar" (decidir que será HMAC) sin "medir" (definir la clave, el alcance, la verificación).

---

### 🟡 **DEFECTO-6: Eslabón 0 en el mismo PR que el ADR — violación del invariante de trazabilidad**

§7 dice: "El ADR entra en el mismo PR que el Eslabón 0 (commit de doc no pasa gate de build, va con la implementación)".

- Pero el ADR afirma estar "trazado a `fichero:línea` del binario". Si el ADR se mergea **con** la implementación, no puede haber sido validado **contra** la implementación antes del merge. Es un **post-hoc rationalization**, no una decisión medida pre-merge.
- El Consejo ratifica el ADR **después** de leerlo, pero la implementación ya está en el PR. La ratificación es teórica, no un gate real.
- **Recomendación:** Separar: PR del ADR (solo doc, ratificación del Consejo), luego PR de implementación (contra el ADR ratificado). O aceptar que este ADR es **retrospectivo** (documenta decisiones ya tomadas en el plan DAY 196-197), no prospectivo.

---

### 🟢 **DEFECTO-7 menor: "Vectores congelados verificados byte-idénticos C++ ↔ `hashlib.blake2b`"**

V9 afirma paridad cross-language congelada, pero no cita **dónde** viven esos vectores. Si el converter Flujo A es Python (§3.1 sugiere "o, si es Python, los vectores golden congelados"), ¿dónde están?

- Si no están en el repo, el converter puede "reusar" un encoding que **cree** ser el mismo pero no está verificado. La deuda `DEBT-FLOWUID-CANONICAL-ENCODING-001` está "resuelta de facto" pero la acción residual ("converter reusa") no tiene mecanismo de verificación.

---

## Resumen para el Consejo

| # | Severidad | Defecto | Bloquea cierre? |
|---|-----------|---------|-----------------|
| 1 | 🔴 Alto | `event_id` no existe en bronce → predicado vacío para alerts/telemetry | **SÍ** — el test de equivalencia es falso positivo |
| 2 | 🔴 Alto | MERGE enmascara divergencias reales por orden de ejecución | **SÍ** — el predicado mide el sink, no los caminos |
| 3 | 🟡 Medio | `flow_start_window` redundante y no trazada al bronce | No, pero introduce deuda técnica |
| 4 | 🟡 Medio | Bit-exact asume schema Parquet/Kuzu correcto sin medirlo | No, pero el argumento es circular |
| 5 | 🟡 Medio | HMAC del Parquet sin definir clave ni alcance | No, P0 sin especificación |
| 6 | 🟡 Medio | ADR + implementación en mismo PR = ratificación post-hoc | No, pero debilita el proceso |
| 7 | 🟢 Bajo | Vectores golden no referenciados en el ADR | No |

### Mi recomendación como miembro del Consejo:

**No ratificar** hasta que:
1. El predicado §3.1 se restrinja a lo **medible** en ambos caminos (`NetworkFlow` como mínimo común), o se defina explícitamente cómo Camino 0 genera `event_id` (con `fichero:línea`).
2. El test de equivalencia use `CREATE` puro (con manejo de colisión explícito) o compare los outputs **antes** del MERGE, para no enmascarar divergencias.
3. Se documente el tipo `DOUBLE` explícito en el schema Parquet greenfield y en `schema.cypher` de Kuzu, con verificación de schema en el test (no solo de datos).

Los demás defectos (3-7) pueden abordarse como deudas P1/P2, pero 1 y 2 socavan la integridad del gate de cierre del medallón.

FDO 

KIMI