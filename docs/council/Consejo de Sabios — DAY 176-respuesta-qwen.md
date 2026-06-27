Estimado equipo,

Como árbitro final y en nombre del Consejo, validamos el cierre exitoso del hito **(A)** en el DAY 176. La implementación es sólida, el enfoque *fail-closed* es la decisión correcta para evitar degradaciones silenciosas, y las lecciones operativas documentadas son oro puro para la estabilidad del CI.

A continuación, respondemos a vuestras preguntas y establecemos el rumbo para el DAY 177, priorizando la determinística sobre la velocidad de ejecución.

---

### Respuestas del Consejo a las Preguntas (Q1 - Q5)

#### **Q1 — `node_id` sintético: ¿qué valor?**
**Decisión:** Opción **(c) adaptada**, alineada con la filosofía de `community_id`.
- **Modo Mock:** `node_id = "synth:node:mock"`. Debe ser auto-identificable para que cualquier consumidor (Kuzu, dashboards) pueda filtrar o ignorar este tráfico de prueba fácilmente.
- **Modo Isomorfo:** `node_id = "synth:node:00"` (o un valor fijo configurable vía env var `ARGUS_NODE_ID=synth-node-00`).
- **Razonamiento:** No acopléis el injector al `config.json` del sniffer (opción b). El injector es una herramienta de CI; debe ser autónomo. Al usar un prefijo `synth:`, garantizamos que el `flow_uid` sea determinista en CI (resolviendo la degeneración), pero claramente distinguible del tráfico de producción en los joins de Kuzu.

#### **Q2 — El gap de filas: ¿lo perseguimos antes de confiar en el bronce sintético para CI?**
**Decisión:** **SÍ, prioridad absoluta antes de cualquier otra cosa.**
Un CI determinista que no puede predecir el número exacto de filas de salida es un CI rojo por diseño.
- **Acción inmediata:** Cambiad el `zmq::send_flags::dontwait` a `send_flags::none` (bloqueante) **solo en el injector sintético**. El injector no tiene restricciones de rendimiento de producción; su único trabajo es garantizar la entrega para la prueba.
- **Diagnóstico:** Si el gap desaparece, era `dontwait` (pérdida no determinista bajo carga). Si el gap persiste exactamente en las mismas filas, es el *threshold* del `CorrelationWriter`. En ese caso, es determinista y aceptable, pero debe documentarse en el test de CI (ej. `assert rows == 42`). No aceptaremos "pérdida silenciosa" como estado final.

#### **Q3 — Orden DAY 177: ¿(B) col 17 primero, o estabilizar (A) primero?**
**Decisión:** **Estabilizar (A) primero.**
- **Razonamiento:** "Mide dos veces, corta una". Si cambiamos el contrato de la columna 17 a string (lo que invalida los HMACs actuales) mientras el injector aún tiene deudas de `node_id` y conteo de filas, cualquier fallo en el test `test_correlation_roundtrip` será un dolor de cabeza para depurar: ¿falló por el cambio de string, por el HMAC, o por el gap de filas?
- **Flujo DAY 177:**
    1. Fix `node_id` sintético.
    2. Fix/Documentar gap de filas (ZMQ blocking).
    3. Ejecutar E2E y confirmar conteo exacto.
    4. **Solo entonces**, aplicar el cambio de (B) col 17 a string y actualizar el test golden.

#### **Q4 — Concurrencia del bronce: ¿basta el mutex, o queremos una prueba de estrés?**
**Decisión:** **Prueba de estrés ligera y específica.**
No hace falta un framework de over-engineering, pero la intuición no sustituye a la evidencia en sistemas multi-hilo.
- **Acción:** Añadid un script o target de make `make test-bronze-concurrency` que lance el `CorrelationWriter` con 10 hilos inyectando 10,000 eventos cada uno.
- **Asserts:**
    1. `wc -l` del archivo de salida == 100,000.
    2. Un `grep` o script simple que verifique que **todas** las líneas tienen exactamente 18 comas (19 columnas) y que el HMAC (col 18) es válido para un subconjunto aleatorio. Si hay entrelazado, el número de comas se disparará o el HMAC fallará. Esto es barato de implementar y blindará la confianza en el patrón `CsvEventWriter`.

#### **Q5 — Fuente compartida `community_id.cpp`: ¿acoplamiento aceptable o frontera a formalizar?**
**Decisión:** **Paso intermedio con deuda técnica formalizada.**
- Extraer una librería completa (`libs/flow-identity`) hoy es prematuro si solo la consumen el sniffer, el injector y los tests. Sin embargo, el acoplamiento de directorios (`tools/` dependiendo de `sniffer/src/`) es una mala práctica arquitectónica a largo plazo.
- **Acción:** Dejadlo como está por hoy para no bloquear, pero añadid un comentario explícito en `tools/CMakeLists.txt`:
  `# TODO(DEBT-LIB-001): Cuando un tercer consumidor (ej. adaptador Zeek) necesite esto, extraer a libs/flow-identity para romper el acoplamiento de directorios.`
- **Nota sobre el cosmético:** Moved el `enum CidMode` y la validación a scope de archivo **hoy**. Son 5 minutos que mejoran la legibilidad y eliminan la duplicación de `getenv`. No dejéis deudas cosméticas que se acumulan.

---

### Validación de las Lecciones Operativas
El Consejo respalda plenamente las lecciones anotadas. Por favor, actualizad el `README.md` del repositorio o el script de bootstrap del CI con:
1. La advertencia de `make` desde el HOST.
2. La secuencia sagrada de limpieza: `tmux kill-session` -> `rm` -> `make start`.
3. El requisito de `sudo` + `LD_LIBRARY_PATH` para el injector.

Documentar esto ahorra horas de depuración a cualquier nuevo miembro del equipo o a vosotros mismos en 3 meses.

### Resumen de Órdenes para DAY 177
1. **Fix cosmético:** `CidMode` a scope de archivo.
2. **Fix funcional:** `node_id` sintético (prefijo `synth:`).
3. **Investigación:** Cambiar ZMQ a bloqueante en el injector para aislar la causa del gap de filas. Documentar el resultado.
4. **Validación:** Correr la prueba de estrés de concurrencia ligera del `CorrelationWriter`.
5. **Feature:** Una vez lo anterior sea verde y determinista, aplicar el cambio de (B) `DetectorSource_Name()` en col 17 y actualizar el test de roundtrip.

Quedamos a la espera del reporte de cierre del DAY 177. Excelente trabajo manteniendo la invariante de que "el sniffer es la única autoridad de la identidad del flujo".

**Alonso**  
*Árbitro Final — Consejo de Sabios*

FDO

qwen