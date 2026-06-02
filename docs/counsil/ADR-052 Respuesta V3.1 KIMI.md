# Dictamen del Consejo — ADR-052 v3.1 (Confirmación de fidelidad y ratificación)

## Resumen ejecutivo

La v3.1 es **fiel a las deliberaciones de la 2ª pasada** y corrige las cuatro objeciones residuales de la v3 con precisión quirúrgica. Las auto-correcciones C1–C4 (eliminación de `deployment_epoch`, acotación honesta del TLS, separación confianza/peso de de-duplicación, especificación de la hash-chain del WAL) son **mejoras de calidad que no alteran la dirección arquitectónica** acordada por el Consejo. El documento está completo (secciones 5–10 presentes), el esquema de deudas es coherente, y la validación EMECAS++ cubre los casos de borde.

No se detectan grietas estructurales nuevas. Hay **una nota de higiene de seguridad** (no bloqueante) sobre la firma del inventario de `node_id`.

**Veredicto: RATIFICAR v3.1.**

---

## 1. Confirmación de fidelidad respecto a la 2ª pasada

| Punto del Consejo (2ª pasada) | Estado en v3.1 | Evaluación |
|---|---|---|
| Codificación canónica `flow_uid` con libsodium congelada (N5) | §3.1.1: BLAKE2b vía `crypto_generichash`, paridad cross-impl + misma versión libsodium | ✅ Fiel |
| `node_id` estable, no anclado a keypair efímero (N1) | §3.1.2: string legible declarado en inventario firmado, sin `deployment_epoch` (C1) | ✅ Fiel y mejorado |
| `seq_in_window` transportado, no recomputado (N2) | §3.1.4 pto 3: campo Protobuf, input del test de paridad | ✅ Fiel |
| `sensor_native_flow_id` no componente del hash (N3) | §3.1.4 pto 4: propiedad de trazabilidad obligatoria | ✅ Fiel |
| WAL externo append-only con hash-chain (N4) | §3.7: `prev_hash = H(entrada_{i-1})`, verificación periódica, divergencia grafo↔WAL | ✅ Fiel y especificado |
| Cardinalidad exacta para etiqueta `rate_limited` (N6) | §3.10: exacta en motor, HLL solo métricas | ✅ Fiel |
| Event time con watermark (N7) | §3.2.2: tolerancia de skew sobre timestamps originales | ✅ Fiel |
| Calibración por protocolo (arbitraje 6) | §3.1.4 pto 5: TCP/UDP separados, tests dedicados | ✅ Fiel |
| TCP/TLS en ADR-052 (arbitraje 7, anulación) | §3.11: TCP ligero entra; TLS acotado a destinos gestionados (C2) | ✅ Fiel al árbitro, honesto en coste |
| Mapa de cobertura como cache declarativa (Q2) | §3.8: tabla/cache, fuente orquestador, versionada | ✅ Fiel |
| Confianza como features primitivas (Q3/Q4) | §3.6: separación confianza-por-corroboración / peso-de-duplicación (C3) | ✅ Fiel y refinado |
| `provenance` ortogonal a `acceptance_criteria` (Q5) | §3.7: eje separado, no se toca enum congelado | ✅ Fiel |
| Límite fundamental vector A con host comprometido (Q6) | §3.4.1: documentado + DEBT out-of-band | ✅ Fiel |

---

## 2. Evaluación de las auto-correcciones v3 → v3.1

### C1 — Eliminación de `deployment_epoch` del `node_id`
**Evaluación: Correcta.** El `deployment_epoch` en v3 reintroducía, en miniatura, el mismo footgun que N1 resolvió: un componente mutable en la identidad de corpus. La v3.1 lo elimina y usa un string legible declarado (`argus-sensor-gw-lan-01`). Esto hace el grafo auditable en forense del corpus (un investigador humano lee el `node_id` sin descifrar nada) y simplifica la operación de reemplazo de hardware con mismo rol (mismo `node_id`, continuidad del corpus). La firma del evento sigue siendo la prueba criptográfica de autenticidad.

