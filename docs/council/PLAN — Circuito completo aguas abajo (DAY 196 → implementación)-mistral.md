Aironman DirtDiver, **el Consejo de Sabios se ha reunido**. Aquí están las respuestas, los desafíos y las objeciones a tu plan, **sin concesiones**. Vamos a desmenuzar los puntos críticos, las decisiones pendientes y los riesgos ocultos. **No hay palmaditas: solo fuego amigo y preguntas incómodas.**

---

---

## **🔥 CRÍTICAS ESTRUCTURALES (el Consejo no ratifica sin esto)**

### **1. El "circuito verde" es un espejismo si no se define "fluir" de forma medible**
Tesis:
> *"Un motor (aRGus) E2E antes de añadir adapters reales. Circuito verde = una fila entra por sniffer, sale enriquecida del ml-detector, aterriza en bronce como correlation_v1, la LZ la convierte a AVRO→PARQUET, Kuzu materializa el grafo, y el dashboard la recupera."*

**Problema:**
- **¿Qué significa "aterriza en bronce"?**
    - ¿Es suficiente con que el fichero CSV exista en el path esperado, o debe **validarse que el HMAC es correcto, las 19 columnas están presentes, y el `parse_and_verify` no descarta la fila**?
    - **[MEDIDO]** `correlation_reader.parse_and_verify` **descarta la fila en silencio** si falla el HMAC o el conteo de columnas. **Si el writer escribe basura, el circuito "fluye" pero el reader lo ignora.** ¿Dónde está la métrica de "flujo real"?
    - **Propuesta adversarial:** El circuito verde debe incluir **un test automático** que:
        1. Inyecta un evento sintético en el sniffer (ej: `NetworkSecurityEvent` con `community_id=TEST-123`).
        2. Verifica que el fichero en bronce **contiene la fila con HMAC válido**.
        3. Verifica que `correlation-engine` **lee la fila y la materializa en Kuzu** (ej: consulta Cypher `MATCH (f:NetworkFlow {community_id: "TEST-123"}) RETURN f`).
        4. **Falla el pipeline si cualquier paso falla.**

- **¿Y si el Kuzu actual no está configurado para leer desde el medallón?**
  **[POR VERIFICAR]** `kuzu_graph_sink` hoy lee **directamente el CSV de bronce** (`ifstream`). Si el medallón (AVRO/PARQUET) es nuevo, **¿existe ya el conector Kuzu para PARQUET?** Si no, el Eslabón 2 **no puede validarse** hasta que ese conector exista. **Riesgo: bloqueo oculto.**

---

### **2. La dualidad de pipelines Parquet es una bomba de tiempo**
**Decisión en §8.1:**
> *"El medallón de correlación es greenfield. Se reutilizan patrones, no código."*

**Problema:**
- **`scripts/parquet/` (RAG-127) y el medallón de correlación (correlation_v1) son dos pipelines paralelos con:**
    - **Firmas distintas** (Ed25519 vs HMAC-SHA256).
    - **Esquemas distintos** (127 columnas vs 19 columnas).
    - **Propósitos distintos** (análisis RAG vs grafo de correlación).
- **Riesgo:**
    - Si alguien confunde los pipelines (ej: usa el converter del RAG para el correlation_v1), **el HMAC fallará** (el converter del RAG no valida HMAC-SHA256).
    - **`DEBT-DOCS-MEDALLION-DUALITY-001` es insuficiente.** Se necesita:
        - **Nombres de directorios distintos y explícitos** (ej: `/parquet/rag/` vs `/parquet/correlation/`).
        - **Un test de integración** que verifique que el converter de correlación **no toca** los ficheros del RAG.
        - **Documentación en el README de cada pipeline** con un **⚠️ WARNING: NO CONFUNDIR CON...** en mayúsculas.

---

### **3. El hardcode de `bronze_root` es un síntoma, no el problema**
**Decisión en §6.3:**
> *"Sacar el hardcode de `zmq_handler.cpp:154` a JSON (Eslabón 0)."*

**Problema:**
- **El hardcode es solo la punta del iceberg.** El problema real es que **no hay un único JSON de configuración cross-componente.**
    - `ml-detector` tiene su `ml_detector_config.json`.
    - `correlation-engine` **no tiene JSON** (usa `--bronze` o `ARGUS_BRONZE_CSV`).
    - **¿Dónde vive `silver_root`/`gold_root`?** No existen aún (**[MEDIDO]**).
