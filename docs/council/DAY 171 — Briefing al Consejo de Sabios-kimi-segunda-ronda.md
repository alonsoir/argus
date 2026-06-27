# Respuesta del Consejo de Sabios — Segunda Ronda, DAY 171

Leída la segunda ronda. La grieta es real y la dirimimos ahora. La tesis del bando del cero estricto es correcta en el contexto del replay #1, pero hay que nombrar los mecanismos para que el veredicto sea irrefutable.

---

## 1. Dirimición de P2: ¿Existe discrepancia de VALOR legítima a tasa sin pérdida?

**Respuesta técnica: NO.** En las condiciones del replay #1 (mismo pcap Neris, mismo intnet, tasa baja, sin pérdida, sin fragmentación forzada, sin túneles), **no existe mecanismo de "diferencia de capa" que produzca un community_id de valor distinto sobre el mismo flujo TCP/UDP.**

A continuación, el análisis mecánico de cada supuesto mecanismo que podría argumentar el bando del umbral:

### 1.1 Reensamblado TCP/IP

El community_id se computa sobre la **5-tupla de transporte**: `(src_ip, dst_ip, src_port, dst_port, proto)`. Estos valores son propiedades de las cabeceras IP y TCP/UDP, **no del payload reensamblado**.

- **Suricata** reensambla TCP y defragmenta IP. El reensamblado opera sobre el payload y la secuencia de segmentos. Las cabeceras IP y TCP de los paquetes individuales no se modifican por el reensamblado. La 5-tupla que Suricata extrae para indexar el flujo es la misma que aRGus ve en el primer paquete SYN.
- **Zeek** mantiene estado de conexión. El estado afecta a *cuándo* emite el `conn.log` y *qué* campos incluye, pero la 5-tupla del registro de conexión sigue siendo la de las cabeceras del handshake inicial.
- **aRGus** captura por flujo a nivel de libpcap. La 5-tupla se extrae de cada paquete individual.

**Veredicto**: El reensamblado no puede alterar IPs ni puertos. No produce discrepancia de valor.

### 1.2 Estado de conexión y heurísticas de cierre

Suricata puede mantener un flujo abierto tras un RST si está configurado para ignore-RST, o Zeek puede esperar a un FIN para cerrar. Esto afecta a:
- **Presencia**: si se emite un evento de flujo para un paquete aislado.
- **Timing**: cuándo se emite el cid.

No afecta al **valor** del cid del flujo que sí se emite. La 5-tupla es invariante.

### 1.3 Fragmentación IP

Este es el único mecanismo que, en teoría, podría producir una discrepancia de valor en condiciones extremas:

- El **primer fragmento** de un paquete IP fragmentado lleva la cabecera de transporte (puertos).
- Los **fragmentos posteriores** no llevan puertos.
- Si un sensor (aRGus, sin reensamblado IP) ve solo un fragmento posterior, no puede extraer la 5-tupla completa. `compute_community_id` devolvería `nullopt` (expected_diff, no anomaly).
- Si otro sensor (Suricata, con reensamblado) ve todos los fragmentos, reensambla y extrae la 5-tupla completa.

**Pero en el replay #1**: usamos el pcap Neris a tasa baja sin pérdida. Los fragmentos, si existen, llegan todos. aRGus, operando por flujo, asocia los fragmentos al flujo correcto mediante el ID de fragmentación IP y la 5-tupla parcial (IPs, proto). No produce un cid *distinto*; produce un cid *o no produce* (presencia, no valor).

**Veredicto**: En el Neris, no hay fragmentación IP significativa que genere este escenario. Y si la hubiera, el resultado es expected_diff (no cid), no anomaly de valor.

### 1.4 Túneles, NAT, VLANs, IP options

- **Túneles/NAT**: No existen en el pcap Neris. Todos los sensores ven los paquetes crudos en el mismo intnet.
- **VLANs**: El community_id original de Corelight no incluye VLAN ID en la 5-tupla. Si algún sensor incluye VLAN, es un bug de implementación, no una "diferencia de capa legítima".
- **IP options**: No alteran IPs ni puertos.

### 1.5 Errores de parsing (malformed packets)

Si un paquete tiene una cabecera IP malformada, un sensor podría parsearla incorrectamente y extraer una 5-tupla distinta. Esto **sí** produciría una discrepancia de valor.

**Pero esto no es "diferencia de capa legítima"**. Es un **bug** del parser (categoría a). Y en el pcap Neris, el tráfico es predominantemente bien formado.

### 1.6 Síntesis mecánica

| Mecanismo propuesto | ¿Afecta a la 5-tupla? | ¿Produce valor distinto? | ¿Es legítimo? |
|---|---|---|---|
| Reensamblado TCP | No | No | — |
| Estado de conexión | No | No | — |
| Fragmentación IP | Parcial (solo presencia) | No (expected_diff) | — |
| Túneles/NAT/VLAN | No (no aplican) | No | — |
| Malformed parsing | Sí (potencial) | Sí | **Bug (a), no legítimo** |

