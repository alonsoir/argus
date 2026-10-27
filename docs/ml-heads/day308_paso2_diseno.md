# DAY308 — Paso 2: caducidad de flujos (diseño, antes de tocar código)

Rama `feat/sniffer-flow-expiry`, base `bef2ac0b`. DEBT-SNIFFER-FLOW-EXPIRY-001 + DEBT-SNIFFER-FLOWTABLE-CONFIG-001.
Decisiones ya tomadas (Alonso, DAY308): tope de duración activa en el JSON, **desactivado por defecto** (0 = sin
tope) hasta que un barrido mida su efecto en ddos_v2; al vencer, el flujo se cierra y el siguiente paquete abre uno
nuevo con la misma clave y el estado a cero; en esta rama solo el **mecanismo**; el barrido y su medida en ddos_v2, en
otra rama junto a la del ataque largo (DEBT-DDOS-V2-LONG-ATTACK-001).

## 1. Lo que hay hoy (leído en el código de la rama)

- **La tabla está escrita a mano** en `ring_consumer.cpp:131-133`: 16 shards × 10 000 flujos, `flow_timeout_ns` 120 s.
- **Nada caduca.** `ShardedFlowManager::cleanup_expired_flows` existe pero nadie la llama. Con la tabla llena, la LRU
  desaloja el flujo menos reciente al llegar uno nuevo, **sin contarlo ni decirlo en el log**.
- **La limpieza es O(n²)**: por cada flujo caducado hace `lru_queue->remove(key)`, que recorre la lista entera; la
  entrada ya guarda `lru_pos`, con el que el borrado sería O(1).
- **`should_expire` resta sin signo**: si la última marca de un flujo es posterior a la hora de la limpieza, la resta da
  la vuelta y caduca un flujo vivo.
- **Relojes**: la marca del paquete es `bpf_ktime_get_ns()` (`sniffer.bpf.c:328`, CLOCK_MONOTONIC) y la hora de la
  tabla es `steady_clock` (CLOCK_MONOTONIC en libstdc++). Misma base según la documentación; **se mide en el E2E**
  (contador de marcas futuras, §2.5), no se da por hecho.
- **Tres configuraciones de caducidad mienten** (ninguna llega a la tabla; inventario con `git grep`, 0 consumidores):
  `kernel_space.flow_timeout_seconds` (300), `processing.feature_extraction.flow_timeout_seconds` (300) y el bloque
  `user_space` entero (`flow_table_size` 1 000 000, `time_window_buffer_size`, `memory_management` con
  `gc_interval_seconds` 60). Se leen con `get(campo, defecto)` en silencio y se copian entre los dos modelos de
  configuración; nadie las usa.
- `FlowTracker` (`flow_tracker.cpp`) tiene su propia `cleanup_expired_flows`: es del procesador de ransomware, no de
  esta tabla. Fuera de alcance.

## 2. Diseño

### 2.1 Un solo sitio en el JSON: sección `flow_table` de `sniffer.json`

| Campo | Rango | Defecto | Qué es |
|---|---|---|---|
| `shards` | entero [1, 256] | 16 | número de shards (cada uno con su lock) |
| `max_flows_per_shard` | entero [100, 10 000 000] | 10 000 | tope de flujos por shard; al llegar, la LRU desaloja |
| `idle_timeout_s` | entero [1, 86 400] | **decisión P1** | inactividad que caduca un flujo |
| `active_timeout_s` | entero 0 o [1, 604 800] | 0 | duración máxima de un flujo; **0 = sin tope** |
| `cleanup_interval_ms` | entero [100, 60 000] | 1 000 | cada cuánto pasa la limpieza |
| `log_interval_s` | entero [1, 3 600] | 60 | cada cuánto escribe la línea `[FLOW-TABLE]` |

Con `_doc_<campo>` para cada uno (rango, formato, defecto, "defecto SEGURO, no óptimo"), como la EWMA y timebase.
Reglas cruzadas: `idle_timeout_s * 1000 > cleanup_interval_ms`; si `active_timeout_s > 0`, `active_timeout_s >=
idle_timeout_s`. Si se rompen: defectos de los campos implicados + `[CONFIG-DEFAULT]`.

**Mismo patrón que timebase (DAY295)**, sin inventar otro:
- `include/flow_table_config.hpp`: `FlowTableParams` con los defectos y las constantes de rango (`kShardsMin`...),
  `params_ok()`. Los defectos viven en un solo sitio del código.
