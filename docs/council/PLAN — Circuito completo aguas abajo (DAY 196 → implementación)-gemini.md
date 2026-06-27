Aquí no hay palmaditas en la espalda, Alonso. El plan es ambicioso, pero tiene inconsistencias estructurales, suposiciones peligrosas y puntos ciegos que van a reventar el circuito en cuanto intentéis meter tráfico real. Como adversarios de este Consejo, vamos a demoler el borrador sección por sección para forzar la robustez que exige la *Via Appia*.

Procedemos a auditar, impugnar y responder a las cuestiones planteadas.

---

## I. Impugnaciones Críticas del Consejo (El Factor Adversario)

### 1. La falacia de la "Fase Chapu" en el Eslabón 0 e Invariante de Rotación

Proponéis pasar `--bronze {bronze_root}/argus/{hoy}.csv` por argumento de arranque al engine para evitar el JSON temporalmente. Esto viola vuestra propia invariante de medición y introduce el bug **`ROTATION-FOLLOW`** desde el minuto uno.

* Si el engine abre el `ifstream` de `{hoy}.csv` a las 23:59, a las 00:01 el `correlation_writer` del detector creará `{mañana}.csv`. El engine seguirá leyendo un descriptor de fichero muerto o vacío.
* **Enmienda radical:** No hay eslabón 0 con `ifstream` sobre fichero datado estático. O el engine procesa por directorio entero (vigilando el último modificado) o el Eslabón 0 implementa el pipeline ZMQ directamente. Romper el circuito a medianoche no es "Via Appia", es meter deuda consciente en el microscopio.

### 2. La Disonancia del Timestamp-ns (`DEBT-PARQUET-TIMESTAMP-NS-001`)

Afirmáis que solucionar el workaround del timestamp mutando el writer C++ a nanosegundos es el camino correcto. Cuidado: `flow_start_sec` y `flow_start_nano` en `correlation_v1` (bronce) están separados en las columnas 5 y 6 **[MEDIDO]**.

* Si el writer los funde en una sola columna en bronce para facilitar la LZ, rompeis el contrato posicional de 19 columnas de `correlation_v1` que ya lee el reader actual.
* Si mantenéis las 19 columnas, la LZ *tiene* que hacer la fusión. Aclarad esto: el "origen" para Arrow es la LZ, no podéis alterar el layout de bronce sin versionar el contrato a `correlation_v2`.

### 3. El sesgo de Kuzu como sumidero analítico

Asumir que Kuzu puede digerir todo el flujo crudo de Parquet sin una capa de agregación previa en Oro es optimista. Los grafos de propiedades sufren con escrituras masivas de aristas duplicadas si el "ledger" inyecta millones de eventos idénticos por segundo (por ejemplo, ráfagas del sniffer). Kuzu necesita que Oro actúe como un filtro de unicidad o agregación temporal si no queréis degradar las consultas Cypher del dashboard.

---

## II. Respuestas y Resoluciones a las Preguntas Abiertas

### 1. Ratificación de Formato: A vs B (Contrato de Salida)

**RATIFICADO: Opción B.** Bronce **PRESERVA**, Gold **DECIDE**.
No se inventa un envelope Protobuf que no existe en el cable. Cada adapter escribe su dialecto nativo mapeado a las 19 columnas de `correlation_v1` en su subdirectorio correspondiente dentro de `bronze_root`. El acoplamiento es el formato CSV posicional y el HMAC, nada más. El desajuste de `AdapterSpec v1` se degrada oficialmente a `v1.1` mediante la apertura inmediata de `DEBT-ADAPTERSPEC-ENVELOPE-001`.

### 2. Forma del Oro: ¿Join en Arrow vs Join en Kuzu?

**DECISIÓN: Oro-como-Ledger (Kuzu une).**
El Consejo rechaza el *Oro-como-join* en Arrow por las siguientes razones de arquitectura:

* **Idoneidad del Grafo:** El `community_id` es, por definición, la clave de identidad de la entidad `:NetworkFlow`. Forzar un wide-table en Parquet plano obliga a realizar un join relacional pesado antes de cargar el grafo, duplicando el trabajo que Kuzu hace de forma nativa mediante punteros de memoria indexados.
* **Tolerancia al Desalineamiento Temporal (Staleness):** Zeek cierra flujos cada ~5 minutos; Suricata emite alertas casi en tiempo real. Un join en Arrow obligaría a mantener ventanas de tiempo complejas en disco esperando que lleguen rezagados. En Kuzu, si llega primero la alerta de Suricata, se crea el nodo; cuando llega el flujo de Zeek, se conecta a la misma entidad `:NetworkFlow` de manera asíncrona.
* **Grafo resultante:**

