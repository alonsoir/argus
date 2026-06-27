# Brief para el Consejo de Sabios — DAY 184 → DAY 185

**Contexto.** aRGus NDR, rama `feature/day183-kuzu-sink-unwind-flush`. El eje no negociable sigue siendo: ¿pueden los modelos ensemble aprender de la experiencia acumulada de nodos distribuidos y mejorar con ella? Se publica salga como salga. La condición de validez es el split MITRE disjunto (train A–M, eval N–Z). Todo lo de hoy es *suelo que protege esa medición*, no la medición en sí.

## Qué se cerró hoy (DAY 184), medido no afirmado

**Contrato `flush()→FlushResult`.** `IGraphSink::flush()` pasó de `void` (que ocultaba fallo de durabilidad) a un POD `[[nodiscard]] FlushResult{ok, rows_flushed, rows_pending}`. El `[[nodiscard]]` va en el *tipo*, no en cada método: ningún sink presente o futuro puede descartar el fallo de durabilidad en silencio. Enforcement estructural bajo `-Werror`, mismo espíritu que H-1 se cierra por param tipado y no por recordar `esc()`. `main.cpp`: flush final fallido → `EXIT_FAILURE`, para que el harness E2E no lea "ok" sobre datos perdidos. Migrados los 8 puntos de la superficie (interface + 3 sinks + mock + 2 callers), barrido repo-wide confirmó cero fugas a otros componentes.

**Cableado real del `KuzuGraphSink` batch.** `write()` acumula (copia `record` + `flow_uid` materializado + `ingested_at` sellado a la entrada); `flush()` ejecuta el batch en UNA transacción (`BEGIN` / execute-loop sobre prepared statement / `COMMIT`), con `ROLLBACK` + buffer retenido ante fallo (reintento, nunca drop silencioso). **Esto cierra H-1 en el path EJECUTADO de Kuzu**, no solo en el de logging: el sink ya no corre `query(string_interpolado)`, corre `execute(prepared, params)`. Lo prometido en ADR-057 entró en producción.

**API de Kuzu 0.11.3 verificada contra el header vendorizado, no de memoria.** Tres hallazgos: (1) no hay método tipado de transacción — el control es por string (`query("BEGIN TRANSACTION")`); (2) `Value` no tiene constructor desde `string_view` y todos son `explicit` → hay que materializar cada texto a `std::string`; (3) el propio header documenta el SIGSEGV de DAY 183 en un comentario: *rollback-on-destruction sobre Database cerrada = SEGFAULT*. El orden de miembros (`db_` → `conn_` → `preps` → acumulador) resuelve el lifetime por RAII.

**VERIFY-3: la transacción por string agrupa de verdad.** Dos tests gemelos, mismas N filas, solo cambia `COMMIT` vs `ROLLBACK`. COMMIT → 2 nodos durables, ROLLBACK → 0. Prueba que el `BEGIN/COMMIT` envuelve los `execute(prepared)` en una sola transacción = amortización de 1 checkpoint por batch. La premisa de la que dependía el diseño de `flush()` queda medida. Baseline de coste del componente con BD: 0.86s (era 0.48s antes del batch; crecimiento contabilizable).

## Qué decidimos para DAY 185 y por qué (el punto que requiere vuestro escrutinio)

**Decisión de no construir la arquitectura completa todavía.** Se describió la arquitectura de destino: `*-adapter-producer` (lee log del sensor, genera `correlation_v1`, pushea a ZMQ topic) + `*-adapter-consumer` (consolida CSV+HMAC → Avro vía Arrow → Parquet → Iceberg medallón bronce/plata/oro), replicado para aRGus/Suricata/Zeek/Wazuh, con productores cerca de las Raspberries y conectividad TCP/ZMQ hacia el servidor que aloja correlation-engine + Iceberg + Kuzu. Es la arquitectura correcta de producción.

**La decisión es NO construirla entera antes de la primera tortura, sino medir primero el camino que ya existe.** Razón: el eje dice que el objetivo no es la mejor implementación del grafo sino torturar el pipeline sin perder/corromper datos. Construir el medallón completo (Avro/Parquet/Iceberg) antes de medir es *asumir* que hace falta — y D3 (Arrow/C++ solo vs. también DuckDB para join silver→gold) sigue abierta como decisión medida, no votada. La primera corrida puede medirse sobre el camino directo: bronce CSV → correlation-engine → Kuzu. Si ese camino ya pierde filas a caudal, se sabe sin escribir una línea de Avro; si no las pierde, se valida el suelo antes de construir encima.

**El refactor que SÍ se hace en piedra de una vez: extraer `CorrelationWriter` de ml-detector a librería compartida.** Hoy ml-detector tiene dos responsabilidades pegadas: clasificar (su trabajo) y serializar `correlation_v1` (no su trabajo — igual que rag-ingester adapta para rag-security con otra información). Se extrae la serialización a `libcorrelation_v1`. Ese mismo trabajo sirve a tres consumidores: ml-detector (refactorizado), el injector de tortura, y mañana el `argus-adapter-producer`. Una piedra, tres muros.

