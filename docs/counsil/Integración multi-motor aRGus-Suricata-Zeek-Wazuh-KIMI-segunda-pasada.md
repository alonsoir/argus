# Respuesta del Consejo de Sabios — Kimi (Moonshot AI)
**Pasada 2 — Ratificación de Mociones M1–M4 y posición sobre D5**

**Proyecto:** aRGus NDR (arXiv:2604.04952)  
**Sesión:** DAY 169 — Viernes 29 de mayo de 2026  
**Miembro:** Kimi (Moonshot AI)

---

He revisado las mociones de la Pasada 2. Mi posición en la Pasada 1 ya anticipaba varios de estos cierres; ahora ratifico con los matices que la deliberación intermedia ha afinado.

---

## M1 (D1) — Timestamp canónico: **RATIFICO**

La resolución de Claude es correcta y completa. El tiempo de **ocurrencia** debe gobernar el *windowing*; la emisión y la ingesta son métricas operativas, no dimensiones de correlación.

**Matiz técnico sobre el "steelman" de Qwen:** es cierto que para FIM/syscheck el tiempo de ocurrencia es una aproximación (el *mtime* del fichero vs. el *scan_time* del agente). Sin embargo, usar el tiempo de emisión no resuelve este problema — empeora la situación porque añade latencia variable del pipeline Wazuh (que depende de la carga del manager, de la cola de analisisd, y del intervalo de syscheck). La incertidumbre de FIM ya está absorbida por diseño en el `bridge_window` host↔flujo (15–30 s), que es precisamente el mecanismo correcto para eventos de host con cuantización temporal imprecisa.

**Propuesta adicional:** para eventos Wazuh donde el timestamp nativo sea ambiguo (FIM, rootcheck), el adapter Wazuh debe aplicar una **heurística de estabilización**: usar el campo `timestamp` del alerta Wazuh (que es el momento de generación de la alerta, no de escaneo) como `event_time_unix_ns`, pero documentar en `metadata` tanto `scan_time` como `file_mtime` cuando estén disponibles. Esto preserva el invariante de que `event_time_unix_ns` es siempre el "mejor timestamp disponible de la fuente", sin forzar al engine a interpretar semánticas motor-específicas.

**Ratificación:** sí, ocurrencia para windowing, emisión/ingesta a metadatos.

---

## M2 (D2) — Política de evicción: **RATIFICO con matiz de implementación**

La síntesis de tres capas es superior a mi propuesta original de LRU puro + protección caliente. La **cuota anti-pinning** (Capa 3) es el elemento que faltaba y que neutraliza el vector de DoS que identifiqué en mi Pasada 1.

**Matiz de implementación sobre la Capa 3:**

La cuota debe aplicarse sobre el **anclaje estructural** de la crisis, no sobre el `source_ip` en bruto. Una crisis anclada a un flujo `community_id` tiene dos IPs; la cuota debe contar contra la IP que actúa como **origen externo** (no gestionado). Si una crisis tiene múltiples flujos con múltiples orígenes externos, cada origen externo consume su propia cuota.

**Detalle algorítmico propuesto:**
```
cuota_consumida[source_ip_externo] = count(crisis_abiertas WHERE anchor_ip_externo == source_ip)
if cuota_consumida[source_ip] > MAX_OPEN_CRISES * Q:
    nueva_crisis_de_este_origen → eviction_first = true
```

Esto es más preciso que una cuota por `/24` (que podría agrupar orígenes legítimos distintos) y evita que un atacante con múltiples IPs en el mismo /24 evada la cuota.

**Sobre la demostración EMECAS++:** el test de escenario de pinning (un origen externo generando N crisis de severidad alta) debe verificar no solo que la memoria se mantiene acotada, sino que las crisis de **host interno gestionado** (la víctima) sobreviven incluso cuando el atacante agota su cuota. Esto prueba que la asimetría interno/externo de R2 se hereda correctamente en la política de evicción.

**Ratificación:** sí a las tres capas, con la precisión de que la cuota anti-pinning opera por `source_ip_externo_no_gestionado` individual, no por bloque CIDR.

---

## M3 (D3) — Transporte de adapters: **RATIFICO**

El reencuadre por tramos disuelve el conflicto artificial. Mi propuesta de ZeroMQ PUB/SUB para el tramo interno ya es arquitectura del proyecto (ADR-026/027); lo que variaba era el tramo externo, y la resolución por tier-y-motor es la única que respeta tanto la reproducibilidad (tier determinista necesita fichero/replay) como la resiliencia operativa (tier vivo necesita push o tail durable).

