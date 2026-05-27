**CONSEJO DE SABIOS — DAY 155 — VEREDICTO**

Hemos revisado el excelente trabajo de DAY 154, incluyendo la implementación de `CryptoAutonomyStateMachine` en `crypto_autonomy.h` y la creación del `FirewallAutonomyReactor`. Las preguntas son precisas y procedemos a dirimirlas.

---

### P1 — Señal de autonomía: ¿polling etcd o eventos ZMQ?

**Veredicto: Opción B — Evento ZMQ, sin escalas.**

La Opción A (polling cada 30s) introduce una latencia innecesaria de hasta 30 segundos en la activación de `default-deny`, lo cual es una ventana inaceptable para un ataque de ransomware que cifra ficheros en milisegundos.

La arquitectura ya está preparada para ZMQ. La clase `CryptoAutonomyStateMachine` define explícitamente un `TransitionCallback` y el código indica: `DEBT-AUTONOMY-ZMQ-EVENTS-001: en el futuro emitirá evento ZeroMQ`. El callback ya existe; solo falta instanciarlo.

**Decisión táctica para DAY 155**: Usar el `TransitionCallback` inyectado en `CryptoAutonomyStateMachine` para publicar un mensaje en un tópico ZeroMQ (`argus.crypto.autonomy`). El `FirewallAutonomyReactor` se suscribe a este tópico y reacciona instantáneamente a las transiciones de estado `NORMAL → AUTONOMOUS` y `AUTONOMOUS → NORMAL`. Esto elimina el acoplamiento temporal, permite pruebas unitarias con callbacks directos y sienta las bases para que otros componentes (RAG, alertas) consuman el mismo flujo de eventos.

---

### P2 — Granularidad del default-deny: ¿fail-closed total o selectivo?

**Veredicto: Fail-closed total para tráfico externo, con preservación quirúrgica de loopback e infraestructura interna.**

El escenario de hospital bajo ataque (DAY 152) exige máxima protección, pero un `DROP` indiscriminado puede romper la propia capacidad de defensa: el NDR necesita comunicarse con etcd local, el sniffer, y potencialmente con el sistema de logging para emitir alertas SOS.

**Recomendación específica**:
- **Preservar `INPUT 1` DROP para todo tráfico externo** (interfaz WAN). Esta es la regla crítica que detiene el ransomware.
- **Añadir reglas explícitas `ACCEPT` antes del DROP** para:
    1. Loopback (`-i lo`)
    2. Subred de gestión del hospital (si está definida en configuración)
    3. Tráfico ya establecido (`-m conntrack --ctstate ESTABLISHED,RELATED`)
- Esto se logra insertando las reglas `ACCEPT` en posiciones 1, 2, 3 y el `DROP` en posición 4.

Este diseño mantiene la postura `fail-closed` para el vector de ataque principal (WAN), pero evita que el NDR quede ciego, mudo o incapaz de coordinar su propia defensa.

---

### P3 — Parámetros ZMQ críticos antes de benchmarks

**Veredicto: HWM (High Water Mark) es el parámetro crítico. Sin él, los benchmarks mienten.**

Si el HWM de los sockets ZMQ (especialmente en el sniffer → ml-detector → firewall) no está calibrado, se producirán dos fenómenos que invalidan cualquier benchmark de capacidad:

1. **Pérdida silenciosa de mensajes**: Si el productor es más rápido que el consumidor y el HWM se alcanza, ZMQ descarta mensajes sin notificar. El benchmark reportará throughput alto pero con datos incompletos, ocultando pérdida de paquetes maliciosos.
2. **Backpressure no medida**: Sin HWM explícito, ZMQ usa memoria indefinidamente, distorsionando las métricas de latencia y uso de RAM.

**Parámetros a fijar antes de benchmarks, en orden**:
1. **`ZMQ_SNDHWM` / `ZMQ_RCVHWM`**: Establecer un valor inicial conservador (ej. 10000 mensajes) y documentarlo. El benchmark debe medir explícitamente la tasa de descarte (`ZMQ_EVENTS` para monitorizar si se alcanzó el HWM).
2. **`ZMQ_LINGER`**: Fijar a 0 para evitar bloqueos en cierre durante escenarios de fallo.
3. **`ZMQ_RCVTIMEO` / `ZMQ_SNDTIMEO`**: Establecer timeouts explícitos para que los benchmarks midan latencia real, no bloqueos indefinidos.
4. **`ZMQ_RECONNECT_IVL`**: Solo es relevante si se introducen fallos de red en el benchmark; puede esperar a la fase de resiliencia.

---

### P4 — `DEBT-CAPTURE-BACKEND-ISP-001`: ¿ahora o después?

**Veredicto: Después de la integración ZMQ del reactor. Mañana NO.**

La deuda ISP en `CaptureBackend` es una mejora estructural que no bloquea ninguna funcionalidad crítica. En cambio, `DEBT-AUTONOMY-ZMQ-EVENTS-001` es el eslabón que conecta la máquina de estados (DAY 152) con el reactor de firewall (DAY 154), cerrando el circuito de autonomía edge.

**Secuencia propuesta para DAY 155-156**:
- **DAY 155**: `DEBT-AUTONOMY-ZMQ-EVENTS-001` (ZMQ pub/sub interno) + `DEBT-AUTONOMY-STATE-PERSISTENCE-001` (tmpfs).
- **DAY 156**: `DEBT-CAPTURE-BACKEND-ISP-001` + inicio de `BACKLOG-ZMQ-TUNING-001`.

Cerrar el circuito de autonomía edge es una prioridad funcional P1 que protege al hospital; la segregación de interfaces es una prioridad de calidad P2. La primera salva vidas operativas; la segunda, elegancia arquitectónica.

---

### Resumen del Consejo — DAY 155

| Decisión | Fundamento |
|---|---|
| **ZMQ pub/sub** para señal de autonomía | Latencia cero. El `TransitionCallback` ya está definido en `crypto_autonomy.h`. |
| **Fail-closed externo + ACCEPT interno** | Máxima seguridad sin cegar al defensor. |
| **HWM primero** en ZMQ tuning | Sin HWM explícito, los benchmarks no son reproducibles ni fiables. |
| **ISP después de autonomía** | La integración del reactor cierra un circuito funcional P1; ISP es calidad P2. |

El Consejo espera el próximo parte con la integración ZMQ completada y el EMECAS en verde.