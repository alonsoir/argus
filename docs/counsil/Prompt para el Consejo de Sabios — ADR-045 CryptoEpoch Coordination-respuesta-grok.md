**Respuesta del Consejo de Sabios — Miembro 1 (Experto en Sistemas Distribuidos y Criptografía Enterprise)**

Saludos, PI. He revisado ADR-045 de forma independiente, considerando el contexto de 6 componentes en el mismo nodo (o clúster estrecho), ZeroMQ + CurveZMQ (o equivalente), RCU via `CryptoProviderHandle`, y las restricciones de infraestructura crítica (baja latencia, zero-downtime preferido, autonomía).

### 1. ¿`not_before` en etcd es suficiente o se necesita mecanismo más fuerte (acks)?

`not_before` + watch es **suficiente como base** para la mayoría de casos, pero debería complementarse con **heartbeats periódicos de epoch actual** (no acks síncronos por rotación).

Razones:
- etcd watches son eficientes y entregan notificaciones consistentes (Raft). Un `not_before` futuro da una barrera temporal clara.
- Acks explícitos introducen 2PC-like complexity y single-point-of-failure (el escritor esperaría quórum de acks). En sistemas de 6 componentes locales, el riesgo de split-brain por fallo parcial es bajo si el grace period cubre jitter de scheduling/OS.
- Mejora recomendada: Cada componente publica periódicamente su `/argus/crypto/epoch/current` (con lease corto). El etcd-server o un watcher central puede alertar si hay discrepancias > grace period. Esto es "best-effort coordination" mejorado sin bloquear.

**Posición**: `not_before` + watches + heartbeats de epoch = buen equilibrio. Rechazo acks por rotación (demasiado overhead para el beneficio marginal aquí).

### 2. Grace period de 30s

**Razonable y conservador** para 6 componentes en el mismo nodo (baja varianza en scheduling). En práctica, la transición (reload del provider via RCU) debería ser sub-segundo si `CryptoProvider::create()` es eficiente (carga seed → HKDF derivaciones → caché de keys).

Recomendación:
- Default: **10-15s** (suficiente para jitter de thread pools, etcd watch propagation ~<100ms típica, y reload).
- Hacerlo **configurable globalmente** vía etcd (no por componente inicialmente). Per-component solo si hay heterogeneidad real (e.g., un componente I/O-bound pesado).
- Durante grace: ventana dual-key (ver Q5).

30s es seguro pero introduce ventana de exposición innecesaria en rotaciones frecuentes.

### 3. Único escritor de `/argus/crypto/epoch`

**Un proceso externo dedicado (Vault agent o servicio de orquestación — Jenkins/CI o dedicated rotator)**, **no** el etcd-server directamente.

Razones técnicas:
- Separación de concerns: etcd es fuente de verdad para *lectura/coordinación*, no el generador de material criptográfico. Vault ya genera el seed → el agente que interactúa con Vault debe escribir el epoch (con atomicidad via etcd transactions/CAS si es necesario).
- etcd-server como escritor mezcla concerns y complica auditoría/secretos (principio de least privilege).
- Best practice en entornos Vault + etcd/K8s: Vault agents o operadores externos publican estado derivado.

Si usáis VaultProvider enterprise, el rotator debería ser parte del flujo Vault (sidecar o job).

### 4. Detección y recuperación de split-brain

La **autonomy state machine existente es casi suficiente**, pero **se recomienda un estado transitorio `EPOCH_TRANSITION`** (o sub-estado).

Argumentos:
- Detección: Durante/tras grace period, si un peer reporta epoch diferente (via heartbeat o primer mensaje ZMQ fallido con auth error), entrar en autonomy. Monitoreo central (o etcd heartbeats) detecta "laggards".
- Recuperación: El componente retrasado debe intentar reload forzado (watch retry + backoff). Si falla persistentemente → quarantine + alert + posible reinicio controlado.
- `EPOCH_TRANSITION`: Útil para logging, métricas, y evitar que el componente acepte/mande tráfico normal mientras está recargando (evita races en dual-key). Transición: Old → Transition (al detectar cambio) → New (post-reload exitoso).

Sin nuevo estado explícito, podéis sobrecargar autonomy, pero un estado dedicado mejora observabilidad en infraestructura crítica.

### 5. Ventana dual-key ZMQ sin cambios en protocolo wire

**Es implementable sin añadir `epoch_id` al header binario actual (LZ4 + LE uint32_t)**, aprovechando la capa superior de `CryptoProviderHandle` y multi-key support en CurveZMQ (o equivalente).

Cómo:
- El provider mantiene **dos contextos/keys activos** durante grace (N y N+1). Cada socket ZMQ puede configurarse para aceptar ambos (CurveZMQ soporta verificación contra lista de claves públicas permitidas).
- En recepción: Intentar decrypt/verify primero con current epoch, fallback a previous si falla. El `CryptoProvider` abstrae esto.
- En envío: Usar siempre la nueva epoch una vez cargada.
- Sin tocar wire format: El epoch negotiation queda implícito en la capa crypto (fallos de auth indican mismatch y trigger de recovery).

**Si el protocolo evoluciona**: Añadir epoch_id (uint64 LE) en header es limpio y future-proof (facilita debug y multi-epoch más amplio), pero no es obligatorio para FASE 2. Priorizad compatibilidad backward.

**Recomendaciones generales**:
- Probar exhaustivamente con inyección de delays/fallos (chaos engineering: kill etcd watcher temporal, delay reload en un componente).
- Métricas clave: epoch drift, reload latency, ZMQ auth failures por epoch.
- Documentar fallback manual (forzar epoch via admin tool).
- Considerar leases en etcd para la epoch entry (auto-expiry si rotator falla).

Esta propuesta es sólida para enterprise. Con los ajustes menores propuestos (grace más corto, escritor externo, heartbeats, estado transition opcional), pasa a implementación. Disiento solo en detalles operacionales para robustez.

El PI decide. Estoy disponible para contra-argumentar o profundizar.

— Sabio en Sistemas Críticos.