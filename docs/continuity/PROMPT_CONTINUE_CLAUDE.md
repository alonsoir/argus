# PROMPT DE CONTINUIDAD — DAY 209 (continúa DAY 205-208)
# Instrucciones generales para Claude:

1. Piensa antes de codificar
   Expón tus suposiciones. Pregunta cuando no estés seguro. Nunca adivines.

2. Simplicidad primero
   Escribe el código mínimo que resuelva el problema.
   Sin abstracciones que nadie pidió.

3. Cambios quirúrgicos
   No toques código no relacionado con la solicitud.
   Cada línea cambiada debe rastrearse hasta lo que se pidió.

4. Ejecución orientada a metas
   Convierte instrucciones vagas en criterios de éxito verificables
   antes de escribir una sola línea.

## Invariantes
- **medir, no votar** — verificar contra fichero, nunca contra memoria; trazar hacia atrás desde el binario.
- **JSON is the law** · **bronce PRESERVA, gold DECIDE** · **Via Appia** (ledger inmutable durable y verificable; Kuzu = proyección reconstruible).
- **EMECAS++** antes de cualquier merge · **PR obligatorio** (main tiene branch protection).
- **Consejo de Sabios** (9 modelos: Claude, ChatGPT, DeepSeek, Gemini, GLM, Grok, Kimi, Mistral, Qwen) ratifica decisiones de arquitectura.
- Python3 heredoc (lectura→memoria→escritura) para editar ficheros en macOS · NUNCA `sed -i` · `vagrant ssh defender -c` para comandos del VM · commits/push desde el HOST.
- Un día, una batalla. Features pequeñas (días, no semanas), merge frecuente a main vía EMECAS++.
- `.PHONY` en Makefile: lista separada por ESPACIOS, nunca comas (lección DAY 205).
- Al comitear y hacer push, verificar SIEMPRE con `git log --oneline -3 <rama>` y `git log --oneline -3 origin/<rama>` (lección DAY 206).
- Crear la rama de trabajo ANTES del primer commit, no después (lección DAY 207, aplicada correctamente DAY 208).
- pkg-config en shells no-interactivos: `vagrant ssh <vm> -c "..."` no carga `.bashrc` de forma fiable; exportar `PKG_CONFIG_PATH` explícitamente con doble-escape `\$$` en Makefile/CMake (lección DAY 207).
- No asumir que un target de `test-all` cubre lo que parece cubrir — verificar la cadena de dependencias del Makefile antes de lanzar `emecas+++` (lección DAY 207).
- **Lección nueva DAY 208 — orden de declaración en CMakeLists importa, CMake no avisa de variables vacías.** Un bloque `target_link_libraries(... ${Protobuf_LIBRARIES} ...)` insertado ANTES del `find_package(Protobuf REQUIRED)` correspondiente (que vivía más abajo en el fichero, en otra sección) enlazó silenciosamente contra una variable vacía — símbolos de protobuf indefinidos en el link, sin ningún aviso de CMake sobre la causa real. Regla operativa: cualquier bloque nuevo que use `${VARIABLE}` de un `find_package`/`find_library` debe insertarse DESPUÉS de esa declaración en el fichero, nunca asumir que "está en el mismo CMakeLists" es suficiente.
- **Lección nueva DAY 208 — los scripts scratch `.py` se cuelan en `git add` si no se meten en `.gitignore` INMEDIATAMENTE tras crearlos**, no al final de la sesión. Pasó dos veces (DAY 207 y DAY 208): un `git add` amplio capturó scripts de un solo uso junto con el código real, obligando a `git restore --staged` para desenredar. Regla operativa: en cuanto Claude cree un script Python de un solo uso para editar ficheros, añadirlo al `.gitignore` en el mismo momento, antes de cualquier `git add`.
- **Lección nueva DAY 208 — capturar decisiones estratégicas en BACKLOG en el momento, no "para después".** Hoy hubo una conversación larga y sustanciosa sobre arquitectura de flota multi-instalación, servicio GeoIP propio, gobernanza de datos entre instalaciones, y una línea de investigación concreta con MITRE ATT&CK/Atomic Red Team para el ransomware_detector inerte. **Nada de esto se llegó a escribir en BACKLOG.md como entrada formal** — quedó solo en la conversación. Acción 1 de DAY 209: capturarlo antes de que se diluya.

