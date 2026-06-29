# Consulta al Consejo de Sabios — Reproducibilidad de `event_id`

**Deuda:** `DEBT-ARGUSPP-CLOCK-INJECTION-PROD-001` (P1)
**Día:** DAY 180 · **Branch:** `feature/day170-community-id-protobuf`
**Fecha:** 2026-06-10
**Estado:** diagnosticado en DAY 180 · **decisión postergada y escalada al Consejo**
**Principio rector:** *medir, no votar.* Las preguntas piden criterios falsables, no preferencias.

---

## 1. Resumen ejecutivo

El `event_id` —ancla de la deduplicación del engine y semilla de la cadena `flow_uid`—
se deriva del reloj monótono del kernel (`bpf_ktime_get_ns()`). Ese reloj **no es estable
entre ejecuciones**: el mismo pcap reproducido dos veces produce `event_id` distintos.
Esto rompe la reproducibilidad bit-a-bit del *golden tier*, que sostiene la
reproducibilidad del paper (arXiv:2604.04952) y del demo FEDER. La deuda es **real**, no
fantasma. El fix no toca la arquitectura, pero sí el ancla de dedup, por lo que se escala.

---

## 2. Diagnóstico (evidencia)

**Generación del `event_id`** — `sniffer/src/userspace/ring_consumer.cpp:853`:

```cpp
std::string event_id = std::to_string(event.timestamp) + "_" +
                       std::to_string(event.src_ip ^ event.dst_ip);
```

**Origen del `timestamp`** — `sniffer/src/kernel/sniffer.bpf.c:246`:

```cpp
event->timestamp = bpf_ktime_get_ns();
```

**Estructura compartida** — `sniffer/include/main.h:31`: `uint64_t timestamp;`
(struct `SimpleEvent`, debe coincidir bit-a-bit con el `simple_event` del eBPF).

Descartado el caso wall-clock de userspace: las únicas escrituras de `timestamp` vía
`std::chrono::now()` viven en `sniffer/tests/obsolete_archive/` (código muerto). El camino
de producción es exclusivamente `bpf_ktime_get_ns()`.

**Análisis de tres casos:**

| Caso | Fuente | ¿Replay-stable? | Veredicto |
|------|--------|-----------------|-----------|
| 1 | `bpf_ktime_get_ns()` (monótono desde boot) | **No** | **← caso actual** |
| 2 | wall-clock userspace (`chrono::now`) | No | descartado (código muerto) |
| 3 | timestamp del frame pcap original | Sí | **inalcanzable desde XDP en vivo** |

**Conclusión:** estamos en el caso 1. `bpf_ktime` es monótono desde el arranque de la VM:
depende de cuánto lleva la máquina arriba y del instante exacto de inyección del paquete.
La parte de IPs (`src_ip ^ dst_ip`) sí es intrínseca y reproducible; el reloj la contamina.

**Nota clave sobre el caso 3:** el sniffer en producción captura en vivo por XDP. El paquete
llega sin timestamp de captura previo. El ts intrínseco de un pcap solo existe al
reproducirlo (p.ej. `tcpreplay`), y XDP tampoco lo ve: ve el paquete tal cual entra por la
interfaz. Por tanto **no hay un timestamp de frame que rescatar kernel-side**. El caso 3
puro no es una opción real.

---

## 3. Por qué importa

- `event_id` es el ancla de dedup del engine y la semilla de `flow_uid`
  (`flow_uid = base64(BLAKE2b-256(encode(node_id, community_id, flow_start_window, seq)))`).
- Si `event_id` no es reproducible, dos corridas del mismo pcap divergen → el grafo Kuzu
  materializado no es bit-idéntico entre ejecuciones.
- El *golden tier* es justo el que da reproducibilidad al claim del paper
  (F1=0.9985 sobre CTU-13 Neris) y al demo FEDER. Sin reproducibilidad, un revisor no
  puede replicar el resultado partiendo del mismo input.

---

## 4. Las tres salidas (en orden de cuánto cambian las cosas)

