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
