# Dictamen del Consejo — ADR-045 CryptoEpoch Coordination

He analizado la propuesta v1 en el contexto de aRGus NDR (C++20, ZeroMQ, infraestructura crítica). A continuación, mi dictamen técnico punto por punto, con argumentos concretos y disidencias donde considero que la propuesta actual es insuficiente.

---

## 1. ¿Es suficiente `not_before` en etcd o se necesita ack explícito por componente?

**Disidencia fuerte: `not_before` solo es insuficiente para infraestructura crítica.**

**Argumentos técnicos:**

- **Best-effort no es aceptable en split-brain criptográfico.** Si un componente (ej. el ML detector en un nodo saturado) no procesa el watch de etcd a tiempo, o si hay un GC pause en el proceso C++, el `not_before` expira y el componente entra en época N+1 sin haber recargado el provider. El resultado es un canal ZMQ muerto que solo se detecta por timeout de heartbeat — demasiado tarde para una rotación programada.

- **El problema es asimétrico:** el firewall puede rotar en T+grace, pero el sniffer puede estar en T+grace+50ms. Durante esos 50ms, todos los paquetes del sniffer al firewall se descartan por MAC/encryption mismatch. En infraestructura crítica, eso es pérdida de telemetría activa.

- **Contra-argumento (que rechazo):** "Pero etcd watch es eventualmente consistente y el reloj está sincronizado." Falso en la práctica: `std::chrono` en C++20 no garantiza sincronización de relojes de pared entre procesos del mismo nodo (aunque estén sincronizados vía NTP, hay jitter de kernel scheduling).

**Propuesta alternativa:**
```
etcd:
  /argus/crypto/epoch/target        → { epoch_id, seed_hash, not_before, deadline }
  /argus/crypto/epoch/ack/<comp_id> → { epoch_id, timestamp, status: READY|FAILED }

Flujo:
  1. Escritor publica target
  2. Cada componente, tras reload() exitoso, escribe ack con status=READY
  3. Si en T=deadline no hay 6/6 acks → rotación abortada, epoch_target se marca ABORTED
  4. Solo si 6/6 READY → escritor publica /argus/crypto/epoch/current = target
```

Esto es un **2PC simplificado** (fase de prepare + commit), no un 2PC distribuido completo. No requiere transaction manager externo porque el commit es unilateral del escritor basado en conteo de acks.

---

## 2. ¿Grace period de 30s para 6 componentes en mismo nodo?

**Parcialmente de acuerdo, pero con matiz crítico: debe ser configurable por *rol funcional*, no por instancia.**

**Argumentos técnicos:**

- **30s es excesivo para 6 componentes colocados.** Si todos están en el mismo nodo (o incluso en VMs Vagrant del mismo host), el reload de `CryptoProviderHandle` vía RCU es microsegundos (atomic swap de `shared_ptr`). El tiempo dominante es el network round-trip a Vault (si se usa `VaultProvider`) o la re-derivación HKDF-SHA256 (si es `SeedFileProvider`). Ni uno ni otro justifica 30s para 6 procesos.

- **El grace period realmente necesario no es para el reload, es para la ventana dual-key (FASE 3).** Necesitas tiempo suficiente para que todos los sockets ZMQ hayan drenado los mensajes en vuelo cifrados con época N antes de que el receptor deje de aceptarlos.

- **Configuración por rol:** El ML detector puede tener buffers de inferencia de 5s; el firewall puede tener state tables que requieren 10s para estabilizar. Un grace period único de 30s penaliza al detector innecesariamente.

**Recomendación:**
```cpp
struct EpochTransitionConfig {
    std::chrono::seconds grace_period{5};      // default: 5s, no 30s
    std::chrono::seconds dual_key_window{2}; // FASE 3 overlap
    std::chrono::seconds ack_timeout{3};       // para el 2PC simplificado
};
```

Para un despliegue enterprise crítico, 5s de grace + 2s de dual-key son suficientes si los componentes están en el mismo datacenter/nodo. 30s solo es razonable si hay componentes remotos con latencia >100ms — que no parece ser el caso según el contexto (Vagrant VMs locales).

---

## 3. ¿Quién debe ser el único escritor de `/argus/crypto/epoch`?

**Disidencia: Ni etcd-server ni Jenkins. Debe ser un **CryptoEpochManager** dedicado, co-ubicado con etcd pero como proceso separado con lease TTL.**

**Argumentos técnicos:**

- **etcd-server como escritor:** Violación de separación de responsabilidades. etcd es almacenamiento de configuración/consenso; no debe contener lógica de negocio criptográfica (generación de seeds, derivación HKDF, cálculo de hashes). Además, si etcd-server se reinicia, pierdes el estado de transición a medio camino.

- **Jenkins/Vault agent externo:** Introduce un actor fuera del runtime del sistema. Si el agente pierde conectividad durante una rotación, no hay forma de abortar o consultar estado desde los componentes C++ sin salirse del trust boundary.

- **La solución correcta:** Un proceso `argus-epoch-manager` (o integrado en `etcd-server` como sidecar) que:
    1. Tiene un **lease etcd TTL** (ej. 10s) — si muere, el lease expira y la clave `/argus/crypto/epoch/target` se autodestruye (mechanismo de safety).
    2. Es el único con permisos de escritura en `/argus/crypto/epoch/*` (ACLs de etcd con mTLS + CN=`argus-epoch-manager`).
    3. Expone una API interna (gRPC/Unix socket) para que el operador humano o Jenkins *dispare* la rotación, pero el manager ejecuta el protocolo.