- `config_manager.cpp`: `parse_flow_table()`. Campo ausente, no entero o fuera de rango → defecto +
  `[CONFIG-DEFAULT] flow_table.<campo> ... rango=[a, b]`; el sniffer arranca siempre; al final, si hubo alguno,
  `[CONFIG-DEFAULT] N ajustes con valor por defecto en flow_table: revisar sniffer.json`.
- Se copia por el mismo camino que `timebase`: `config_manager` → `config_types.cpp` → `main.cpp` →
  `RingBufferConsumer::config_`.
- Al arrancar, **siempre** (también si todo es correcto): `[FLOW-TABLE] shards=16 max_por_shard=10000
  capacidad=160000 idle_timeout_s=… active_timeout_s=0 (sin tope) cleanup_interval_ms=1000 log_interval_s=60`.

### 2.2 `ShardedFlowManager::Config`

`flow_timeout_ns` → `idle_timeout_ns` y `active_timeout_ns` (0 = sin tope). `ring_consumer.cpp` deja de escribir
la tabla a mano y la inicializa con `config_.flow_table`. Inventario de `.flow_timeout_ns` fuera del código del
sniffer (`git grep`, sin truncar): 4 tests (`test_ddos_flow_snap`, `test_ring_consumer_protobuf`,
`test_sharded_flow_full_contract`, `test_sharded_flow_multithread`) y 4 instrumentos de `scripts/flow_expiry/`
(`d307_paridad_rasgos`, `d307_ram_flujo`, `d308_paridad_tolerancia`, `d308_ram_hist`); el resto son páginas viejas de
`site/`. Los tests y los tres instrumentos vivos pasan a `.idle_timeout_ns` en el mismo parche.
`d307_paridad_rasgos.cpp` ya no compila desde el paso 1 (populate cambió de firma) y `d308_paridad_tolerancia.cpp`
reproduce su salida byte a byte: decisión P4.

### 2.3 Tope de duración activa: perezoso, en `add_packet`, O(1)

Al llegar un paquete a un flujo existente, si `active_timeout_ns > 0` y `ts >= flow_start_ns` y `ts - flow_start_ns
>= active_timeout_ns`: el estado del flujo vuelve a cero (núcleo e histograma) **y después** se añade el paquete, que
abre el flujo nuevo. Usa solo marcas de paquete (mismo reloj). No necesita recorrer la tabla. Contador `cortes_tope`.
Un flujo cortado que luego queda inactivo lo recoge la limpieza por inactividad.

### 2.4 Limpieza por inactividad: desde la cola de la LRU, O(caducados)

La LRU de cada shard pone delante el flujo del último paquete; la cola es el de paquete más antiguo. Por shard, con su
lock: mientras la cola esté caducada (`now - last_seen > idle_timeout_ns`), borrar con `lru_pos` (O(1)) y `pop_back`;
parar en la primera que no lo esté. Coste O(caducados + shards), y el lock de cada shard solo mientras borra lo suyo.

Matiz: la LRU ordena por **llegada**, no por marca. Con marcas desordenadas, un flujo caducado puede quedar detrás de
uno vivo y esperar a una pasada posterior. Se acepta y se documenta; el contador permite verlo.

### 2.5 `should_expire` con guarda

Si `last_seen > now`, el flujo no caduca y se cuenta en `marcas_futuras`. Si en el E2E sale distinto de 0, los dos
relojes no son la misma base y hay que parar (mide la suposición de §1).

### 2.6 Hilo de la tabla

`flow_table_loop` en `RingBufferConsumer`, junto a `timebase_loop` y con su mismo esquema (duerme a trozos de 100 ms
para que la parada no espere): cada `cleanup_interval_ms` limpia; cada `log_interval_s` escribe

`[FLOW-TABLE] vivos=N capacidad=C caducados=X cortes_tope=Y desalojos_lru=Z marcas_futuras=F max_lock_us=L`

con contadores del intervalo. `desalojos_lru` hace visible lo que hoy pasa en silencio con la tabla llena; si no es 0,
la tabla se queda corta para el tráfico y el admin lo ve. Política de logs DAY284: línea mínima y periódica por
defecto.

### 2.7 Fuera lo que miente

- `sniffer.json`: fuera `kernel_space.flow_timeout_seconds`, `processing.feature_extraction.flow_timeout_seconds` y el
  bloque `user_space`.
