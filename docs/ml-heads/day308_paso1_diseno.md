# DAY308 — Paso 1: estadísticos incrementales en `FlowStatistics` (diseño, antes de tocar código)

Rama `feat/sniffer-flow-expiry`, base `34149159`. Leídos enteros: `sniffer/include/flow_manager.hpp` (177 l.),
`sniffer/src/userspace/ml_defender_features.cpp` (897 l.), helpers de `ml_defender_features.hpp` (l. 160-242),
`ShardedFlowManager::get_flow_stats_copy` y las llamadas de `ring_consumer.cpp` (l. 642-649 foto, l. 929-940 copia).

## 1. Qué sobra y qué entra

**Sale** (8 vectores, crecen sin límite, ~30 B por paquete): `fwd_lengths`, `bwd_lengths`, `all_lengths`,
`packet_timestamps`, `fwd_timestamps`, `bwd_timestamps`, `fwd_header_lengths`, `bwd_header_lengths`.

**Se queda igual:** `flow_start_ns`, `flow_last_seen_ns`, `spkts`, `dpkts`, `sbytes`, `dbytes`, los 8 contadores de
flags, los 4 direccionales, `sum_all_lengths`, `len_hist` (la foto DDoS v2 en el lock los usa; no se tocan).

**Entra** (tamaño fijo):

```
struct LenAcc {                 // una por serie: all, fwd, bwd
    uint32_t min = UINT32_MAX;
    uint32_t max = 0;
    unsigned __int128 sum_sq = 0;   // Σ x²   (la Σ x ya existe: sum_all_lengths, sbytes, dbytes)
};
struct IatAcc {                 // una por serie: all, fwd, bwd
    uint64_t last_ts = 0;       // marca del ultimo paquete de la serie (valido o no)
    uint64_t pairs = 0;         // pares validos (ts >= anterior)
    uint64_t sum = 0;           // Σ iat de pares validos (mismo uint64 que hoy)
    uint64_t min = UINT64_MAX;
    uint64_t max = 0;
    unsigned __int128 sum_sq = 0;   // Σ iat²
};
uint64_t fwd_header_sum = 0, bwd_header_sum = 0;   // la cuenta es spkts / dpkts
```

El número de marcas de cada serie no se guarda: es `spkts + dpkts`, `spkts` y `dpkts` (hoy los vectores tienen
exactamente ese tamaño; `test_sharded_flow_full_contract` lo afirma).

**Regla de pares, idéntica a hoy:** al llegar una marca `ts` a una serie con al menos una marca previa, si
`ts >= last_ts` es par válido (`iat = ts - last_ts`, se acumula); `last_ts = ts` siempre, sea válido o no. Hoy el
recorrido compara `timestamps[i]` con `timestamps[i-1]` (la anterior en orden de llegada, no la máxima): es lo mismo.

**Desbordamiento (acotado, no supuesto):** `packet_len` es `uint32_t` ⇒ `x² < 2^64` y `Σx² < 2^128` para menos de
2^64 paquetes. Para los IAT, el código de hoy ya suma en `uint64_t` (`Σiat < 2^64`); como todos los iat son ≥ 0,
`Σiat² ≤ (Σiat)² < 2^128`. Con `unsigned __int128` no hay desbordamiento posible dentro de las hipótesis que el
código ya hace.

**Varianza:** `var = Σx²/m − (Σx/m)²` en `long double`, recortada a 0 si sale negativa por redondeo;
`std = (float) sqrtl(var)`. El error relativo de la varianza es ≈ 2^-64·(1 + media²/var): para un CV ≥ 10⁻³ queda
en 10⁻¹³, siete órdenes por debajo de la precisión de un float. Es más exacto que el cálculo de hoy, que acumula
en float en dos pasadas (con miles de términos el float se estanca: error esperado creciente con el tamaño).

## 2. Acumulador por rasgo (todo lo que escribe `populate_ml_defender_features`)

Clases: **E** = idéntico bit a bit (misma suma entera, misma conversión a float); **V** = varianza (cambia, ver §3);
**D** = umbral sobre un CV (puede cambiar de escalón, ver §3).