**Patrón:** Single writer con lease + TTL. Esto evita split-brain del escritor mismo.

---

## 4. ¿Detección y recuperación de split-brain en transición?

**Disidencia fuerte: La state machine de autonomy existente es insuficiente. Se requiere estado nuevo `EPOCH_TRANSITION` + sub-estados.**

**Argumentos técnicos:**

- **Autonomy actual (asumo):** Probablemente tiene estados como `HEALTHY`, `DEGRADED`, `ISOLATED`, `AUTONOMOUS`. Ninguno de estos modela la semántica de "estoy intentando rotar criptográficamente pero no lo he conseguido".

- **El problema concreto:** Si un componente falla en `reload()` (ej. Vault está temporalmente unavailable), ¿qué hace? Con el mecanismo best-effort actual, simplemente no rota y entra en split-brain. La state machine de autonomy detectará "canal ZMQ muerto" eventualmente, pero eso es un síntoma, no una causa accionable.

- **Propuesta de state machine extendida:**
```
HEALTHY
  └─> EPOCH_TRANSITION_PREPARE   (recibió target, intentando reload)
        ├─> EPOCH_TRANSITION_READY    (reload OK, ack enviado)
        └─> EPOCH_TRANSITION_FAILED   (reload falló, reintentando)
              └─> AUTONOMOUS_EPOCH_STALE  (máximo reintentos agotados,
                                           operar con época N hasta intervención)
```

- **Recuperación:** Si un componente entra en `AUTONOMOUS_EPOCH_STALE`, debe:
    1. Seguir operando con época N (no morir).
    2. Intentar re-sincronización periódica (cada 30s) leyendo `/argus/crypto/epoch/current`.
    3. Si logra sincronizarse, transicionar a `HEALTHY` automáticamente (self-healing).
    4. Alertar vía telemetry (no solo log local).

**Esto es crítico:** En infraestructura crítica, un componente que no puede rotar no debe morir; debe operar en modo degradado con la época anterior hasta que un operador o el sistema lo resuelva.

---

## 5. ¿Ventana dual-key ZMQ sin cambios en wire protocol?

**Disidencia: No es implementable de forma segura sin añadir `epoch_id` al header binario.**

**Argumentos técnicos:**

- **El wire actual:** `LZ4 + LE uint32_t`. Asumo que el `uint32_t` es el length del payload comprimido. No hay campo para discriminar la época criptográfica.

- **¿Por qué no basta con "aceptar N y N+1 durante grace"?** Porque el receptor no sabe qué clave probar primero. Si intenta descifrar con N+1 y falla, luego con N — eso es un oracle de timing (side-channel) y además es O(n) con n=épocas activas. Con 6 componentes y rotaciones frecuentes, esto escala mal.

- **¿Por qué no usar un "magic byte" implícito?** El ciphertext de época N vs N+1, si usas AEAD (ChaCha20-Poly1305 o AES-GCM), fallará en la verificación de MAC. Eso es indistinguible de un ataque de bit-flipping. No puedes usar "fallo de MAC" como señal de "prueba la otra época" en producción — eso viola la semántica criptográfica de authenticate-then-decrypt.

- **La solución mínima viable:**
  ```
  Header binario actual:  [LE uint32_t: payload_len]
  Header binario ADR-045: [LE uint32_t: payload_len][LE uint16_t: epoch_id][2 bytes reserved]
  ```

    - `epoch_id` es un `uint16_t` (suficiente para 65k épocas; si rotas cada 24h, duras 179 años).
    - Los 2 bytes reservados permiten extensión futura sin romper compatibilidad.
    - **Backward compatibility:** Si `epoch_id == 0`, se asume "legacy, usar época actual" durante un periodo de migración.

- **Implementación en ZMQ:** El header va en el ZMQ message frame, antes del payload LZ4. No requiere cambios en el framing ZMQ (multipart o single-part), solo en el parseo del primer frame.

---

## Resumen ejecutivo para el PI

| Punto | Posición del Consejo | Riesgo si se ignora |
|-------|---------------------|---------------------|
| 1. Coordinación | **Rechazar best-effort.** Usar 2PC simplificado con acks en etcd. | Split-brain silencioso, pérdida de telemetría. |
| 2. Grace period | **5s default**, configurable por rol funcional. | Latencia artificial innecesaria en detector ML. |
| 3. Escritor | **Proceso dedicado `epoch-manager`** con lease TTL, no Jenkins ni etcd-server. | Escritor fantasma, rotaciones huérfanas, race conditions. |
| 4. Recuperación | **Nuevo estado `EPOCH_TRANSITION`** + `AUTONOMOUS_EPOCH_STALE`. | Componente muerto en rotación = outage. |
| 5. Wire protocol | **Añadir `epoch_id` uint16_t al header binario.** | Oracle de timing, complejidad O(n) en descifrado, imposibilidad de debug. |

**Recomendación de bloqueo:** No proceder a FASE 2 hasta que ADR-045 v2 incorpore los 5 puntos anteriores. La FASE 1 (RCU handle) es sólida y puede permanecer en producción con rotación manual hasta entonces.

---

¿Necesitas que profundice en algún punto concretamente, o que bosqueje la interfaz C++ del `CryptoEpochManager`?