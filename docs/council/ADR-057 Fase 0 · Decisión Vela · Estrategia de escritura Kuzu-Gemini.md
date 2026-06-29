## Acta del Consejo de Sabios — DAY 182

**Proyecto:** aRGus NDR

**Fase:** Fase 0 · Decisión Vela · Estrategia de escritura Kuzu

**Metodología aplicada:** *Medir, no votar.*

---

## Q1 — ¿El ×61 transfiere o es un artefacto de la VM?

### 1. La objeción en una frase

El factor de aceleración ×61 está inflado artificialmente por la penalización del `fsync` síncrono por cada sentencia `MERGE` individual en el entorno virtualizado (VirtualBox).

### 2. El experimento o el número

Para aislar el coste de parse/plan del coste de I/O (`fsync`), el benchmark de inserción por fila (run 1) debe ejecutarse bajo tres perfiles de almacenamiento distintos en la misma VM:

* **Perfil A (Base):** `/tmp` nativo en el disco virtual actual.
* **Perfil B (No-Sync):** Montar un subdirectorio en memoria real mediante `tmpfs` (`mount -t tmpfs -o size=1G tmpfs /tmp/kuzu_mem`). Si el cuello de botella era parse/plan, el tiempo por upsert se mantendrá idéntico al Perfil A. Si era `fsync`, el rendimiento del Perfil B se disparará, aproximándose al coste neto de CPU.
* **Perfil C (Hardware Real):** Ejecución directa en el target físico (N100/RPi5 con NVMe/MicroSD de buena calidad) para fijar el factor transaccional real.

```
Métrica a registrar: Delta_fsync = (Tiempo_PerfilA - Tiempo_PerfilB) / Tiempo_PerfilA

```

Si `Delta_fsync > 0.85`, el beneficio del batching en hardware real caerá drásticamente (pero seguirá existiendo por la amortización del parseo).

### 3. Veredicto

**Hardening posterior.** La decisión D1 (usar `UNWIND` con batching) sigue siendo arquitectónicamente superior porque reduce tanto las transacciones como el parseo redundante. Conocer el multiplicador exacto en metal no frena la fusión de la Fase 0.

---

## Q2 — Staleness a bajo caudal (Régimen de goteo)

### 1. La objeción en una frase

El buffer basado puramente en tamaño (`batch=1000`) induce una latencia de detección (staleness) inaceptable de minutos en entornos de bajo tráfico, rompiendo el principio de tiempo real de un NDR.

### 2. El experimento o el número

Establecer un mecanismo de **Flush Cooperativo por Tiempo** mediante un temporizador asíncrono. El SLO de staleness para un NDR de infraestructura crítica se fija de forma invariable en $\le 1000\text{ ms}$ para eventos de red de severidad estándar, y $\le 100\text{ ms}$ para alertas críticas.

* **El experimento:** Implementar un hilo de control (`Ticker`) que emita una señal de `FLUSH` cada 1000 ms si el buffer tiene elementos, independientemente de si ha alcanzado los 1000 registros.
* **La medida:** Simular goteo constante a tasas de 1, 5 y 10 flows/s. Registrar el delta temporal exacto entre la captura del paquete (`ts_packet`) y su disponibilidad en el grafo tras el commit (`ts_graph`). El p99 de este delta debe ser $< 1100\text{ ms}$.

### 3. Veredicto

**BLOQUEANTE.** La inclusión de la política `flush(size OR time)` con un `flush_interval_ms = 1000` debe codificarse e integrarse en el sumidero (sink) antes de fusionar la Fase 0, o introduciremos un fallo de diseño que cegará al correlador en producción.

---

## Q3 — El reader del smoke es un juguete

### 1. La objeción en una frase

La contención medida en el smoke test no es realista porque una consulta estructuralmente pesada (como un recorrido de grafos multi-hop) retendrá bloqueos de lectura y mutará las estructuras del gestor de memoria intermedia de forma radicalmente distinta a un simple `count(*)`.

### 2. El experimento o el número

