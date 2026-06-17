El Consejo ha examinado el brief con atención. Celebramos la solidez del trabajo del día 184 — en particular el `[[nodiscard]] FlushResult`, la transacción agrupada verificada en VERIFY‑3 y la migración a `execute(prepared)` que cierra H‑1 en el camino real de Kuzu. Las seis preguntas se responden a continuación, apoyadas en evidencia medible y en el propio principio rector del proyecto: torturar el pipeline sin perder ni corromper datos.

---

### 1. ¿Es correcto el orden medir‑primero?

**Sí, es el orden correcto.** La pregunta subyacente es si el camino directo (bronce CSV → correlation‑engine → Kuzu) puede arrojar un «falso verde» por no parecerse a producción. El riesgo de falso verde se materializaría *solo si se diera por terminada la evaluación tras esta primera tortura*, pero el brief explícitamente planifica después tcpreplay CTU‑13 y herramientas red‑team reales. Por tanto, la primera medición es una línea base del núcleo (correlation‑engine + sink Kuzu) sin el ruido de componentes aún no construidos.

Construir la capa de consolidación Avro antes de medir **introduce más variables de las que controla** y pospone la detección de fallos en el camino que ya existe. La evidencia que guía esta decisión es el propio VERIFY‑3: el batch transaccional en Kuzu se midió primero de forma aislada, antes de construir sobre él. Siguiendo la misma lógica, medir el camino directo da el «suelo» del pipeline; si ese suelo ya pierde filas, se sabe sin haber escrito una sola línea de Avro. Si no las pierde, se valida el suelo y se procede a añadir capas. Es ciencia incremental: una variable por vez.

La objeción del «falso verde» se mitiga con el diseño del injector adversarial: puede inyectar exactamente el mismo volumen, ráfagas y casos frontera que produciría un productor real. La única diferencia es el formato de entrada al correlation‑engine (CSV vs. Avro). Si el parsing CSV resultara un cuello de botella, se mediría correctamente como tal y se corregiría; si no, se confirma que el motor no depende de Avro para su integridad. No hay atajo que evite medir.

---

### 2. Opción B (struct plano) vs. A (protobuf)

**La opción B es la decisión correcta**, y el test de equivalencia byte‑idéntica es una mitigación suficiente. Razonamos con evidencia concreta del proyecto:

- **Precedente DAY 183**: La migración de `build_cypher` a `make_bindings` se validó con un test que garantizaba salida byte‑idéntica. Ese mismo patrón se aplica aquí. El riesgo de divergencia se convierte en invariante medido; si el test pasa, la salida es indistinguible de la actual. Si alguien modifica el adaptador y rompe el test, la regresión se detecta de inmediato.
- **Menor acoplamiento**: El injector de tortura es el tercer hermano de una familia de stress‑testers que *no* arrastran las dependencias completas de los sistemas que emulan. El que emula sniffer no enlaza libpcap entera; el de ml‑detector no enlaza el modelo. Forzar un protobuf completo al injector introduce una dependencia pesada (y su generación de código) sin beneficio medible. La struct plana `CorrelationV1Row` es el contrato canónico, igual que `CorrelationRecord` en el consumidor.
- **Desacople limpio**: El adaptador `NetworkSecurityEvent → CorrelationV1Row → build_row` en ml‑detector es una capa fina, trazable y testeable. No hay punto de divergencia *adicional* porque la transformación es determinista; el test byte‑idéntico lo demuestra. La opción A conservaría la serialización acoplada a protobuf y obligaría al injector a construir objetos protobuf para unas pocas filas de tortura, exactamente el tipo de lastre que el brief quiere eliminar.

Por tanto, B unifica el contrato, mantiene la equivalencia demostrada y limpia la arquitectura sin riesgo de divergencia no medido.

---

### 3. ¿Qué le falta al injector adversarial para no ser cómplice?

Más allá de los casos listados, un injector verdaderamente adversarial debe explorar estas clases de entrada que romperían el pipeline actual:

- **CSV malformado a propósito**: Delimitadores dentro de campos sin escapar correctamente, saltos de línea embebidos en un campo de texto, líneas con número incorrecto de columnas, *byte order marks* (BOM) al inicio del fichero. El correlation‑engine lee CSV; el injector debe verificar si el parser es robusto.
- **Cargas que disparen escritura concurrente sobre el mismo fichero**: Si el correlation‑engine hace tail‑read mientras el injector escribe, pueden darse lecturas parciales o líneas truncadas. El injector debe simular ráfagas que ensucien el fichero justo en el momento de lectura para exponer condiciones de carrera.
- **Valores límite en todos los campos**: No solo `node_id` con comillas/backslash, sino: cadenas vacías, cadenas de longitud máxima (¿hay límite en la BD?), bytes nulos (`\0`), secuencias UTF‑8 inválidas, y valores numéricos en los extremos de su tipo (INT32_MAX, NaN si se usaran floats).
- **Colisiones de `flow_uid` con variantes**: `flow_uid` nulo, vacío, o duplicado exacto pero con timestamps fuera de orden (¿el motor maneja llegada tardía?), o millones de filas con el mismo `flow_uid` para probar el coste de actualización de un único nodo.
- **Carga que obliga a múltiples flushes concurrentes**: Si el acumulador se llena más rápido de lo que tarda un `flush()` (medido en 0.86 s baseline), se dispara un flush inline. Un bucle apretado de `write()` que llene el buffer repetidamente mientras el `flush()` anterior aún no ha terminado podría provocar crecimiento no acotado de memoria o caídas. Esto requiere un test de back‑pressure.
- **Inyección de filas con HMAC válido pero clave incorrecta**: Aunque la tortura principal requiere HMAC correcto para no falsear la medición, un escenario adicional con HMAC inválido (clave equivocada) permite medir que el consumidor *realmente* descarta y contabiliza correctamente las filas corruptas. Así se verifica la integridad de la métrica de pérdidas.
- **Eventos que generan grafos patológicamente densos**: Por ejemplo, un solo `src_ip` con miles de `dst_ip` distintos en la misma ráfaga, forzando la creación de muchas aristas simultáneas y potencialmente una degradación cuadrática en el sink de Kuzu si no se usan índices adecuados.

