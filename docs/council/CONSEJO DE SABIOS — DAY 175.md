# CONSEJO DE SABIOS — DAY 175

## aRGus NDR | 2026-06-05 | Zona Bronce `correlation_v1` cableada y verificada E2E

Hola a los ocho. Soy Alonso, Lead Developer de aRGus NDR.

DAY 175 ha sido día de **cableado y verificación**, no de ADR. El objetivo era
cerrar el primer eslabón real de la zona bronce de correlación: conectar el
`CorrelationWriter` (productor, en ml-detector) que ayer quedó suelto, y demostrar
que produce datos consumibles por el `correlation-engine` (consumidor). Os traigo
el parte de cierre, el plan de mañana, y tres preguntas donde quiero vuestro criterio.

---

## 1. Qué hemos hecho hoy (los 4 pasos, todos verdes)

**Contexto de ayer (DAY 174):** nació el `correlation-engine` como componente C++20
sobre Debian. Se diseñó la arquitectura lambda/medallion (bronce CSV → Avro transporte
→ plata/gold Parquet), se eligió Kuzu v0.11.3 como motor de grafo embebido tras un
`IGraphSink` sustituible, y se escribió el writer (ml-detector) + el reader
(correlation-engine), pero **cada lado se probó por separado**: el writer contra stubs
del proto, el reader contra filas escritas a mano. El writer quedó SIN cablear al
pipeline. Sin eso, no hay datos de bronce reales.

**Hoy, DAY 175 — cuatro pasos en orden:**

**Paso 1 — Alta en build.** `correlation_writer.cpp` dado de alta en `SOURCES` del
CMakeLists del ml-detector (lista explícita, no GLOB). OpenSSL ya estaba linkado por
el `CsvEventWriter`, así que el HMAC no necesitó nada nuevo.

**Paso 2 — Hook en el punto único.** El `correlation_writer_` se construye en el
`zmq_handler` junto al `csv_writer_`, **reutilizando el mismo `hmac_key_hex_`** (cero
divergencia de clave por construcción). La llamada a `write_record()` se cableó en el
PUNTO ÚNICO del bucle de eventos, ANTES de la bifurcación rag/no-rag — esquivando
deliberadamente el "bug de los dos caminos" (el CSV del RAG solo se escribe con
`rag_logger_` apagado; meter ahí el bronce habría heredado ese defecto). Filtro:
`if (correlation_writer_ && !community_id().empty())`.

**Paso 3 — Round-trip unitario (prueba de oro de contrato).**
`test_correlation_roundtrip` en `ml-detector/tests/integration/`: construye un
`NetworkSecurityEvent`, lo escribe con el `CorrelationWriter` REAL, localiza el fichero
vía `get_stats().current_file`, relee la última línea y la pasa al `parse_and_verify`
REAL del correlation-engine. Verifica las 18 columnas + HMAC. **Verde.** Decisión de
alojamiento: el test vive en ml-detector (que ya linka protobuf/OpenSSL) e incluye el
reader del engine, NO al revés — el correlation-engine se mantiene limpio de protobuf.
Gateado contra rebuild limpio vía `make ml-detector && make test-components`: sobrevive.

**Paso 4 — Integración con pipeline vivo (el cierre real).**
Arranque quirúrgico: etcd (clave) + ml-detector (writer construido, confirmado en log:
`✅ CorrelationWriter initialized (bronce correlation_v1)`) + sniffer eBPF. Replay de
`smallFlows.pcap` (14.261 paquetes, 1.209 flujos) por la interfaz correcta.
**Resultado: 3.712 filas reales en `/vagrant/logs/correlation/argus/2026-06-05.csv`,
todas con `community_id` poblado** por el sniffer eBPF (formato `1:wKZ...=`).
Y el sello final: una fila REAL del pipeline, validada por el `parse_and_verify` del
engine con la **clave de producción de etcd**. Cadena completa demostrada:
sniffer real → community_id → ZMQ → ml-detector → bronce → reader valida.

---

## 2. Algo que me preocupa de lo de hoy (y por qué)

El sello del paso 4 estuvo a punto de darnos un falso verde, y la lección es
importante para vosotros porque toca el lado consumidor que viene:

**El round-trip unitario (paso 3) era necesario pero NO suficiente.** Validaba
writer↔reader con una clave de test que ambos lados compartían por construcción
(`KEY_HEX` hardcodeada en el test). Eso ocultaba un problema de *provisioning*: cuando
fui a validar una fila real, usé `seed.hex` como clave HMAC — y el reader la RECHAZÓ.
Bien rechazada: el HMAC no cuadraba. Resultó que la clave HMAC del ml-detector **no es
el seed crudo de disco**, sino una clave servida por etcd en `/secrets/ml-detector`
(campo `key`), distinta del `seed.hex`. Con la clave correcta de etcd, la fila validó.

**Por qué me preocupa:** el contrato de bronce es correcto, pero el *provisioning de la
clave* solo se valida cuando cruzas la clave REAL — no en un test con clave compartida.
Cuando el correlation-engine consuma bronce en producción (lado Avro/file_watch), su
arranque tendrá que pedir la clave a etcd `/secrets/<componente>` EXACTAMENTE igual que
el ml-detector. Si esto se descubre con el lado Kuzu y miles de filas "que no validan",
es un incidente de medianoche. Hoy es una línea de deuda. Lo abro como
`DEBT-BRONZE-KEY-PROVISIONING-001`.

Mi filosofía del día, que comparto porque guio cada paso: **medir, no presuponer.**
Cada vez que medimos en vez de asumir, encontramos algo (el proto rancio que rompió el
build, la columna 17, los injectors sin community_id, y esta clave). No hay que tener
miedo al proceso de medir.

---

## 3. Qué haremos mañana o más tarde (DAY 176+)

Dos batallas pendientes, ninguna bloqueada por lo de hoy:

**(A) Injectors sintéticos sin `community_id`.** Confirmado por grep: SOLO el sniffer
real puebla `community_id` (`ring_consumer.cpp` para eBPF, `main_libpcap.cpp` para
libpcap). Los `synthetic_*_injector` NO lo rellenan. Eso significa que nuestros tests
de estrés y E2E sintéticos **no ejercitan el bronce** — inyectarían eventos con
community_id vacío que el hook descarta. Hay que actualizarlos, uno a uno, mecanismo
oficial primero y luego el de estrés.

**(B) Lado consumidor del engine.** El file_watch de bronce → lectura de clave desde
etcd → `parse_and_verify` → conversión Avro → ZMQ al servidor. Aquí aterriza
`DEBT-BRONZE-KEY-PROVISIONING-001`.

---

## 4. Preguntas para el Consejo (donde quiero vuestro criterio)

**Q1 — Orden de batalla.** ¿(A) injectors primero o (B) lado consumidor primero?
Mi instinto dice **(A)**: sin injectors que pueblen community_id, no tengo forma barata
de generar bronce en CI (hoy dependí de un replay de pcap real + sniffer eBPF, que es
caro y no determinista). (B) es más vistoso pero (A) desbloquea la verificación
continua. ¿Coincidís, o veis razón para invertirlo?

**Q2 — `authoritative_source` como int crudo (columna 17).** El writer escribe
`static_cast<int>(enum DetectorSource)` y el reader lee `int`. El mapeo int→enum
(0=UNKNOWN … 4=ML_PRIORITY … 6=DIVERGENCE) se difiere a Kuzu aguas arriba ("bronce
preserva, gold decide"). ¿Es la decisión correcta, o el bronce debería escribir el
nombre simbólico (`ML_PRIORITY`) para ser auto-descriptivo y robusto frente a un cambio
futuro de los valores del enum en el .proto? Trade-off: tamaño/velocidad (int) vs
legibilidad/estabilidad-de-contrato (string).

**Q3 — `DEBT-BRONZE-KEY-PROVISIONING-001` y el modelo de confianza.** La frontera de
bronce asume secreto compartido (HMAC simétrico, misma clave etcd para writer y reader).
Esto funciona dentro de UN nodo. Pero la arquitectura medallion apunta a miles de nodos
(hospitales, ayuntamientos) cuyo bronce se correlaciona en un Kuzu central. ¿El HMAC
simétrico por-componente sigue sirviendo cuando el consumidor es un servidor central que
debe validar bronce de N sensores distintos? ¿O esto pide ya pensar en una clave de
correlación por-tenant, o firma asimétrica (Ed25519, que ya usamos para plugins)?
No es para resolver mañana, pero quiero saber si véis aquí una grieta de diseño que
convenga anclar en un ADR antes de que el lado consumidor se escriba.

---

Como siempre: marcad vuestras sugerencias con `[SUGERENCIA-NOMBREMODELO: texto]`.
Gracias por 175 días. El bronce ya corre de verdad.

— Alonso, Lead Developer aRGus NDR