**Opción de corte elegida: B (struct plano), no A (protobuf).** El `CorrelationWriter` actual acopla serialización a `protobuf::NetworkSecurityEvent`. Opción A: extraer tal cual, el injector construye protobuf. Opción B: definir `struct CorrelationV1Row` (18 campos planos, los mismos que el `CorrelationRecord` del consumidor), `build_row(const CorrelationV1Row&)`, y ml-detector se vuelve adaptador fino `NetworkSecurityEvent → CorrelationV1Row → build_row`. **Se elige B por dos razones:** (1) el injector `correlation_v1` es el tercer hermano de la familia de stress-testers de `tools/` (uno emula sniffer, otro ml-detector, este emula el contrato AspectV1) — los otros no arrastran el protobuf completo de quien emulan, este tampoco debe; (2) arrastrar protobuf entero para usar una porción es peso innecesario. El contrato ya vive como struct en el consumidor (`CorrelationRecord`) y como protobuf en el productor; B unifica eso.

**Riesgo de B y su mitigación:** la conversión `protobuf → CorrelationV1Row` podría divergir de la salida actual. Mitigación: test de equivalencia que pase un `NetworkSecurityEvent` por el camino viejo (`build_row(event)`) y el nuevo (`event → row → build_row(row)`) y asierte **salida byte-idéntica** — mismo patrón que DAY 183 (`build_cypher` rebasado sobre `make_bindings` con salida idéntica garantizada por test). El riesgo de divergencia se convierte en invariante medido.

**El HMAC se conserva en B — y no es securización de más.** El consumidor descarta toda fila con HMAC inválido antes del grafo. Sin HMAC correcto en el injector, el correlation-engine tira las filas como corruptas y se mide pérdida del 100% ficticia. El HMAC aquí no es defensa ante atacante: es la condición para que el consumidor acepte la fila y la medición no sea basura.

**El injector debe ser adversarial, no cómplice.** El propio principio del proyecto: si el diseño solo pudiera confirmar, no sería medición. El injector no debe producir "bronce bonito" sino el que rompería el pipeline si estuviera mal: `node_id` con comillas/backslash (el caso H-1), timestamps que disparan `temporal_anomaly`, colisiones de `flow_uid`, ráfagas que fuerzan el flush inline, volumen que desborda el acumulador.

**Por qué injector-a-fichero y no tcpreplay para la PRIMERA tortura.** El cuello de botella documentado de Vagrant/VirtualBox es el NIC ("Message too long", drops de MTU). Un tcpreplay a 100 Mbps mide *el NIC de VirtualBox*, no el pipeline. El injector que escribe bronce directo al fichero evita ese cuello → mide el código de aRGus, no la red virtual. El tcpreplay CTU-13 Neris entra después, para medir el sistema entero (incluidos sensores) aceptando el techo de VirtualBox como límite conocido. Tras CTU-13, el cliente MITRE con herramientas red-team reales (hydra, nmap, etc.) para generar los primeros datasets — aunque sean de baja calidad inicial, el objetivo es aprender a gestionar el ciclo de vida completo del pipeline.

## Preguntas explícitas al Consejo

1. **¿Es correcto el orden medir-primero?** ¿O hay un argumento para construir al menos la capa de consolidación Avro antes de la primera tortura, porque medir el camino CSV-directo mediría algo que no se parece a producción y daría un falso verde?

2. **Opción B vs A.** ¿El struct plano `CorrelationV1Row` + adaptador en ml-detector es el corte correcto, o el desacople protobuf introduce un punto de divergencia que no compensa la limpieza? ¿El test de equivalencia byte-idéntica es mitigación suficiente?

3. **¿Qué le falta al injector adversarial para no ser cómplice?** Más allá de los casos frontera listados (H-1 strings, temporal_anomaly, colisiones flow_uid, ráfagas), ¿qué clase de input rompería este pipeline y no está contemplado?

4. **Injector-a-fichero vs tcpreplay para la primera medición.** ¿Es legítimo medir el pipeline aislándolo del NIC de VirtualBox, o eso oculta un cuello real que en producción (Raspberries + TCP) sí existirá y debería medirse desde el principio?

5. **El refactor `CorrelationWriter` → librería compartida.** ¿Es el primer ladrillo correcto del `argus-adapter-producer`, o estamos sobre-anticipando una arquitectura cuyos requisitos aún no conocemos (p.ej. el producer real necesitará leer-de-log + ZMQ, no serializar-desde-struct, y la librería podría quedar mal cortada)?

6. **HMAC en el banco de tortura.** ¿De acuerdo en que aquí es correctitud-de-medición y no securización de más? ¿O hay forma de que el injector firme con la misma clave sin que esto acople el banco a la provisión de claves (DEBT-BRONZE-KEY-PROVISIONING-001)?

---