- **Riesgo:**
    - Si cada componente tiene su propio JSON, **el desync es inevitable** (como en DAY 194).
    - **Solución adversarial:**
        - **Un único JSON de infraestructura** (ej: `circuit_config.json`) que defina:
          ```json
          {
            "bronze_root": "/data/correlation/bronze",
            "silver_root": "/data/correlation/silver",
            "gold_root": "/data/correlation/gold",
            "zmq": {
              "ml_detector": { "pub": "tcp://*:5555", "sub": "tcp://localhost:5556" },
              "correlation_engine": { "sub": "tcp://*:5555" }
            }
          }
          ```
        - **Todos los componentes leen de este JSON** (o de un subconjunto generado por Ansible/Jinja2).
        - **El Eslabón 0 no es solo mover `bronze_root` a JSON: es definir el JSON único y obligar a todos a usarlo.**

---

### **4. La regla de centinela es ambigua en la práctica**
**Decisión en §5:**
> *"Centinela numérico: `-1` (preferencia). `0` es ambiguo para score/puerto."*

**Problema:**
- **`-1` en `src_port`/`dst_port`:**
    - **¿Qué significa un puerto `-1`?** En networking, los puertos son `0-65535`. `-1` es inválido, pero **¿el grafo Kuzu lo interpretará correctamente?**
    - **Riesgo:** Si Kuzu espera un `uint16` y recibe `-1`, **¿lo castea a 65535 (wrap-around) o lo rechaza?**
    - **Propuesta adversarial:**
        - **Usar `65535` como centinela para puertos** (máximo valor uint16, reservado para "no aplica").
        - **Usar `-1.0` para scores** (flotante, no ambigüo con `0.0`).
        - **Validar en el `parse_and_verify` que los centinelas sean consistentes** (ej: si `protocol` es `UNKNOWN`, entonces `src_port`/`dst_port` deben ser `65535`).

- **`UNKNOWN` en campos string:**
    - **¿Cómo se representa en Kuzu?** ¿Como `NULL` o como la cadena `"UNKNOWN"`?
    - **Riesgo:** Si Kuzu lo trata como `NULL`, **las consultas Cypher deben usar `IS NULL` en lugar de `= "UNKNOWN"`**.
    - **Propuesta adversarial:**
        - **Decidir ahora:** `UNKNOWN` en CSV → `NULL` en Kuzu.
        - **Documentar en el esquema de Kuzu** qué campos pueden ser `NULL`.

---

### **5. El "circuito verde" no incluye Wazuh, pero Wazuh es el elefante en la habitación**
**Decisión en §4:**
> *"Wazuh es categoría aparte. `host_key` NO es `community_id`. El join de Wazuh es por IP + ventana temporal."*

**Problema:**
- **El circuito verde (Eslabón 4) solo valida aRGus/Suricata/Zeek.** Wazuh **no cabrá en `correlation_v1` sin cambios** (**[MEDIDO]**).
- **Riesgo:**
    - Si el Consejo ratifica el circuito verde **sin resolver Wazuh**, **el 25% de los motores de seguridad quedarán fuera del grafo.**
    - **`DEBT-CORRELATION-V1-HOSTKEY-001` debe resolverse ANTES del Eslabón 4**, no después.
- **Propuesta adversarial:**
    - **Opción A:** Extender `correlation_v1` a `correlation_v2` con una columna `host_key` (rompe el sellado de 19 columnas, pero permite incluir Wazuh).
    - **Opción B:** Crear un **contrato separado `host_event_v1`** para Wazuh/Andrés, con su propio sink en bronce (ej: `/bronze/host/`).
    - **El Consejo debe decidir YA.** Si se elige la Opción B, **el Eslabón 5 (Wazuh) no puede ser posterior al Eslabón 4 (Suricata/Zeek).**

---

### **6. La migración a ZMQ PUB/SUB es un riesgo de regresión**
**Decisión en §7.6:**
> *"Eslabón 6: Migración a ZMQ PUB/SUB. Sustituir FS-drop por el contrato §7.1 en todos los adapters."*