Sustituir el hilo lector genérico por una consulta de correlación adversarial real que fatigue al motor de Kuzu mientras el único hilo de escritura ejecuta la ráfaga de `UNWIND`.

* **La Query de Stress:**
```cypher
MATCH (a:Host)-[:Flow]->(b:Host)-[:Flow]->(c:Host)
WHERE a.community_id == $cid OR b.community_id == $cid
RETURN count(distinct c)

```


* **La medida:** Ejecutar run 2 (1 writer batcheado) en paralelo con 4 hilos lectores lanzando la query anterior continuamente con CIDs aleatorios pero existentes. Medir el incremento del p99 de la escritura y el rendimiento (queries/s) de la lectura. Si el p99 de la escritura se degrada en más de un 50% frente al run 2 original, el aislamiento de lectura/escritura de Kuzu no es tan inmune como se asume en D4.

### 3. Veredicto

**BLOQUEANTE.** No podemos dar por buena la arquitectura in-process de un único servicio (D4) si una consulta compleja puede bloquear o degradar críticamente la ingesta de tráfico de red en la Fase 0.

---

## Q4 — A escala real, el cuello es la MEMORIA, no la escritura

### 1. La objeción en una frase

Kuzu mantiene estructuras en memoria (Buffer Manager) proporcionales al tamaño del grafo activo, lo que provocará un desbordamiento de memoria (OOM) en dispositivos con recursos limitados como la RPi5 cuando se alcance el volumen real de millones de flujos.

### 2. El experimento o el número

* **Paso 1: Medición de la curva RSS.** Automatizar un script que inserte lotes incrementales de flujos sintéticos pero realistas (5 tuplas únicas) y registre el MaxRSS del proceso de forma estricta:
* Punto A: 100k nodos + relaciones (Línea base actual: 632 MB).
* Punto B: 500k nodos + relaciones.
* Punto C: 1M nodos + relaciones.


* **Paso 2: La estrategia de acotación.** Kuzu permite configurar el tamaño máximo del Buffer Manager en su configuración inicial (`SystemConfig`). El experimento debe demostrar que limitando el buffer manager a 2 GB en la inicialización (`bufferPoolSize = 2 * 1024 * 1024 * 1024`), el sistema procesa 1M de nodos sin lanzar OOM, delegando el exceso al sistema de paginación del motor de almacenamiento de Kuzu.

### 3. Veredicto

**Hardening posterior (con pre-requisito regulatorio).** Para dar luz verde a la Fase 0, basta con añadir una validación explícita en la inicialización del componente que fuerce un límite estricto al `bufferPoolSize` basado en la memoria disponible detectada en el host, evitando que Kuzu consuma toda la RAM de la RPi5 por defecto. El tiering externo (DuckDB/Parquet) se relega al ADR-041.

---

## Q5 — Atomicidad: un flow envenenado tira 1000 detecciones

### 1. La objeción en una frase

Un error sintáctico, una violación de restricciones de integridad o un desbordamiento de tipo de datos en un solo registro de la consulta estructurada `UNWIND` provocará el fallo completo de la transacción, descartando de forma catastrófica 999 registros legítimos.

### 2. El experimento o el número

Verificar el comportamiento transaccional ante fallos mecánicos de Kuzu mediante un test de inyección de fallos.

* **El experimento:** Preparar un vector de entrada con 1000 elementos donde el elemento número 500 contenga un valor inválido (por ejemplo, romper una restricción de clave, inyectar un string mal formado en un campo numérico estricto o un timestamp desbordado). Ejecutar la consulta con la API de C++ de Kuzu:
```cpp
auto queryResult = connection.query("UNWIND $batch AS row ...", queryParams);

```


* **La medida:** Comprobar si `queryResult->isSuccess()` devuelve falso. Acto seguido, realizar un `count(*)` sobre el grafo para verificar si se han insertado los 499 elementos anteriores o si el contador es exactamente igual al estado previo (Rollback Total).

```
Invariante esperado en Kuzu: Rollback Total de la transacción (ACID estricto).

```

