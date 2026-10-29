# DAY310 — Rama del RAG Logger del ml-detector (diseño y medidas)

Deudas: DEBT-RAG-LOGGER-BRANCH-001 y DEBT-DOCS-CSV-SCHEMA-V1-001. Base: `main` en `6605c296` (PR #151); el árbol de
trabajo de Alonso está en `cc0b9bc0` (= `6605c296` + un commit de documentación: BACKLOG y `prompt_day310.md`).
Marca en el código: `[RAG-LOGGER-RETIRE-D310]`. Rama propuesta: `feat/rag-logger-retire`.

Regla de este documento: las secciones escritas antes de medir no se reescriben; el resultado va aparte.

## 1. Inventario (sacado contra el árbol, no heredado de la deuda)

Patrón (`git grep -i -E`): `rag_logger|RagLogger|RAGLogger|rag-logger|rag_log|CTX_RAG|logs/rag|secrets/rag|log_hmac_key|explore_rag|test_rag|rag-watch|rag-validate|rag-consolidate|verify-rag|rag-log`.

Recuento corregido (con `git grep -c`, ver lección 1): en `6605c296`, **451 líneas en 126 ficheros**; fuera de
`docs/`, `site/` y `emecas*.md`, **216 líneas en 42 ficheros**. La documentación histórica no se toca.

Lo vivo, por grupos:

- ml-detector: `rag_logger.hpp/.cpp`, `rag_logger_config.json`, su cableado en `zmq_handler.hpp/.cpp`
  (`rag_logger_`, `MLContext`, `log_rag_statistics`, `calculate_events_per_minute`, `events_processed_total_`),
  `config_loader.hpp/.cpp` (`rag_logger.enabled`, `scoring.requires_rag_threshold`, `scoring.divergence_high_threshold`),
  `ml_detector_config.json`, `CMakeLists.txt`, `test_rag_logger_artifact_save` (no prueba el RAG Logger: semántica proto3).
- tools: `generate_synthetic_events.cpp` compila `ml-detector/src/rag_logger.cpp`; `tools` entra en `pipeline-build`.
  Solo lo usaba `day38-step2`. `tools/config/synthetic_generator_config.json` solo lo leía él.
- Makefile: 19 entradas `.PHONY` del RAG sin receta ni uso; familia `day38-*` (genera artefactos RAG sintéticos).
- Vagrantfile: alias `explore-logs`. Scripts del RAG: `explore_rag_logs.sh`, `test_rag_logger.sh(.backup)`,
  `day15_automated_test.sh`, `analyze_rag_logs.py`, `export_rag_to_csv.py`.
- ansible: plantilla `rag_logger_config.json.j2`, su tarea en `deploy_configs.yml`, el bloque `rag_logger` de
  `ml_detector_config.json.j2` y las variables `rag_*`/`ml_rag_base_dir` de los cuatro `group_vars`.
- crypto-transport: `CTX_RAG_ARTIFACTS` (`contexts.hpp`) y su línea en `test_integ_contexts.cpp`.
- etcd: entrada `rag_log_hmac` de `etcd-server.json`; ejemplos `/secrets/rag/log_hmac_key` en `etcd_client.hpp` y en
  `test_hmac_integration_client.cpp`; bloque de ejemplo `rag_logger` en `test_put_config_integration.cpp`.
- sniffer: dos comentarios que nombran al rag_logger (`ring_consumer.cpp:1603`, `test_proto3_embedded_serialization.cpp`).
- residuos (van a DEBT-REPO-RESIDUOS-001, no a esta rama): `scripts/d285_patch_writers.py`, `scripts/ddos_v1/*`,
  `scripts/flow_expiry/d309_backlog.py`, `scripts/monitor_day23.sh`, `scripts/tsan/tsan_investigation_inside_vm.sh`.

## 2. Lo que dice el código (hipótesis antes de medir, tal como se escribieron)

1. El proceso que no se puede deprecar es la clave HMAC: `main.cpp:403` la pide "para el CSV", pero sin ella tampoco se
   crea el `correlation_writer` (bronce), y en silencio (`zmq_handler.cpp:159`, sin `else`). La clave sale de
   `/secrets/ml-detector` (generada bajo demanda), no de `/secrets/rag/log_hmac_key`.
2. El etcd-server no lee el bloque `secrets` de su JSON: lo construye fijo en `etcd-server/src/main.cpp:193-199`.
3. `rag_logger_config.json` anida los umbrales en `thresholds`/`performance`; la fábrica lee claves de primer nivel:
   se aplicaban los defectos del código en silencio.
4. `csv_writer` apagado desde `9134c5b7` (2-oct, DAY285); con el RAG encendido el CSV pasaba por el filtro del RAG (dos
   caminos); se escribe antes de que corran ransomware/traffic/internal; `test-parquet` (en `test-all`) exige Parquet
   del ml-detector y solo puede pasar con CSV viejos de `/vagrant/logs`.
5. Con todo apagado, cada evento construía `MLContext` y calculaba `requires_rag_analysis` sin consumidor.
6. `test_rag_logger_artifact_save` no enlaza `rag_logger.cpp`.

## 3. Medidas M0-M4

Predicciones escritas antes de medir (texto de la sesión):

- M0 (Mac): "451 y 122".
- M1 (defender, `ml-detector.log`): por arranque, `HMAC key received for /secrets/ml-detector (64 chars)`,
  `[csv] HMAC key retrieved (64 chars)`, `CsvEventWriter desactivado`, `CorrelationWriter initialized`,
  `RAG Logger desactivado`; ninguna línea con `secrets/rag`.
- M2 (defender, `etcd-server.log`): "solo componentes por su nombre (ml-detector como mínimo); nunca rag".
- M3 (defender): "M3a muestra CSV, todos con fecha anterior al 2-oct; M3b vacío".
- M4 (defender, `ctest -N`): "Total Tests: 15 ... entre ellos test_rag_logger_artifact_save, test_csv_event_writer y
  test_csv_feature_extraction".
- M0b (Mac): "122 ... el diff solo muestra ficheros de documentación ... +5 líneas, +2 ficheros".

Resultados:

| Medida | Resultado | Veredicto |
|---|---|---|
| M0 | 456 líneas, 124 ficheros | NO coincide → se paró y se midió M0b |
| M0b | `6605c296`: 126 ficheros (no 122). Diff Mac: BACKLOG +1, `PROMPT_CONTINUE_CLAUDE.md` +2 (sin commitear), `prompt_day310.md` +2; HEAD `cc0b9bc0` | El "122" era un error de cuenta (lección 1). Diferencia solo documental: +5 líneas, +2 ficheros, como se predijo |
| M1 | Tres arranques del 27-oct, las cinco líneas cada uno, 0 `secrets/rag` | Coincide |
| M2 | Desde el 15-sep solo `/secrets/ml-detector` y `/secrets/firewall`; casi cada arranque trae `Generating new HMAC key` | Coincide. Hecho nuevo: claves solo en memoria, se regeneran en cada arranque del etcd-server |
| M3a/M3b | Último CSV `2026-10-10.csv`, posterior al 2-oct | NO coincide (ver abajo) |
| M4 | 15 tests, los tres citados entre ellos | Coincide |

M3, explicación escrita tras el fallo (no es predicción): la fecha que cuenta es la llegada a `main`, no la del commit.
`9134c5b7` llegó a `main` en `bc73b831` (PR #143, 11-oct). En `bc73b831^1` el JSON no tenía `csv_writer.enabled`
(defecto `true`) y tenía `rag_logger.enabled=true`. Encaja: el último CSV es del 10-oct y ninguno después. Queda
confirmado que `test-parquet` pasa con CSV viejos.

## 4. Quién firma qué (medido en código, DAY310)

| Fichero | Lo escribe | Firma | Destino |
|---|---|---|---|
| Bronce `correlation_v1` (`/vagrant/logs/correlation`) | `CorrelationWriter` del ml-detector; mismo contrato en los adapters Suricata/Zeek/Wazuh | HMAC col 18 (`libs/correlation-v1`), clave `/secrets/ml-detector` | `bronze_to_gold_converter` → oro → Kuzu |
| `firewall_blocks.csv` | logger del firewall-acl-agent | clave `/secrets/firewall` | mitad firewall de `parquet-convert` |
| CSV 127 columnas (`/vagrant/logs/ml-detector/events`) | `CsvEventWriter` | clave `/secrets/ml-detector` | se retira (D2) |
| `.jsonl` + `.pb.enc`/`.json.enc` (`/vagrant/logs/rag`) | RAG Logger | cifrado `CTX_RAG_ARTIFACTS`, sin HMAC | se retira (D1) |

- El canal ml-detector → firewall no usa la clave del etcd-server: `CryptoTransport` con la semilla local de
  `SeedClient` (HKDF-SHA256 + ChaCha20-Poly1305). Sin etcd-server, las clasificaciones llegan autenticadas.
- Adapters y conversores no tienen clave propia: `mitre_start.sh:32` y `ctu_start.sh:38` piden `/secrets/ml-detector`
  con `curl`. Con el etcd-server caído no llega bronce firmado de ningún sensor.
- El firewall sin clave no escribe `firewall_blocks.csv` (`zmq_subscriber.cpp:794`) y sigue bloqueando; solo avisa
  una vez al arrancar.

## 5. Decisiones de Alonso (DAY310)

- D1: se retira el RAG Logger entero.
- D2: se retira el `CsvEventWriter` y la mitad ml-detector de `parquet-convert`/`test-parquet`; se queda la del firewall.
- D3 (regla): el ml-detector arranca y recibe su clave HMAC del etcd-server para clasificar y escribir bronce firmado.
  Nunca se escribe bronce sin firma: al grafo solo llegan operaciones firmadas. Sin clave, el firewall sigue actuando
  (la protección del hospital es la misión prioritaria) y el grafo muestra el hueco; alarma enorme en el log.
- D4: el etcd-server que lee el bloque `secrets` de su JSON va en deuda propia (DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001).
- E1: el intervalo de la alarma y del reintento va al JSON (rango 10-3600, defecto 60).
- E2: en cuanto el ml-detector obtiene la clave, firma bronce, sea al arrancar o tras reiniciarse el etcd-server. Más
  adelante: que solo los componentes autorizados de un despliegue puedan hablar entre ellos.
- E3: la alarma periódica del firewall va en otra deuda.
- E4: se parte en dos: la mitad ml-detector (reintento y cambio de clave) va en esta rama dentro de E2; la mitad
  etcd-server (no regenerar en cada arranque, persistir, adapters y conversor) va con la deuda de D4.

## 6. Plan de la rama

1. Retirar el RAG Logger (D1): ml-detector, tools, Makefile, Vagrantfile, scripts, ansible.
   1b. Lo que cuelga fuera: `CTX_RAG_ARTIFACTS`, entrada `rag_log_hmac` de `etcd-server.json`, ejemplos de
   etcd-client, comentarios del sniffer, campo protobuf `requires_rag_analysis` → `reserved` (como DAY306).
2. Retirar el `CsvEventWriter` y la mitad ml-detector de `parquet-convert`/`test-parquet` (D2).
3. Clave del bronce (E1/E2): campo `bronze_key.check_interval_seconds`; sin clave, `CRITICAL [BRONCE-SIN-CLAVE]`
   periódico con eventos sin bronce y reintento; con clave, comprobación de cambio y `[BRONCE-CLAVE-CAMBIADA]` cerrando
   el segmento. Mensajes `[csv] HMAC key` → clave del bronce.
4. BACKLOG: D4 ampliada (persistencia, desincronización), alarma del firewall (E3),
   DEBT-ETCD-SECRETS-CONFIG-HARDCODED-001.
5. Documentación: `feature_schema.md`, `csv_event_writer.hpp` (se va), `contract_validator.cpp`.

Cada paso con su antes y su después; EMECAS+++ production al final.

## 7. Paso 1 — retirar el RAG Logger

Parcheador de un solo uso `d310_paso1_retirar_rag_logger.py` (no se commitea), sha256
`9870ba901b3680842de0dc77c946ab0f446f1bbbe9c1017a1e6bb090cee43344`. 16 ficheros editados (50 ediciones) y 13 borrados.
Probado en una copia desechable de `6605c296`:

- `--check` → 29 pendientes, 0 errores; `--apply` → 29 de 29 en su estado de llegada; `--check` → 29 ya aplicados.
- `git diff` idéntico (sha256 `34430c1f…`) al de una segunda copia parcheada con el mismo plan.
- Con un fichero tocado por fuera: `--apply` da ERROR y no escribe nada.
- Sintaxis con `-std=c++20 -Wall -Wextra -Werror` de los 16 `.cpp` de `ml-detector/src` contra las cabeceras del repo
  (protobuf 3.21.12, onnxruntime 1.17.1, `-DHAVE_ETCD_CPP_API -DPLUGIN_LOADER_ENABLED`): todos OK. No es la
  compilación del pipeline: esa se mide en la VM.
- Inventario del árbol parcheado (fuera de docs): 17 ficheros, 60 líneas = marcas propias en `config_loader.cpp` (4)
  y `zmq_handler.cpp` (1) + lo de 1b + comentario de la clave propia del firewall + residuos.

Nuevo en el código: `[CONFIG-OBSOLETO] rag_logger` y `[CONFIG-OBSOLETO] scoring.<campo>` para
`divergence_high_threshold` y `requires_rag_threshold` (solo los usaba el RAG Logger), patrón DAY306.
Se borra también la familia `day38-*` del Makefile (solo existía para generar artefactos RAG sintéticos; `day38-step1`
duplicaba `etcd-server-start`).

Predicciones del paso 1 (antes de medir; el "antes" es el de DAY309 sobre `69d8f207`, mergeado como `6605c296`):

- P1. `git status --short`: 30 líneas = 16 `M` + 13 `D` del parcheador + `PROMPT_CONTINUE_CLAUDE.md`.
- P2. `make pipeline-build PROFILE=production`: rc 0 y 0 líneas de `warning`/`error` de compilador.
- P3. `make test-components PROFILE=production`: cinco líneas, 9, 23, **14**, 3 y 82 (antes 9, 23, 15, 3, 82).
- P4. `ctest -N` del ml-detector: `Total Tests: 14`, sin `test_rag_logger_artifact_save`.
- P5. `lab-e2e-mitigacion` y `lab-e2e-protegidos` (`LAB_E2E_DIA=day310`): PASA los dos.
- P6. En `ml-detector.log` tras esas corridas: 0 líneas `RAG Logger`, 0 `[CONFIG-OBSOLETO]`, una
  `CorrelationWriter initialized` por arranque y la `[csv] HMAC key retrieved` igual que antes (se renombra en el paso 3).

## 8. Lecciones DAY310

1. Un recuento por fichero no se hace con `cut -d:` si las rutas pueden llevar ":" (cuatro informes del Consejo se
   fundieron en uno: 122 en vez de 126). Se cuenta con `git grep -c` o `git grep -l`.
2. La fecha de un cambio es su llegada a la rama que corre, no la del commit (M3).
3. Antes de borrar un componente, mirar quién lo compila además de quién lo llama: `tools` compilaba
   `rag_logger.cpp` dentro de `pipeline-build`.
4. "Firmado" no es una sola cosa: el canal al firewall se autentica con la semilla; el bronce y el CSV del firewall,
   con claves HMAC del etcd-server. Cada consecuencia de una caída se razona por su mecanismo.

## 9. Resultados de los pasos 1, 1b y 2 (medidos DAY310; las predicciones de §7 no se tocan)

Paso 1 (commit `9a5ccf0f`): P1 30 líneas, P2 rc 0 y 0 diagnósticos, P3 9/23/14/3/82, P4 14 tests, P5 mitigación PASA
(C1-C5) y protegidos PASA (FIN 10762, alertas 5381), P6 sin `RAG Logger` ni `[CONFIG-OBSOLETO]`. Todo como se predijo.

Paso 1b (commit `d745b930`), parcheador `d310_paso1b_retirar_rag_restos.py` (sha256 `2f0910c9…4112`):

| Medida | Predicción | Medido |
|---|---|---|
| A3 `test_hmac_integration_client` antes | 1/4 (solo `test_key_not_found`) | 1/4 |
| B3 compilación | rc 0, 0 diagnósticos | rc 0, 0 |
| B4 `grep -c requires_rag_analysis pb.h` | 0 (antes 20) | 0 |
| B4 `git status` | 13 líneas | 42: el paso 1 estaba en el índice sin commitear (premisa falsa); las 13 sin indexar, exactamente las predichas |
| B5 test-components | 9/23/14/3/82 | igual |
| B6 test-libs | igual a A1 (3, 5, 12/12, 1, 1) | igual |
| B8 test HMAC después | 4/4 | 4/4 |
| B9 protegidos | PASA | rc 2 sin veredicto: `DIA=day310b` no cumple `^day[0-9]{3}$` (error del comando, C1 lo confirmó) |
| C4 protegidos (corrida `lab_protegidos_p1b`) | PASA | PASA (FIN 10767, alertas 5382) |

Paso 2, parcheador `d310_paso2_retirar_csv_writer.py` (sha256 `d18205b4…67ed`): A1 `test-parquet` antes 86 ficheros
ml-detector + 1 firewall, PASSED; B1-B3 25 pendientes, 25 de 25, 26 líneas; B4 rc 0, 0 diagnósticos; B5 9/23/12/3/82;
B6 12 tests; B7 solo `firewall files validados: 1`, PASSED; B9 protegidos PASA (FIN 10773, alertas 5385); B10 sin
`CsvEventWriter` ni `[CONFIG-OBSOLETO]`. Todo como se predijo.

Lecciones añadidas:

5. Antes de inventar un parámetro, leer el validador que lo recibe (`day310b`).
6. Una predicción de `git status` depende de qué hay commiteado: escribirla con la premisa explícita.

## 10. Paso 3 — clave del bronce (diseño escrito antes del código)

### Lo que hay hoy (leído en el código)

- `main.cpp` pide la clave una vez (`get_hmac_key()` → `GET /secrets/ml-detector`) y la pasa al constructor de
  `ZMQHandler` como texto. Mensajes `[csv] HMAC key ...` (nombre heredado del CSV, ya retirado).
- `ZMQHandler` crea el `CorrelationWriter` solo si la clave no está vacía, y si lo está no avisa (`zmq_handler.cpp`, sin
  `else`). La clave no se vuelve a pedir nunca.
- `CorrelationWriter` exige la clave en el constructor (`hex_decode` lanza si no son 64 hex) y la usa en `serialize()`
  fuera del `mutex_`; la escritura del segmento sí va bajo `mutex_`. Ya cierra segmentos con rename atómico
  (`finalize_segment_locked`).
- El cliente etcd del ml-detector (`etcd_client::EtcdClient::get_hmac_key`) toma su propio mutex: se puede llamar
  desde otro hilo. En `main.cpp`, `etcd_client` se declara antes que `zmq_handler` en el mismo ámbito: vive más.
- El etcd-server regenera las claves en cada arranque y las guarda solo en memoria (M2).
- Si el etcd-server no responde al ARRANCAR, el ml-detector sale (`main.cpp:154-163`, `return 1`): ver F1.

### Comportamiento propuesto

1. JSON, bloque nuevo (el JSON es la ley; el defecto del código es el mismo valor):
   `"bronze_key": {"_doc": "...", "check_interval_seconds": 60}`, entero en [10, 3600]. Al arrancar se registra
   `[CONFIG] bronze_key.check_interval_seconds=60 (del JSON)`, o `[CONFIG-DEFAULT] ... (ausente | no entero | fuera de
   [10, 3600]): se usa 60` y el ml-detector arranca igual.
2. `CorrelationWriter`:
   - se construye siempre, con o sin clave;
   - `set_key(hex)` bajo `mutex_` devuelve `Primera | Igual | Cambiada | Invalida`. `Cambiada` cierra antes el segmento
     abierto (rename atómico), así que cada fichero de bronce va firmado con una sola clave. `Invalida` (no son 64 hex)
     conserva la clave anterior;
   - `write_record` sin clave no escribe y suma `records_sin_clave`; con clave, `serialize()` pasa a hacerse dentro del
     `mutex_` (la clave puede cambiar desde otro hilo). Un único hilo escribe: la contención es una vez por intervalo.
3. `ZMQHandler` recibe un proveedor de clave (`std::function<std::string()>`) en vez del texto, y un hilo propio
   (`bronze_key_thread_`, arrancado en `start()`, unido en `stop()`, espera en tramos de 200 ms para parar rápido):
   - cada `check_interval_seconds` llama al proveedor (la llamada HTTP nunca va en el hilo que procesa eventos);
   - sin clave: `CRITICAL [BRONCE-SIN-CLAVE]` en cada intervalo, con desde cuándo, cuántos segundos y cuántos eventos
     sin bronce, la consecuencia (la clasificación y el firewall siguen; al grafo no llega nada de aRGus) y qué hacer;
   - llega la primera clave o vuelve tras faltar: `[BRONCE-CLAVE-RECUPERADA]` con la duración del hueco y los eventos
     sin bronce;
   - cambia: `[BRONCE-CLAVE-CAMBIADA]` con el segmento cerrado y la huella de la clave vieja y la nueva (F3);
   - igual: nada (no hay nada nuevo que contar).
4. `main.cpp`: fuera la petición única y los mensajes `[csv]`; la primera petición la hace `ZMQHandler` al construirse
   (mismo orden que hoy: antes de procesar eventos) y registra `[BRONCE-CLAVE] clave recibida (huella …)` o
   `[BRONCE-SIN-CLAVE]`.

### Decisiones pendientes (Alonso)

- F1. El ml-detector sale si el etcd-server no responde al arrancar: sin clasificación ni firewall. Opciones: (a) deuda
  propia, ligada al etcd-server en HA y a D4; (b) en esta rama: arrancar sin etcd-server (sin registro, sin clave) y
  reintentar. Propuesta: (a), porque el registro y la subida de config también dependen del etcd-server y cambia el
  arranque entero.
- F2. Con clave vigente, el etcd-server no responde: (a) seguir firmando con la vigente y avisar
  `[BRONCE-CLAVE-SIN-CONFIRMAR]` en cada intervalo; (b) dejar de escribir bronce hasta confirmarla. Propuesta: (a): que
  el etcd-server no conteste no invalida la clave. Si vuelve con otra (se reinició), se detecta y se corta el segmento;
  las filas de la ventana quedan con la vieja (problema de la deuda de D4).
- F3. ¿Huella de la clave en el log (8 hex del sha256 de la clave, nunca la clave)? Propuesta: sí, para auditar
  cambios sin exponerla.

### Pruebas (antes de medir)

- Unitarias nuevas, `test_bronze_key` (gtest, mismo montaje que `test_correlation_roundtrip`, verifica con
  `parse_and_verify` del lector real): sin clave no escribe y cuenta; primera clave escribe; misma clave no corta
  segmento; clave distinta cierra el segmento, sus filas verifican con la vieja y no con la nueva, y las siguientes con la
  nueva; clave inválida conserva la anterior. ml-detector pasa de 12 a 13 tests.
- Regresión: protegidos PASA, log de arranque con `[BRONCE-CLAVE] clave recibida` y `[CONFIG] bronze_key...`.
- Medida nueva en el lab (instrumento commiteado): reiniciar el etcd-server con el pipeline vivo. Predicción a precisar
  cuando esté el instrumento: `[BRONCE-CLAVE-CAMBIADA]` en ≤ `check_interval_seconds`; el conversor con la clave nueva
  acepta todos los segmentos posteriores y rechaza como mucho las filas escritas en esa ventana.

## 11. Paso 3 — decisiones, hallazgo y predicciones (antes de medir en la VM)

Decisiones de Alonso (DAY310):

- F1: sin etcd-server el ml-detector no arranca, y así se queda: sin registro, un componente impostor podría colarse
  entre dos legítimos e inyectar datagramas fabricados, que es peor que no arrancar. El pipeline arranca fiable y
  consistente o no arranca. Deuda DEBT-ETCD-HA-TLS-RAFT-001 (justo después de REA): etcd-server con HTTPS y en HA con
  Raft por instalación, copia de respaldo en un clúster maestro por zona horaria, solo componentes autorizados del
  despliegue; absorbe la deuda de D4 (persistir claves, no regenerarlas en cada arranque, leer `secrets` del JSON) y
  enlaza con DEBT-ETCD-REMOTE-ADMIN-001 (acceso de admin por HTTPS).
- F2: con clave vigente y etcd-server sin responder se sigue firmando con la vigente; se marca en el log el tiempo en
  modo extendido (`[BRONCE-CLAVE-SIN-CONFIRMAR]` cada intervalo, `[BRONCE-CLAVE-CONFIRMADA]` al volver, con duración).
- F3: en el log solo la huella (8 hex del SHA-256 de la clave), nunca la clave.
- Re-verificar el grafo a posteriori es imprescindible; la retención la fija la ley (pueden ser años). Va a la deuda
  DEBT-BRONZE-KEY-ID-001: identificador de clave por segmento (camino b), historial de claves en Vault (solo
  versiones de clave) y un registro de ingesta por segmento fuera de Vault. Pendiente medir cuánto vive el bronce en
  disco y quién depende del formato del nombre del segmento.

Hallazgo medido en el código actual (`test_colision_antes.cpp`, compilado contra la rama en `efab4558`): con
`max_events_per_file=1` se escriben 3 filas (`write_record` devuelve true las tres) y en disco queda 1 fichero con 1
fila. El nombre del segmento tiene resolución de segundos y el segundo segmento abierto en el mismo segundo pisa en el
rename el fichero final del anterior. En producción ocurre con más de `max_events_per_file` (10000) eventos en un
segundo y, con el paso 3, en cada cambio de clave. Arreglo: sufijo `-1`, `-2`... si el nombre ya existe (el
BronzeDirWatcher recoge `*.csv`). Mismo test contra el código del paso 3: 3 ficheros, 3 filas.

Lo que ya se midió fuera de la VM (copia desechable de la rama, protobuf 3.21, OpenSSL, spdlog, gtest):

- `test_bronze_key`: 7/7 (sin clave no escribe y cuenta; primera clave escribe y verifica; misma clave no corta;
  clave distinta cierra el segmento y cada fila verifica con una sola clave; clave inválida conserva la vigente;
  huella de 8 hex estable y distinta; tres segmentos en el mismo segundo, tres ficheros y tres filas).
- `test_correlation_roundtrip` contra el writer nuevo: 4/4.
- `-fsyntax-only -Wall -Wextra -Werror` de los 15 `.cpp` de `ml-detector/src`: OK. `-O3 -Wall -Wextra -Wpedantic
  -Werror` a objeto de `config_loader`, `zmq_handler`, `correlation_writer`, `etcd_client` y `main` (este último con
  `-U_FORTIFY_SOURCE`: el `write()` sin comprobar de `main.cpp:37` ya existía y solo salta con el fortify de Ubuntu).

Parcheador `d310_paso3_clave_bronce.py`: 11 ficheros editados (30 ediciones) y 1 creado (`test_bronze_key.cpp`).
En copia limpia de `efab4558`: 12 pendientes, 12 de 12, todo ya aplicado; diff idéntico al árbol de trabajo.

Predicciones en la VM (base: rama en `efab4558`):

- Q1. `git status --short --untracked-files=no`: 12 líneas (11 `M` + `PROMPT_CONTINUE_CLAUDE.md`); el `.cpp` nuevo
  aparece como `??` sin ese filtro.
- Q2. `make pipeline-build PROFILE=production`: rc 0 y 0 diagnósticos.
- Q3. `make test-components PROFILE=production`: 9, 23, **13**, 3, 82.
- Q4. `ctest -N` del ml-detector: 13, con `test_bronze_key`.
- Q5. Protegidos (corrida `lab_protegidos_p3`): PASA, FIN en [10584, 10800], alertas en [5292, 5400].
- Q6. En `ml-detector.log` tras la corrida: una `[CONFIG] bronze_key.check_interval_seconds=60 (del JSON)`, una
  `[BRONCE-CLAVE] clave del bronce: /secrets/ml-detector, comprobada cada 60 s`, una `[BRONCE-CLAVE] clave HMAC del
  bronce recibida de /secrets/ml-detector (huella <8 hex>) al arrancar`; 0 `[csv] HMAC key`, 0 `[etcd] HMAC key
  received`, 0 `BRONCE-SIN-CLAVE`, 0 `BRONCE-CLAVE-CAMBIADA`, 0 `BRONCE-CLAVE-SIN-CONFIRMAR`.
- Q7. En `/vagrant/logs/correlation`, segmentos `argus-*.csv` escritos durante la corrida: más de 0 (el bronce se
  sigue escribiendo firmado).

Medida pendiente, con instrumento propio (siguiente entrega): parar y volver a arrancar el etcd-server con el pipeline
vivo y tráfico; comprobar `SIN-CONFIRMAR` → `CONFIRMADA` + `CAMBIADA`, el segmento cerrado y qué filas acepta el
conversor con la clave nueva.

## 12. Paso 3 — resultados (medidos DAY310; las predicciones de §11 no se tocan)

Parcheador `d310_paso3_clave_bronce.py` (sha256 `7073904a…cda7`), aplicado sobre `efab4558`. Corrida `lab_protegidos_p3`
(binarios del paso 3); la `lab_protegidos_p2` es la del paso 2 (binarios anteriores al paso 3): son el antes y el después.

| Medida | Predicción | Medido |
|---|---|---|
| Q1 `git status --short --untracked-files=no` | 12 líneas | 13: `day310_diseno.md` ya estaba modificado (premisa) |
| Q2 compilación | rc 0, 0 diagnósticos | rc 0, 0 |
| Q3 test-components | 9/23/13/3/82 | 9/23/13/3/82 |
| Q4 `ctest -N` ml-detector | 13, con `test_bronze_key` | 13 |
| Q5 protegidos | PASA; FIN en [10584, 10800], alertas en [5292, 5400] | **FALLA P4**; FIN 10743 y alertas 5370 dentro de rango; P1, P2, P3 y P5 pasan |
| Q6 log de arranque | `[CONFIG] bronze_key...=60 (del JSON)`, "comprobada cada 60 s", huella al arrancar; 0 del resto | igual (huella `3c813ec7`) |
| Q7 segmentos `argus-*.csv` | más de 0 | 13 |

Colisión de segmentos: el instrumento `scripts/bronze_key/d310_colision_segmentos.cpp` (sha256 `1d8ec24c…4833`) da en
la VM 3 ficheros y 3 filas de 3 con el código del paso 3 (antes: 1 fichero, 1 fila).

### P4, abierto

P4 exige `DROP_resumenes = DROP_FIN + alertas`. p3: 16115 frente a 10743 + 5370 = 16113, sobran **2**. p2: 16158 =
10773 + 5385, cuadra. Cuenta comprobada a mano sobre los `[SOMBRA-DDOS]` de los dos logs (M-P4a/M-P4b).

- H1 (la de OBS-FW-SOMBRA-DROP-FUERA-EPISODIO-001: DROP de una ventana anterior al INICIO que el FIN no cuenta):
  **refutada en p3**. El "primer DROP recibido" (`19699287310714_51`) es el `primer_evento` del INICIO, no hay
  resúmenes con DROP > 0 antes de él ni entre el último resumen con DROP (19874-19884) y el FIN.
- H3 (duplicados o anomalías de tiempo que el resumen cuenta y el episodio descarta): **refutada**. En p3 y en p2 todas
  las líneas `[TIMEBASE]` dan `seq_dup=0 seq_hueco=0 seq_desorden=0` y todas las anomalías a 0.
- H2 (efecto del paso 3) **no está descartada**: p2 y p3 son binarios distintos. A favor de algo anterior: DAY300 ya
  midió una diferencia de 4 en otra corrida (sin el paso 3). En contra de juzgarlo ya: el mecanismo de DAY300 (ventana
  previa) no es el de hoy. El paso 3 no toca el envío al firewall (solo el bronce y un hilo de clave), pero eso es
  lectura, no medida.

Siguiente, antes de otra hipótesis: leer en `DdosShadowPolicy` cómo cuentan el resumen y el FIN, y en el comprobador de
protegidos de dónde sale "alertas"; después, si hace falta, contar los DROP por origen y protocolo en el bronce de p3.

### Hallazgo leído en el código (sin medir aún en el lab)

`etcd-server/src/etcd_server.cpp`: `GET /secrets/{componente}` devuelve la clave HMAC activa y
`POST /secrets/rotate/{componente}` la rota, ambos por HTTP sin autenticación, escuchando en `0.0.0.0:2379`. Mientras
sea así, la firma del bronce protege contra la corrupción accidental, no contra quien alcance ese puerto: puede leer la
clave y firmar filas falsas, o rotarla (y el ml-detector, por E2, adopta la nueva). Medida pendiente: si el client llega
al puerto. Va a DEBT-ETCD-SECRETS-UNAUTHENTICATED-001.

### Lecciones añadidas

7. Antes de proponer una hipótesis sobre una cuenta, leer el código que cuenta (H1 y H3 se escribieron sin leer
   `DdosShadowPolicy`).
8. Nombrar cada corrida por lo que cambió: `p2`/`p3` son pasos de la rama, no fases de una corrida; tratarlas como "el
   mismo binario" fue un error de lectura.
9. Una decisión de seguridad se contrasta con lo que el componente del que depende hace hoy, leído en su código: el
   argumento del impostor (F1) necesita un etcd-server que autentique, y hoy no autentica.

## 13. DAY311 — P4 cerrado: DROP aislados y alcance del etcd-server (medido; §12 no se toca)

### Lectura del código (antes de la hipótesis)

- `[SOMBRA-DDOS] resumen: DROP=` cuenta TODO evento con `final_decision == "DROP"` (`zmq_subscriber.cpp`), antes de
  cualquier filtro.
- El `eventos_drop` del FIN solo suma los DROP de SU víctima `{dst, proto}` (`DdosShadowPolicy::add_drop`). Una víctima
  con DROP sueltos (< m por ventana) que nunca llega a episodio se borraba en el siguiente `advance` sin dejar rastro.
- Las alertas (origen protegido) salen antes de `add_drop`.
- El bronce no lleva `final_decision`: DROP equivale a col 16 (p1 de ddos_v2 si pasa la etapa 1) > 0,5. No lleva ICMP
  (community_id vacío).

### Hipótesis y predicción (escritas antes de medir)

- H4: los 2 de p3 son DROP de otra víctima que nunca llega a episodio. Bronce p3: .50→.1 UDP 10743, .61→.1 UDP 5370 y
  2 filas con otra clave (o ninguna si son ICMP). p2: nada más.
- H5: DROP de .50 a {.1, 17} que la política no sumó (bronce .50 = 10745). Sin camino en el código: si sale, PARAR.

### Medido (instrumento `scripts/timebase/d311_p4_cuentas.py`, sha256 `6e4b33ea…3302`)

| Medida | p3 (paso 3) | p2 (paso 2) |
|---|---|---|
| bronce DROP .50→.1 UDP | 10743 (= FIN) | 10773 (= FIN) |
| bronce DROP .61→.1 UDP | 5370 (= alertas) | 5385 (= alertas) |
| bronce DROP con otra clave | **2: 192.168.100.11 → 192.168.100.12 TCP** | 0 |
| pcap (dst .1) | .50 10806, .51 3300, .61 5400 UDP; .12 tcp 54 | igual; .12 tcp 52 |

**H4 confirmada.** .11 es la VM de Zeek (agente Wazuh) y .12 el wazuh-manager. Los 2 DROP son dos eventos del mismo
flujo `sport=43821 → dport=1514` (p1 0,74 y 0,70), con `flow_start` dentro del ataque. De 45 filas .11→.12 solo
esas 2 pasaron la etapa 1. Es un falso positivo aislado de la etapa 2 sobre tráfico legítimo (familia de
DEBT-DDOS-V2-ETAPA2-FP-BENIGNOS-001), **no un efecto del paso 3**. La columna de mitigación del instrumento no
discriminó (mitigación `deshabilitada` en protegidos): decidió el bronce. En EMECAS (3 VMs, sin Zeek ni Wazuh) no
aparece.

### Decisión de Alonso (DAY311)

Opción 1: el firewall no pierde ningún DROP en silencio. Descartadas: que el comprobador lea el bronce (no ve ICMP) y
apagar Zeek/Wazuh en protegidos (esconde el fenómeno).

### Implementación [SOMBRA-AISLADO-D311]

- `DdosShadowPolicy`: al borrar el estado de una víctima que nunca llegó a episodio y tenía DROP, guarda un registro
  AISLADO, que se recoge con `take_aislados()` (canal aparte: `advance()` sigue devolviendo solo INICIO/FIN).
  `drop_pendientes_fuera()` / `drop_pendientes_episodio()` dan lo aún no cerrado.
- Suscriptor: detalle `[SOMBRA-DDOS] AISLADO victima=… eventos_drop=… origenes=… (no se bloquea)` con el tope
  `anomalias_detalle_max` por periodo, y una línea propia tras cada resumen: `[SOMBRA-DDOS] aislados: drop= victimas=
  detalle_omitido= drop_pendientes_fuera= drop_pendientes_episodio=`. El `resumen:` no se toca. Sin parámetro nuevo
  en el JSON (se documenta en el `_doc` de `ddos_shadow`).
- P4 (`d303_veredicto_protegidos.sh` y `d300_protegidos_analisis.sh`): `DROP_resumenes = DROP_FIN + alertas +
  Σ aislados.drop + pendientes de la última línea aislados:`.
- `test_ddos_shadow_policy`: casos 7-10 (4 DROP sueltos; el caso 2 antiguo ahora da 240 en AISLADO; DROP tras un FIN;
  identidad FIN + AISLADO = todo lo sumado con 3 víctimas y 600 s). Mutación (sin el registro AISLADO): fallan los 4.
- Límite conocido: si el evento que dispara la última impresión es un DROP, P4 podría dar diferencia 1. Si ocurre,
  sale como FALLA, no se esconde.

### Predicción y medida del cambio

| Medida | Predicción | Medido |
|---|---|---|
| Q1 `git status --short --untracked-files=no` | 8 líneas (7 + `PROMPT_CONTINUE_CLAUDE.md`) | 8 |
| Q2 compilación production | rc 0, 0 diagnósticos | rc 0, 0 |
| Q3 test-components | 9/23/13/3/82 | 9/23/13/3/82 |
| Q4 protegidos `day311/lab_protegidos_p4` | PASA P1-P5, P4 diferencia 0; líneas `aislados:` = `resumen:`; aislados en [0, 10] | PASA; 16116 = 10746 + 5370 + 0 + 0; 41 = 41; 0 |
| bronce p4 | .50 10746, .61 5370, nada más | igual |

El fondo .11→.12 estaba (43 filas en el bronce de p4) y ninguna pasó la etapa 1: el falso positivo no se repitió por
azar, como en p2. El camino AISLADO queda cubierto por los tests y la mutación; en el lab no ha salido aún un aislado
real. Primera corrida parada en el paso 1 (alias .51 perdido tras reiniciar el client); `make lab-e2e-prep` lo repone.

### Alcance del etcd-server (DEBT-ETCD-SECRETS-UNAUTHENTICATED-001)

`ss` en el defender: `0.0.0.0:2379` (etcd-server). Desde el client (`ml-client`, 192.168.100.50/.51):
`curl http://192.168.100.1:2379/secrets/keys` → **200**, como se predijo. El hallazgo de §12 deja de ser solo lectura
de código: la posición del atacante en el lab alcanza el servicio que entrega y rota las claves HMAC sin autenticación.
No se pidió `/secrets/ml-detector`: no hace falta sacar una clave para el dato. Dos medidas anteriores no valen: una
lanzada en el defender y otra desde el Mac, ambas con el pipeline parado.

### Lecciones DAY311

1. Un recuento por víctima no se compara con un recuento global sin preguntar qué otras víctimas hay: el resumen
   cuenta todo DROP y el FIN solo los de su víctima.
2. Un instrumento débil (una foto cada 10 s de `victimas_activas`) no refuta nada: un estado que vive un segundo no
   sale en la foto.
3. Una columna que depende de una función apagada (mitigación `deshabilitada`) no discrimina: se comprueba el modo
   antes de leerla.
4. Antes de medir un servicio, comprobar que está en marcha: la corrida de protegidos termina con `pipeline-stop`.
5. El prompt del terminal no dice en qué máquina se está (`vagrant@…`): `hostname` primero.

## 14. DAY311 — reinicio del etcd-server, paso 5 y test de Kuzu (medido; §13 no se toca)

### Reinicio del etcd-server con el pipeline vivo y tráfico

Instrumento `scripts/bronze_key/d311_reinicio_etcd.sh` (Mac, sha256 `9fffe4e4…9133`) +
`scripts/bronze_key/d311_etcd_defender.sh` (defender, `7e4ab48b…2348`). Tráfico benigno .51 → .1 a 10 pps; 60 s;
`make etcd-server-stop`; 150 s; `make etcd-server-start PROFILE=production`; 150 s; fin. Cada segmento de la ventana
se pasa por el conversor real (`bronze_to_gold_converter`) con la clave de antes (A) y la de después (B). Las claves se
leen en el defender a `/tmp/d311_claves` (solo root, nunca `/vagrant`), en la salida solo la huella, y se borran al
final (trap). Probado antes en simulador (vagrant/make/etcd falsos y escritor de segmentos), que cazó dos fallos del
propio guion (`test -x` sobre un fichero no ejecutable; parada del tráfico solo por PID).

Corrida `day311/lab_etcd_reinicio_1`:

| Predicción (escrita antes) | Medido |
|---|---|
| R1 puerto 0 tras parar, 1 tras arrancar | 0 y 1 |
| R2 2 o 3 `SIN-CONFIRMAR` con huella A; 0 `SIN-CLAVE`, 0 `RECUPERADA` | 3 (huella 574cc3de); 0; 0 |
| R3 1 `CONFIRMADA` ("otra clave") y 1 `CAMBIADA` A → B, ≤ 60 s tras arrancar | 1 y 1 a las 05:49:27 (192 s en modo extendido), 17 s después del primer `/register` del servidor nuevo (05:49:10) |
| R4 huellas del instrumento = las del log; A ≠ B | 574cc3de → 8037d2d5, iguales |
| R5 MEZCLA 0, A antes que B, el segmento de `CAMBIADA` es A | 17 segmentos: 11 A (3380 filas), 6 B (1800), MEZCLA 0; `054921` A, 92 filas, cortado a los 6 s |
| R6 continuidad: eventos ≥ 1 por resumen, seq sin huecos | mínimo 8; seq_dup/hueco/desorden 0 |
| R7 `Heartbeat failed` > 0 con el servidor caído | **FALLA: 0** (ver abajo) |

El conversor acepta el 100 % de cada segmento con una sola clave. Las filas escritas con el servidor caído verifican
con A (F2). Cada comprobación fallida de la clave tarda ~4 s (timeout HTTP), por eso las tres no caen en múltiplos
exactos de 60 s.

**R7.** La predicción buscaba un texto que no existe en ese camino: `http::post` no lanza, escribe `⚠️  HTTP POST
connection failed` / `⚠️  HTTP POST failed: 404` y devuelve `success=false`, que `send_heartbeat()` no mira; el
`catch` del `Heartbeat failed` nunca salta. Medido después: los tres componentes laten (también el sniffer); con el
servidor caído 6 `connection failed` cada uno (~190 s, latido cada ~30 s); al volver, 404 en cada latido hasta el
final (8/8/7), y el etcd-server cuenta lo mismo en `❌ Componente no encontrado`. Los 17 `✅ Heartbeat registrado`
son 10 de antes del reinicio (cuatro latidores: el propio etcd-server también late) y 7 de después, todos del
etcd-server. El único `/register` tras el arranque es el etcd-server registrándose a sí mismo (`component=unknown` en
el log porque `log_request` no lee ese cuerpo).

**Hallazgos (medidos):**
1. Tras reiniciar el etcd-server el registro solo contiene al etcd-server. ml-detector, firewall y sniffer siguen
   funcionando (el canal ZMQ usa `seed.bin` y no se entera) pero para el etcd-server no existen, y ninguno avisa más
   allá de un `HTTP POST failed: 404` cada 30 s. La defensa del registro frente a un impostor (F1) desaparece en
   silencio con un reinicio.
2. El log del etcd-server miente: el endpoint de heartbeat escribe `log_request(req, 200, …)` antes de decidir y luego
   responde 404.
3. Todo el bronce A (3380 filas aquí) deja de poder verificarse tras el reinicio: el etcd-server regenera las claves
   en memoria y A deja de existir. Aquí solo se pudo verificar porque el instrumento la leyó antes de parar (y la
   borró al final). Es la medida que hace necesarias DEBT-ETCD-HA-TLS-RAFT-001 (claves persistidas) y
   DEBT-BRONZE-KEY-ID-001, no una mejora.
4. Leído, sin medir: `get_hmac_key` genera la clave en la primera petición, con la consulta y la generación bajo
   bloqueos separados; dos primeras peticiones simultáneas podrían generar dos claves.

### Paso 5 — resumen del contrato (`contract_validator.cpp`)

Medido con el descriptor de `network_security.proto` (protobuf 3.21.12): `NetworkFeatures` tiene 73 escalares, 6
repetidos y 8 submensajes (`flow_start_time` 2, `flow_duration` 2, `ransomware` 20, `ddos_embedded` 9,
`ransomware_embedded` 10, `traffic_classification` 10, `internal_anomaly` 10, `smb_scan` 3). La línea fija "Baseline: 74
scalars + 40 embedded (4x10) = 114 minimum" estaba desfasada (ddos_embedded es el contrato v2) y además ningún mínimo
fijo es cierto: `count_features` cuenta solo los campos presentes (proto3 no lista los ceros) y el tamaño de los
repetidos. Ahora la línea se calcula del descriptor en tiempo de ejecución, sin cifras escritas a mano
[CONTRACT-ESQUEMA-D311]. Probado fuera de la VM: compilación con -Wall -Wextra (los mismos 4 avisos de fmt/spdlog con
GCC 13 que el original, ninguno en el fichero) y ejecución de `log_summary()` con la salida esperada. En la VM:
compilación rc 0, 0 diagnósticos.

### Test de Kuzu intermitente (`test_kuzu_graph_sink`)

`make test-components` falló una vez tras el paso 5: `KuzuGraphSink.ExplicitCommitPersistsBatch:208`, 1 NetworkFlow
en vez de 2. Falló también en la primera repetición y pasó en la segunda. No toca el paso 5 (ningún test del
correlation-engine compila `contract_validator.cpp`).

Leído en el código: `CypherBindings` guarda `string_view` y el test hacía `make_bindings(r1, fuid_of(r1), …)`;
`fuid_of` devuelve un `std::string` temporal, así que `b1.flow_uid` apunta a memoria liberada al acabar la línea
(comportamiento indefinido). Si b1 y b2 leen el mismo contenido reciclado, el `MERGE` los funde en un nodo: el fallo
observado. Producción no está afectada (`kuzu_graph_sink.cpp:171` pasa `e.flow_uid`, que vive en la entrada). Arreglo
[KUZU-TEST-DANGLING-D311]: el `flow_uid` en variables con nombre, en los dos tests de transacción.

| Predicción | Medido |
|---|---|
| antes (binario viejo, test aislado con `--gtest_filter`), 50 veces: > 0 fallos | **FALLA: 0 de 50** |
| después (aislado), 50 veces: 0 | 0 de 50 |
| después (binario entero), 50 veces: 0 | 0 de 50 |
| test-components 9/23/13/3/82 | 9/23/13/3/82 |

La predicción del "antes" falló por un error de diseño del instrumento: aislado, el test no reproduce las condiciones
del fallo (los dos fallos del día fueron con el binario entero, con los tests anteriores dejando la memoria). Por eso el
comportamiento indefinido es cierto y el arreglo necesario, pero que sea LA causa de los fallos de hoy es la hipótesis
principal, no una medida. Pendiente: binario entero viejo frente a nuevo, 50 veces cada uno, y una pasada con
AddressSanitizer (DEBT-KUZU-TEST-DANGLING-001).

### EMECAS+++ production (punta de código 7ae4c93c)

rc 0: los 5 E2E del lab con `RESULTADO PASA` (reinicio antes, ordenada, kill9, protegidos y mitigación), componentes
9/23/13/3/82, 19 carteles `PASSED`. Protegidos: `DROP_resumenes 16129 = DROP_FIN 10750 + alertas 5375 + aislados 4 +
pendientes 0`. Predije aislados en [0, 10] y mi hipótesis (fondo del lab hacia .1) cayó: los 4 son
`AISLADO victima=192.168.100.1 proto=17 eventos_drop=4 ventanas_positivas=0 origenes=192.168.100.50:4`, la primera
ventana del ataque (5630) con menos de m DROP. Al cerrarla sin positivas el estado se borraba; el episodio empezaba en la
siguiente (INICIO 5633, primer_evento del FIN `5631016…`). Es el mecanismo que DAY300 sospechaba para los 4 de antes2
(H1, refutada en p3 para aquella corrida; medida aquí en otra). Hay dos causas de DROP fuera de episodio, las dos
visibles ahora en AISLADO: falsos positivos sueltos (Wazuh, p3) y el arranque de un ataque en una ventana débil. Es lo
que el comprobador ya admitía en P5 ("el primer segundo antes del INICIO"), que antes no se veía. Sin el arreglo de
§13, este EMECAS habría dado FALLA en P4. EMECAS escribe sus corridas en `logs/lab/day303/` (`LAB_E2E_DIA ?= day303`).

### Lecciones añadidas

6. Antes de predecir el texto de un log, leer la función que lo escribe, no solo la que la llama (`Heartbeat failed`
   está en un `catch` que nunca salta).
7. Un fallo intermitente se reproduce en las condiciones en que falló: aislar el test cambia la memoria que lo provoca.
8. Un comprobador que se apoya en un log tiene que saber si ese log dice la verdad: el etcd-server escribe 200 y
   responde 404.
9. `ls -dt` no sirve para encontrar la última corrida si se reutiliza el directorio: sobrescribir ficheros no cambia
   la fecha del directorio.
