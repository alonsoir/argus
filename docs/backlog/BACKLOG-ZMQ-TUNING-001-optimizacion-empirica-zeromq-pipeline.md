# BACKLOG-ZMQ-TUNING-001 — Optimización Empírica de Parámetros ZeroMQ y Pipeline

**Estado:** BACKLOG  
**Prioridad:** P1 — Prerequisito de BACKLOG-BENCHMARK-CAPACITY-001  
**Bloqueado por:** ADR-029 Variant A estable + ADR-029 Variant B estable  
**Estimación:** 2–4 días de sesión  
**Responsable:** Alonso (PI) + Consejo de Sabios (revisión de protocolo y resultados)  
**Fecha de registro:** 2026-05-01 (DAY 137)

---

## Motivación

Los parámetros ZeroMQ y de pipeline actuales (HWM, IO threads, batch size, linger, backpressure) fueron fijados en su momento bajo un único criterio: **el pcap relay funcionaba correctamente**. Eso es un criterio de corrección, no de rendimiento.

Como consecuencia directa:

- Los números de rendimiento publicados en el abstract de arXiv:2604.04952 (Draft v18) corresponden a una configuración **no optimizada** — o posiblemente subóptima, o posiblemente cerca del óptimo por casualidad. No lo sabemos.
- BACKLOG-BENCHMARK-CAPACITY-001 (capacity benchmark eBPF vs libpcap vs ARM64) mediría una mezcla de rendimiento real del backend de captura y penalización artificial del tuning ZeroMQ. Los resultados quedarían contaminados.

**Este experimento debe concluir antes de ejecutar BACKLOG-BENCHMARK-CAPACITY-001**, o al menos sus resultados deben ser inputs del protocolo de ese benchmark.

> Los números incorrectos del arXiv se corregirán cuando la experimentación esté concluida. No es un problema — es el método científico funcionando correctamente.

---

## Parámetros bajo estudio

Los parámetros candidatos son los presentes en los ficheros JSON de configuración del pipeline. A confirmar contra el estado actual del repositorio, pero incluyen como mínimo:

| Parámetro            | Descripción                                              | Valor actual | Rango a explorar |
|---------------------|----------------------------------------------------------|--------------|-----------------|
| `zmq_sndhwm`        | High-Water Mark del lado emisor (sniffer)                | ???          | 100 – 100.000   |
| `zmq_rcvhwm`        | High-Water Mark del lado receptor (ml-detector, etc.)    | ???          | 100 – 100.000   |
| `zmq_io_threads`    | Threads de I/O del contexto ZMQ                          | ???          | 1 – 8           |
| `zmq_linger`        | Tiempo de drenado en cierre de socket (ms)               | ???          | 0 – 5.000       |
| `batch_size`        | Paquetes por mensaje ZMQ (si aplica batching)            | ???          | 1 – 1.000       |
| `zmq_rcvbuf`        | Buffer de recepción OS (bytes, 0 = SO default)           | ???          | 0 – 4 MB        |
| `zmq_sndbuf`        | Buffer de envío OS (bytes)                               | ???          | 0 – 4 MB        |

> **Primer paso de la sesión:** volcar los valores actuales de todos los JSON de configuración y construir la tabla completa antes de diseñar el barrido.

---

## Riesgos específicos a investigar

1. **Drops silenciosos bajo carga alta.** Si `zmq_sndhwm` es demasiado bajo, ZeroMQ descartará mensajes sin notificación explícita al sniffer cuando el pipeline downstream (ml-detector) vaya más lento. Nunca hemos medido esto bajo carga.

2. **Backpressure asimétrico.** El sniffer produce a la tasa del tráfico de red. ml-detector consume a la tasa de inferencia XGBoost. Si HWM está mal calibrado, el buffer actúa como cubo con agujero en lugar de mecanismo de backpressure controlado.

3. **Interacción batch_size ↔ LZ4 ↔ ChaCha20-Poly1305.** El tamaño óptimo de batch no es independiente del overhead de compresión y cifrado. Un batch demasiado pequeño infla el overhead criptográfico; demasiado grande introduce latencia de acumulación.

4. **IO threads vs cores disponibles.** En ARM64 con 4 cores (RPi5), el número óptimo de IO threads puede diferir significativamente del óptimo en x86-64 con 8+ cores.