* **Estrategia de Mitigación (Quarantine/Retry Pattern):** Si la transacción falla, la cola intercepta el lote, lo divide en dos sub-batches de 500 elementos y reintenta de forma recursiva (Bisección de Fallos) hasta aislar el elemento corrupto en un lote individual. Este elemento se envía a un log de cuarentena (`/var/log/argus/quarantine.log`) y el resto se procesa con éxito.

### 3. Veredicto

**BLOQUEANTE.** El código del sumidero debe incorporar la captura de excepciones/errores del objeto `QueryResult` y la lógica de reintento por bisección (o caída a inserción secuencial de emergencia para ese lote) antes de poder procesar tráfico real hostil.

---

## Q6 — 1000 es un número mágico

### 1. La objeción en una frase

El tamaño de lote de 1000 registros ha sido elegido de manera arbitraria sin un barrido empírico que demuestre dónde se encuentra el punto de inflexión de la curva de rendimiento y su impacto directo en la latencia operativa.

### 2. El experimento o el número

Ejecutar un barrido paramétrico automatizado en el entorno de pruebas fijo bajo las mismas condiciones exactas de estrés.

* **El barrido:** Evaluar el rendimiento configurando el tamaño del lote en $N \in \{1, 10, 100, 500, 1000, 2500, 5000\}$.
* **Métricas a extraer simultáneamente:**
1. Throughput neto (upserts/s).
2. MaxRSS durante la prueba.
3. Latencia de confirmación del lote (p95 de la escritura).



El tamaño óptimo será el menor valor de $N$ donde la ganancia de throughput respecto al escalón anterior sea inferior al 5%, acotando así el radio de impacto de fallos (Q5) y el consumo transaccional de memoria.

### 3. Veredicto

**Hardening posterior.** El valor de 1000 ha demostrado ser sumamente efectivo en el primer test de estrés, ofreciendo una mejora sustancial (×61). El ajuste fino del parámetro óptimo final se puede refinar en la Fase 1 sobre el hardware de destino real.

---

## Q7 — Borrar el WAL es lo contrario de lo que necesita producción

### 1. La objeción en una frase

La eliminación manual de los archivos del diario de escritura por adelantado (`WAL`) en las pruebas para solventar bloqueos destruye las garantías de durabilidad fundamentales y camufla fallos de recuperación del motor de la base de datos tras una parada abrupta o fallo del sistema.

### 2. El experimento o el número

Sustituir la rutina destructiva actual por un test de tolerancia a fallos reales (`Crash-Recovery Smoke Test`).

* **El experimento:** Lanzar el hilo de inserción masiva con el escritor batcheado único. A mitad de la operación (por ejemplo, a los 2.5 segundos), enviar un `SIGKILL` (`kill -9`) fulminante al proceso. Esto dejará un archivo `.wal` con datos confirmados en disco que aún no se han volcado al almacenamiento principal.
* **La medida:** Volver a levantar la aplicación de forma normal *sin borrar ningún archivo del directorio de datos*. Inicializar la base de datos Kuzu y realizar una verificación de consistencia mediante consultas. El motor debe procesar el archivo de diario de forma nativa de manera automática. Contar los registros totales e identificar si coinciden exactamente con los lotes confirmados antes de la recepción de la señal de parada. El test pasa si el estado de la base de datos es consistente y no se produce ninguna corrupción.

### 3. Veredicto

**BLOQUEANTE.** Eliminar la directiva de limpieza destructiva `cleanup_db` de los scripts de inicialización y validar este comportamiento de recuperación automática es obligatorio. Un sistema de detección de intrusiones no puede permitirse corromper su base de datos o perder eventos tras un corte de energía en el servidor donde opera.

---

## Q8 — Diferir sharding ¿es diferir, o es cerrar la puerta?

### 1. La objeción en una frase

Diferir el particionamiento de datos (sharding) sin establecer interfaces desacopladas en el flujo de escritura actual creará un acoplamiento directo con un único archivo de base de datos local en disco, forzando una reescritura masiva de la arquitectura en el futuro.

### 2. El experimento o el número

Establecer una invariante de diseño a nivel de código de tipado estricto en la API del sumidero (`Sink`) mediante un test de conformidad arquitectónica.