- Código: sus campos en `config_manager.hpp` (`KernelSpaceConfig::flow_timeout_seconds`, `UserSpaceConfig` entero,
  `parse_user_space`, el `flow_timeout_seconds` de `feature_extraction`) y en `config_types.h/.cpp`.
- Si un `sniffer.json` antiguo los trae: `[CONFIG-OBSOLETO] <campo> ya no se usa desde DAY308: la tabla de flujos se
  configura en flow_table` (precedente: `ddos_victim_ewma_tau_s`, DAY298). Decisión P3.
- El resto de campos ceremoniales de `processing.feature_extraction` (`max_concurrent_flows`, ...) no se tocan aquí:
  DEBT-SNIFFER-CONFIG-CEREMONIAL-001, rama propia.

## 3. Decisiones que te tocan

- **P1. Defecto de `idle_timeout_s`.** El código decía 120 s (`ring_consumer.cpp`); el JSON decía 300 s en dos sitios.
  Ninguno se aplicaba: hoy un flujo inactivo no caduca nunca (solo lo saca la LRU con la tabla llena). Cualquier valor
  cambia lo que ve ddos_v2: un flujo que vuelve tras estar inactivo más que el tope empieza con
  `flow_packet_count` a cero. Propongo **300 s**: es el mayor de los dos declarados, el que menos cambia la semántica
  respecto a hoy, y su valor óptimo lo medirá el mismo barrido que el tope activo.
- **P2. Intervalos.** `cleanup_interval_ms` 1 000 y `log_interval_s` 60. ¿De acuerdo?
- **P3. Campos antiguos.** ¿Aviso `[CONFIG-OBSOLETO]` si aparecen (propuesto), o silencio?
- **P4. `d307_paridad_rasgos.cpp`.** No compila desde el paso 1 y lo sustituye `d308_paridad_tolerancia.cpp`, que da la
  misma salida. Propongo borrarlo en este parche (la historia de git lo conserva y el documento de DAY307 dice qué
  hacía).

## 4. Predicciones (escritas antes de medir)

- **Paridad**: con los defectos, el instrumento de paridad no cambia ni un byte (`fbc2b693…` sin banderas): no llama a
  la limpieza y su generador no deja huecos de más de 2 s dentro de una conversación, así que ni el tope (desactivado)
  ni la inactividad tocan sus flujos.
- **Coste de la limpieza** (instrumento nuevo `d308_limpieza.cpp`, tabla llena de 160 000 flujos, todos caducados,
  antes y después, **escribiendo en `/tmp`**):
  - Antes (O(n²)): del orden de segundos en total. No sé el valor; la cuenta (~5·10⁷ pasos de lista por shard) dice
    entre 0,5 y 10 s.
  - Después: entre 10 y 100 ms en total y por debajo de 10 ms de lock por shard.
  - Con nada caducado, después: por debajo de 50 µs por pasada (una comprobación por shard).
- **E2E del lab**: `marcas_futuras=0`; `vivos` se estabiliza en lugar de crecer hasta la capacidad; `desalojos_lru=0`
  en la corrida normal.
- **Tests**: 82/82 más el test nuevo, y los 3 tests sin registrar en verde.

## 5. Plan de medida, antes y después

1. Instrumento `d308_limpieza.cpp` contra el código de HOY (la `cleanup_expired_flows` O(n²) existe): coste con la
   tabla llena y todo caducado, y con nada caducado. Salida en `/tmp`.
2. Parcheador (`--check`/`--apply`, sha256, anclas únicas, probado en copia desechable).
3. Test nuevo registrado en ctest, `test_flow_expiry`: inactividad (con hora inyectada), tope activo (corte y flujo
   nuevo con estado a cero), guarda de marcas futuras, borrado desde la cola con marcas desordenadas, contadores y
   el parser de `flow_table` (ausente, no entero, fuera de rango, reglas cruzadas → defecto y aviso).
4. `make pipeline-build PROFILE=production`, `make test-components PROFILE=production`, tests sin registrar, paridad
   en los dos perfiles, instrumento de limpieza después, y E2E del lab con la línea `[FLOW-TABLE]`.

## 6. Resultado (escrito DESPUÉS de medir; las secciones 1-5 se dejan como se escribieron antes)

Commit del paso: `97e48add` (`feat(sniffer): DAY308 paso 2 — caducidad de la tabla de flujos, configurada en
flow_table`). Medidas en el defender.

### 6.1 Decisiones de Alonso

