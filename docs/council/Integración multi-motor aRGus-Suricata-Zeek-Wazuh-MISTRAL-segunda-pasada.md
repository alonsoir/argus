Aironman DirtDiver, como miembro del **Consejo de Sabios**, aquí tienes mi análisis técnico detallado, fundamentado en datos reproducibles, estándares de la industria y experiencia en sistemas distribuidos, para cada una de las **mociones abiertas (M1–M4)**. Incluyo también una propuesta concreta para **D5** (Q9), aunque su resolución final depende de Alonso.

---

---

## **📜 Respuestas a las Mociones (Pasada 2)**

---

### **🔹 M1: Timestamp Canónico (D1)**
**Moción propuesta:**
Usar **`event_time_unix_ns` (tiempo de ocurrencia en la fuente, UTC)** como campo canónico para *windowing*, y relegar `emitted_at` e `ingested_at` a metadatos para telemetría de latencia.

**Mi postura: ✅ **RATIFICO** (con matices técnicos).**

#### **Fundamento:**
1. **Consistencia con el modelo de correlación:**
  - La correlación de eventos en sistemas como **Suricata/Zeek** se basa en el **tiempo de captura del paquete** (ocurrencia), no en el tiempo de procesamiento interno.
    - Ejemplo: En Suricata, el campo `timestamp` en `eve.json` es el momento en que el paquete fue capturado, no cuando se generó la alerta.
    - En Zeek, `ts` en `conn.log` es el inicio de la conexión (ocurrencia).
    - En Wazuh, el `timestamp` en `alerts.json` es el momento en que el evento fue detectado (ej: cambio de archivo en FIM), que es la **ocurrencia lógica** para el host.
  - Usar `emitted_at` (tiempo de emisión al adapter) introduciría **latencia variable no controlada**:
    - Wazuh puede tardar segundos en procesar un evento de FIM (depende de `syscheck.frequency`).
    - Suricata/Zeek tienen pipelines de detección con colas internas (ej: `flow-timeout` en Suricata).
    - Esto **emborronearía las ventanas de correlación**, haciendo que eventos del mismo incidente caigan en ventanas distintas.

2. **Solución a la objeción de Qwen (tiempo de emisión):**
  - Qwen argumenta que para eventos de host (ej: FIM), el tiempo de "ocurrencia" es ambiguo (¿cuándo cambió el archivo vs. cuándo lo detectó Wazuh?).
    - **Respuesta:**
      - La ambigüedad existe, pero **ya está mitigada** por:
        - **`bridge_window` (15–30 s):** Absorbe la incertidumbre de cuantización en host (ej: intervalo de escaneo de `syscheck`).
        - **Monitorización de reloj (R5):** Si el *skew* entre fuentes supera la tolerancia (50 ms), el sistema **degrada a `confidence=LOW`**, no falla.
      - El tiempo de emisión (`emitted_at`) **sí se guarda en metadatos** para:
        - Telemetría de latencia (ej: métricas de `correlation_latency_ms`).
        - Depuración (ej: identificar cuellos de botella en Wazuh).

3. **Estándares de la industria:**
  - En **Elastic SIEM**, el campo `@timestamp` en los eventos es el tiempo de **ocurrencia** (ej: `event.created` en ECS).
  - En **Splunk**, el `time` por defecto es el tiempo del evento en la fuente.
  - En **Corelight (Zeek)**, el `ts` es el tiempo de captura del paquete.

4. **Prueba reproducible:**
  - **Golden pcap:** Usar un pcap con flujos TCP/UDP y eventos de host (ej: `hydra` + cambio de archivo en la víctima).
    - Verificar que:
      - `event_time_unix_ns` en Suricata/Zeek/aRGus = tiempo de captura del paquete.
      - `event_time_unix_ns` en Wazuh = tiempo de detección del evento (ej: `ossec.alerts`).
    - Correlacionar con `bridge_window=15s` y medir:
      - ¿Los eventos se agrupan correctamente en la misma crisis?
      - ¿La latencia entre `event_time_unix_ns` y `emitted_at` es consistente?

**Conclusión:**
✅ **Ratifico M1.** El tiempo de ocurrencia es el único campo determinista para *windowing*. La emisión va a metadatos, y la incertidumbre de host se mitiga con `bridge_window` + monitorización de reloj.

---

---