**Problema:**
- **El FS-drop actual funciona.** ZMQ PUB/SUB **ya existe entre sniffer→ml-detector→firewall** (**[MEDIDO]**).
- **Riesgo:**
    - **¿Qué pasa si ZMQ falla en producción?** (ej: buffer lleno, mensajes perdidos).
    - **¿Hay métricas de latencia/throughput para ZMQ vs FS-drop?** Si no, **la migración es un salto de fe.**
    - **Propuesta adversarial:**
        - **Validar ZMQ en paralelo con FS-drop** (dual-write) antes de eliminar el FS-drop.
        - **Definir un SLA de latencia** (ej: <100ms por evento) y **un test de carga** (ej: 10K eventos/segundo).
        - **Si ZMQ no cumple el SLA, se revierte a FS-drop.**

---

### **7. El oro-como-ledger vs oro-como-join es una decisión con consecuencias a largo plazo**
**Decisión en §10.2:**
> *"Lean: oro-como-ledger + join en Kuzu."*

**Problema:**
- **Oro-como-ledger:**
    - **Ventaja:** Flexibilidad (Kuzu hace el join).
    - **Desventaja:** **El oro no es auto-suficiente.** Si Kuzu falla, **el grafo no puede reconstruirse** (el oro son solo filas sueltas).
- **Oro-como-join:**
    - **Ventaja:** El oro es un dataset completo y auto-suficiente.
    - **Desventaja:** **Pérdida de flexibilidad** (si se añade un nuevo motor, hay que re-hacer el join).
- **Riesgo:**
    - **Si el oro es el ledger inmutable (Via Appia), ¿cómo se garantiza su integridad?**
        - **Propuesta adversarial:**
            - **Firmar el oro con HMAC** (como en bronce).
            - **Almacenar checksums en un lado** (ej: `gold_root/checksums.sha256`).
- **El Consejo debe decidir:**
    - **¿El oro es un ledger (dato crudo) o un dataset correlacionado (dato procesado)?**
    - **¿Qué consumidores tendrán acceso al oro?** (Si solo Kuzu, el ledger es suficiente. Si hay otros, el join puede ser necesario).

---

---
---
## **⚖️ DECISIONES QUE EL CONSEJO EXIGE RATIFICAR (o rechazar)**

| **Pregunta** | **Opciones** | **Recomendación del Consejo (con objeciones)** |
|--------------|-------------|-----------------------------------------------|
| **1. Formato de salida del adapter (A vs B).** | A: Envelope protobuf intermedio. B: `correlation_v1` directo a bronce. | **B (ratificado).** Pero: **El AdapterSpec v1.1 debe dejar claro que NO hay envelope protobuf.** El §3 actual es **vapor de documento** y debe eliminarse. |
| **2. Forma del oro.** | A: Join en Arrow (oro fundido). B: Ledger + join en Kuzu. | **B (ledger + join en Kuzu).** Pero: **Se requiere un mecanismo de validación de integridad del oro (HMAC/checksums).** |
| **3. Centinela numérico.** | A: `-1`. B: `0`. | **A (`-1` para scores, `65535` para puertos).** Pero: **Validar que Kuzu no castee `-1` a 65535.** |
| **4. Rotación/follow.** | A: Engine vigila directorio (sigue el fichero más nuevo). B: Lanzador recalcula datado. | **A (vigilar directorio).** Pero: **¿Cómo se maneja el caso de ficheros corruptos? ¿Se salta el fichero o se para el pipeline?** |
| **5. Wazuh.** | A: Extender `correlation_v1` a `v2` con `host_key`. B: Contrato `host_event_v1` separado. | **B (contrato separado).** Pero: **El Eslabón 5 (Wazuh) debe ser PRIORITARIO, no posterior al Eslabón 4.** |
| **6. Andrés.** | A: Mantener stub. B: Eliminar del scope. | **A (stub).** Pero: **Documentar explícitamente que Andrés NO forma parte del circuito verde.** |

---

---
---
## **🚨 RIESGOS OCULTOS (el Consejo los señala)**

1. **El `correlation-engine` hoy lee CSV directamente.**
    - **Si el medallón (AVRO/PARQUET) no tiene un conector Kuzu listo, el Eslabón 2 está bloqueado.**
    - **Acción:** Verificar si existe `kuzu_parquet_sink` o similar. Si no, **priorizar su implementación.**

2. **La LZ (Landing Zone) es greenfield, pero no hay dueño claro.**
    - **¿Quién implementa el converter CSV→AVRO→PARQUET?** ¿El equipo de Kuzu? ¿El equipo de infra?
    - **Riesgo:** Sin dueño, **el Eslabón 1 se alargará indefinidamente.**