## Estado al cierre de DAY 208 — Flujo B completo, verificado en limpio, EMECAS+++ verde (1h36m)

### Resumen de lo cerrado hoy

1. **`parquet_to_kuzu_loader.cpp` escrito e integrado en producción.**
   `correlation-engine/tools/parquet_to_kuzu_loader.cpp`, según el diseño
   ratificado por el Consejo el DAY 207 (ver
   `docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md`):
   - Bucle multi-chunk completo desde el primer commit (nunca `chunk(0)` a
     ciegas), con `WARNING` vía `spdlog` si `num_chunks() > 1` — decisión de
     Alonso, desviación deliberada de la mayoría del Consejo.
   - Manejo de error explícito si el Parquet gold no existe
     (`fs::exists` antes de tocar Arrow) — verificado en la práctica cuando
     `/tmp` desapareció tras un `vagrant destroy` a mitad de sesión.
   - `flow_uid` (col 21) leído directo, nunca recomputado. Cols 18-20
     documentadas explícitamente como no usadas, con el motivo de cada una.
   - Integrado en `correlation-engine/CMakeLists.txt` (target nuevo, sin
     `avro-c` — Flujo B no toca AVRO).

2. **`test_flujo_b_end_to_end.cpp` — verificación real, no solo diseñada.**
   En vez de refactorizar el converter (bloqueo que se dejó pendiente ayer),
   se optó por invocar los binarios REALES (`bronze_to_gold_converter`,
   `parquet_to_kuzu_loader`) como subprocesos — caja negra, más fiel a cómo
   los usaría un operador. El test:
   - Escribe bronce real con `CorrelationWriter` real (2 filas sintéticas,
     1 MALICIOUS + 1 BENIGN, community_id distintos).
   - Ejecuta converter + loader reales vía `std::system()`.
   - Verifica el grafo Kuzu resultante: `NetworkFlow=2`, `Alert=1`,
     `TelemetryEvent=1` (hueco detectado al diseñar el test — la verificación
     manual de ayer no comprobó `TelemetryEvent`, que `cypher_builder.hpp`
     genera SIEMPRE para filas no-MALICIOUS), y las dos aristas.
   - **Calcula el `flow_uid` esperado de forma independiente** dentro del
     propio test (llamando a `compute_flow_uid`/`window_micros` directamente)
     y confirma que Kuzu tiene exactamente esos nodos — cierra el hueco de
     "lo comparé a ojo" de la verificación manual previa.
   - Kuzu de test aislado y desechable (path temporal, borrado al final) —
     nunca compartido con nada persistente.
   Bug encontrado y corregido durante la integración: el bloque de
   `target_link_libraries` quedó insertado ANTES de `find_package(Protobuf
   REQUIRED)`/`find_library(CORRELATION_V1_LIB...)` (que viven en la sección
   de `test_bronze_to_kuzu_circuit`, más abajo en el fichero) — símbolos de
   protobuf indefinidos en el link, sin aviso de CMake sobre la causa real
   (ver lección nueva arriba). Corregido moviendo el bloque al final del
   fichero, después de esas declaraciones.

3. **Verificación manual previa a los tests automatizados — primera prueba
   empírica real de Flujo B.** Antes de escribir el test, se verificó a mano
   contra el Parquet gold real (24 filas, todas BENIGN): `NetworkFlow: 24`,
   `Alert: 0`/`Alert->Flow: 0` confirmados correctos contra el CSV bronce
   original (`awk` confirmó 24/24 filas BENIGN). El primer `flow_uid`
   coincidió bit a bit con el que el converter había impreso como "fila 0"
   en dos ejecuciones distintas del día — la primera evidencia empírica
   (no solo diseñada) de que Flujo A y Flujo B comparten el mismo
   identificador.

4. **8/8 en `ctest` del correlation-engine.** Confirmado tanto en build
   incremental como en reconstrucción completa desde cero (`emecas+++` con
   `vagrant destroy -f && vagrant up`, 1h36m de reloj, 20% CPU medio — la
   mayoría del tiempo es I/O de red/descargas, no cómputo). EMECAS+++ PASSED.

