Estimado equipo de aRGus. El Consejo ha revisado los hallazgos del DAY 184 y las propuestas para el DAY 185. Reconocemos el rigor demostrado: el cambio a `[[nodiscard]] FlushResult`, la verificación empírica de la API de Kuzu 0.11.3 y la corrección del orden de destrucción RAII (`db_` → `conn_` → `preps`) son aplicaciones impecables de principios de ingeniería de software y gestión de memoria en C++.

A continuación, emitimos nuestro dictamen sobre las 6 preguntas planteadas, basándonos estrictamente en el método científico, el control de variables y los principios de arquitectura de software.

---

### 1. ¿Es correcto el orden medir-primero (CSV directo) vs. construir la capa Avro/Iceberg?
**Dictamen del Consejo:** **SÍ, es correcto y metodológicamente obligatorio.**
*   **Principio:** *Navaja de Ockham y Control de Variables.*
*   **Razonamiento:** Introducir Avro, Parquet e Iceberg antes de establecer la línea base del *correlation-engine* + *KuzuSink* introduce múltiples variables de confusión (overhead de serialización, gestión de esquemas, joins en DuckDB). Si el pipeline pierde datos a caudal, añadir capas de complejidad no resolverá el problema raíz; solo hará que la depuración sea exponencialmente más difícil.
*   **Condición de validez:** La medición CSV-directo es válida *siempre y cuando* el cuello de botella de I/O del disco (escritura del CSV por el injector y lectura por el consumer) se monitoree. Si el disco se satura, se debe usar `tmpfs` (RAM disk) en el entorno de prueba para aislar la medición a la CPU/RAM del pipeline, no al subsistema de almacenamiento.

### 2. Opción B (Struct plano) vs. Opción A (Protobuf). ¿Es el test de equivalencia mitigación suficiente?
**Dictamen del Consejo:** **La Opción B es la arquitectónicamente superior, condicionada al test de equivalencia.**
*   **Principio:** *Principio de Mínima Sorpresa y Desacople de Dependencias.*
*   **Razonamiento:** Arrastrar la dependencia completa de Protobuf a un inyector de pruebas y a una librería compartida viola el principio de mínima dependencia. Un contrato de datos plano (`CorrelationV1Row`) es más rápido de serializar, más fácil de inspeccionar en un debugger y elimina la fricción en los *stress-testers*.
*   **Condición de validez (Prueba demostrable):** El test de equivalencia byte-idéntica no es solo una "mitigación", es el **axioma** que hace viable la Opción B. Este test debe ser parte obligatoria del CI. Debe tomar un `NetworkSecurityEvent` protobuf, pasarlo por el camino antiguo y por el nuevo (`event → row → build_row`), y realizar un `assert(memcmp(old_output, new_output) == 0)`. Sin este test en verde, la Opción B es una suposición no verificada.

### 3. ¿Qué le falta al injector adversarial para no ser cómplice?
**Dictamen del Consejo:** **Faltan pruebas de degradación de tipos, estados nulos explícitos y concurrencia de escritura.**
*   **Principio:** *Análisis de Valores Límite y Inyección de Fallos.*
*   **Razonamiento:** Los casos mencionados (H-1, anomalías temporales, colisiones) son buenos, pero incompletos para un sistema que mapea a una base de datos con tipado fuerte (Kuzu).
*   **Acciones requeridas para el injector:**
    1.  **Violaciones de tipo sutiles:** Inyectar números como strings con formatos locales (ej. `"1,000.50"`), o floats donde se espera int. Esto prueba la robustez del constructor `kuzu::main::Value` ante datos sucios.
    2.  **Estados Nulos vs. Vacíos:** Inyectar campos explícitamente `NULL` (si el struct lo permite) vs. strings vacíos `""`. Kuzu trata estos casos de forma distinta y un mapeo incorrecto puede causar fallos de inserción silenciosos o excepciones.
    3.  **Interleaving (Entrelazado):** Ejecutar *dos* instancias del injector escribiendo en el mismo fichero CSV (o directorio de entrada) simultáneamente. Esto prueba si el *correlation-engine* maneja correctamente la lectura de filas entrelazadas de diferentes flujos sin corromper el estado de agregación.