5. **Comportamiento en degradación.** ¿Qué ocurre cuando el pipeline está al límite? ¿Falla de forma controlada y medible, o silenciosa?

---

## Estructura del experimento

### Fase 1 — Virtualizado (pre-hardware)

**Objetivo:** Entender qué parámetros importan y cuáles son casi indiferentes. No buscamos el óptimo absoluto — buscamos reducir el espacio de búsqueda para Fase 2.

**Método:** Barrido paramétrico con tráfico sintético controlado vía tcpreplay.

```
Para cada parámetro P en {sndhwm, rcvhwm, io_threads, batch_size}:
    Fijar todos los demás en valor baseline
    Barrer P en su rango definido
    Medir métricas durante 60s sostenidos a cada tasa de inyección
    Registrar curva P → métrica
```

**Tasas de inyección:** 100 Mbps / 500 Mbps / 1 Gbps (límite VM)

**Criterio de parada:** Cuando la curva de sensibilidad muestre plateau claro o el parámetro demuestre ser indiferente (variación < 5% en métricas clave).

### Fase 2 — Hardware real

**Objetivo:** Confirmar y refinar los valores candidatos de Fase 1 en condiciones reales. Exprimir el hardware para encontrar el óptimo por perfil de despliegue.

**Perfiles:**
- Servidor x86-64 con NIC XDP-native — BM-A (despliegue con recursos)
- Intel N100 board con i226-V / i225, XDP-native — BM-D (x86-64 low-power)
- Raspberry Pi 5 ARM64 (`genet`, sin XDP nativo) — BM-C (despliegue con recursos limitados)
- Configuración multi-SBC (exploratoria, ver BACKLOG-BENCHMARK-CAPACITY-001)

> Los parámetros ZMQ óptimos pueden diferir entre perfiles. El tuning no es universal — cada perfil de hardware necesita su propia tabla de valores.

---

## Métricas a capturar

| Métrica                        | Unidad   | Notas                                               |
|-------------------------------|----------|-----------------------------------------------------|
| ZMQ message drop rate         | msg/s    | Medido con `zmq_socket_monitor` o contadores propios |
| ZMQ send queue depth          | msgs     | Profundidad media y máxima del buffer               |
| Pipeline throughput           | pps      | End-to-end: sniffer → ml-detector                   |
| Latencia P50/P95/P99          | µs       | Desde captura hasta salida de ml-detector           |
| CPU por componente            | %        | sniffer, ml-detector, firewall-acl-agent por separado |
| Backpressure onset            | Mbps     | Tasa a la que empieza a acumularse cola ZMQ         |
| Drop onset                    | Mbps     | Tasa a la que empiezan drops medibles               |

---

## Outputs esperados

1. **Tabla de parámetros optimizados** por perfil de despliegue (x86 alto rendimiento / ARM64 recursos limitados).
2. **Curvas de sensibilidad** para cada parámetro — publicables como figura en paper derivado.
3. **Actualización de los JSON de configuración** en el repositorio con los valores óptimos documentados y justificados.
4. **Corrección del abstract de arXiv:2604.04952** — los números de rendimiento se actualizarán en una revisión posterior una vez concluida la experimentación.
5. **Inputs validados para BACKLOG-BENCHMARK-CAPACITY-001** — el capacity benchmark correrá sobre la configuración ZMQ óptima, no sobre la configuración accidental original.

---

## Prerequisitos técnicos

- [ ] ADR-029 Variant A (`EbpfBackend`) estable
- [ ] ADR-029 Variant B (`PcapBackend`) estable
- [ ] DEBT-CAPTURE-BACKEND-ISP-001 resuelto
- [ ] Volcado y documentación de valores JSON actuales (primer paso de la sesión)
- [ ] Protocolo EMECAS validado para el entorno de benchmark

---

## Referencias

- BACKLOG-BENCHMARK-CAPACITY-001 (este experimento es prerequisito de ese)
- ADR-029: Capture Backend Architecture (Variants A/B/C)
- arXiv:2604.04952 (Draft v18) — los números del abstract serán corregidos post-experimentación
- prospecto_argus_ndr_v3.docx — FEDER Extremadura 2026 (empirical capacity benchmark, Year 1)
- FEDER deadline: 22 septiembre 2026