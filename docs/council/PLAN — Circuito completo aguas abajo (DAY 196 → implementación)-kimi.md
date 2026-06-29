# Deliberación del Consejo de Sabios — DAY 196

## Dictamen: **APROBADO CON ENMIENDAS OBLIGATORIAS**

He revisado el plan como adversario, no como palmaditas. Hay acierto estratégico, pero también grietas que pueden derrumbar el circuito si no se sellan **antes** del primer commit. A continuación, mi veredicto por secciones, con la agresividad que pediste.

---

## 1. La tesis es correcta, pero el orden de trabajo tiene un fallo de dependencia

> "chapu de FS primero, verificar flujo aguas abajo, y solo entonces migrar a ZMQ"

**Problema:** El Eslabón 0 (config JSON) y el Eslabón 1 (Landing Zone) son **independientes** en su implementación pero **dependientes** en su validación. Si haces el chapu FS sin definir el contrato de rotación (§9, `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001`), el "circuito verde" que declares puede ser **falso positivo**: pasará las pruebas a las 23:59 y fallará silenciosamente a las 00:01.

**Enmienda obligatoria:** El Eslabón 0 debe incluir **explicitamente** una decisión sobre rotación. No puede ser "dejamos el chapu y ya veremos". El engine debe o bien:
- (a) Leer el directorio y auto-seleccionar el fichero más reciente (vigila directorio), o
- (b) Recibir el path exacto del lanzador (recalcula datado).

Mi recomendación: **(a)** para el chapu, porque el lanzador Vagrant no tiene mecanismo de recálculo sin re-provisionar. Pero (a) introduce una race condition si el writer rota exactamente cuando el engine lee. Documenta la race; no la ignores.

---

## 2. AdapterSpec v1.1 — La enmienda es correcta, pero incompleta

La decisión de reescribir §3 para reflejar que la salida real es `correlation_v1` CSV+HMAC (no protobuf) es **sólida** y cierra el desync DAY 194. Pero el documento deja una pregunta sin responder:

**¿Qué pasa con el HMAC en la migración a ZMQ?**

El `correlation_v1` actual firma la fila CSV completa (cols 0-17). Cuando migres a ZMQ PUB/SUB (Eslabón 6), el mensaje en el cable no es CSV — es un frame ZMQ con la carga útil. ¿El HMAC se calcula sobre:
- (i) La serialización CSV de los campos (manteniendo compatibilidad con el lector actual)?
- (ii) Un nuevo esquema de firma sobre el frame ZMQ?

Si eliges (ii), rompes compatibilidad con `correlation_reader.parse_and_verify`. Si eliges (i), estás arrastrando CSV como formato de serialización interna **dentro** de ZMQ, lo cual es feo pero funcional.

**Enmienda obligatoria:** Especificar en AdapterSpec v1.1 que el contrato de transporte ZMQ (§7.1) transporta **bytes del CSV firmado**, no un protobuf re-ensamblado. El envelope ZMQ es solo framing; el cuerpo sigue siendo `correlation_v1` CSV+HMAC. Esto preserva `parse_and_verify` sin cambios cuando llegue el Eslabón 6.

---

## 3. La regla de centinela — `-1` es correcto, pero falta un caso

Confirmo `-1` para numéricas ausentes. `0` es ambiguo para puertos (puerto 0 existe en TCP/UDP como reservado) y para scores (0 es un score válido, "no amenaza detectada").

**Pero:** ¿Qué pasa con `flow_start_sec` y `flow_start_nano` cuando el motor no puede derivar timestamp? `-1` en epoch seconds es 1969. Si Kuzu o el dashboard interpretan eso como fecha válida, tendrás flujos "detectados" en plena Guerra Fría.

**Enmienda obligatoria:** El centinela temporal debe ser **par de centinelas**: `(-1, -1)` para (sec, nano). El lector C++ ya descarta "campo numérico ilegible", pero el grafo debe interpretar el par como `null` temporal, no como `1969-12-31T23:59:59`. Documenta esto en el contrato de ingesta a Kuzu.

---

## 4. Landing Zone / medallón — La arquitectura por componente es acertada, pero hay un riesgo de coherencia

La decisión de zonas LZ independientes por motor (`LZ-argus`, `LZ-suricata`, etc.) con oro compartido es **la correcta** dado el staleness diferencial (Zeek ~5 min). Pero introduces un problema que no abordas:

**¿Quién coordina el "orchestrator" que decide cuándo una zona ha terminado su batch y puede contribuir al oro?**

Si `LZ-zeek` tiene un flujo que cierra a los 5 minutos, y `LZ-argus` emite en tiempo real, el oro compartido necesita saber cuándo "congelar" una ventana temporal para hacer el join. Sin un coordinador, el oro será eventualmente consistente con un lag no acotado.