### 4. Injector-a-fichero vs. tcpreplay para la primera medición.
**Dictamen del Consejo:** **Legítimo y necesario. Aislar el NIC de VirtualBox es un requisito científico.**
*   **Principio:** *Aislamiento del Sistema Bajo Prueba (SUT).*
*   **Razonamiento:** El objetivo del DAY 185 es medir la capacidad de procesamiento y durabilidad del *código de aRGus* (correlación + Kuzu sink). El NIC de VirtualBox es una variable de entorno no controlada y conocida por ser defectuosa a ciertos caudales ("Message too long"). Medir a través de ella invalidaría los resultados, ya que cualquier pérdida de datos sería atribuible al hipervisor, no al pipeline.
*   **Hoja de ruta validada:**
    1. Medición 1 (DAY 185): Injector → Fichero (Aísla el software, mide la lógica).
    2. Medición 2 (Futuro): Tcpreplay CTU-13 (Mide el sistema completo, aceptando el techo de VirtualBox como una constante conocida del entorno).

### 5. Refactor `CorrelationWriter` → librería compartida. ¿Sobre-anticipación?
**Dictamen del Consejo:** **Es el primer ladrillo correcto, siempre que el alcance de la librería esté estrictamente delimitado.**
*   **Principio:** *Principio de Responsabilidad Única (SRP).*
*   **Razonamiento:** Que `ml-detector` serialice es una deuda técnica. Extraerlo es correcto. El riesgo de sobre-anticipación existe solo si la librería compartida absorbe lógica de *transporte* (leer logs, conectar a ZMQ).
*   **Condición de validez:** La librería `libcorrelation_v1` debe ser **pura**. Solo debe contener:
    1. La definición del struct `CorrelationV1Row`.
    2. La función `build_row(const CorrelationV1Row&)` que genera la salida (CSV/JSON/Protobuf según se decida, pero idealmente el formato que el consumer espera).
       *No* debe contener clases `LogReader`, `ZmqPublisher` o `FileWatcher`. Eso mantiene la librería útil para el injector, el ml-detector refactorizado y el futuro `argus-adapter-producer`, sin acoplarlos a una estrategia de I/O específica.

### 6. HMAC en el banco de tortura. ¿Correctitud de medición o acoplamiento?
**Dictamen del Consejo:** **Es correctitud de medición. El acoplamiento se mitiga con una clave de prueba estática.**
*   **Principio:** *Validez del Instrumento de Medición.*
*   **Razonamiento:** Si el consumer descarta el 100% de las filas por HMAC inválido, la métrica de "pérdida de datos" es un artefacto de la prueba, no un fallo del pipeline. Para medir la pérdida real, las filas deben ser válidas a los ojos del consumer.
*   **Mitigación del DEBT-BRONZE-KEY-PROVISIONING-001:** El injector **no debe** interactuar con el sistema de provisión de claves de producción. Debe utilizar una clave de prueba hardcodeada y conocida (ej. `constexpr std::string_view TEST_HMAC_KEY = "ARGUS_TEST_KEY_32B!!";`). Esta misma clave debe estar configurada en el entorno de prueba del *correlation-engine*. Esto satisface la lógica de validación del consumer sin acoplar el banco de pruebas a la infraestructura de secretos.

---

### Resumen de Acciones para DAY 185
1.  **Aprobar** el camino de medición CSV-directo (usando `tmpfs` si es necesario para aislar I/O).
2.  **Implementar** la Opción B (`CorrelationV1Row`), pero **bloquear el merge** hasta que el test de equivalencia byte-idéntica esté en el CI y pase.
3.  **Ampliar** el injector adversarial para incluir: tipos numéricos malformateados, nulos explícitos y escritura concurrente (interleaving).
4.  **Delimitar** `libcorrelation_v1` estrictamente a estructuras de datos y funciones de serialización puras, sin lógica de red o lectura de ficheros.
5.  **Utilizar** una clave HMAC estática de prueba en el injector para garantizar la ingestión, evitando el sistema de provisión real.

El suelo está protegido. Procedan con la medición.

FDO

QWEN