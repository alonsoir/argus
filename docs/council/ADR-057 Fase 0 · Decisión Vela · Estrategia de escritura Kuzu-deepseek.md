**Consejero R. Karpov — Revisión adversarial ADR-057**

Me ciño a la regla: cada respuesta termina en un experimento medible o un invariante verificable.

---

### Q1 — ¿El ×61 transfiere o es un artefacto de la VM?

**Objeción:** El ×61 está inflado porque la VM penaliza `fsync`; en hardware real con SSD la ventaja puede desplomarse y hacer irrelevante la decisión de batching.

**Experimento:** Instrumentar el perfil de latencia con `perf`/`strace` en la VM y en el target real (NVMe sin virtualización), separando tiempo en `parse+plan`, `execute` y `fsync`. Medir el ratio `run2/run1` en ambos entornos. Si en target real el ratio cae por debajo de ×5, hay que recalcular si UNWIND+batch sigue bastando para el SLO de ingesta sin Vela.

**¿Bloqueante?** Sí, **bloqueante para el merge de Fase 0** si el dimensionamiento de capacidad depende de ese ×61. Si el SLO de ingesta puede cumplirse incluso con un ×2, pasa a hardening.

---

### Q2 — Staleness a bajo caudal

**Objeción:** Con 3 flows/s un batch de 1000 tarda >5 min en llenarse; un ataque activo no sería correlable hasta entonces, latencia de detección inadmisible.

**Experimento:** Simular caudal bajo (1–10 flows/s) y medir el tiempo desde que un upsert llega al sink hasta que está visible en una consulta de correlación. Barrer `flush_timeout_ms` ∈ {100, 500, 1000, 5000} y medir staleness p99. El SLO de detección del NDR debe ser un número (ej. 5 s). `flush_interval_ms` será el máximo valor que mantenga la staleness p99 por debajo de ese SLO. El número resultante es vinculante.

**¿Bloqueante?** **Bloqueante.** Sin política `flush(size OR time)` validada, el sistema pierde su razón de ser en redes tranquilas.

---

### Q3 — Reader real bajo carga de escritura

**Objeción:** La contención se midió con `count(*)`, una lectura trivial; una correlación multi-hop real (ej. 3 saltos por `community_id`) puede disparar la contención de lectura y falsear la conclusión de que “un writer batcheado mantiene la lectura sana”.

**Experimento:** Ejecutar una query de correlación representativa (e.g., “dado un nodo sospechoso, recuperar los flows relacionados en 3 saltos y sus procesos”) concurrentemente con la riada de upserts, replicando el setup de run2 y run3. Medir latencia p50/p99 de lectura y rechazos de escritura. Si la latencia de lectura supera el SLO (ej. 2 s), la decisión D1/D3 queda en entredicho.

**¿Bloqueante?** **Bloqueante.** Sin esta evidencia, la afirmación de que el lector sobrevive en producción es una conjetura.

---

### Q4 — Memoria a escala real y tiering hot/cold

**Objeción:** Con 100k nodos ya se usan 822 MB; una red hospitalaria puede generar millones de nodos en la ventana de retención, superando la RAM de una RPi5/N100 y provocando thrashing o OOM.

**Experimento:** Construir datasets de 100k, 500k y 1M nodos con la misma forma de datos real (propiedades, relaciones) y medir RSS exacto. Si la curva no es sublineal, implementar un mecanismo de tiering: exportar periódicamente los datos que exceden la ventana caliente a Parquet/DuckDB y borrarlos de Kuzu, midiendo el impacto en queries que tocan el borde caliente/frío. La métrica de decisión: RSS máximo aceptable en producción (ej. 6 GB en N100). La estrategia de tiering debe garantizar que el grafo caliente nunca supera ese límite.

**¿Bloqueante?** **Bloqueante.** Sin esta validación, el sistema no es desplegable en el hardware objetivo.

---

### Q5 — Atomicidad: un flow envenenado tira 1000 detecciones

**Objeción:** Si una sola fila malformada revienta la transacción UNWIND completa, se pierden 999 eventos legítimos, lo que es un vector de denegación de servicio.

