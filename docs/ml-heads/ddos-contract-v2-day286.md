# Contrato DDoS v2 — un solo cálculo de rasgos para entrenar y servir (DAY286)

Documento de respaldo para el paper (arXiv:2604.04952, revisión pendiente). Rama
`feat/ddos-head-contract`. Commits: `d9901d67` (contrato v2 en el sniffer, campos 11–15) y el commit
de H2 (campo 14, EWMA por víctima, y definición única de la duración de ventana). Todo lo que sigue
está medido en el laboratorio VirtualBox (defender Debian bookworm, 6 vCPU, XDP genérico, build
`production` `-O3 -flto`), con la regla de trabajo del proyecto: predicción escrita antes de medir y
parada cuando el resultado no la cumple.

## 1. Problema de partida

El inventario DAY282 midió **tres definiciones distintas** de cada rasgo de la cabeza DDoS: la del
generador sintético de entrenamiento, la que recalcula el ml-detector (`extract_level2_ddos_features`) y
la que calcula el sniffer (`ddos_embedded`). El bosque desplegado come la segunda, que tiene rasgos
constantes (`source_ip_dispersion = 0,1`, `protocol_anomaly = 0`) y un `traffic_escalation_rate` que en
realidad es caudal instantáneo del flujo. Es la generalización del skew train/serve de DAY255 (geo):
decisiones razonables por separado, incoherentes en conjunto.

Principio adoptado: **el dataset de entrenamiento se generará con el mismo código que sirve**. Con eso el
skew desaparece por construcción y la elección de cada rasgo deja de depender de "parecerse a train":
pasa a depender de (a) que discrimine, (b) que se calcule al 100 % en el sniffer y (c) que su nombre diga
lo que mide. El bosque es invariante a escala, así que los valores van en crudo, sin MinMaxScaler.

## 2. Hallazgo de captura: el sensor solo ve el tráfico entrante

Medida M1: subida TCP legítima de 1500 paquetes (50 KB/s, 30 s) del client al defender.

| Medida | Resultado |
|---|---|
| Eventos de la subida (`.50 → .1:9999`) | 1503 |
| Eventos con `bwd ≥ 1` | 0 |
| Eventos con origen `192.168.100.1:9999` (ACK del servidor) | 0 |

Dos defectos superpuestos:

1. **Captura**: en el tráfico que termina en el defender, XDP solo ve la entrada.
2. **Código de flujos**: `FlowKey` es la 5-tupla del paquete sin normalizar y `ShardedFlowManager` busca
   la clave exacta, así que cada sentido es un flujo propio y `dpkts`, `dbytes` y todos los `bwd_*` valen
   0 siempre. Evidencia en ejecución: en tráfico entre otras dos máquinas (agente Wazuh `.10` ↔ manager
   `.12:1514`) el sensor ve los dos sentidos, como dos flujos con `0 bwd` cada uno.

Consecuencia para DDoS: el ataque llega a la víctima como tráfico entrante, así que una cabeza DDoS puede
construirse solo con rasgos de entrada. Los rasgos que dependen de la vuelta (`packet_symmetry`,
`traffic_amplification_factor`) son constantes y salen del vector. La amplificación, además, no es
observable desde la víctima ni con captura bidireccional (la petición va del atacante al reflector).
Consecuencia para las otras cabezas y level1 (entrenadas con CIC bidireccional): todo su lado `Bwd` está
muerto (deuda DEBT-SNIFFER-FLOW-UNIDIRECTIONAL-001, fuera de este trabajo).

## 3. El contrato v2: 8 rasgos, solo tráfico entrante

| Campo proto | Rasgo | Definición | Fuente |
|---|---|---|---|
| 1 | `syn_ack_ratio` | `syn / (ack + 1)`, tope 10 | flujo |
| 11 | `mean_packet_size` | media de las longitudes del flujo (B) | flujo |
| 12 | `reflection_signature` | 1 si UDP desde puerto reflejable a puerto ≥ 1024 | paquete |
| 5 | `packet_size_entropy` | entropía de las longitudes del flujo (bits) | flujo |
| 13 | `flow_packet_count` | paquetes del flujo | flujo |
| 7 | `flow_completion_rate` | {0; 0,5; 1} por flags TCP | flujo |
| 14 | `victim_rate_ratio` | pps de la víctima / max(EWMA previa, 10) | víctima (kernel) |
| 15 | `victim_pps` | `d_pkts · 1000 / window_ms` de la ventana del kernel | víctima (kernel) |

