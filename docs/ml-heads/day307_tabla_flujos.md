# DAY307 — Tabla de flujos del sniffer: solo código de producción, y coste por evento medido

Rama `feat/sniffer-flow-expiry` (desde main `57d1d400`, merge de DAY306). Deudas de la rama:
DEBT-SNIFFER-FLOW-EXPIRY-001 y DEBT-SNIFFER-FLOWTABLE-CONFIG-001. Herramientas del día en `scripts/flow_expiry/`.
Evidencia (sin trackear) en `logs/lab/day307/`.

Regla del día (Alonso): **en cada paso se mide antes y después**. Ningún commit de hoy cambia lo que sale del
sniffer: se demostró con el instrumento de paridad (salida idéntica byte a byte) en cada paso.

## 1. Pregunta abierta de DAY306: los "28/28 hitos"

El contador no lo escribe EMECAS sino `scripts/emecas/emecas_watch.sh` (lista fija de 28 hitos, `FASES`), que lee
`logs/lab/emecas/emecas_actual.log`, y ese log solo lo crea `scripts/emecas/emecas_run.sh`. En DAY306 se lanzó
`make emecas+++` a mano con la salida a `/tmp`. Contado a posteriori sobre `emecas_20261024_day306.log`: **28/28**.
EMECAS se lanza siempre con `nohup bash scripts/emecas/emecas_run.sh emecas+++ production < /dev/null > /dev/null 2>&1 &`.

## 2. Medida de partida (instrumentos nuevos)

- `scripts/flow_expiry/d307_ram_flujo.cpp`: enlaza el `ShardedFlowManager` real. Fase A: 320 000 flujos de 1
  paquete (tabla 16 × 10 000), VmRSS cada 10 000. Fase B: un flujo, 10 M paquetes, VmRSS y tiempo de
  `get_flow_stats_copy` cada millón.
- `scripts/flow_expiry/d307_paridad_rasgos.cpp`: reproduce el camino de cada evento de `ring_consumer` (clave
  direccional, foto ddos_v2 en el lock, copia, `populate_ml_defender_features`, sobrescritura de los 5 rasgos DDoS)
  con paquetes deterministas (300 000 eventos, semilla 307) y vuelca todos los campos de `network_features`
  (float `%.9g`, double `%.17g`). Mide el tiempo de populate por evento, repartido por tamaño del flujo.

Partida (defender, -O3):
- **RAM por flujo: 1 697 B**; tabla llena (160 000 flujos) = **265 MB**; plana pasado el tope (la LRU acota el
  número de flujos).
- **Un flujo que nunca está inactivo crece ~30 B por paquete sin límite**: 10 M paquetes = 292 MB para un solo
  flujo. La caducidad por inactividad no lo toca nunca.
- **La copia por evento es O(n)**: 7,7 ms a 1 M paquetes (lineal hasta 4 M; más allá, saltos y ruido). Con 1 M
  paquetes en un flujo, ≤ ~130 eventos/s de ese flujo solo en copiarlo.
- Populate por evento: media 121 µs con un flujo medio de 511 paquetes por evento. Tramo 1–20 paquetes: 6,0 µs;
  21–500: 40 µs; 501+: 289 µs y el 81 % del tiempo. O(n): ~0,2–0,3 µs por paquete acumulado más ~6 µs fijos.

## 3. Commits del día (todos medidos, ninguno cambia la salida)

| Commit | Qué | Medida |
|---|---|---|
| `290f342d` | `sharded_flow_manager.cpp` incluía `_fix3.hpp` (idéntica a la canónica, ODR latente desde Day 45, `a2b8f3cb`): include canonizado; fuera 9 residuos `_fix*`/`_original` | Fuente preprocesado (`-E -P`) idéntico antes/después: 70 125 líneas, sha256 `fb4029a8…` |
| `62b3c20` | Fuera la clase `FlowManager` (se compilaba, nadie la usaba) y `scripts/verify_integration.sh` | build y 82/82 |
| `0f5e5a8e` | Paso 3: fuera `TimeWindowManager` por flujo (se actualizaba en cada paquete y se recreaba en cada copia; solo lo leía la clase `FeatureExtractor`, muerta) y la clase `FeatureExtractor` (669 líneas) | Paridad idéntica; **RAM por flujo 1 697 → 658 B; tabla llena 265 → 103 MB**; populate 1–20 6,0 → 5,7 µs; 501+ 289 → 265 µs |
| `73d27542` | Fuera el mecanismo `feature_groups` de `sniffer.json` (ceremonial: nadie abría sus ficheros, dos ni existían; la validación no la llamaba nadie) y `user_features`; fuera `rf_23_features.json` y `ransomware_20_features.json` | Resumen de arranque del sniffer: solo pierde las 5 líneas de "Feature groups" |
| `bdf2506b` | Paso 2: fuera el cálculo de los 5 rasgos DDoS en populate (`extract_ddos_features`): ring_consumer los sobrescribía SIEMPRE con la foto en lock | Paridad idéntica; **populate media 121 → 92,7 µs (−24 %)**; 501+ 265 → 216 µs; 21–500 40 → 33 µs |

Instrumento de paridad: `antes.tsv` = `paso3.tsv` = `paso2.tsv`, sha256 `64471c1e…dcc0`.

## 4. Hallazgos

- **Los flujos son unidireccionales.** `ring_consumer.cpp:634` y `:921` construyen la `FlowKey` con los campos del
  paquete tal cual y `FlowKey` no normaliza el sentido: cada sentido de una conversación es un flujo propio.
  En producción `dpkts`, `bwd_*` y los rasgos backward salen siempre a 0; el SYN-ACK de la respuesta cae en el
  flujo inverso. ddos_v2 se entrenó así: no se toca sin decisión y sin reentrenar/medir.