**Enmienda obligatoria:** Define el SLO de staleness del oro. No necesitas un coordinador distribuido todavía, pero necesitas documentar que el oro es **best-effort join con ventana temporal configurable** (ej. "el oro incluye todo lo que haya llegado hasta T-30s"). Esto impacta el dashboard: las consultas deben asumir que el oro puede no tener el join más reciente.

---

## 5. Oro-como-ledger vs oro-como-join — Mi voto: **oro-como-ledger + join en Kuzu**

Tu lean ya argumenta bien por esta opción. Añado un argumento adversarial:

**Si eliges oro-como-join (arrow funde):**
- Pierdes la trazabilidad de qué motor aportó qué campo en el wide-table. Si Suricata dice `threat_category="Malware"` y Zeek dice `threat_category="C2"`, el wide-table debe elegir uno (¿el último? ¿un array?). Eso es pérdida de información.
- El wide-table aplanado obliga a un esquema rígido: cada nuevo motor puede requerir nuevas columnas. Con oro-como-ledger, añadir un motor es añadir filas con el mismo `community_id`, no alterar el esquema.

**Con oro-como-ledger:** Kuzu materializa `:NetworkFlow` con `community_id` como clave primaria, y cada detección es un nodo `:Detection` con arista `:detectado_en → :NetworkFlow`. El join es la estructura del grafo, no una operación ETL.

**Enmienda obligatoria:** Especifica el DDL de Kuzu en el plan. Sin el DDL, "re-apuntar a oro-PARQUET" (§7, Eslabón 2) es vago. Necesitas:

```cypher
CREATE NODE TABLE NetworkFlow(
    community_id STRING PRIMARY KEY,
    src_ip STRING,
    dst_ip STRING,
    src_port INT64,
    dst_port INT64,
    protocol STRING,
    flow_start TIMESTAMP
);

CREATE NODE TABLE Detection(
    detection_id STRING PRIMARY KEY,
    source_sensor STRING,
    event_id STRING,
    final_classification STRING,
    threat_category STRING,
    ml_detector_score DOUBLE,
    overall_threat_score DOUBLE,
    authoritative_source STRING,
    detected_at TIMESTAMP
);

CREATE REL TABLE detected_en(
    FROM Detection TO NetworkFlow,
    MANY_MANY
);
```

Esto obliga a que `detection_id` sea único global. ¿Cómo se genera? Propuesta: `<source_sensor>:<native_event_id>:<timestamp_utc_ns>`.

---

## 6. Wazuh y `host_key` — No lo pospongas tanto

Tu plan deja Wazuh para el Eslabón 5, con `DEBT-CORRELATION-V1-HOSTKEY-001`. Pero la decisión de esquema impacta el **Eslabón 1** (LZ), porque la estructura del parquet plata depende de si `host_key` existe o no.

**Enmienda obligatoria:** Decide el esquema de Wazuh **antes** de construir el medallón. Dos opciones viables:

- **Opción A (extensión mínima):** Añadir `host_key` como columna 20 opcional en `correlation_v1`. Los motores de flujo (aRGus, Suricata, Zeek) la dejan vacía (`""` o centinela). Wazuh la rellena. El lector actual descarta `community_id == ""`, pero si añades `host_key`, necesitas cambiar la regla de descarte: descartar solo si `community_id == ""` **Y** `host_key == ""`. Esto es un cambio de comportamiento del reader; no es trivial.

- **Opción B (contrato separado):** Wazuh no usa `correlation_v1`. Emite a un bronce separado (`host_v1`) con su propio schema, su propia LZ, y su propio sink a Kuzu como `:Host`. El join contra `:NetworkFlow` se hace en Cypher por IP + ventana temporal, no en el medallón.

Mi voto: **Opción B**. `correlation_v1` está diseñado para flujos de red (la prueba: tiene `community_id`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `protocol`). Forzar a Wazuh (host-domain) en ese schema es violar el principio de dominio. El grafo Kuzu puede tener `:Host` como entidad de primer clase; no todo tiene que pasar por el mismo CSV.

---

## 7. ZMQ PUB/SUB — El "patrón conocido" tiene una trampa

Dices que la migración FS→ZMQ es "patrón conocido, no investigación" porque ya funciona sniffer→ml-detector→firewall. Pero hay una diferencia crítica:

- **sniffer→ml-detector:** Un solo productor, un solo consumidor (por nodo). El sniffer no persiste nada; si el ml-detector cae, los paquetes se pierden. Eso es aceptable para detección en tiempo real.
- **adapters→engine:** Múltiples productores (aRGus, Suricata, Zeek, Wazuh), un consumidor (engine). Si el engine cae, los adapters no pueden perder eventos — el AdapterSpec manda at-least-once.