* **El invariante:** Cada evento procesado por el componente de ingesta debe incluir obligatoriamente un método de cálculo de clave de enrutamiento basado en los datos del evento, y la interfaz del escritor no debe aceptar consultas genéricas arbitrarias sin ella:
```cpp
class SecurityEvent {
public:
    // Fuerza la existencia de una clave de enrutamiento basada en la 5-tupla
    uint64_t getRoutingKey() const noexcept;
};

```


* **El experimento/verificación:** Demostrar en el diseño de código que el componente encargado de la correlación (`CorrelationEngine`) interactúa con una abstracción de interfaz de consulta (`GraphRepository`), en lugar de instanciar o recibir una referencia directa a la clase concreta `kuzu::Connection`.

### 3. Veredicto

**Hardening posterior.** Siempre que se mantenga el aislamiento de las operaciones de acceso a datos detrás de interfaces abstractas en esta fase, la lógica de distribución física en múltiples bases de datos puede diferirse de forma segura al hito de hardware real sin bloquear la Fase 0.

---

## Q9 — El footgun ¿está prevenido o solo anotado?

### 1. La objeción en una frase

Confiar la exclusión mutua de la inicialización de la base de datos únicamente a la disciplina de los desarrolladores o a comentarios explicativos en el código garantiza que se acabe produciendo una corrupción de datos fatal en producción por un doble acceso accidental in-process.

### 2. El experimento o el número

Implementar una protección mecánica estricta en tiempo de compilación e inicialización utilizando un patrón de diseño Singleton coordinado, combinado con un test unitario adversarial.

* **El mecanismo de protección:** Envolver la inicialización de la instancia única de `kuzu::Database` dentro de una factoría controlada que gestione un puntero único global y un flag de estado atómico interno. Si se detecta un segundo intento de construcción desde cualquier hilo con la misma ruta de acceso, se debe lanzar una excepción explícita de forma inmediata.
* **El test de estrés unitario:**
```cpp
TEST(KuzuGuardTest, PreventDoubleInitialization) {
    auto& db1 = aRGus::DatabaseRegistry::getInstance("/tmp/db");
    EXPECT_THROW({
        auto& db2 = aRGus::DatabaseRegistry::getInstance("/tmp/db");
    }, std::runtime_error);
}

```



### 3. Veredicto

**BLOQUEANTE.** Esta guarda mecánica mitiga de raíz el riesgo de corrupción del gestor de memoria intermedia internamente en la aplicación. Debe estar integrada y verificada por el test correspondiente para dar por concluida con éxito la Fase 0.

---

### Resumen de Acciones para el Cierre de la Sesión

| Pregunta | Clasificación | Acción Requerida para el Verde (Merge) |
| --- | --- | --- |
| **Q1 (VM)** | Hardening posterior | Ninguna para la Fase 0. Medir en N100 en la Fase 1. |
| **Q2 (Staleness)** | **BLOQUEANTE** | Implementar temporizador asíncrono con límite de `1000 ms`. |
| **Q3 (Reader)** | **BLOQUEANTE** | Añadir query de correlación multi-hop en el hilo de lectura del smoke. |
| **Q4 (Memoria)** | Hardening posterior | Configurar de manera estricta el límite del `bufferPoolSize`. |
| **Q5 (Fallos)** | **BLOQUEANTE** | Programar la bisección recursiva ante fallos en bloques `UNWIND`. |
| **Q6 (Batch)** | Hardening posterior | Mantener `1000` de forma provisional; optimizar más adelante. |
| **Q7 (WAL)** | **BLOQUEANTE** | Eliminar la limpieza del WAL; verificar recuperación tras `kill -9`. |
| **Q8 (Sharding)** | Hardening posterior | Asegurar interfaces limpias y abstractas en el código de ingesta. |
| **Q9 (Footgun)** | **BLOQUEANTE** | Implementar el Singleton con control de estado y su test unitario. |

¿Procedemos con las modificaciones de los 5 puntos bloqueantes en el sumisionador de código antes de volver a evaluar el estado general del sistema?

FDO
GEMINI