**Matiz sobre `AdapterSpec v1`:** el spec debe exigir que todo adapter, sea push o tail, exponga un **checkpoint monotónico** que el engine pueda consultar para *replay* controlado. En ZeroMQ interno, esto se mapea al patrón `XPUB/XSUB` con *sequence numbers* en el envelope; en tail-durable, es el offset en fichero; en push nativo (Kafka/Redis), es el *offset de topic/partition*. La monotonicidad del checkpoint permite que el engine, ante un restart, solicite al adapter "reanuda desde checkpoint X" sin pérdida ni duplicación (la dedup por `(source_engine, native_event_id)` actúa como cinturón-y-tirantes).

**Ratificación:** sí a `AdapterSpec v1` + tabla por-tier, con checkpoint monotónico como requisito del spec.

---

## M4 (D4) — Predicado de "fuente esperada": **RATIFICO ambas partes**

**M4.a — Separar ventanas:** ADOPTAR sin reservas. La distinción `correlation_window` vs. `late_arrival_window` es limpia y evita el problema de INQ-3 (crisis de flujo puras esperando 90s por Wazuh). La crisis se cierra cuando:
- todas las fuentes **armadas** han reportado dentro de `correlation_window`, **O**
- `crisis_idle_timeout` vence sin actividad.

Un evento rezagado que llega dentro de `late_arrival_window` se adjunta a la crisis ya cerrada (posiblemente generando una actualización/reenvio), pero **no** reabre la espera. Esto es esencial para la estabilidad del estado.

**M4.b — Rechazar condición "regla Wazuh cubre proto/puerto":** RATIFICO el rechazo. La preocupación de Qwen es legítima pero la solución propuesta (acoplar al ruleset) es peor que el problema. El acoplamiento ruleset-engine introduce una dependencia de configuración que es imposible de mantener consistente: las reglas Wazuh cambian por actualizaciones de vulnerabilidades, por tuning operativo, y por personalización del entorno. El engine no puede asumir conocimiento de ese estado.

La mitigación correcta ya está en la arquitectura: el *predicado* de armado de Wazuh es "host gestionado + dentro de `bridge_window`" (R3 + R10), y la *semántica de cierre* es M4.a (ventanas acotadas). El coste de una expectativa muerta es, como máximo, `correlation_window` (que puede ser mucho menor que los 90s de `source_wait_timeout` si la crisis no involucra host gestionado). Esto es aceptable.

**Ratificación:** sí a M4.a y M4.b.

---

## D5 (Q9) — Corpus vs pipeline como entregable del 22-sep: **REAFIRMO corpus-first**

Mi posición en la Pasada 1 fue: **corpus etiquetado reproducible como entregable mínimo viable, pipeline vivo como demostración operativa**. Reafirmo esto con un argumento adicional de *verificabilidad científica*.

El Dr. Caro Lindo evalúa un sistema de detección. La evidencia que puede auditar, revisar por pares, y reproducir es el **corpus**: pcap fijo + JSON de crisis esperadas + script de validación determinista. Un pipeline vivo es una demostración de *viabilidad de integración*, no de *correctitud de correlación*. Si el pipeline falla en la demo por un race condition en el adapter, no demuestra nada sobre la arquitectura; si el corpus pasa, demuestra que la lógica de correlación es correcta.

**Propuesta de compromiso para Grok:** el pipeline vivo es **entregable complementario** (Fase 6), no duro. Se graba una ejecución del pipeline procesando tráfico en vivo (nmap/hydra) como **artefacto de demostración** (video/logs), pero las aserciones de correctitud funcionan contra el corpus. Esto da a Alonso ambas cosas: reproducibilidad científica (corpus) y evidencia de funcionamiento en condiciones reales (pipeline grabado).

**Ratificación:** corpus-first; pipeline vivo como demo complementaria, no como entregable duro de correctitud.

---

## Estado de mi voto tras Pasada 2

| Moción | Voto Kimi |
|--------|-----------|
| M1 (timestamp canónico) | **Ratifico** (ocurrencia + emisión/ingesta a metadata) |
| M2 (evicción 3 capas) | **Ratifico** (con cuota por IP externa individual, no /24) |
| M3 (transporte por tramos) | **Ratifico** (AdapterSpec v1 + checkpoint monotónico) |
| M4.a (separar ventanas) | **Ratifico** |
| M4.b (rechazar regla-Wazuh) | **Ratifico** |
| D5 (corpus vs pipeline) | **Corpus-first**, pipeline demo complementaria |

Las cinco discrepancias abiertas están cerradas desde mi posición. Queda pendiente la confirmación de Qwen en M1/M4.b, y la decisión de Alonso en D5 para desbloquear el ordenamiento de fases.

En paralelo, R1–R10 pueden comenzar a materializarse en `network_security.proto` y en el borrador de **ADR-046 v4**.

— Kimi (Moonshot AI), Consejo de Sabios.