- **Hash de `FlowKey` débil** (XOR con desplazamientos): afecta al reparto entre shards.
- **La configuración del sniffer es en buena parte ceremonial.** Tres "timeouts de flujo" en `sniffer.json`
  (`kernel_space.flow_timeout_seconds`, `processing.feature_extraction.flow_timeout_seconds`, el bloque
  `user_space` con `flow_table_size: 1000000` y `gc_interval_seconds: 60`), ninguno aplicado; la tabla real es
  16 × 10 000 escrita en `ring_consumer.cpp:131` y no caduca nunca. Dos modelos de configuración
  (`SnifferConfig` y `StrictSnifferConfig`, el segundo con campos que nunca se rellenan), 20 `validate_*_section`
  vacíos, y la mayoría de campos leídos con `get(campo, defecto)` en silencio.
- **Tres tests del sniffer se compilan pero no están en ctest**: `test_ring_consumer_protobuf` (4),
  `test_sharded_flow_multithread` (6) y `test_sharded_flow_full_contract` (3). `test-components` no los ejecuta.
  Pasan los tres (ejecutados a mano antes y después de cada paso).
- **La copia del flujo pierde `time_windows`** (ya no aplica tras el paso 3) y el arreglo de DAY219 (`fc292bc8`,
  rama `fix/verdict-multihead-honest`, sin mergear) nunca llegó a main.
- **Con la configuración actual** (`ml_detector_config.json`: solo `ddos_v2` encendida; level1, ransomware, web,
  internal, rag_logger y csv_writer apagados) ningún consumidor encendido usa el valor de los rasgos O(n) del
  sniffer; el contrato protobuf sí los transporta.
- `should_expire` resta sin signo: si un paquete llega con marca del kernel posterior a la hora leída por la
  limpieza, la resta da la vuelta y caduca un flujo vivo (hipotético hoy: la limpieza no se llama nunca).
- `cleanup_expired_flows` es O(n²) (`lru_queue->remove`).

## 5. Lecciones del día

- **Con LTO, el hash del `.o` no sirve para comparar**: guarda las ubicaciones fuente. Comparar el preprocesado.
- **`git log -S` cuenta apariciones**: no vio el commit que canonizó el include porque dejó la cadena en un
  comentario. Para cambios de una línea concreta, `git log -G '<regex>'`.
- **Un inventario no se trunca.** Un `| head -30` dejó fuera el test que falló en el paso 2. Se vuelca entero a
  fichero y se cuenta.
- **En un bucle con `| grep`, `$?` es el del grep**, no el del programa.
- **Los logs de ctest guardan códigos de color ANSI dentro de la línea** (y `\r`): buscar trozos que no crucen
  colores (`out of 82`) o quitar antes los códigos.
- **Una predicción de tiempo pesa eventos, no conversaciones**: los eventos se concentran en los flujos largos.

## 6. Lo que queda en la rama

1. **Paso 1: estadísticos incrementales en `FlowStatistics`** (acumuladores de tamaño fijo en vez de vectores):
   O(1) por paquete y O(k) por evento (k = longitudes distintas, por la entropía con `len_hist`), memoria por flujo
   fija. Antes de tocar código: diseño escrito (acumulador por rasgo) y tolerancia de paridad escrita (las
   desviaciones hoy se calculan en float en dos pasadas; incremental en enteros de 128 bits dará valores más
   precisos, distintos en los últimos decimales). Peculiaridad a respetar: `calculate_iat_mean` divide entre
   `size-1` (cuenta los pares desordenados) y `calculate_iat_std_dev` entre los pares válidos.
2. **Caducidad**: limpieza periódica que se llame, desde la cola de la LRU (O(caducados)); `should_expire` con
   guarda; decisión de Alonso sobre tope de duración activa; configuración de la tabla en un solo sitio del JSON,
   validada y registrada en el log; fuera los timeouts que mienten.
3. Batería de la etapa 2 (ddos_v2) y E2E del lab antes/después (la caducidad cambia `flow_packet_count`).
4. Registrar en ctest los tres tests sin registrar.
5. EMECAS+++ production, PR, merge, etiqueta. Entrada de Twitter al cerrar la feature.

## 7. Notas para el paper (arXiv)

Material honesto y medido, utilizable si el paper documenta el coste del sniffer:
- La tabla de flujos acota el número de flujos (LRU, 16 × 10 000) pero no su tamaño: el estado por flujo crece
  ~30 B por paquete mientras el flujo siga vivo, y la caducidad configurada en el JSON no se aplicaba.
- El coste del cálculo de rasgos por evento era O(n) en los paquetes acumulados (copia completa del flujo y
  recálculo de medias, desviaciones, entropías y tiempos entre llegadas en cada paquete): 289 µs por evento en
  flujos de más de 500 paquetes, 7,7 ms por copia a 1 M paquetes.
- Retirando solo código sin lector vivo y un cálculo cuyo resultado se sobrescribía, sin cambiar un solo valor de
  salida (paridad byte a byte en 300 000 eventos): RAM por flujo −61 % (1 697 → 658 B) y coste medio por evento
  −24 % (121 → 92,7 µs). El paso de fondo (estadísticos incrementales) queda pendiente.
- Método: instrumento de paridad determinista + predicción escrita antes de cada medida; tres predicciones
  fallaron y se documentan (hash de `.o` bajo LTO, coste fijo atribuido a `TimeWindowManager`, peso de los flujos
  largos en el tiempo medio).