P1: `idle_timeout_s` 300 s, también como defecto en el código. P2: `cleanup_interval_ms` 1 000 y `log_interval_s` 60,
con el mismo criterio: el JSON se lee siempre; si un campo falta, no es entero o está fuera de rango, se aplica el
defecto escrito en el código (igual al del JSON) y se avisa. P3: aviso `[CONFIG-OBSOLETO]`, y la línea `[FLOW-TABLE]`
del arranque dice el valor de cada campo y de dónde sale (JSON o defecto, y por qué). P4: fuera
`d307_paridad_rasgos.cpp`.

### 6.2 Cambio sobre el diseño, antes de escribir el parche

Los parámetros (`flow_table_params.hpp`, sin JSON) se separan del lector (`flow_table_config.hpp`, con jsoncpp): el
`ShardedFlowManager` incluye solo los parámetros, para que los tests y los instrumentos que lo enlazan no necesiten
jsoncpp. El lector sigue el patrón de `heads_config.hpp` (DAY305): sin estado y probado suelto.

### 6.3 Medidas

| | Antes | Paso 2 |
|---|---|---|
| Limpieza, 80 000 flujos, nada caducado (por pasada) | 8,7-9,1 ms | 1,2 µs |
| Limpieza, 8 000 caducados | 1,49-1,57 s | 2,5-2,6 ms |
| Limpieza, 72 000 caducados | 6,0-6,1 s | 32 ms |
| Paridad sin banderas (contra `antes.tsv`) | — | idéntica (`fbc2b693…`) |
| Paridad con banderas de producción (contra el paso 1) | — | 0 eventos distintos |
| Tests del sniffer en ctest | 18 | 19 (`test_flow_expiry`) |
| Tests sin registrar (4 / 6 / 3) | pasan | pasan |

`test_flow_expiry`: 26 pruebas; detecta las cuatro mutaciones probadas (sin guarda en `should_expire`, tope roto,
desalojo sin contar, limpieza que no para en la cola).

**E2E del lab** (pipeline completo, 7 minutos, tráfico de fondo): la línea `[FLOW-TABLE]` del arranque con los seis
campos de origen `(JSON)`; ningún `[CONFIG-DEFAULT] flow_table` ni `[CONFIG-OBSOLETO]`; 7 líneas periódicas con
`marcas_futuras=0` y `desalojos_lru=0` en todas; vivos de 22 a 72; 12 y 13 caducados en las líneas 6 y 7 (los
primeros flujos en pasar 300 s sin paquetes); `max_lock_us` entre 10 y 277.

**`marcas_futuras=0` mide la suposición de §1:** la marca del paquete (`bpf_ktime_get_ns`) y la hora de la tabla
(`steady_clock`) son el mismo reloj.

### 6.4 Predicciones

- **Se cumplieron:** paridad en los dos perfiles; caducados exactos; limpieza con 8 000 y 72 000 caducados (2-5 ms y
  20-40 ms predichos); E2E (orígenes JSON, `marcas_futuras=0`, `desalojos_lru=0`, caducados hacia la 6.ª línea).
- **Fallaron:**
  - **Limpieza sin caducados (2-4 µs predichos, 1,2 µs medidos).** Apliqué el factor del defender en trabajo con
    memoria a una pasada que solo mira la cola de 16 shards.
  - **Antes de la limpieza con 72 000 caducados (2,7-4,5 s predichos, 6 s medidos).** El mismo error en sentido
    contrario: `list::remove` persigue punteros por memoria, y ahí la VM castiga más que el factor del microbanco
    (×3,4).
  - **"83 de 83" en `make test-components`: mal planteada.** El "82" del log es el número de tests del firewall, no
    el total (9 + 19 + 15 + 3 + 82 = 128). La regla de comprobación de DAY307 (`grep 'out of 82'`) solo miraba al
    firewall: se corrige comprobando las cinco líneas de resumen, cada una con su número esperado, y que todas digan
    `0 tests failed`.
- **Diferencia con el diseño:** el instrumento de limpieza llena la tabla a la mitad (80 000 flujos), no entera, para
  que la LRU no desaloje y los caducados esperados sean exactos.

### 6.5 Siguiente en la rama

Batería de la etapa 2 (ddos_v2) y E2E antes/después; registrar en ctest los tres tests sin registrar
(DEBT-SNIFFER-TESTS-NOT-REGISTERED-001); EMECAS+++ production; PR.