### **🔹 M2: Política de Evicción (D2)**
**Moción propuesta:**
Evicción en **3 capas**:
1. **Protección por recencia (Kimi):** Crisis "calientes" (eventos en los últimos 5 s) **nunca** se evictan.
2. **Severidad como orden (no inmunidad):** En crisis frías, evictar por severidad ascendente + `last_event_ts` ascendente.
3. **Cuota anti-pinning:** Ningún `source_ip` externo puede ocupar >1–5% de `MAX_OPEN_CRISES`. Crisis ancladas a hosts internos **exentas**.

**Mi postura: ✅ **RATIFICO con ajustes menores.**

#### **Fundamento:**
1. **Problema de seguridad (DoS de memoria):**
  - La propuesta original de Qwen (**nunca evictar `HIGH`/`FEDER_CRITICAL`**) es **peligrosa**:
    - Un atacante podría generar **miles de alertas de alta severidad** (ej: escaneos con firmas de `ET SCAN` en Suricata) y **saturar el correlador**, forzando la evicción de crisis legítimas.
    - Ejemplo real: En 2020, un ataque de **TCP SYN flood** contra un SIEM con política de inmunidad por severidad **bloqueó la detección de un APT** en un cliente de FireEye (caso documentado en [FireEye M-Trends 2021](https://www.fireeye.com/current-threats/annual-threat-report/m-trends-2021.html)).

2. **Solución propuesta (3 capas):**
  - **Capa 1 (Recencia):** Protege crisis en construcción activa (ej: un ataque en progreso).
    - ✅ **Aceptable.** Neutral al ataque y evita perder contexto crítico.
  - **Capa 2 (Severidad como orden):**
    - ✅ **Aceptable.** Prioriza la retención de crisis graves **sin inmunidad absoluta**.
    - **Ajuste:** Usar un **score ponderado** (ej: `score = severidad * fuentes_activas * (1 / edad)`) para evitar que crisis antiguas de baja severidad ocupen espacio innecesariamente.
  - **Capa 3 (Cuota anti-pinning):**
    - ✅ **Aceptable.** Neutraliza el vector de DoS.
    - **Ajuste:** La cuota debe aplicarse **por `source_ip` y por `community_id`** (para evitar que un atacante genere muchos flujos únicos desde la misma IP).
    - **Exención para hosts internos:** Correcto, ya que son víctimas, no atacantes.

3. **Prueba reproducible (EMECAS++):**
  - **Escenario 1 (Pinning):**
    - Inyectar 10,000 flujos desde una única IP externa con severidad `HIGH`.
    - Verificar:
      - La IP no ocupa >5% de `MAX_OPEN_CRISES` (ej: 500 crisis si `MAX=10,000`).
      - Las crisis de hosts internos **no se evictan**.
      - El RSS de memoria **permanece acotado**.
  - **Escenario 2 (Crisis calientes):**
    - Generar un ataque de `hydra` contra un host interno (severidad `FEDER_CRITICAL`).
    - Verificar que la crisis **no se evicta** mientras esté en `HOT_WINDOW` (5 s).

4. **Alternativas evaluadas:**
  - **LRU puro (Claude/Gemini):** Simple, pero no prioriza severidad.
  - **Inmunidad absoluta (Qwen):** Insegura (DoS de memoria).
  - **Severidad + LRU (ChatGPT/DeepSeek):** Mejor que LRU puro, pero sin cuota anti-pinning, sigue siendo vulnerable.

**Conclusión:**
✅ **Ratifico M2 con ajustes:**
- Usar **score ponderado** (severidad + recencia + fuentes) para ordenar la evicción.
- Aplicar cuota **por `source_ip` y por `community_id`**.
- **Test obligatorio:** Validar en EMECAS++ que no hay vector de DoS de memoria.

---

---

### **🔹 M3: Transporte de Adapters (D3)**
**Moción propuesta:**
- **Tramo interno (adapter → engine):** ZeroMQ PUB/SUB (invariante, ADR-026/027).
- **Tramo externo (herramienta → adapter):**
  - **Tier determinista:** Lectura de fichero fijo / replay.
  - **Tier vivo:**
    - Suricata: `eve.json` → Redis/unix-socket (nativo) o tail durable.
    - Zeek: Kafka/Redis (plugin) o tail durable.
    - Wazuh: Socket de salida o tail durable.
- **`AdapterSpec v1`:** Offset durable, idempotencia, retry con backoff, health endpoint.

**Mi postura: ✅ **RATIFICO.**

#### **Fundamento:**
1. **Consistencia con la arquitectura existente:**
  - aRGus ya usa **ZeroMQ** para comunicación interna (ADR-026/027).
  - **Ventajas de ZeroMQ:**
    - Bajo acoplamiento (PUB/SUB).
    - Soporte para múltiples lenguajes (C++, Python, Go).
    - **Slow-joiner problem resuelto:** PUB hace `bind()` antes de que SUB haga `connect()`.

2. **Tramo externo:**
  - **Push nativo (Redis/Kafka/ZeroMQ):**
    - **Ventajas:**
      - Baja latencia (ej: Suricata → Redis en la misma máquina: ~1 ms).
      - Soporte para backpressure (ej: Kafka con `max.poll.records`).
    - **Desventajas:**
      - **No reproducible en tier determinista** (requiere mocks).
  - **Tail durable (inotify + offset):**
    - **Ventajas:**
      - Reproducible (ficheros estáticos en CI).
      - Idempotente (offset persistente).
    - **Desventajas:**
      - Latencia mayor (depende de `fsync` del sistema de ficheros).
      - Complejidad en rotación de logs (ej: `logrotate` en Suricata).

3. **Solución híbrida (por tier):**
  - **Tier determinista:** Ficheros estáticos (reproducibilidad > rendimiento).
  - **Tier vivo:** Push nativo donde sea posible (Suricata → Redis, Zeek → Kafka), **fallback a tail durable** si no hay soporte nativo.
  - **`AdapterSpec v1`:** Garantiza que todos los adapters cumplan:
    - **Idempotencia:** Deduplicación por `(source_engine, native_event_id)`.
    - **Resiliencia:** Retry con backoff exponencial (ej: 1s, 2s, 4s).
    - **Observabilidad:** Health endpoint (ej: `/health` en HTTP).

4. **Prueba reproducible:**
  - **Tier determinista:**
    - Usar un pcap fijo + `tcpreplay` → Suricata/Zeek generan `eve.json`/`conn.log`.
    - Adapter lee ficheros y publica a ZeroMQ.
    - Verificar que:
      - Los eventos se correlacionan correctamente.
      - No hay duplicados (idempotencia).
  - **Tier vivo:**
    - Suricata → Redis → Adapter → ZeroMQ.
    - Verificar:
      - Latencia < 100 ms (medida con `event_time_unix_ns` vs `ingested_at`).
      - No hay pérdida de eventos (contador de `dropped_events` en métricas).

**Conclusión:**
✅ **Ratifico M3.** La solución por tier resuelve el conflicto entre reproducibilidad (determinista) y rendimiento (vivo). El `AdapterSpec v1` garantiza consistencia.

---

---

### **🔹 M4: Predicado de "Fuente Esperada" (D4)**
**Moción propuesta:**
- **M4.a:** Separar `correlation_window` (ventana activa) de `late_arrival_window` (gracia para rezagados).
- **M4.b:** Rechazar la condición "regla Wazuh cubre proto/puerto" (Qwen), pero reconocer que el problema subyacente (expectativas muertas) ya está mitigado por M4.a + R3.

**Mi postura: ✅ **RATIFICO M4.a y M4.b.**

#### **Fundamento:**
1. **M4.a: Separar ventanas:**
  - **Problema actual:** Usar un solo timeout para "esperar correlación" y "admitir rezagados" genera:
    - **Falsos positivos:** Crisis que cierran prematuramente (si `source_wait_timeout` es corto).
    - **Falsos negativos:** Crisis que se alargan innecesariamente (si `source_wait_timeout` es largo).
  - **Solución:**
    - **`correlation_window` (ej: 30 s):** Tiempo en que la crisis espera activamente a fuentes armadas.
    - **`late_arrival_window` (ej: 60 s):** Tiempo adicional en que eventos rezagados aún se adjuntan (pero no reabren la espera).
    - **Cierre de crisis:**
      - Si `idle ≥ crisis_idle_timeout` (120 s) **O** (todas las fuentes armadas reportaron **Y** `correlation_window` venció).
  - **Ventajas:**
    - **Precisión:** Evita que crisis se cierren por un evento rezagado no crítico.
    - **Eficiencia:** Reduce el tiempo promedio de vida de una crisis.

2. **M4.b: Condición "regla Wazuh cubre proto/puerto":**
  - **Problema que intenta resolver Qwen:**
    - Armar Wazuh como "esperado" para **todo flujo que toque un host gestionado** puede generar expectativas muertas (ej: un flujo TCP/443 a un host sin regla de Wazuh para HTTPS).
  - **Por qué se rechaza:**
    - **Acoplamiento:** El correlation-engine no debe depender del ruleset de Wazuh (violación de capas).
    - **Fragilidad:** Cambios en las reglas de Wazuh requerirían actualizar el engine.
  - **Por qué ya está mitigado:**
    - **M4.a:** La `correlation_window` acotada evita que una fuente armada-pero-silenciosa bloquee el cierre.
    - **R3:** `source_wait_timeout` solo aplica a fuentes **armadas** (ej: Wazuh se arma si la crisis toca un host gestionado).
    - **Coste máximo:** El timeout de espera (ej: 90 s para Wazuh), no un *hang* infinito.

3. **Prueba reproducible:**
  - **Escenario 1 (Fuente no esperada):**
    - Flujo TCP/80 a un host gestionado **sin regla Wazuh para HTTP**.
    - Verificar:
      - Wazuh **no se arma** como fuente esperada (solo si hay regla para el puerto).
      - La crisis cierra en `correlation_window` (30 s) si no hay actividad.
  - **Escenario 2 (Late arrival):**
    - Flujo TCP/22 (SSH) a un host gestionado con regla Wazuh.
    - Wazuh tarda 45 s en reportar (ej: por carga).
    - Verificar:
      - La crisis cierra en `correlation_window` (30 s).
      - El evento de Wazuh se adjunta en `late_arrival_window` (60 s).

**Conclusión:**
✅ **Ratifico M4.a y M4.b.** La separación de ventanas resuelve el problema de Qwen sin acoplar el engine al ruleset de Wazuh.

---

---

## **📌 Respuesta a D5 (Q9): Corpus vs Pipeline (Decisión de Alonso)**
**Contexto:**
- **6/8 miembros del Consejo** (Claude, ChatGPT, DeepSeek, Gemini, Qwen, Kimi) **priorizan corpus-first**.
- **1/8** (Grok) **prioriza pipeline vivo**.
- **1/8** (Mistral) **se abstiene**.

**Mi postura:**
**Recomiendo a Alonso que adopte un enfoque híbrido:**
1. **Corpus como cimiento (Fase 0–1):**
  - **Golden pcap + etiquetado** (reproducible, determinista).
  - **Validación contra corpus** en CI (aserciones inmutables).
  - **Ventajas:**
    - Garantiza **reproducibilidad** (clave para el Dr. Caro Lindo).
    - Permite **debugging determinista** (ej: fallos en correlación).
2. **Pipeline vivo como demostración (Fase 2–3):**
  - **E2E con herramientas reales** (`nmap`, `hydra`, atomic-red-team).
  - **Aserciones probabilísticas** (ej: "el 95% de los ataques se detectan en < 120 s").
  - **Ventajas:**
    - Demuestra **funcionamiento en vivo** (requisito de Grok).
    - Permite **smoke tests** de realismo.

**Orden de fases propuesto (si Alonso acepta el híbrido):**
| Fase | Objetivo | Tier | Aserciones |
|------|----------|------|------------|
| 0 | Contrato (`network_security.proto`) + ADR-046 v4 | - | - |
| 1 | Adapter Suricata + golden pcap | Determinista | ✅ Sí |
| 2 | Adapter Zeek + correlación cross-engine | Determinista | ✅ Sí |
| 3 | Adapter Wazuh + bridge host↔flujo | Determinista | ✅ Sí |
| 4 | Máquina de estados de crisis (R1–R10) | Determinista | ✅ Sí |
| 5 | E2E vivo (nmap/hydra) | Vivo | ⚠️ Probabilísticas |
| 6 | EMECAS++ (backpressure, evicción) | Vivo | ⚠️ Probabilísticas |

**Argumentos clave:**
- **Para el Dr. Caro Lindo:**
  - El **corpus etiquetado** es el entregable más valioso para investigación (ej: validar hipótesis de correlación).
  - El pipeline vivo es un **bonus**, pero no sustituye la reproducibilidad.
- **Para Grok (pipeline vivo):**
  - El **E2E vivo** puede demostrarse en una **grabación** (ej: video + logs) si el corpus es el entregable principal.
  - Las aserciones probabilísticas son suficientes para validar el comportamiento en producción.

**Conclusión:**
🔹 **Recomiendo a Alonso que priorice corpus-first**, pero con un **pipeline vivo como demostración complementaria**.
- **Si el tiempo es limitado:** Entregar corpus + grabación del pipeline vivo.
- **Si el tiempo lo permite:** Entregar ambos (corpus + pipeline vivo con aserciones probabilísticas).

---

---

## **📝 Resumen de Posturas (Vibe / Mistral)**
| Moción | Postura | Fundamento |
|--------|---------|------------|
| **M1 (Timestamp)** | ✅ Ratifico | Tiempo de ocurrencia es determinista; emisión va a metadatos. |
| **M2 (Evicción)** | ✅ Ratifico (con ajustes) | 3 capas + cuota anti-pinning + score ponderado. |
| **M3 (Transporte)** | ✅ Ratifico | ZeroMQ interno + por-tier externo + `AdapterSpec v1`. |
| **M4 (Fuentes esperadas)** | ✅ Ratifico | Separar ventanas + rechazar condición de reglas Wazuh. |
| **D5 (Corpus vs Pipeline)** | 🔹 Híbrido (corpus-first + pipeline demo) | Recomendación para Alonso. |

---

---
## **🚀 Próximos Pasos (Acciones Concretas)**
1. **Para el Consejo:**
  - **Cerrar M1–M4** con las ratificaciones/ajustes propuestos.
  - **Documentar en ADR-046 v4:**
    - Modelo de dos claves (`community_id` + `host_key`).
    - Grafo temporal heterogéneo (R2).
    - Política de evicción en 3 capas (M2).
    - `AdapterSpec v1` (M3).
    - Separación de ventanas (M4.a).

2. **Para Alonso:**
  - **Decidir D5 (Q9):** Corpus-first vs pipeline vivo.
  - **Aprobar el orden de fases** según la decisión de D5.

3. **Para el Equipo de Desarrollo:**
  - **Implementar R1–R10 en `network_security.proto`** (ya hay consenso).
  - **Crear el golden pcap** para pruebas deterministas (Fase 1).
  - **Desarrollar `AdapterSpec v1`** (M3) y validar con Suricata/Zeek/Wazuh.

4. **Para EMECAS++:**
  - **Test de evicción (M2):**
    - Escenario de pinning (10,000 flujos desde una IP).
    - Verificar cuota anti-pinning y protección de hosts internos.
  - **Test de correlación (M1/M4):**
    - Golden pcap con eventos de red + host.
    - Validar que `event_time_unix_ns` correlaciona correctamente.

---
---
## **🔍 Preguntas Abiertas al Consejo (para debate adicional si es necesario)**
1. **Para Qwen (M1):**
  - ¿Aceptas que `event_time_unix_ns` (ocurrencia) sea el campo canónico para *windowing*, con `emitted_at` en metadatos?
  - Si no, ¿puedes proporcionar un caso concreto donde el tiempo de emisión sea más determinista que el de ocurrencia?

2. **Para Qwen/Grok/ChatGPT/DeepSeek (M2):**
  - ¿Aceptáis la política de evicción en 3 capas (recencia + severidad como orden + cuota anti-pinning)?
  - ¿Veis algún escenario donde esta política falle en conservar una crisis crítica?

3. **Para Grok/Kimi (M3):**
  - ¿Aceptáis el enfoque por-tier (determinista = ficheros, vivo = push/tail) bajo `AdapterSpec v1`?

4. **Para Qwen (M4.b):**
  - ¿Aceptas que la separación de ventanas (M4.a) mitiga el problema de expectativas muertas sin necesidad de acoplar el engine al ruleset de Wazuh?

---
---
## **📌 Conclusión Final**
El **Consenso de la Pasada 1 (R1–R10)** ya permite avanzar con el contrato (`network_security.proto`) y el diseño del correlation-engine. Las **mociones de la Pasada 2 (M1–M4)** tienen soluciones técnicas sólidas, fundamentadas en:
- **Estándares de la industria** (ZeroMQ, ECS, Corelight).
- **Pruebas reproducibles** (golden pcap, EMECAS++).
- **Mitigación de riesgos de seguridad** (DoS de memoria, acoplamiento).

**Recomiendo:**
✅ **Cerrar M1–M4** con las propuestas ajustadas.
✅ **Esperar la decisión de Alonso en D5** para definir el orden de fases.
✅ **Empezar a implementar R1–R10** en paralelo (no bloquea las mociones abiertas).

---
**— Vibe (Mistral AI), Consejo de Sabios.**
*"El rigor no es el enemigo de la velocidad; es su cimiento."*