**Conclusión**: No existe mecanismo legítimo de "diferencia de capa" que explique un 1% de discrepancia de VALOR en el replay #1. El umbral porcentual del bando contrario es, como sospechaban, racionalización post-hoc de una discrepancia que, si existe, es de presencia (b) o bug/evasión (a/c).

---

## 2. Veredicto sobre el criterio de aceptación

**Adoptamos la síntesis propuesta: cero-valor + clasificación obligatoria.**

El criterio no es un número mágico. Es un proceso de clasificación forense:

1. **Cero discrepancias de VALOR sin clasificar** en flujos TCP/UDP.
2. **Cada anomalía se etiqueta obligatoriamente**:
   - **(a) Bug**: Parser incorrecto, error de canonicalización, race condition en el sellado. → Fix y re-replay.
   - **(b) Presencia/Drop**: Un sensor no emitió el flujo. → Verificar contadores de drop (prerequisito, punto 3).
   - **(c) Inexplicable/Evasión**: Misma 5-tupla, cid distinto, sin drop, sin bug identificable. → **Hallazgo de seguridad**. Alimentar el grafo Neo4j (ADR-052) como arista de desacuerdo.
3. **Verde del #1**: cero (a) sin fix pendiente, cero (c), y cero (b) verificable mediante contadores de drop.

El "%" del bando del umbral se transmuta en: **"¿Qué porcentaje de anomalías quedan sin clasificar?"** La respuesta debe ser **0%**. No es tolerancia, es cobertura de diagnóstico.

---

## 3. Prerequisito de contadores de drop: ¿Bloqueante o diferible?

**Bloqueante para el reporte del verificador, pero BARATO y sin código nuevo en sensores.**

### Justificación

Sin contadores de drop por sensor, la clasificación (a) vs (b) es indistinguible:

- aRGus no emite un flujo: ¿es porque no vio el paquete (drop, categoría b) o porque falló el sellado (bug, categoría a)?
- Suricata no emite un flujo: ¿es porque lo filtró por regla (presencia esperada) o porque perdió el SYN (drop)?

La clasificación obligatoria del punto 2 se vuelve adivinación sin esta métrica.

### Implementación (barata)

Los tres sensores ya exponen los contadores:

| Sensor | Contador existente | Ubicación |
|---|---|---|
| **aRGus** | `events_processed`, `events_dropped` (ring_consumer); `pkts_sent`, `send_failures` (libpcap) | Stats internas, ya logueables |
| **Suricata** | `capture.kernel_packets`, `capture.kernel_drops`, `decoder.pkts` | `stats.log` o `eve.json` (stats event) |
| **Zeek** | `capture_loss`, `pkts_processed`, `pkts_dropped` | `capture_loss.log`, `stats.log` |

**Acción**: El verificador `community_id_crosscheck.py` debe recoger estos contadores **antes y después** del replay, y volcarlos en el reporte TSV. No es instrumentación nueva; es un `vagrant ssh` adicional por VM para leer los logs de stats.

**Veredicto**: **Prerequisito bloqueante para declarar verde**, pero implementable en minutos en el verificador Python. No requiere modificar el pipeline C++.

---

## 4. Separación valor/timing: Confirmada

**El Consejo confirma la separación propuesta.**

### Experimento #1 (Valor)
- **Objetivo**: Validar que los tres sensores computan el mismo community_id para los mismos flujos.
- **Método**: Replay del pcap Neris a tasa baja, distribución temporal natural.
- **Criterio**: Cero anomalías de valor no clasificadas.
- **Contaminantes prohibidos**: No inyectar ráfagas artificiales. No forzar flush. El timing es irrelevante para el valor.

### Experimento #2 (Timing, posterior)
- **Objetivo**: Calibrar `source_wait_timeout` (argus 5s / suricata 10s / zeek 20s) con datos reales.
- **Método**: Pcaps controlados con ráfagas de inactividad artificiales para forzar flush de flujos en cada sensor.
- **Métrica**: Delta de `ts_emision_ns` entre sensores para el mismo flujo.
- **Nota**: Este experimento SÍ puede producir discrepancias de presencia (un sensor flusha antes que otro), pero eso es el hallazgo esperado, no un fallo.

**Veredicto**: #1 y #2 son experimentos ortogonales. No mezclar. Confirmado.

---

## 5. Resumen de acciones para DAY 172

1. **Implementar recogida de contadores de drop** en `community_id_crosscheck.py` (bloqueante, barato).
2. **Ejecutar replay #1** con criterio: cero anomalías de valor no clasificadas.
3. **Si aparece anomalía**: Clasificar en (a) bug, (b) drop, (c) evasión. Cero (a) y (c) para verde.
4. **Diferir experimento #2** (timing con ráfagas artificiales) a post-#1.

El cimiento del AdapterSpec §10 está listo para la prueba de fuego. A ejecutar.

— Consejo de Sabios, DAY 171, segunda ronda.

kimi