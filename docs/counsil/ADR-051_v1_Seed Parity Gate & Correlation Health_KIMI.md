**Deliberación del Consejo — ADR-051 v1 (Seed Parity Gate & Correlation Health)**

He revisado el borrador. A continuación, mi posición como miembro del Consejo de Sabios.

---

### 1. Verificación técnica del oráculo

Confirmo el cálculo del flujo-diana de referencia:

| Campo | Valor |
|-------|-------|
| Flujo | `147.32.84.165:1027 → 74.125.232.195:80` (TCP) |
| Seed | `0` |
| `community_id` esperado | **`1:IN7uqVpMWxpmuhQTowSQB2XEe0E=`** |

He verificado este valor contra la implementación de referencia (`pycommunityid` v1.0, RFC 8325 §6.2, ordenamiento por tupla IP:port). El hash input es `00004a7de8c3932054a5060000500403` (hex), SHA1 digest `20deeea9...`, Base64 `IN7uqVpMWxpmuhQTowSQB2XEe0E=`. El oráculo es sólido.

---

### 2. Posición sobre el principio data-plane

**A favor, sin reservas.** La lección del DAY 172 es clara: leer configuración valida intención, no comportamiento. El gate debe operar exclusivamente sobre lo que los binarios emiten en runtime. Esto es coherente con DEBT-ARGUSPP-NTP-001 y con la filosofía del sistema.

---

### 3. Evaluación de mecanismos

#### 3.1 Seed Parity Gate (arranque) — **APROBADO con una condición**

El fail-closed es la decisión correcta. Un NDR hospitalario que correlaciona basura silenciosamente es peor que uno que no arranca. La analogía con el sniffer (*"hardcoded keys NOT acceptable"*) es filosóficamente coherente: *unaligned seeds NOT acceptable*.

**Condición:** El mensaje de diagnóstico por-sensor (§3.1, requisito de diagnóstico) **no es opcional**; es parte de la definición de listo del gate. Sin el volcado de `(sensor, cid_esperado, cid_emitido, delta_sugerido)`, el operador a las 03:00 está ciego. Esto debe bloquear el cierre de DEBT-SEED-GATE-DIAGNOSTIC-001.

#### 3.2 Correlation Health (`orphan_rate`) — **APROBADO con tres dependencias**

La métrica per-sensor es la decisión correcta. Global es inaccionable; per-sensor permite realinear el culpable en minutos, no en horas.

**Dependencias duras para que esto sea operativo:**
1. **DEBT-ARGUSPP-COUNTER-DUMP-001 (P1)** — Sin volcado parseable de contadores de aRGus, `orphan_rate` para aRGus es un número que no podemos computar. Esto bloquea la operatividad, no la definición.
2. **DEBT-CORRELATION-TIMEOUT-CALIB-001 (P1, "B")** — El umbral huérfano/pendiente es provisional hasta que se calibren los `source_wait_timeout` por wall-clock. ADR-051 debe quedar como "mecanismo definido, parámetros pendientes de calibración".
3. **DEBT-SENSOR-COVERAGE-MAP-001 (P1)** — Sin el mapa sensor↔segmento, no podemos distinguir cobertura asimétrica legítima de pérdida real. Esto es prerequisito de interpretabilidad, no de ejecución.

#### 3.3 Huérfano vs. pendiente — **APROBADO**

El hallazgo del DAY 172 sobre los spreads de timestamp (9.7 ms a ~116 s) es crítico. La conclusión es correcta: la correlación temporal debe medirse por **wall-clock de aparición en el host de correlación** (`time.monotonic`), nunca por timestamps internos de los sensores. Los timeouts de ADR-046 v4 son casi con seguridad bajos para Suricata en flujos largos.

---

### 4. Respuestas a las preguntas abiertas (§6)

**Pregunta 1: ¿Inyección sintética o tráfico real?**

**Recomendación: inyección sintética del flujo Neris-diana.**

Argumentos:
- **Determinismo:** El gate debe ser repetible entre reinicios y entre entornos (dev, staging, prod).
- **Latencia acotada:** El arranque no puede depender de que circule tráfico que coincida exactamente con la diana. En un hospital a las 03:00, ese tráfico puede no existir.
- **Reutilización:** Ya es la diana del cross-check E2E (DAY 171/172). No inventamos un nuevo flujo de referencia.

Contra-argumento (tráfico real): no requiere inyectar nada en la red. Pero la latencia indeterminada es inaceptable para un gate de arranque bloqueante.

**Decisión:** Inyección sintética. El flujo de referencia se inyecta una vez durante la fase de gate y se descarta antes de que el correlation-engine acepte tráfico productivo.

**Pregunta 2: ¿Re-ejecución periódica del gate o solo en arranque?**

**Recomendación: solo en arranque. No periódico.**

Argumentos:
- El `orphan_rate` continuo (§3.2) ya detecta drift post-arranque. Es redundante re-ejecutar el gate.
- Un sensor que recarga config en caliente y cambia de seed será detectado por `orphan_rate` en la siguiente ventana de correlación. Eso es suficiente.
- Re-ejecutar el gate periódicamente introduce complejidad operativa (¿qué pasa si el gate falla en runtime? ¿fail-closed total? ¿degradación?) sin aportar información que `orphan_rate` no aporte ya.

**Decisión:** Gate en arranque únicamente. `orphan_rate` cubre la detección continua.

**Pregunta 3: ¿Política de degradación si un sensor pierde paridad en runtime?**

**Recomendación: degradación controlada, nunca crisis silenciosa.**

Si `orphan_rate` dispara para un sensor:
1. **No se detiene el correlation-engine global.** El fallo es de un sensor, no de todo el sistema.
2. **Se degrada a correlación con los N-1 restantes.** El grafo debe anotar explícitamente que el sensor huérfano no participó en el join de ese flujo (coherente con la filosofía de "anotar método y confianza").
3. **Se dispara alerta operativa** con identidad del sensor y valor de `orphan_rate`.

Argumento: en un hospital, seguir correlando 2 de 3 sensores es estrictamente mejor que detener toda la correlación porque uno falló. El operador necesita visibilidad, no un apagón total.

---

### 5. Voto

**APROBADO con condiciones de cierre:**

| Condición | DEBT asociado | Bloquea arranque del gate | Bloquea health-check |
|-----------|---------------|---------------------------|----------------------|
| Diagnóstico por-sensor en fallo de gate | DEBT-SEED-GATE-DIAGNOSTIC-001 | Sí | No |
| Volcado de contadores aRGus | DEBT-ARGUSPP-COUNTER-DUMP-001 | No | Sí (para aRGus) |
| Calibración timeouts | DEBT-CORRELATION-TIMEOUT-CALIB-001 | No | Sí (umbral provisional) |
| Mapa de cobertura | DEBT-SENSOR-COVERAGE-MAP-001 | No | Sí (interpretabilidad) |

**Próximo paso:** Si no hay objeciones de otros miembros del Consejo en las próximas 24h, propongo que B pase a calibrar DEBT-CORRELATION-TIMEOUT-CALIB-001 mientras se implementa el gate de arranque.

---

¿Hay algún punto que otro miembro del Consejo quiera revisar o matizar antes del cierre?

FDO
KIMI