### Opción 1 — `event_id` = hash de contenido invariante del paquete
`event_id = BLAKE2b(5-tupla ‖ IP-ID ‖ seq/ack TCP ‖ longitud ‖ …)`.
- **A favor:** cero dependencia del reloj; determinista sobre el mismo input; libsodium ya
  linkado; idéntico en captura en vivo y en replay (Via Appia: ancla intrínseca al contenido).
- **En contra:** el `bpf_ktime` deja de estar en el `event_id` (sigue viajando en
  `event_timestamp` del proto, no se pierde dato). Dos paquetes idénticos en el mismo flow
  pueden colisionar → exige un desambiguador explícito (ver §5).
- **Toca:** el ancla de dedup. Material de fondo.

### Opción 2 — `event_id` = offset-en-pcap ‖ 5-tupla (solo modo golden)
- **A favor:** reproducibilidad perfecta en el tier golden; semántica clara
  ("clock-**injection**": se inyecta un índice reproducible en lugar del reloj).
- **En contra:** prod y golden usarían estrategias distintas de `event_id` → dos caminos que
  mantener; exige inyectar el offset del paquete en el pipeline.

### Opción 3 — dejar `bpf_ktime` y mockear el time source en el harness golden
- **A favor:** el menos invasivo; un solo `event_id` en todo el sistema.
- **En contra:** la reproducibilidad vive en el harness de test, no en el componente. Menos
  satisfactorio; frágil ante cambios futuros del pipeline.

---

## 5. Vínculo con `DEBT-FLOWUID-SEQ-COLLISION-001`

La Opción 1 obliga a definir el desambiguador de paquetes idénticos en el mismo flow. Eso es
exactamente el problema que hoy aplaza el `seq=0` de `compute_flow_uid`
(`DEBT-FLOWUID-SEQ-COLLISION-001`, P2). Resolver el desambiguador del `event_id` y el `seq`
del `flow_uid` con el **mismo** mecanismo (p.ej. contador por flow estable, u offset en
captura) cierra ambas deudas de una. Son el mismo problema visto desde dos capas.

---

## 6. Preguntas al Consejo (falsables, no de opinión)

1. **¿Es el contenido invariante del paquete suficiente para unicidad sin reloj?**
   Medible: tasa de colisión de `event_id` bajo Opción 1 sobre CTU-13 Neris completo
   (¿cuántos pares de paquetes comparten 5-tupla + IP-ID + seq/ack + longitud?). Umbral de
   aceptación a fijar antes de medir.

2. **¿Debe prod y golden compartir una sola estrategia de `event_id`, o se acepta
   bifurcación (Opción 2)?** Criterio: coste de mantener dos caminos vs. coste de la colisión.

3. **¿El desambiguador de la Opción 1 debe ser el mismo que resuelva el `seq` del
   `flow_uid`?** (Unificar `DEBT-FLOWUID-SEQ-COLLISION-001`.)

4. **¿IP-ID y seq/ack TCP son campos fiables?** IP-ID puede venir a 0 o aleatorizado; seq/ack
   solo existe en TCP. ¿Qué subconjunto de campos garantiza determinismo cross-protocolo
   (incluido UDP, ICMP)?

## 7. Criterios de decisión medibles (medir, no votar)

- **Reproducibilidad:** dos replays del mismo pcap → conjunto de `event_id` idéntico
  (verificable con `diff` de los CSV bronce ordenados). Métrica binaria: pasa / no pasa.
- **Tasa de colisión:** nº de `event_id` duplicados / nº total de eventos sobre el golden set.
- **Coste de mantenimiento:** LOC y nº de componentes tocados por cada opción.
- **Delta de cobertura cross-protocolo:** % de paquetes (TCP/UDP/ICMP) que reciben un
  `event_id` determinista bajo cada esquema de campos.

## 8. Recomendación del relator (no vinculante)

Inclinación inicial hacia la **Opción 1** (event_id intrínseco al contenido, independiente
del reloj y de si se captura en vivo o por replay — coherente con Via Appia), unificada con
`DEBT-FLOWUID-SEQ-COLLISION-001` vía un único desambiguador. Pero la decisión toca el ancla
de dedup y debe medirse (tasa de colisión real sobre CTU-13) antes de comprometerse. Se
escala al Consejo en pleno.