| Rasgo(s) | De dónde sale | Clase |
|---|---|---|
| total_forward/backward_packets/bytes, flow_duration_microseconds | contadores existentes | E |
| forward/backward_packet_length_min/max | `LenAcc fwd/bwd .min/.max` | E |
| forward/backward_packet_length_mean | `(float)sbytes/(float)spkts`, ídem bwd (= `calculate_mean`) | E |
| minimum/maximum_packet_length | `LenAcc all .min/.max` | E |
| packet_length_mean, average_packet_size | `(float)sum_all_lengths/(float)n` | E |
| forward/backward_packet_length_std, packet_length_std | `LenAcc .sum_sq` + Σ; 0 si n < 2 (como hoy) | V |
| packet_length_variance | `std*std` en float (se conserva la fórmula de hoy, no la varianza directa) | V |
| flow/fwd/bwd packets/bytes per second, download_upload_ratio, avg segment sizes | contadores | E |
| flow/forward/backward_inter_arrival_time_min/max | `IatAcc .min/.max` (solo si pairs ≥ 1, como hoy) | E |
| …_inter_arrival_time_mean | `(float)sum/(float)pairs /1000.0` | E |
| forward/backward_inter_arrival_time_total | `sum/1000.0` | E |
| …_inter_arrival_time_std | `IatAcc .sum_sq` + `.sum` / `.pairs` | V |
| flags (8 + 4), smb rst_ratio/syn_ack_ratio | contadores | E |
| forward/backward_header_length | `(double)fwd_header_sum/spkts`, ídem bwd | E |
| bulk (6 ceros), active_mean, idle_mean | sin cambios | E |
| ransomware: network_activity, access_frequency, data_volume; traffic: packet_rate, avg_packet_size; internal: data_exfiltration | contadores | E |
| ransomware.entropy, internal.access_pattern_entropy | entropía de las longitudes (decisión D1) | E |
| rasgos de ventana (aggregator) y centinelas | sin cambios | E |
| ransomware.behavior_consistency | `1 − std_iat/mean_iat_quirk` | V |
| traffic.temporal_consistency, internal.protocol_regularity | `1 − cv_iat` | V |
| internal.packet_size_consistency | `1 − std_all/mean_all` | V |
| ransomware.temporal_pattern (umbrales 0,5 / 1,0) | `cv_iat` | D |
| internal.temporal_anomaly_score (umbrales 0,2 / 2,0) | `cv_iat` | D |

**Peculiaridad que se respeta:** `cv_iat = std_iat / mean_iat_quirk`, con
`mean_iat_quirk = (float)all.sum / (float)(spkts + dpkts − 1)` (divide entre el número de marcas menos uno, es decir,
cuenta también los pares desordenados) y `std_iat` sobre los pares válidos (`pairs`). Si `spkts + dpkts < 2` o
`mean_iat_quirk == 0`, cv = 0 (como hoy); si `pairs == 0`, std = 0 (como hoy). Se mantienen los helpers con su
nombre y semántica, ahora sobre acumuladores.

## 3. Tolerancia de la paridad (escrita antes de medir)

Instrumento nuevo `scripts/flow_expiry/d308_paridad_tolerancia.cpp`, misma semilla 307 y mismos 300 000 eventos que
`d307_paridad_rasgos.cpp`. Lleva **sus propios vectores en sombra** por flujo (solo el instrumento, no producción)
y calcula un **oráculo**: varianza en `long double` en dos pasadas sobre los valores exactos, con el mismo
post-proceso en float que producción. Comparaciones:

1. **Clase E:** byte a byte contra `logs/lab/day307/paridad/antes.tsv`. Criterio: 0 diferencias.
2. **Clase V:** nuevo contra oráculo. Criterio: |nuevo − oráculo| ≤ 2 ulp de float en el 100 % de los eventos.
   Además se informa (no es criterio) el error viejo contra oráculo por tramo (1–20, 21–500, 501+), para dejar
   escrito cuánto se equivocaba el cálculo de hoy.
3. **Clase D:** el escalón nuevo tiene que ser el del cv del oráculo en el 100 % de los eventos. Los cambios de
   escalón viejo → nuevo se cuentan y se listan; cada uno tiene que tener el cv del oráculo pegado al umbral.