**Experimento:** Inyectar en un lote de 1000 filas una fila que viole una restricción (nodo duplicado, tipo incorrecto) y observar el comportamiento de Kuzu: ¿rollback total o inserción parcial? Documentar la semántica exacta. Si es total, implementar una capa de cuarentena que pre-valide y separe filas sospechosas (esquema, unicidad) antes del batch, escribiendo las malas en un dead-letter y reemitendo las buenas. Medir la tasa de pérdida y la sobrecarga de la prevalidación.

**¿Bloqueante?** **Bloqueante.** Un NDR no puede descartar eventos válidos por culpa de tráfico hostil.

---

### Q6 — 1000 es un número mágico

**Objeción:** No hay barrido de tamaño de lote que justifique 1000 frente a otros valores, y el óptimo de throughput puede ser incompatible con staleness, memoria y radio de fallo.

**Experimento:** Barrer `batch_size` ∈ {1, 10, 100, 500, 1000, 5000, 10000} en condiciones de saturación y de bajo caudal. Medir:
- Throughput (upserts/s)
- Staleness (tiempo hasta visibilidad) bajo bajo caudal
- RSS máximo durante la prueba
- Blast radius de fallo (eventos perdidos si una fila es mala)
  Construir frente de Pareto y seleccionar el punto que satisfaga simultáneamente los SLOs operativos. Si el codo de throughput está en 5000 pero la staleness se dispara, el óptimo operativo probablemente sea menor. Responder con un número justificado.

**¿Bloqueante?** Hardening posterior si el sweep confirma que 1000 está en el orden de magnitud correcto; bloqueante si el óptimo operativo resulta ser <100 o >10000 y obliga a rediseñar parámetros del sink.

---

### Q7 — Borrar el WAL es lo contrario de lo que necesita producción

**Objeción:** El smoke “arregla” el WAL huérfano borrándolo; eso es una prueba de que el camino de crash existe, pero no valida la recuperación real de datos commiteados, ocultando un agujero de durabilidad.

**Experimento:** `restore_from_wal_smoke_test` debe:
1. Iniciar una riada de escritura con un marcador único en cada transacción.
2. Enviar `SIGKILL` en un punto aleatorio durante el commit (tras escribir algunas transacciones).
3. Reabrir la base de datos y verificar que todas las transacciones cuyo commit fue reconocido por la API están presentes y correctas, sin pérdida ni corrupción.
4. Repetir N veces (≥100) para cubrir diferentes puntos de muerte.
   Si no se hace esto, la durabilidad no está probada.

**¿Bloqueante?** **Bloqueante.** Sin recuperación validada, el sistema no es apto para producción.

---

### Q8 — Diferir sharding ¿es diferir, o es cerrar la puerta?

**Objeción:** Si hoy no se impone una clave de sharding explícita en el write path y las queries de correlación asumen un grafo monolítico, “diferir” sharding equivale a hacerlo imposible sin reescritura.

**Experimento:** Definir invariante de shardability: cada inserción debe incluir una clave de particionado determinista (ej. `community_id` o hash de flow) y las queries de correlación deben expresarse de forma que el planificador pueda enrutarlas a una única partición (o a una consulta scatter-gather con semántica conocida). Implementar un prototipo sobre un dataset pequeño con dos shards lógicos y medir la latencia extra. Si con la arquitectura actual no se puede expresar esa clave sin cambiar el modelo de datos, la decisión D3 está cerrando la puerta.

**¿Bloqueante?** **Bloqueante.** La ADR debe incluir esta invariante como parte de D3 para asegurar que “diferir” no significa “descartar”.

---

### Q9 — El footgun ¿está prevenido o solo anotado?

**Objeción:** Documentar el riesgo de múltiples instancias de `Database` in-process no impide el desastre; debe ser imposible por construcción.

**Experimento:** Implementar un guarda singleton en el constructor de `Database` (variable estática atómica, con verificación y terminación controlada si ya existe una instancia). Test unitario que intente crear una segunda instancia sobre el mismo path y verifique que lanza una excepción o `exit` documentada. Medir que el coste de la verificación es insignificante (<1 µs). El invariante es: *es imposible tener dos `Database` sobre el mismo path dentro del mismo proceso*.

**¿Bloqueante?** **Bloqueante.** Corrupción silenciosa de datos es inaceptable; la guarda es trivial y su ausencia es una negligencia de ingeniería.

FDO

Deepseek