Puertos reflejables: 17, 19, 53, 69, 111, 123, 137, 138, 161, 389, 1434, 1900, 3702, 5683, 11211.

Cobertura de los tipos de DDoS conocidos:

| Tipo | Rasgos que lo delatan |
|---|---|
| SYN flood | `syn_ack_ratio` alto, `completion` 0, paquetes diminutos |
| Reflexión / amplificación | `reflection_signature` = 1, paquetes grandes |
| UDP flood volumétrico | `victim_pps` alto, entropía ≈ 0, tamaño fijo |
| Cualquier ráfaga nueva contra una víctima | `victim_rate_ratio` alto |

**Límite honesto**: el HTTP flood (capa 7, peticiones de aspecto legítimo) no lo ve ningún rasgo de flujo;
solo en parte `victim_pps`.

Decisiones de implementación:

- **Campos nuevos (11–15), no renombrados.** Renombrar con el mismo número no rompe el formato en la red y
  por eso mismo haría que los lectores viejos (CSV, tools) leyeran el significado nuevo con el nombre
  viejo sin que nada falle: la grieta A (homónimos) llevada al formato en la red. Los campos viejos se
  conservan con un comentario, no con `[deprecated]` (con `-Werror` rompería a los lectores).
- **Centinela** `MISSING_FEATURE_SENTINEL` en 11–15 cuando no hay dato (flujo no encontrado, ventana sin
  foto del kernel), para que "sin dato" no se confunda con 0.
- **Funciones puras con `static_assert`** en `sniffer/include/ddos_contract_v2.hpp`: tests que se comprueban
  al compilar, sin cableado de CMake.

## 4. Verificación E2E del contrato (commit `d9901d67`)

Corrida: prueba de reflexión (20 datagramas UDP desde `client:53` al defender, 400 B de carga), flood
CICDDoS2019 (12 000 paquetes a 100 pps, reescrito a la topología del laboratorio) y subida TCP legítima.
Eventos de flujo; las fast alerts quedan excluidas.

| Grupo | n | refl | mean_size (p50) | entropía (p50) | pkts (p50 / máx) | completion | vpps (p50) |
|---|---|---|---|---|---|---|---|
| Reflexión | 20 | 1 (20/20) | 442 | 0 | 13 / 20 | 0 | 8 |
| Flood | 10 894 | 0 | 482 | 0 | 49 / 200 | 0 | 100,1 |
| Subida TCP | 1502 | 0 | 1090 | 0,90 | 755 / 1502 | 0,5 (máx 1) | 50,1 |

Los tres tráficos quedan separados por varios rasgos independientes.

## 5. H2: escalada por víctima sin envenenamiento de la línea base

Estudio offline sobre `ddos_windows.csv` (el CSV de ventanas por víctima del agregador en el kernel):
117 403 ventanas de ~1 s, 4238 víctimas, 12 días, 77 episodios de flood contra `192.168.100.1/UDP`.
Ratio = pps de la ventana / max(EWMA previa, suelo); las ventanas sin tráfico cuentan como cero.

| Variante | Arranque ≥ 5 (episodios) | Ambiente: ventanas ≥ 10 | Problema |
|---|---|---|---|
| EWMA simple (α = 0,1, suelo 10) | 49/77 | 66 | los floods repetidos envenenan la línea base |
| Congelar si ratio ≥ 5 (60 ventanas) | 65/77 | 408 | congela claves nuevas desde 0: FP en tráfico de prueba (Neris) |
| Congelar solo claves calientes (≥ 30 ventanas vistas) | 64/77 | 67 | — |
| **Dos alfas (elegida):** α/60 si caliente y ratio ≥ 5 | 63/78 | 67 | — |
| α_anom = 0 (congelación pura) | 66/78 | 67 | un cambio legítimo permanente sería FP para siempre |

Criterio de elección (Alonso): **evitar siempre los falsos positivos permanentes**. Con la opción elegida, un
flood sostenido deja de "escalar" hacia la ventana ~125 (la EWMA llega a 1/5 del caudal del ataque en
~134 ventanas con α/60 ≈ 0,0017), y su nivel lo sigue marcando `victim_pps`. Una víctima sin historia
(fría) aprende con α normal: el ratio solo marca el arranque (10 → ~1 en ~20 ventanas).

