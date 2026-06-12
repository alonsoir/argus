# Síntesis — Deliberación del Consejo sobre ADR-051 v1

- **ADR:** ADR-051 — Seed Parity Gate & Correlation Health
- **Día:** DAY 173
- **Firmantes (8/8):** Claude, ChatGPT, DeepSeek, Gemini, Grok, Kimi, Mistral, Qwen
- **Veredicto global:** **APROBADO con condiciones.** Ningún sabio rechaza el ADR. Ninguno cuestiona el principio rector (data-plane > config) ni el fail-closed en arranque. Las objeciones son refinamientos, no vetos.

---

## 1. Consenso unánime — ratificable sin más debate

### 1.1 Las tres preguntas abiertas (§6 del borrador) están resueltas por unanimidad

| Pregunta | Resolución unánime | Disidencias |
|----------|--------------------|-------------|
| **1. Flujo-diana** | **Inyección sintética determinista** del flujo Neris-diana. | Ninguna. 8/8. |
| **2. Gate periódico BLOQUEANTE** | **NO.** Nadie quiere re-ejecutar un *gate bloqueante* en runtime. | Ninguna sobre el bloqueo. (Ver §2 para el matiz). |
| **3. Degradación en runtime** | **Degradar a N-1 con anotación explícita en el grafo.** Nunca apagón total, nunca silencioso. | Ninguna. 8/8. |

### 1.2 Principios técnicos validados por todos
- **Data-plane como única verdad** (se mide lo que el binario EMITE, no lo que declara el yaml). Confirmado por los 8.
- **`orphan_rate` PER-SENSOR**, no global. Confirmado por los 8 — "global es inaccionable" (Gemini, Grok, Kimi coinciden literalmente).
- **Wall-clock de aparición** para la distinción huérfano/pendiente, nunca timestamps internos. El hallazgo DAY 172 (spreads 9.7ms→116s) se acepta como justificación. Confirmado por los 8.
- **Diagnóstico por-sensor en el fallo del gate** (sensor / cid esperado / cid emitido) es parte de la *definición de listo*, no opcional. Kimi lo eleva a condición de cierre de DEBT-SEED-GATE-DIAGNOSTIC-001.
- **Prerequisitos honestos:** COUNTER-DUMP-001 (bloquea health-check de aRGus), TIMEOUT-CALIB-001 (umbral provisional), COVERAGE-MAP-001 (interpretabilidad). Los 8 respaldan el reorden de prioridad 2→3.

### 1.3 Verificación independiente del oráculo
Kimi recomputó el flujo-diana contra `pycommunityid` y **confirma** `1:IN7uqVpMWxpmuhQTowSQB2XEe0E=` (seed 0, TCP, ordenamiento canónico por tupla). El oráculo es sólido.

---

## 2. Único punto de divergencia real — la sonda activa periódica

Aquí está la **única** discrepancia sustantiva, y es reconciliable. Todos rechazan un *gate bloqueante* periódico. La pregunta residual es si se añade una **sonda activa NO bloqueante** que complemente al `orphan_rate` pasivo:

| Postura | Sabios | Argumento |
|---------|--------|-----------|
| **Solo arranque; `orphan_rate` cubre el drift** | Claude, ChatGPT, Gemini, Grok, Kimi (5) | El `orphan_rate` continuo ya detecta el drift post-arranque sobre tráfico real. Una sonda activa contamina el data-plane productivo. Dos mecanismos para la misma condición = deuda de diseño. |
| **Sonda activa no bloqueante periódica** | DeepSeek, Qwen (2) | Detecta drift por recarga en caliente *antes* de que el `orphan_rate` acumule evidencia. No bloquea: eleva alerta CRÍTICA y marca el sensor "no confiable". |
| **Configurable, off por defecto** | Mistral (1) | Solo en arranque por defecto; activable (p.ej. cada 6h) en entornos de alta criticidad. |

**Resolución propuesta (satisface a las tres posturas):** la sonda activa periódica **no entra en el núcleo** de ADR-051 v2 — el `orphan_rate` per-sensor es el mecanismo continuo primario. La sonda se registra como **DEBT diferida y opcional** (`DEBT-SEED-ACTIVE-PROBE-001`, P3), activable por configuración, sin contaminar producción por defecto. Así el campo "solo arranque" (5) tiene su núcleo limpio, y el campo "sonda" (2+1) tiene el mecanismo disponible cuando la operación demuestre que el `orphan_rate` reacciona demasiado lento.

> Nota de acoplamiento: la **reintegración automática** que propone DeepSeek ("reintegrar el sensor cuando recupere paridad, verificado por el gate periódico") depende de tener un disparador de recuperación. Si la sonda activa se difiere, la reintegración se dispara por (a) `orphan_rate` que vuelve por debajo del umbral, o (b) re-gate iniciado por el operador. Esto debe quedar escrito en v2.

---

## 3. Enmiendas convergentes a incorporar en v2

Todas estas son **aditivas** (refuerzan, no contradicen) y varias vienen propuestas por más de un sabio. Agrupadas por naturaleza:

### 3.1 Estructurales (cambian el texto/alcance del ADR)

- **[ADOPTAR] Renombrar el alcance del gate — ChatGPT.** El gate no valida solo el *seed*; valida que todos los sensores producen el **mismo `community_id`** para el mismo flujo. Con seed idéntico, la correlación puede romperse igual por: bug en plugin Zeek, cambio de versión de Suricata, normalización IPv6 distinta, implementación defectuosa. Propuesta: retitular a **"Community ID Parity Gate"**, manteniendo el *drift de seed* como la causa-raíz nombrada y más común, pero reconociendo la superficie de fallo más amplia. (El nombre de la DEBT `DEBT-CORRELATION-SEED-GATE-001` puede conservarse o ampliarse — decisión menor.)

- **[ADOPTAR] Batería mínima de vectores de referencia, no un único flujo — ChatGPT.** Un solo flujo TCP/IPv4 deja pasar bugs que solo aparecen en IPv6 o en canonicalización de dirección invertida. Batería mínima propuesta:
    - A: TCP IPv4 (`147.32.84.165:1027 → 74.125.232.195:80`) — la diana actual.
    - B: UDP IPv4 (p.ej. mDNS `…:5353 → 224.0.0.251:5353`).
    - C: TCP IPv6.
    - D: dirección invertida (A→B y B→A deben producir el MISMO community_id — verifica canonicidad).
    - *Sinergia:* esto ataca exactamente las aristas que `DEBT-FLOWUID-CANONICAL-ENCODING-001` (ADR-052) ya identificó como peligrosas (paridad C++/Python, caso 2-sensores). Conviene que la batería de vectores sea compartida entre ambas DEBTs.

- **[ADOPTAR] Oráculo en dos niveles + quórum — ChatGPT, Mistral.** Separar:
    - **Nivel 1 — paridad entre sensores:** ¿todos los sensores coinciden ENTRE SÍ?
    - **Nivel 2 — paridad con oráculo:** ¿coinciden con `pycommunityid`?
    - Si todos los sensores coinciden entre sí pero NO con el oráculo → no es drift de sensor, es problema del oráculo (bug o cambio de versión). Mistral propone una regla de quórum que emite alerta *"posible error en oráculo"* (no bloqueante). Versionar el oráculo (incluir su hash en el diagnóstico).

### 3.2 Diagnóstico enriquecido (§3.1 del ADR)

Convergencia fuerte en hacer el mensaje de fallo del gate más accionable. Adoptar el núcleo, marcar lo caro como opcional:

- **[ADOPTAR] Plantilla verbose — Grok.** `sensor / cid_esperado(oráculo) / cid_emitido / acción sugerida`.
- **[ADOPTAR] Hash SHA-256 del config cargado — Qwen.** Cierra el ciclo data-plane↔control-plane: el operador ve si el binario está ignorando el config o si el config fue alterado. (Es info de control-plane usada SOLO para diagnóstico, no como criterio del gate — coherente con el principio.)
- **[ADOPTAR] Seed del oráculo en el volcado — DeepSeek.** Imprimir el seed con que el oráculo generó el valor esperado, para comparar con el declarado de cada sensor.
- **[OPCIONAL/DIFERIR] Inferencia del seed efectivo por fuerza bruta — Mistral, Grok.** Útil pero potencialmente caro/frágil. Nice-to-have, no núcleo. → enhancement dentro de `DEBT-SEED-GATE-DIAGNOSTIC-001`.

### 3.3 Despliegue por fases (consecuencia práctica de los prerequisitos)

- **[ADOPTAR] Fase 1 vs Fase 2 — Gemini, DeepSeek, Qwen.** Dado que COUNTER-DUMP-001 bloquea el `orphan_rate` de aRGus:
    - **Fase 1 (inmediata):** desplegar el **Gate de arranque** completo + health-check en modo "degradado/pasivo" midiendo solo **Suricata y Zeek**.
    - **Fase 2:** incorporar aRGus al health-check cuando COUNTER-DUMP-001 cierre.
    - DeepSeek añade una métrica parcial provisional: flujos que Suricata+Zeek ven y que aRGus *debería* corroborar (según mapa de cobertura) y no aparecen en su log. Aproximación imperfecta pero da visibilidad temprana.

### 3.4 Inputs para B (DEBT-CORRELATION-TIMEOUT-CALIB-001) — no son de ADR-051, pero quedan registrados

Estos refinan la calibración, no el ADR. Se trasladan a B como requisitos de su diseño:

- **Qwen:** `Timeout = max_diferencia_ts_sensores + jitter_pipeline + margen_ε`. Ignorar el jitter interno (colas, GC, escritura Neo4j) generará falsos huérfanos bajo carga.
- **Gemini:** timeout como matriz dinámica indexada por protocolo/duración, no valor estático.
- **Mistral / DeepSeek:** umbrales por percentil (P95) / variación relativa, no absolutos.
- **Grok:** valor inicial conservador 120s para la ventana "pendiente" mientras B calibra.