5. **`test_parquet_to_kuzu_loader.cpp` (esqueleto de ayer, con `GTEST_SKIP()`)
   queda REDUNDANTE** — `test_flujo_b_end_to_end.cpp` cubre el mismo terreno
   por la vía de caja negra (subprocesos), sin el bloqueo de refactorización
   que el esqueleto original esperaba resolver. **Sigue en el repo, sin
   registrar en CMakeLists (inerte). Se elimina en DAY 209 — ver acción 2.**

6. **Mergeado a `main`** — rama `day208/flujo-b-parquet-to-kuzu-loader`
   (parquet_to_kuzu_loader.cpp, test_flujo_b_end_to_end.cpp, fix de orden en
   CMakeLists), vía PR, EMECAS+++ verde como evidencia adjunta.

### Conversación extensa sin cerrar en código — capturar en DAY 209 (ver acción 1)

Sesión larga de reflexión estratégica sobre el rumbo del proyecto, disparada
por el mockup de Three.js/dashboard. Resumen para no perderlo:

- **Arquitectura de flota**: mismo software, dos perfiles de config (mismo
  patrón que `ml_detector_config.json` ya usa con `lab/cloud/bare_metal`) —
  un perfil "central" (recibe grafos de N instalaciones, capacidad de
  promocionar datasets/plugins a la flota) y un perfil "campo" (un nodo,
  su propia instalación). **Bloqueado por la fase de anonimización, que
  todavía no existe** — es la primera tarea de post-FEDER, según Alonso.
- **Servicio GeoIP propio**: componente C++ asíncrono y ligero, formato MMDB
  (memory-mapped, actualización asíncrona por diseño del propio formato,
  sin inventar nada), + detección de proxy/Tor (base de datos distinta,
  con coste de licencia a decidir según si "enterprise" significa alta
  disponibilidad, cobertura/precisión comercial, o ambas). Pregunta sin
  resolver: ¿se geolocaliza en el borde (antes de anonimizar, IP nunca sale
  cruda) o en el servidor central? Recomendación no vinculante: en el borde.
- **Línea de investigación concreta — MITRE ATT&CK / Atomic Red Team**: en
  vez de necesitar malware real o laboratorio de contención (que Alonso no
  tiene ni tendrá pronto), emular técnicas documentadas de un ransomware
  real y nombrado (ej. perfil de técnicas de LockBit, ya cartografiado por
  terceros) con Atomic Red Team (Red Canary, activo, +1700 tests) sobre una
  VM ya existente del Vagrantfile. Esto ataca directamente
  `DEBT-RANSOMWARE-ML-HEAD-INERT-001`/`DEBT-CIRCUIT-SCORE-NONTRIVIAL-REVAL-001`
  (ya documentados, el detector de ransomware no tiene señal real de
  entrenamiento de tráfico de red). Metodología estándar de industria,
  publicable, sin ambigüedad legal/ética — el tipo de resultado, aunque sea
  una mejora porcentual pequeña y honesta, que Alonso cree que haría que
  Andrés (contacto institucional UEx/INCIBE, sin respuesta reciente sobre
  el tema de datasets) apoyara abiertamente la solicitud de fondos.
- **Mockup de dashboard (Three.js)**: explorado visualmente en el chat
  (no en el repo) — grafo 3D limitado a subgrafos acotados (el grafo
  completo en vivo se vuelve ilegible pasado unos cientos de nodos), panel
  de geolocalización esquemático, whitelist de consultas Cypher con nombre
  (mismo patrón que `cypher_builder.hpp` ya usa para escritura, aplicado a
  lectura) + modo Cypher libre como vía de escape.
- **Continuidad de KuzuDB (DEBT-KUZU-CONTINUITY-001)**: información nueva
  encontrada — existen forks activos post-archivado (`Vela-Engineering/kuzu`,
  preserva 100% del API/Cypher original + añade multi-writer; `LadybugDB`,
  reposicionado "graph lakehouse"; `Kineviz/bighorn`; `predictable-labs/
  ryugraph`). No cambia la decisión de Alonso (no depreciar hoy), pero reduce
  el riesgo percibido de "abandono total sin alternativa". Pendiente:
  anexar esta info a la entrada de BACKLOG ya existente.
