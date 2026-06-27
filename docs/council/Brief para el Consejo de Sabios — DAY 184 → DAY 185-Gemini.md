Estimado Investigador Principal, Alonso. El Consejo de Sabios se reúne en este DAY 184→185 bajo el rigor metodológico que exige el proyecto aRGus NDR. Validamos las certezas empíricas alcanzadas hoy (especialmente el blindaje estructural del contrato `FlushResult` bajo `-Werror` y la resolución de lifetimes por orden de declaración RAII en Kuzu) y procedemos a emitir un dictamen unificado sobre las decisiones de arquitectura del banco de tortura.

---

## 1. ¿Es correcto el orden medir-primero? (CSV vs. Avro)

**Dictamen:** **Sí, es el único camino científicamente válido.** Construir la capa de consolidación Avro/Parquet/Iceberg antes de la primera tortura violaría el principio de aislamiento de variables.

* **Evidencia técnica:** Si introduces la serialización Avro, la persistencia en disco de bloques Parquet y la coordinación de metadatos de Iceberg simultáneamente con el `KuzuGraphSink`, ante una degradación del rendimiento o pérdida de registros, el diagnóstico estructural se vuelve indeterminado ($N$ posibles focos de falla).
* **Mitigación del "Falso Verde":** El argumento de que medir el camino CSV-directo arroje un falso verde es inválido si acotamos la métrica. El camino CSV-directo mide el **techo absoluto de absorción (Throughput Máximo Teórico)** de tu `KuzuGraphSink` acoplado al `correlation-engine`. Ninguna infraestructura posterior (por eficiente que sea Arrow/Iceberg) superará la velocidad de ingesta directa en memoria/CSV local. Por tanto, esta prueba mide el *suelo de degradación* del grafo. Si el sistema falla o se satura con CSV local, está garantizado que fallará con Iceberg.

---

## 2. Opción B vs. Opción A (`CorrelationV1Row` vs. Protobuf)

**Dictamen:** **La Opción B (struct plano) es la decisión de ingeniería correcta.** El acoplamiento a Protobuf en componentes de testeo que emulan comportamiento (`tools/`) introduce una penalización innecesaria en el tiempo de compilación y dependencias binarias.

* **Suficiencia de la Mitigación:** El test de equivalencia byte-idéntica (`event → row → build_row(row)` vs `build_row(event)`) es matemáticamente suficiente para garantizar la invariabilidad del contrato de datos. No hay margen para la divergencia si el binario del test aserta el *checksum* o la igualdad posicional del stream serializado.
* **Prueba de concepto:** En C++20, un struct plano (`CorrelationV1Row`) aprovecha la inicialización agregada y permite un mapeo trivial a estructuras de serialización o bindings de base de datos sin sobrecoste de indirección o asignación en el heap (a diferencia de los tipos internos de Protobuf que gestionan strings mediante arenas o asignaciones dinámicas ocultas).

---

## 3. ¿Qué le falta al injector adversarial para no ser cómplice?

Para convertir el injector en un verdadero agente de caos que ponga a prueba el subsuelo de Kuzu y el `correlation-engine`, debes incluir en el banco de tortura los siguientes vectores de estrés:

* **Inyección de Timestamps No Monótonos (Desorden Temporal):** Registros donde $t_{n+1} < t_n$ con deltas masivos. Esto no solo estresará `temporal_anomaly`, sino que forzará transacciones Kuzu con escrituras en páginas de propiedades indexadas no contiguas, disparando la fragmentación del almacenamiento persistente de Kuzu.
* **Ataque de Cardinalidad en la Topología del Grafo (Nodos Estrella):** Generar un único `node_id` (IP/Host) conectado a $10^6$ `flow_uid` distintos en una sola ráfaga. Esto saturará las listas de adyacencia (*adj lists*) de Kuzu en memoria antes del `flush()`, permitiendo medir el comportamiento del gestor de memoria virtual de Kuzu ante desbalances de grado en los nodos.
* **Truncamiento de Strings en Fronteras UTF-8:** Cadenas de caracteres malformadas o truncadas a mitad de un carácter multi-byte en los campos de payload/identificadores. Kuzu procesa texto; una secuencia UTF-8 inválida podría hacer colapsar el validador interno del motor de la base de datos o corromper los prepared statements.
* **Presión de Flush Concurrente (Falta de Coordinación):** El injector debe emitir ráfagas que fuercen el vaciado por tamaño de buffer simultáneamente con señales de sistema que disparen el `flush()` por timeout de inactividad, induciendo condiciones de carrera en el estado interno del `FlushResult`.