```
(:Host) —[:INVOLUCRADO_EN]→ (:NetworkFlow {community_id}) ←[:DETECTADO_POR]— (:Detection {source_sensor})

```

### 3. Centinela Numérico: `-1` vs `0`

**DECISIÓN: El centinela numérico en CSV ES `-1`.**
El valor `0` queda totalmente prohibido como centinela. En redes, `0` es un puerto válido (bien conocido en escaneos crudos o tráfico local descabalibrado) y en analítica `0.0` es un score de amenaza mínimo (falso positivo confirmado). El valor `-1` fuerza al parseador C++ a reconocer explícitamente la ausencia de datos. La Landing Zone transformará este `-1` en un valor `null` nativo de Apache Arrow durante la transición Bronce $\rightarrow$ Plata.

### 4. Rotación / Follow del Engine

**DECISIÓN: El Engine vigila Directorio (Mecanismo de Polling/Inotify).**
El lanzador calculando el path datado es frágil frente a caídas del sistema, cambios de hora NTP y desfases de ejecución. El `correlation-engine` debe abrir el directorio `bronze_root/*/.` y procesar por flujo de ficheros activos.

* *Nota de diseño:* Para evitar procesar ficheros parcialmente escritos por el writer, el `correlation_writer` debe escribir en `.<date>.csv.tmp` y renombrar a `<date>.csv` al rotar, o bien asegurar escrituras atómicas por línea (append-only inferior al tamaño de bloque del FS).

### 5. El Muro Estructural de Wazuh

**DECISIÓN: Contrato host-domain separado (No forzar `correlation_v1`).**
No extendáis `correlation_v1` a una versión `v2` metiendo con calzador un `host_key` que rompería los parsers de los tres motores de red que ya funcionan.

* Wazuh (y en el futuro los logs de sistema de componentes internos) ingresará por un canal independiente: `host_event_v1`.
* Tendrá su propia Landing Zone y se materializará en Kuzu directamente como una arista hacia el nodo `:Host` mapeando la dirección IP. Fusionar peras (flujos de red) con manzanas (alertas de host de sistema operativo) en el mismo layout de 19 columnas de texto limpio destruiría la coherencia semántica del circuito de correlación.

### 6. El Stub de Andrés

**DECISIÓN: Se mantiene congelado bajo contrato negativo.**
No gastéis un solo ciclo de CPU en diseñar adaptadores para el flujo de Andrés. Se queda como un componente de simulación que inyecta basura tipada en un test unitario para asegurar que el motor descarta registros corruptos o desconocidos sin colapsar el pipeline.

---

## III. Matriz de Riesgos y Puntos de Fallo Inmediatos

| Componente | Riesgo Identificado | Mitigación Obligatoria |
| --- | --- | --- |
| **Landing Zone** | El volumen de micro-CSV rompe el ratio de compresión de Parquet (ficheros demasiado pequeños). | La LZ acumula en memoria o en búfer intermedio de Plata antes de consolidar el bloque Parquet definitivo en disco. |
| **Kuzu Sink** | Inyección masiva de duplicados causa bloqueos de concurrencia en la base de datos de grafos. | Implementar un filtro de Bloom en memoria dentro del `kuzu_graph_sink` para descartar aristas `(community_id, source_sensor)` ya procesadas en la última hora. |
| **ZMQ Agent** | Pérdida de mensajes en el arranque debido al escenario *Slow-Joiner*. | Respetar escrupulosamente la regla del §7.1 de la especificación: el nodo que enlaza (`PUB`) ejecuta el método `bind()` e inicia la escucha antes de que cualquier suscriptor (`SUB`) intente invocar el método `connect()`. |

---

## IV. Conclusión del Consejo

El plan se aprueba para su transición a desarrollo bajo la rama `day196/circuit-adapters-zmq` **únicamente si se descarta el uso de paths estáticos datados mediante paso de argumentos argv en el Eslabón 0**. La coherencia estructural basada en la derivación de rutas desde el archivo de configuración centralizado `ml_detector_config.json` constituye vuestra única defensa real contra el desalineamiento del sistema (*desync*).

Proceded con el desarrollo del Eslabón 0 modificado y la construcción de la Landing Zone modularizada. La *Via Appia* no admite atajos que rompan el sistema a medianoche.

FDO

GEMINI