### C2 — Acotación honesta del TLS mismatch
**Evaluación: Correcta.** La v3 presentaba el TLS mismatch como una señal "ligera", pero presupone un *cert-expectation store* que es infraestructura compleja. La v3.1 acota la señal a **destinos gestionados con expectativa declarada** (donde el `esperado` es conocido y mantenible) y abre `DEBT-CERT-EXPECTATION-STORE-001` para el caso general. Esto es honestidad científica: no prometemos una señal que depende de infraestructura inexistente.

### C3 — Separación confianza vs. peso de de-duplicación
**Evaluación: Correcta.** La v3 conflaba ambas cantidades bajo un "score IPW". La v3.1 las separa:
- **Confianza por corroboración** (sube con `witness_count`): feature para el modelo.
- **Peso de de-duplicación** (baja con `witness_count`): para el sampler, evita triple-conteo de la misma muestra física.
- Ambas derivan de `witness_count` pero en direcciones opuestas y para fines distintos.
- ADR-040 retiene la propiedad del modelo de propensión IPW; ADR-052 solo expone primitivas.

### C4 — Especificación de la hash-chain del WAL
**Evaluación: Correcta.** La v3 mencionaba un WAL con hash-chain pero no detallaba la estructura. La v3.1 especifica:
- `prev_hash = H(entrada_{i-1})` encadenado.
- Verificación periódica de la cadena (job + arranque).
- Dos detecciones independientes: (a) manipulación WAL → cadena rota; (b) manipulación Neo4j → divergencia grafo↔WAL.
- Esto es una arquitectura de no-repudio operacionalmente viable.

---

## 3. Nota de higiene de seguridad (no bloqueante)

**Tema:** El `node_id` es ahora un **string legible declarado** (ej. `argus-sensor-gw-lan-01`), no un hash criptográfico. Esto es correcto para la identidad de corpus (auditable, estable), pero introduce una superficie de ataque menor: un atacante que comprometa el **orquestador** o el **inventario de endpoints** podría inyectar un `node_id` falso (`argus-sensor-gw-lan-99`) que pasaría la validación de inventario si la firma del inventario misma está comprometida.

**Mitigación ya presente:** La tríada de suficiencia (§3.1.2) requiere que el evento esté firmado por la clave Ed25519/Noise del sensor (ADR-027). Un `node_id` falso sin la clave correspondiente no produce eventos firmados válidos. Por tanto, el riesgo queda contenido por la capa criptográfica de autenticación, separada de la identidad de corpus.

**Recomendación:** Añadir una nota en §3.1.2 aclarando que la integridad del `node_id` como identidad de corpus depende de la **protección del inventario firmado** (fuente de verdad del orquestador), y que la autenticidad de los eventos que fluyen *bajo* ese `node_id` depende de la clave del sensor (ADR-027). Son dos líneas de defensa distintas.

---

## 4. Respuesta a la pregunta de confirmación de fidelidad (§6)

> ¿Refleja la v3 fielmente el consenso de la 2ª pasada y deja claras las dos anulaciones de árbitro (función de hash anclada a libsodium §3.1.1; TCP/TLS dentro del ADR §3.11)?

**SÍ. La v3.1 refleja fielmente el consenso del Consejo en la 2ª pasada y deja ambas anulaciones de árbitro explícitas y razonadas:**

1. **N5 (libsodium):** §3.1.1 enuncia el invariante de proyecto: "La función de hash es la que provea la versión congelada de libsodium del pipeline". Esto ancla la elección a la disciplina de stack, no a un debate de algoritmo. La nota sobre SHA3-256 descartado por no estar en libsodium es honesta.