4. Si cualquiera de los tres criterios falla: PARAR.

## 4. Decisiones que te tocan

**D1 — Coste por evento de la entropía (la que decide si el paso es O(1) o no).** La copia por evento hoy arrastra
`len_hist` (un `std::map`). El generador de la paridad usa longitudes uniformes 40–1500 en el 25 % de los paquetes:
un flujo largo llega a ~1 400 longitudes distintas, y copiar ese mapa es ~1 400 reservas de memoria por evento. Con
vectores fuera, el coste deja de depender de n pero pasa a depender de k (longitudes distintas, acotado por ~1 500).
- **(a)** Copiar el mapa como hoy: lo más sencillo, O(k) por evento.
- **(b)** Calcular las dos entropías dentro del lock con el flujo: no copia el mapa, pero alarga el lock del shard.
- **(c)** Reutilizar la entropía de la foto DDoS (`ddos_snap.packet_size_entropy`): **es el mismo número**
  (`calculate_entropy(all_lengths)`, bit a bit idéntico desde D290), ya está calculado en el lock y viaja con el
  evento. La copia queda sin mapa y el evento es O(1). Cambio de semántica: esas dos entropías pasan a medirse en el
  instante del paquete (como ddos_v2 desde D290) en vez de en el del procesamiento del lote. En el instrumento,
  monohilo, los dos instantes coinciden y la paridad es exacta.
- Recomiendo **(c)**.

**D2 — Copia del flujo.** Con tamaño fijo, `FlowStatistics` puede declarar el constructor de copia `= default`
y `get_flow_stats_copy` copiar de una vez, en lugar de la copia a mano campo a campo (la familia de
DEBT-FLOWSTATS-COPY-AMPUTATED-001: hoy un campo nuevo que no se añada a mano se pierde en silencio). Con (c), la
copia excluye `len_hist`: `FlowStatistics` se parte en un núcleo copiable de tamaño fijo y el mapa al lado.
Recomiendo hacerlo en este paso.

**D3 — Tests que afirman vectores.** `test_ddos_flow_snap` (registrado en ctest) reconstruye suma e histograma desde
`all_lengths`; `test_sharded_flow_full_contract` y `test_sharded_flow_multithread` (sin registrar) afirman tamaños y
orden de los vectores. Se reescriben para comparar los acumuladores contra una referencia que el propio test
acumula con los paquetes que inyecta. Inventario completo (113 líneas, `git grep` de los 8 nombres): 3 tests,
`flow_manager.hpp`, `sharded_flow_manager.cpp`, `ml_defender_features.cpp`; el resto son comentarios y parcheadores
viejos (`day290_patch_ddos_snap.py`, `patch_d286_*.py`, `d307_paso2_sin_ddos_lote.py`, un comentario del
`.proto` y uno de `docs/ddos-head-contract-inventory.md`).

**D4 — `sum_all_lengths` es redundante** (= `sbytes + dbytes`). Propongo no tocarlo en este paso (lo usan la foto y
su test); anotarlo.

## 5. Predicciones (antes de medir)

- **P1, RAM por flujo de 1 paquete** (`d307_ram_flujo`, fase A): 658 B → entre 430 y 540 B. Salen 8 cabeceras de
  vector (192 B) y 8 reservas de un elemento (~256 B); entran ~260 B de acumuladores con relleno de alineación de
  `__int128`.
- **P2, RAM de un flujo largo** (fase B, 10 M paquetes): plana una vez saturadas las longitudes distintas; de ~30 B
  por paquete a ~0.
- **P3, populate por evento** (con D1 = c): sin dependencia del tamaño del flujo; los tres tramos dentro de ±30 %
  entre sí; media entre 3 y 10 µs (hoy 92,7). La foto DDoS en el lock sigue siendo O(k): el instrumento medirá
  también su tiempo, aparte, para ver el coste real por evento entero.
- **P4, paridad:** clase E idéntica; clase V dentro de 2 ulp del oráculo; error viejo contra oráculo creciente con
  el tramo; pocos o ningún cambio de escalón en la clase D.