---

## 4. Injector-a-fichero vs. `tcpreplay` para la primera medición

**Dictamen:** **El aislamiento del NIC de VirtualBox en la primera fase es metodológicamente correcto.** * **Justificación:** Un principio básico del perfilado de sistemas (*profiling*) es eliminar los cuellos de botella externos conocidos. Si el NIC de VirtualBox descarta paquetes por desbordamiento de MTU a 100 Mbps, la métrica de *rows_dropped* del `KuzuGraphSink` reflejará la ineficiencia del hipervisor, no del pipeline en C++20.

* **El peligro oculto (Mitigación obligatoria):** Al escribir directo a fichero, estás sustituyendo el cuello de botella del NIC por el **cuello de botella de I/O del sistema de ficheros (VFS/Page Cache)**. Si el injector escribe en el mismo disco físico donde Kuzu realiza sus transacciones (`COMMIT`), medirás la contención del bloqueo del kernel en operaciones de escritura.
* **Acción requerida:** El injector debe escribir el CSV en un sistema de archivos en memoria (`tmpfs` / `/dev/shm`). Esto garantiza latencia de I/O cercana a cero, emulando verdaderamente la velocidad de una cola de memoria o un socket ZMQ sin el ruido del almacenamiento físico ni de la pila de red virtualizada.

---

## 5. El refactor `CorrelationWriter` a librería compartida

**Dictamen:** El corte es correcto y **no sobre-anticipa la arquitectura**, siempre y cuando la frontera de la librería se limite estrictamente a la **transformación del modelo de datos** y no a la mecánica de transporte.

```
+-------------------------------------------------------------+
|                     libcorrelation_v1                       |
|                                                             |
|  [CorrelationV1Row] -------------> [Serializador Agnóstico] |
+-------------------------------------------------------------+
               |                               |
               v                               v
   (Próximo Adapter-Producer)        (Injector / ML-Detector)
   Mapea a ZMQ / Sockets             Escribe a Archivo / Memoria

```

* **Separación de incumbencias:** Mientras `libcorrelation_v1` contenga únicamente la estructura `CorrelationV1Row`, los validadores de formato y la lógica de serialización del payload, la librería será perfectamente reutilizable.
* El `argus-adapter-producer` real simplemente linkeará esta librería para construir el binario plano y posteriormente pasará el buffer resultante a la capa de transporte (ZMQ). No hay sobre-ingeniería en unificar la definición del contrato de datos.

---

## 6. El HMAC en el banco de tortura

**Dictamen:** **El HMAC es un requerimiento de correctitud de la medición, no seguridad cosmética.** Si el consumidor descarta por diseño las filas sin firma válida, omitir el HMAC invalidaría la prueba transformándola en un sumidero ciego de descarte de datos.

* **Resolución del acoplamiento (`DEBT-BRONZE-KEY-PROVISIONING-001`):** Para evitar que el injector dependa de una infraestructura compleja de HashiCorp Vault en esta fase de estrés, la clave secreta utilizada para el HMAC en el entorno de pruebas debe pasar como una variable de entorno o un argumento de CLI en tiempo de ejecución (`--secret-key-test`).
* Tanto el componente bajo prueba como el injector adversarial se instanciarán en el arnés de testeo usando la misma clave simétrica prefijada (ej. `0xDEADBEEF...`). Esto elimina la deuda técnica de aprovisionamiento sin alterar el código de validación del pipeline.

---

### Veredicto de Consenso del Consejo

El plan para el **DAY 185** queda **APROBADO CON MODIFICACIONES CRÍTICAS**:

1. Proceder con el refactor a la Opción B respaldado por el test de equivalencia byte-idéntica.
2. Construir el injector adversarial directo a fichero, pero **restringido contractualmente a operar sobre `/dev/shm` (tmpfs)** para aislar el factor de I/O de disco.
3. Incorporar desorden temporal y ataques de alta cardinalidad de nodos en el set de datos del injector para validar la resistencia de las transacciones agrupadas en Kuzu.

La base científica está colocada. Quedamos a la espera de los resultados de la primera tortura sistemática del pipeline.

FDO

GEMINI