### 3.5 Operacional / validación (DEBTs ligeras nuevas)

- **[ADOPTAR como DEBT] Regresión en CI — Grok.** `make crosscheck-up/run` obligatorio en CI para cualquier cambio que toque sensores o `community_id`. → `DEBT-CID-CROSSCHECK-CI-001` (P1).
- **[ADOPTAR como DEBT] Pruebas de caos — Mistral.** Forzar drift de seed en un sensor; verificar que (a) el gate falla en arranque, (b) `orphan_rate` sube en runtime, (c) la degradación N-1 funciona y anota. → `DEBT-SEED-CHAOS-TEST-001` (P2).
- **[ADOPTAR] Métrica secundaria `match_rate = 1 − orphan_rate` — ChatGPT.** Más intuitiva para dashboards/SLOs. Trivial, cosmética. Y `expected_orphan_rate` derivada del mapa de cobertura (Grok) cuando COVERAGE-MAP cierre.
- **[ADOPTAR] Umbrales de alerta desde día 1 — Grok.** Provisionales hasta calibración: `>5%` sostenido 5 min → warning; `>15%` → critical. Marcar como provisional (dependen de B).
- **[ADOPTAR] Sección "Cómo recuperar de un fallo de seed" — Grok.** Runbook breve con pasos concretos.

### 3.6 Cautela de inyección (refina la pregunta 1 ya resuelta)

- **[ADOPTAR] No contaminar el grafo de producción — DeepSeek, Qwen, Claude.** La inyección sintética debe: (a) ir al segmento que los N sensores observan (eth1/intnet), no a gestión, o un sensor legítimamente no la verá y el gate fallará por la razón equivocada (Claude); y (b) llevar marca identificable (Qwen propone SNI/User-Agent `ARGUS-SEED-PROBE`) para que el correlation-engine la descarte tras validar, o usar interfaz dedicada (DeepSeek). El flujo de referencia se inyecta una vez y se descarta antes de aceptar tráfico productivo (Kimi).

---

## 4. Recomendación de ruta

**No procede 3ª deliberación.** La convergencia es demasiado fuerte para justificarla:
- Las tres preguntas abiertas están resueltas 8/8.
- La única divergencia (sonda activa) se reconcilia sin contradicción haciéndola DEBT diferida opcional.
- Todas las demás aportaciones son aditivas y mutuamente compatibles.

**Ruta propuesta (precedente ADR-052 v3.2):**
1. Redactar **ADR-051 v2** incorporando §1 (consenso), §2 (resolución de la sonda como DEBT diferida), §3 (enmiendas adoptadas), con las opcionales/diferidas claramente marcadas como tales.
2. Circular v2 para **confirmación de fidelidad** (¿recoge v2 fielmente lo deliberado?), NO para re-deliberar el fondo — igual que ADR-052 v3.2 se ratificó 8/8 "sin 3ª deliberación".
3. Tras ratificación, **extraer el backlog** (§5).

El único elemento que *podría* sorprender a alguien es el renombrado a "Community ID Parity Gate" (cambia el título). Pero refuerza el argumento de ChatGPT que nadie discutió; es clarificación, no cambio de rumbo. La confirmación de fidelidad lo cubre.

---

## 5. Backlog preliminar (sale de v2 una vez ratificada)

DEBTs ya existentes que ADR-051 toca:
- `DEBT-CORRELATION-SEED-GATE-001` — el ADR es su especificación (cierra diseño).
- `DEBT-SEED-GATE-DIAGNOSTIC-001` (P1) — diagnóstico verbose + SHA-256 config + seed oráculo. (Inferencia de seed = enhancement opcional dentro.)
- `DEBT-ARGUSPP-COUNTER-DUMP-001` (P1) — prerequisito duro del health-check de aRGus (Fase 2).
- `DEBT-CORRELATION-TIMEOUT-CALIB-001` (P1, "B") — recibe los inputs de §3.4.
- `DEBT-SENSOR-COVERAGE-MAP-001` (P1) — prerequisito de interpretabilidad de `orphan_rate`.

DEBTs nuevas que generaría v2:
- `DEBT-CID-PARITY-VECTORS-001` (P1) — batería de vectores TCP/UDP/IPv6/invertido, compartida con `DEBT-FLOWUID-CANONICAL-ENCODING-001`.
- `DEBT-CID-ORACLE-QUORUM-001` (P2) — oráculo dos niveles + quórum + versionado del oráculo.
- `DEBT-CID-CROSSCHECK-CI-001` (P1) — `crosscheck-up/run` como gate de CI.
- `DEBT-SEED-CHAOS-TEST-001` (P2) — prueba de caos de drift.
- `DEBT-SEED-ACTIVE-PROBE-001` (P3, DIFERIDA/OPCIONAL) — sonda activa no bloqueante configurable.

---

*Documento de síntesis para circulación al Consejo. Las posturas individuales se conservan en los ficheros `ADR-051_v1_*_<MODELO>.md`.*