**Enmienda obligatoria:** ZMQ PUB/SUB puro **no da at-least-once**. Es fire-and-forget; si el SUB no está conectado cuando el PUB envía, el mensaje se pierde (slow-joiner syndrome, §7.1). El AdapterSpec §2 dice "ningún evento se pierde en silencio", lo cual es **imposible** con PUB/SUB sin buffer persistente.

Tienes dos opciones:
1. **Añadir un buffer persistente** entre adapter y engine (ej. un proxy con disco, o un log rotado que el engine lee como cola). Esto es esencialmente volver a FS-drop con ZMQ como notificación.
2. **Usar ZMQ PUSH/PULL** en lugar de PUB/SUB para el adapter→engine. PUSH/PULL da load-balancing round-robin, no fan-out, pero garantiza que el mensaje queda en cola del sender hasta que un worker lo recoge (hasta HWM). Si hay un solo engine, PUSH/PULL es más apropiado que PUB/SUB.

Mi recomendación: **PUSH/PULL para adapter→engine**, PUB/SUB solo para broadcast a múltiples consumidores (ej. firewall-acl-agent, que sí puede perder mensajes). Esto contradice AdapterSpec §7.1 "transporte interno SIEMPRE ZeroMQ PUB/SUB". Esa regla debe enmendarse: PUB/SUB para fan-out tolerante a pérdidas; PUSH/PULL para handoff con garantía de entrega (hasta HWM + persistencia).

---

## 8. Timestamp `flow_start_sec`+`flow_start_nano` — La lección DAY 148 es correcta, pero incompleta

Propones fundir a `timestamp_utc_ns` **en el origen (writer C++)**. Esto evita el workaround `x1_000_000` del pipeline RAG-127.

**Pero:** Si cambias el writer C++ para emitir `timestamp_utc_ns` en lugar de (sec, nano), estás cambiando `correlation_v1`. Eso rompe `parse_and_verify` y cualquier consumidor existente del CSV bronce.

**Enmienda obligatoria:** Mantén `flow_start_sec` y `flow_start_nano` en el CSV bronce (compatibilidad con `parse_and_verify`), pero añade una columna derivada `timestamp_utc_ns` como columna 20, o mejor: haz la fusión **en la capa de conversión CSV→AVRO** (la LZ), no en el writer C++ ni en el parquet. El writer C++ no debe cambiar su contrato de salida hasta que `correlation_v2` sea ratificado.

---

## 9. Deudas a abrir — Prioridades y dependencias

Tu tabla de deudas es buena, pero subestima la interdependencia:

| ID | Problema real | Impacto |
|---|---|---|
| `DEBT-CIRCUIT-BRONZE-ROTATION-FOLLOW-001` | Bloquea validación E2E real | **P0** (no P1) |
| `DEBT-CONFIG-BRONZE-HARDCODE-001` | Bloquea cualquier despliegue no-Vagrant | **P0** |
| `DEBT-ADAPTERSPEC-ENVELOPE-001` | Bloquea comprensión del contrato para nuevos adapters | **P1** |
| `DEBT-CORRELATION-V1-HOSTKEY-001` | Bloquea diseño del medallón | **P1** (sube de P2) |
| `DEBT-DOCS-MEDALLION-DUALITY-001` | Previene confusión operativa | **P2** |

---

## 10. Preguntas abiertas — Respuestas del Consejo

| # | Pregunta | Dictamen del Consejo |
|---|---|---|
| 1 | Formato B ratificado | **Sí**, pero con enmienda: el envelope ZMQ transporta bytes CSV firmados, no protobuf. |
| 2 | Oro-como-ledger vs join | **Oro-como-ledger**. Especificar DDL Kuzu antes del Eslabón 2. |
| 3 | Centinela numérico | **`-1` en CSV → `null` Arrow**. Par `(-1,-1)` para temporales. |
| 4 | Rotación/follow | **Engine vigila directorio** para el chapu; documentar race condition. |
| 5 | Wazuh | **Opción B**: contrato `host_v1` separado, no extender `correlation_v1`. |
| 6 | Andrés | Mantener stub con contrato negativo. Requiere 5 respuestas antes de cualquier código. |

---

## Veredicto final

El plan es **estratégicamente sólido** pero **tácticamente peligroso** en tres puntos:
1. **ZMQ PUB/SUB no puede garantizar at-least-once** sin redefinir el patrón (PUSH/PULL para handoff).
2. **Wazuh no debe forzarse en `correlation_v1`**; necesita su propio contrato.
3. **La rotación de bronce es un P0 disfrazado de P1**; sin resolverla, el "circuito verde" es un espejismo.

**Condición para aprobación:** Aplicar las 8 enmiendas obligatorias marcadas arriba antes del primer commit de implementación. El plan como documentación puede mergearse; los commits de código no pasan hasta que las deudas P0 estén cerradas o mitigadas.

No hay palmaditas. Hay un camino. Caminadlo con los ojos abiertos.

— *Dictamen del Consejo, DAY 196*

FDO

KIMI