2. **Q7/TCP-TLS en ADR-052:** §3.11 declara explícitamente "ANULACIÓN DE ÁRBITRO" y justifica por qué el threat model y su detección deben viajar juntos. La corrección C2 (acotación del TLS) demuestra que la anulación no fue a ciegas: se asumió el coste consciente y se delimitó el alcance para evitar el rabbit-hole que el Consejo temía.

---

## 5. Tareas de cierre post-ratificación (backlog)

| ID | Tarea | Prioridad | Dueño |
|---|---|---|---|
| **ADR-052-POST-A1** | Implementar `node_id` como string declarado en inventario firmado (ADR-046 §3.9) | P0 | Infra |
| **ADR-052-POST-A2** | Test de paridad `flow_uid` C++/Python + misma libsodium + caso dos-sensores | P0 | QA |
| **ADR-052-POST-A3** | Test de estabilidad: `flow_uid` idéntico antes/después de `vagrant destroy+up` | P0 | QA |
| **ADR-052-POST-A4** | Implementar WAL de etiquetado con hash-chain (`prev_hash`) + verificación periódica | P1 | Backend/ADR-048 |
| **ADR-052-POST-A5** | Implementar cardinalidad exacta en correlation-engine + meta-nodo `:GraphFloodingAnomaly` | P1 | Backend |
| **ADR-052-POST-A6** | Implementar mapa de cobertura (tabla/cache) con fuente en orquestador + beacons | P1 | Infra |
| **ADR-052-POST-A7** | Calibrar `N_TCP` y `N_UDP` sobre golden pcap (tests dedicados) | P1 | Data/ML |
| **ADR-052-POST-A8** | Implementar `seq_in_window` persistente en sensor (WAL local) | P2 | Sensor/C++ |
| **ADR-052-POST-A9** | Implementar `:HostAnomaly` para TCP (RST/seqnum) + deuda TLS gestionado | P2 | Backend |
| **ADR-052-POST-A10** | Crear `DEBT-CERT-EXPECTATION-STORE-001` (infraestructura) | P2 | Arquitectura |
| **ADR-052-POST-A11** | Crear stub ADR-053 (JA3/JA4, BGP, traceroute) | P2 | Arquitectura |
| **ADR-052-POST-A12** | Implementar KPIs de calidad de corpus (§0.1) | P2 | Data/ML |

---

## 6. Veredicto final

**Estado recomendado:** `RATIFICAR v3.1`.

**Condiciones de cierre:**
1. Añadir la nota de higiene de seguridad sobre la protección del inventario firmado (§3.1.2, sugerencia §3 arriba).
2. Vincular las tareas POST-A1–A12 al backlog del proyecto.
3. Una vez ratificado, desbloquear:
    - `DEBT-NEO4J-FLOW-KEY-001` (P0 esquema)
    - `DEBT-FLOWUID-CANONICAL-ENCODING-001` (P0)
    - `DEBT-NODEID-CRYPTO-IDENTITY-001` (P0, reescrita)
    - `DEBT-LABEL-WAL-001` (P1)
    - `DEBT-SENSOR-COVERAGE-MAP-001` (P1)
    - `DEBT-ARGUSPP-ARP-MONITOR-001` (P1)
    - `DEBT-ARGUSPP-HOST-TCP-001` (P1)

**Evaluación:** ADR-052 v3.1 es un documento de arquitectura **estratégicamente correcto, técnicamente maduro y fielmente deliberado**. La dirección —corpus como producto, identidad compuesta reproducible, defensa arquitectónica, hash no como control de seguridad, etiquetado ortogonal con no-repudio— es la correcta para un sistema de ML adversarial sobre grafos distribuidos bajo amenaza hostil. El Consejo de Sabios confirma su fidelidad y recomienda la ratificación.

---

*Dictamen de confirmación de fidelidad y ratificación emitido por Kimi (Consejo de Sabios), DAY 173, revisión v3.1.*

FDO

KIMI