Parámetros: α = 0,1 por ventana; α_anom = α/60; K = 5; W = 30 ventanas vistas; suelo 10 pps; desalojo de
claves tras 3600 ventanas sin aparecer.

## 6. Implementación y equivalencia offline ↔ servicio

La EWMA se actualiza una vez por ventana en `DdosVictimBoard::publish_window` (escritor único: el hilo
lector del kernel); el ratio viaja con la foto y se estampa en cada evento. Test unitario (caso 11 de
`test_ddos_victim_board`, 36 checks): víctima fría = 10; ausente = 0; caliente con ataque = 5,075 y la
ventana siguiente 5,041 (con α normal sería 3,6); tras un hueco de 100 ventanas = 10.

Criterio de HECHO: el script offline aplicado al CSV de la misma corrida debe dar los mismos ratios que el
sniffer estampó. La primera comparación dio **1169 discrepancias** (máx 0,008): el tablero calculaba la
duración de la ventana truncando y el CSV redondeando (−1 ms en 74 de 152 ventanas). Era una cuarta
definición duplicada, de una magnitud auxiliar. Tras unificarla (`ddos_window_ms()` en una sola cabecera):

| Comprobación | Resultado |
|---|---|
| `window_ms` tablero vs CSV | 119/119 iguales |
| Ratios comparados | 3485, **0 discrepancias**, max_diff 0,000496 (redondeo del log) |
| Víctimas ausentes con ratio ≠ 0 | 0 de 643 |

**Lección de método (paper)**: la equivalencia exacta offline ↔ servicio sobre la misma corrida es un
detector de definiciones duplicadas. Encontró una que ninguna revisión de código había visto.

## 7. Corrección de una conclusión anterior (DAY270)

DAY270 explicó el recall ≈ 0 de level1 ante el flood diciendo que el flood eran "flujos de 1 paquete". Esa
cifra salía de la línea `Packets: N fwd` del ml-detector, que vale 1 en el **100 %** de los eventos
(13 109/13 109), incluida la subida TCP, cuyo flujo real tiene 1502 paquetes. El contador real del sniffer
da para el flood p50 = 49 y máx = 200 paquetes por flujo. El hallazgo del veto de level1 (medido abriendo
la compuerta) se mantiene; la explicación del mecanismo, no. Además, los rasgos de recuento de level1
parecen tener el mismo defecto (`Subflow Fwd Packets = 1` junto a `ACK Flag Count = 66`): deuda abierta.

## 8. Limitaciones y pendientes

- El ml-detector **todavía no come** el contrato v2; sigue con el bosque sintético. Falta el paso 2: dataset
  generado por el sniffer (replay de pcaps etiquetados, sin VERBOSE), entrenamiento sin scaler e
  importancias de los 8 rasgos.
- `source_ip_dispersion` fuera hasta tener un pcap multi-origen: la reescritura del laboratorio colapsa
  todos los orígenes en uno, así que ese rasgo no se puede medir con el pcap actual.
- Tope de 200 paquetes por flujo sin investigar.
- Laboratorio: un solo sensor, XDP genérico en VirtualBox, CICDDoS2019 reescrito a la topología del lab.

## 9. Reproducibilidad

- Patchers (atómicos, idempotentes, `--check`/`--apply`): `patch_d286_proto_ddos_v2.py`,
  `patch_d286_sniffer_ddos_v2.py`, `patch_d286_mld_ddos_v2_log.py`, `patch_d286_h2_victim_ratio.py`,
  `patch_d286_window_ms_single.py`.
- Medida y verificación: `scripts/d286_h2_ewma_offline.py`, `d286_h2_ewma_freeze.py`,
  `d286_h2_ewma_warm.py`, `d286_h2_ewma_dual_alpha.py` (estudio H2); `d286_ddos_v2_summary.py`
  (resumen por grupo); `d286_udp_refl.py` (emisor de la prueba de reflexión); `d286_h2_equiv.py` y
  `d286_wms_compare.py` (equivalencia offline ↔ servicio).
- Logs de evidencia en el defender: `/vagrant/logs/lab/d286_m1_upload50.log`, `d286_v2_verify.log`,
  `d286_h2_verify.log`, `d286_h2_verify2.log`.