3. **El `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` no tiene solución propuesta.**
    - **Opción A (engine vigila directorio):**
        - **¿Cómo se maneja el caso de múltiples ficheros nuevos?** (ej: `2026-06-26.csv`, `2026-06-27.csv`).
        - **¿Se procesan en orden? ¿Se asume que el último fichero es el más reciente?**
    - **Opción B (lanzador recalcula datado):**
        - **¿Quién es el "lanzador"?** ¿Un cron? ¿Un script externo?
        - **Riesgo:** Si el lanzador falla, **el pipeline se para.**

4. **El `DEBT-PARQUET-TIMESTAMP-NS-001` no está resuelto.**
    - **El converter RAG-127 tiene un workaround (`x1_000_000`) para ns.**
    - **Propuesta:** **Fusionar `flow_start_sec` + `flow_start_nano` en el writer C++ (Eslabón 0).**

5. **El `firewall-acl-agent` ya usa ZMQ PUB/SUB.**
    - **¿Por qué no reutilizar ese patrón para los adapters?**
    - **Riesgo:** Si los adapters usan un patrón distinto, **habrá dos implementaciones de ZMQ en el sistema.**

---
---
## **📌 ACCIONES INMEDIATAS (el Consejo las exige)**

1. **Definir el JSON único de configuración (`circuit_config.json`)** y obligar a todos los componentes a usarlo. **Eslabón 0 no puede ser solo mover `bronze_root` a JSON: debe ser el JSON cross-componente.**
2. **Implementar un test de circuito verde automático** (inyectar evento sintético → verificar HMAC → verificar Kuzu).
3. **Decidir YA el formato del oro (ledger vs join)** y documentar las consecuencias.
4. **Resoler `DEBT-CORRELATION-V1-HOSTKEY-001` ANTES del Eslabón 4.** Si se elige contrato separado para Wazuh, **el Eslabón 5 debe ser prioritario.**
5. **Verificar si existe `kuzu_parquet_sink`.** Si no, **priorizar su implementación (Eslabón 2 bloqueado).**
6. **Asignar dueño a la LZ (Landing Zone).** Sin dueño, **el Eslabón 1 no avanza.**
7. **Documentar la dualidad Parquet (RAG vs correlación) con warnings explícitos.**

---
---
## **💥 PREGUNTAS DIRECTAS AL EQUIPO (sin escapatoria)**

1. **¿Cómo garantizan que el `parse_and_verify` no descarta filas en silencio durante el circuito verde?** ¿Hay logs de filas descartadas?
2. **¿Qué métricas de latencia/throughput tienen para ZMQ vs FS-drop?** Si no las tienen, **¿cómo justifican la migración?**
3. **¿Quién es el dueño de la implementación de la LZ (converter CSV→AVRO→PARQUET)?** Si no hay dueño, **¿cómo garantizan que el Eslabón 1 se completa?**
4. **Si el oro es el ledger inmutable (Via Appia), ¿cómo garantizan su integridad?** ¿HMAC? ¿Checksums?
5. **¿Qué pasa si Kuzu no soporta PARQUET?** ¿Hay un plan B?
6. **¿Por qué no se usa el patrón ZMQ PUB/SUB del `firewall-acl-agent` para los adapters?** ¿Hay una razón técnica o es solo falta de coordinación?
7. **¿Cómo se maneja el caso de ficheros corruptos en bronce?** ¿Se salta el fichero? ¿Se para el pipeline? ¿Se notifica?

---
---
## **🎯 CONCLUSIÓN DEL CONSEJO**
El plan es **sólido en su estructura**, pero **frágil en los detalles**. Las decisiones clave (oro como ledger, centinelas, Wazuh) **deben ratificarse YA**, y los riesgos ocultos (dualidad Parquet, conector Kuzu-PARQUET, dueño de la LZ) **deben resolverse antes de avanzar**.

**El Consejo no aprueba el plan hasta que:**
✅ Se defina el JSON único de configuración.
✅ Se implemente el test de circuito verde automático.
✅ Se resuelva `DEBT-CORRELATION-V1-HOSTKEY-001` (Wazuh).
✅ Se verifique la existencia de `kuzu_parquet_sink`.
✅ Se asigne dueño a la LZ.

**¿Aceptan el desafío, o prefieren revisar el plan?** *(El Consejo no se andará con rodeos: si no se resuelven estos puntos, el circuito verde será un espejismo.)*

FDO

MISTRAL