## 6. Orden de trabajo propuesto (cuando decidas D1-D4)

1. Instrumento `d308_paridad_tolerancia.cpp` contra el código de HOY: comprobar que reproduce `antes.tsv` y que el
   oráculo cuadra con el viejo en los flujos cortos (validar el instrumento antes de usarlo).
2. Parcheador (`--check`/`--apply`, sha256 de partida y llegada, anclas únicas, probado en copia desechable):
   `flow_manager.hpp`, `sharded_flow_manager.cpp`, `ml_defender_features.{hpp,cpp}`, `ring_consumer.cpp` (si D1 = c)
   y los 3 tests.
3. `make pipeline-build PROFILE=production`, `make test-components PROFILE=production` (82), los 3 tests sin
   registrar a mano, paridad con tolerancia, RAM y tiempos. Antes y después.

## 7. Resultado (escrito DESPUÉS de medir; las secciones 1-6 se dejan como se escribieron antes)

Commit del paso: `refactor(sniffer): DAY308 paso 1 — estadisticos incrementales en FlowStatistics`. Medidas en el
defender (VM VirtualBox, i9-9980HK, FMA/AVX2), 300 000 eventos, semilla 307, salidas en `logs/lab/day308/`.

### 7.1 Decisiones de Alonso

D1 (entropía de la foto), D2 (copia de una vez, `FlowStatsCore`), D3 (reescribir los 4 tests), D4 (fuera
`sum_all_lengths`; la foto usa `sbytes + dbytes`, mismo número bit a bit). P1: se aceptan 618-626 B por flujo con
`__int128`; no se parten las sumas en dos `uint64_t`.

### 7.2 Tolerancia: ajuste hecho ANTES de medir el paso

La sección 3 decía "2 ulp" para toda la clase V. El comparador (`d308_comparar.py`) aplica: desviaciones 2 ulp
relativos (2^-23); `packet_length_variance` (std·std) 4 ulp (2^-22); consistencias 2^-22 absoluto, centinela exacto.
Los derivados heredan el error de lo que derivan.

### 7.3 Medidas

| | Antes | Paso 1 |
|---|---|---|
| Paridad E / V / D, sin banderas (contra `antes.tsv`) | — | 0 / 0 ulp / 0 |
| Paridad E / V / D, banderas de producción (contra `prod_hoy.tsv`) | — | 0 / 0 ulp / 0 |
| Error del cálculo viejo contra el oráculo (máx., tramo 501+) | 1,5·10⁻⁵ relativo (~250 ulp) | 0 |
| RAM por flujo de 1 paquete (fase A) | 658 B | 625,6 B |
| RAM de un flujo de 10 M paquetes (fase B) | ~30 B por paquete (DAY307: 292 MB) | 0 B por paquete |
| Copia por evento a 1 M paquetes | 7,7 ms (DAY307) | 0,2-0,3 µs |
| Flujo con 1 461 longitudes distintas (fase C, pendiente) | 122,7 kB | 70,8 kB |
| Populate aislado (microbanco, flujo fijo) | — | ~0,6 µs, plano |
| Populate en el instrumento, por tramo | 4,5 / 28,6 / 183 µs | 1,5 / 1,6 / 1,7 µs |
| `make test-components PROFILE=production` | 82/82 | 82/82 |
| Tests sin registrar (4 / 6 / 3) | pasan | pasan |

`sizeof(FlowStatistics)`: 344 → 448 B (`LenAcc` 32 B y `IatAcc` 64 B por el alineamiento de `__int128`).

### 7.4 Predicciones: cuáles fallaron y por qué

- **P1 (430-540 B por flujo): falló, 625,6 B.** No calculé el `sizeof` con el relleno de `__int128`; se mide en un
  minuto y no lo hice antes de predecir.
- **P3 (populate 3-10 µs): falló a mejor, ~0,3 µs en mi máquina.** Supuse que el coste fijo del tramo corto seguiría;
  era casi todo trabajo con vectores. Error de modelo, no de suerte.