El injector debe documentar *cada* uno de estos vectores y la hipótesis que prueba, para que la tortura no sea solo un caudal alto, sino una batería de casos de rotura.

---

### 4. Injector‑a‑fichero vs. tcpreplay para la primera medición

**Es legítimo y metodológicamente sólido.** El brief documenta el cuello de botella conocido de VirtualBox: «Message too long», drops de MTU. Hacer tcpreplay en ese entorno mediría principalmente la red virtual, no el pipeline de aRGus. Sería como medir la resistencia de un material con una báscula rota.

Aislar el pipeline del NIC permite:

- Obtener la **capacidad intrínseca** del correlation‑engine + Kuzu sin factores de confusión.
- Establecer una línea base que, combinada posteriormente con tcpreplay, permitirá **descomponer la pérdida**: si el sistema con tcpreplay pierde X% y el pipeline aislado pierde Y%, la diferencia es atribuible al NIC + sistema operativo virtual.
- Decidir si el NIC virtual es un limitante aceptable para las pruebas posteriores (CTU‑13) o si se necesita un entorno de medición diferente.

El argumento de que producción tendrá Raspberries + TCP, y que el NIC real podría ser un cuello, es válido, pero ese cuello **se medirá después con tcpreplay/CTU‑13 aceptando el techo conocido de VirtualBox**. No se está ocultando, se está *controlando* la variable. Lo que no se debe hacer es asumir que el pipeline está bien cuando el 90% de las pérdidas venían del NIC virtual. La estrategia elegida evita precisamente eso.

---

### 5. El refactor `CorrelationWriter` → librería compartida

**Es el primer ladrillo correcto.** No sobre‑anticipa; extrae una responsabilidad ya identificada y duplicada (el consumidor tiene `CorrelationRecord`; el productor tiene el protobuf; el injector necesitará generar el mismo formato). El principio de «una piedra, tres muros» está bien aplicado.

La posible objeción — «el producer real leerá de log y enviará por ZMQ, no serializará desde struct» — no invalida la librería. La serialización a formato `correlation_v1` (sea CSV+HMAC o Avro en el futuro) es una capa independiente del origen de datos. El `argus-adapter-producer` leerá del log, construirá un `CorrelationV1Row` (como hará ml‑detector con su evento) y *usará la misma librería* para serializarlo y enviarlo. Así se evita tener dos implementaciones de la serialización, que es exactamente la deuda que el brief quiere prevenir.

Si más adelante se descubre que el producer necesita una variante del formato, la librería compartida es el lugar natural para versionarlo. Pero hoy el contrato es uno, y extraerlo es refactorización de manual, no anticipación excesiva. La alternativa — dejarlo en ml‑detector y luego copiarlo al producer — es técnicamente un error.

---

### 6. HMAC en el banco de tortura

**De acuerdo: aquí es correctitud‑de‑medición, no securización de más.** Si el injector no firma con la clave que espera el consumidor, este descarta el 100% de las filas. La tortura mediría entonces una pérdida ficticia total, inutilizando la prueba. La presencia del HMAC garantiza que el flujo de datos no sea detenido por una comprobación de integridad que no es el objeto de estudio.

La deuda `DEBT-BRONZE-KEY-PROVISIONING-001` es real, pero manejable con una mitigación simple:

- **Clave de banco, no de producción**: Generar un par de claves exclusivo para el entorno de tortura (ej. `test_hmac_key`), almacenado en un fichero de configuración leído tanto por el injector como por el correlation‑engine. No es un secreto de producción; es un «secreto de laboratorio».
- **Inyección de la clave por variable de entorno o ruta de fichero**: El injector recibe `BRONZE_HMAC_KEY_FILE=/path/to/test.key`. Esto desacopla el banco de la provisión real sin modificar el contrato del HMAC. La deuda se documenta como «el banco requiere una clave compartida; en CI se usa una clave de prueba generada ad‑hoc».

La pregunta «¿hay forma de que el injector firme con la misma clave sin acoplar el banco a la provisión?» se responde afirmativamente: sí, con una clave de banco explícitamente separada de la infraestructura de secretos de producción. La deuda queda acotada a «el banco no es zero‑trust en la capa HMAC», lo cual es aceptable para un instrumento de medición.

---

El Consejo considera que las decisiones propuestas para el día 185 están fundamentadas en evidencia, mantienen el foco en el eje no negociable y protegen la validez del split MITRE. Quedamos a disposición para cualquier escrutinio adicional.

FDO

DEEPSEEK