- **Descartado explícitamente**: motor de grafos propio sobre Boost Graph
  Library. BGL es librería de algoritmos en memoria, NO una base de datos
  (confirmado por búsqueda — clasificación académica explícita, papers que
  "extienden BGL-like libraries with persistent storage" como su aportación
  propia). Construirlo sería construir una base de datos entera desde cero;
  dado que no se puede perder Cypher (Alonso lo confirmó explícitamente),
  ningún fork existente lo pierde, así que no hay razón real para intentarlo.

## Rama

Todo el trabajo de DAY 208 ya vive en `main` tras el merge de este PR.
`day208/flujo-b-parquet-to-kuzu-loader` puede borrarse (ya mergeada).
No hay rama de trabajo abierta pendiente al cierre de DAY 208 — recordar:
rama ANTES del primer commit de DAY 209, no después.

## Acciones DAY 209 (en orden)

1. **Capturar en BACKLOG.md la conversación estratégica de hoy** (ver sección
   de arriba) — al menos tres entradas separadas:
   - Visión de arquitectura de flota (central/campo), explícitamente marcada
     como post-FEDER, bloqueada por anonimización.
   - Servicio GeoIP propio (MMDB + detección proxy/Tor), con la pregunta
     abierta de dónde se resuelve (borde vs central) sin decidir todavía.
   - Línea de investigación MITRE ATT&CK/Atomic Red Team — la más
     accionable de las tres, candidata a convertirse en trabajo real antes
     de post-FEDER si Alonso decide priorizarla.
   - Actualizar `DEBT-KUZU-CONTINUITY-001` con la info de los forks activos
     (Vela-Engineering, LadybugDB, bighorn, ryugraph).
2. **Eliminar `correlation-engine/tests/test_parquet_to_kuzu_loader.cpp`**
   (esqueleto de DAY 207 con `GTEST_SKIP()`, redundante desde que
   `test_flujo_b_end_to_end.cpp` cubre el mismo terreno por caja negra).
   `git rm`, no borrado manual — mantener el historial de por qué existió.
3. **El test de equivalencia REAL Camino-0 ≡ Flujo-A+B** (predicado §3.1,
   ADR-058) sigue sin escribirse — hoy solo se verificó Flujo A+B en
   solitario. La técnica de subprocesos de hoy probablemente sirve para el
   lado Flujo A+B; el lado Camino 0 ya es directamente enlazable
   (`process_segment` + `KuzuGraphSink`, sin subprocesos, como
   `test_bronze_to_kuzu_circuit.cpp` ya demuestra). Diseñar como dos Kuzu de
   test aislados, comparar conteos + `flow_uid` + scores + igualdad de
   conjuntos de aristas, excluyendo `ingested_at`/`temporal_anomaly` (ya
   excluidos por ADR-058 v3).
4. **Pendiente de sesiones anteriores, evaluar margen:**
   - `DEBT-SECRETS-MANAGER-PERSISTENCE-001` (P1, 2-3 sesiones) — Vault.
   - `DEBT-PARQUET-GOLD-SCHEMA-MULTISENSOR-001` — diseño multi-sensor,
     requiere su propia ronda de Consejo.

## Punteros

- `correlation-engine/tools/parquet_to_kuzu_loader.cpp` — Flujo B completo,
  producción, junto a `bronze_to_gold_converter.cpp` en el mismo directorio.
- `correlation-engine/tests/test_flujo_b_end_to_end.cpp` — test real,
  subprocesos de los binarios reales, 8/8 en ctest, verificado en limpio.
- `correlation-engine/tests/test_parquet_to_kuzu_loader.cpp` — ESQUELETO
  REDUNDANTE, eliminar DAY 209 (acción 2).
- `correlation-engine/CMakeLists.txt` — orden importa (lección DAY 208);
  cualquier bloque nuevo que use variables de `find_package`/`find_library`
  va DESPUÉS de esas declaraciones, no antes.
- `docs/council/PROPUESTA -- Flujo B, parquet_to_kuzu_loader (DAY 207).md` —
  diseño ratificado + resolución final, fuente de verdad ya implementada.
- `docs/BACKLOG.md` — pendiente de las 3-4 entradas nuevas de la acción 1
  de hoy (conversación estratégica sin capturar).
- `.gitignore` — todos los scripts Python scratch de sesión van aquí,
  AL MOMENTO de crearlos, no al final (lección DAY 208, ya pasó dos veces).

*Via Appia Quality — Un escudo que aprende de su propia sombra.*