- **Valores absolutos llevados de una máquina a otra (populate 0,3-0,6 µs y base de la fase C ~655 B en el
  defender): fallaron (1,6 µs y 541 B).** Un factor supuesto entre máquinas no sirve: se mide en la máquina de
  registro. La base de la fase C con 2 000 flujos crece a saltos de página (264 kB por fila) y no resuelve 30 B por
  flujo; la medida fina de la RAM por flujo es la fase A.
- **Se cumplieron**: paridad en los dos perfiles, coste plano, 0 B por paquete, fase A ±5 %, fase C ±10 %, 82/82.

### 7.5 Corrección: "memoria por flujo fija" no es verdad del todo

La sección 1 lo daba a entender. `len_hist` sigue creciendo con las longitudes DISTINTAS del flujo (~48 B por
longitud). Peor caso medido: 70,8 kB por flujo con 1 461 longitudes (40-1500); la tabla llena (160 000 flujos) se
extrapola a ~11 GB (no medido). Un atacante en la red puede forzarlo variando la longitud de sus paquetes. Lo introdujo
D290 (la foto de ddos_v2 depende del histograma), no este paso: deuda propia, DEBT-SNIFFER-LENHIST-UNBOUNDED-001.

### 7.6 Banderas de producción

El sniffer se compila con `-O3 -march=native -flto`; la referencia de DAY307 (`antes.tsv`) se generó sin ellas. Con
ellas, el código de antes cambia 104 784 de 300 000 eventos en las últimas cifras (entropías, incluida la de ddos_v2,
y desviaciones en float), por fusión FMA. El código del paso 1 solo cambia las entropías: las desviaciones nuevas (en
`long double`) salen idénticas con y sin banderas. Desde DAY308, antes y después se comparan en los dos perfiles.
Deuda de método: DEBT-PARIDAD-FLAGS-PRODUCCION-001.

### 7.7 Investigación: por qué populate costaba 1,6 µs en el instrumento del defender

Populate costaba en el defender 5,8 veces lo de mi máquina, cuando con el código viejo era 1,6. Hipótesis y medidas,
en orden:

1. **Reloj de la VM: falsada.** `tsc`; un par `steady_clock::now()` vacío cuesta 0,022 µs, igual que fuera.
2. **Reservas y protobuf bajo VirtualBox: falsada.** Microbanco: aritmética ×1,5, `malloc`/`free` ×2,1, protobuf ×1,7.
3. **Caché fría por el oráculo del instrumento: falsada.** Con y sin oráculo, lo mismo (1,87/1,88 y 2,04/2,02 µs).
4. **Reparto de la región cronometrada:** populate 85 % (1,47-1,70 µs), copia 0,15 µs, rasgos DDoS 0,11 µs.
5. **Populate aislado** (microbanco sobre un flujo fijo): ~0,6 µs en el defender, ×2,1 frente a mi máquina, como el
   resto de operaciones. Nada en su código que la VM castigue especialmente.
6. **Escritura del TSV en `/vagrant` (carpeta compartida vboxsf): confirmada en parte.** La misma corrida escribiendo
   en `/tmp`: 0,99-1,12 µs frente a 1,62-1,63 µs. Unos 0,55 µs por evento son de vboxsf; ~0,4-0,5 µs más son del
   resto del trabajo del instrumento entre eventos (no atribuido; es del instrumento, no del sniffer).

Conclusión: el coste propio de populate en el defender es ~0,6 µs por evento, plano. Regla nueva del lab: las medidas
de tiempo no escriben en `/vagrant`. Las de DAY307 lo hacían, igual antes que después: su comparación relativa vale,
sus valores absolutos están inflados.

### 7.8 Lo que ve cada herramienta

Prueba de mutación (regla de pares `>=` cambiada a `>`): `test_ddos_flow_snap` la detecta (63 fallos); el instrumento
de paridad no, porque su generador nunca produce dos marcas iguales seguidas. El caso 7 del test (marcas
desordenadas y repetidas) cubre ese hueco.

### 7.9 Siguiente

El coste dominante por evento pasa a ser la foto DDoS en el lock, O(k) en las longitudes distintas: 23-36 µs en el
tramo 501+ del instrumento (dentro de DEBT-SNIFFER-LENHIST-UNBOUNDED-001). En la rama sigue el paso 2: caducidad.
