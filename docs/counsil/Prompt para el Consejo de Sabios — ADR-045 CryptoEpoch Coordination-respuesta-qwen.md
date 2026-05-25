Aquí tienes la revisión técnica estructurada por pregunta, con argumentos concretos y recomendaciones accionables para la v2 del ADR-045.

---

### 1. ¿`not_before` en etcd es suficiente o necesitamos acks explícitos?
**Respuesta corta:** `not_before` es suficiente como *disparador*, pero insuficiente como *garantía*. Añade un mecanismo ligero de `readiness` sin caer en 2PC.

**Argumento técnico:**
- La coordinación basada en reloj (`not_before`) asume sincronización < 10ms entre todos los componentes. En infraestructura crítica, sin PTP/NTP estricto o con carga de CPU alta, el reloj puede desviarse o el scheduler puede posponer el `reload()`.
- Un 2PC completo es overkill y introduce riesgo de deadlock por partición de red.
- **Recomendación:** Mantén `not_before` como trigger primario, pero exige que cada componente publique un `ready` efímero en etcd: `/argus/crypto/ready/<comp_id>` con `lease=grace*2`. El coordinador puede auditar la alineación sin bloquear. Si un componente no confirma antes de `T+grace`, el sistema entra en `EPOCH_TRANSITION` con tolerancia degradada en lugar de asumir éxito.

---

### 2. ¿Grace period de 30s razonable para 6 componentes en el mismo nodo?
**Respuesta corta:** 30s es excesivo para mismo-nodo. Usa `5–10s` como default, configurable a nivel de *cluster*, no por componente.

**Argumento técnico:**
- `CryptoProviderHandle.reload()` es atómico y no bloqueante (RCU). El cuello de botella real es: derivación HKDF, carga de seed desde disco/Vault, y posible contención en `std::shared_mutex` interno. Todo esto tarda < 200ms en carga normal.
- Configurar grace por componente rompe la invariante de transición simultánea: si el firewall usa 5s y el sniffer 30s, habrá 25s de split-brain garantizado.
- **Recomendación:** Expón `epoch_grace_period` como variable de configuración global (`argus::crypto::epoch_grace_s`). Si algún componente tiene latencia de reload anormal, optimiza el path de carga (precálculo HKDF, cache de claves, I/O asíncrono) en lugar de inflar la ventana.

---

### 3. ¿Quién debe ser el único escritor de `/argus/crypto/epoch`?
**Respuesta corta:** Un proceso dedicado (`epoch-coordinator`), no `etcd-server`.

**Argumento técnico:**
- `etcd` es un almacén de configuración, no un orquestador de lógica de negocio. Permitir que `etcd-server` escriba la época acopla la capa de datos con la de control y complica auditoría, rollback y validación de `seed_hash`.
- **Recomendación:** Implementa un `CryptoEpochCoordinator` (daemon ligero o sidecar de Vault) que:
    1. Solicite nuevo seed a Vault.
    2. Compute `seed_hash = HKDF-SHA256(seed, info="epoch_seed")`.
    3. Adquiera una `lease` en etcd para `/argus/crypto/epoch`.
    4. Publique el JSON con `not_before = now() + grace`.
    5. Renueve lease hasta confirmar `ready_count == component_count` o expire.
       Esto permite idempotencia, cancelación segura y trazabilidad completa (`who rotated what and when`).

---

### 4. ¿Cómo detectar/recuperar split-brain en transición? ¿Basta la autonomy existente o falta `EPOCH_TRANSITION`?
**Respuesta corta:** Añade `EPOCH_TRANSITION` explícito. La autonomy existente es para fallos permanentes, no para estados transitorios de sincronización criptográfica.

**Argumento técnico:**
- Sin estado intermedio, los errores de descifrado se interpretarán como `NETWORK_DEGRADED` o `PROTOCOL_VIOLATION`, disparando acciones incorrectas (ej: reconexiones agresivas, fallback a plaintext si existe, o alertas falsas).
- **Recomendación:**
    - Estado nuevo: `EPOCH_TRANSITION` con timeout `grace * 2`.
    - Métricas: `crypto_mismatch_count`, `last_successful_epoch`, `peer_epoch_hint` (si se implementa en Q5).
    - Lógica: Si `crypto_mismatch_count > threshold` durante `EPOCH_TRANSITION`, promueve a `AUTONOMY_ISOLATED` con motivo `EPOCH_SPLIT_BRAIN`.
    - Recuperación: Re-intenta `handle.reload()` con backoff exponencial, consulta etcd directamente para forzar alineación, y si persiste, notifica a SIEM/SOAR con `epoch_id` y `seed_hash` para rotación de emergencia.

---

### 5. ¿Ventana dual-key ZMQ implementable sin cambiar protocolo wire?
**Respuesta corta:** Técnicamente posible con *trial-decryption*, pero no recomendable para infraestructura crítica. Añade `1-byte epoch_hint` al header.

**Argumento técnico:**
- Sin `epoch_id` en el wire, el receptor debe probar descifrado con clave N, y si falla (MAC inválido o padding), probar con N+1. Esto:
    - Duplica coste CPU por paquete.
    - Introduce riesgo de timing side-channel si el fallback no es constante.
    - Puede aceptar paquetes maliciosos si HKDF genera claves con colisiones accidentales en el primer byte de MAC.
- **Recomendación:** Extiende el header binario actual con un `uint8_t epoch_hint` antes del campo `uint32_t` de longitud/LZ4. Si el protocolo wire es inmutable por contrato, reutiliza 2 bits no usados del `uint32_t` o añade un campo opcional al final del frame (ZeroMQ permite multipart sin romper compatibilidad si el receptor lo ignora). El hint permite descifrado directo O(1), elimina ambigüedad y habilita métricas precisas de rotación.

---

### 📋 Síntesis para ADR-045 v2

| Aspecto | v1 | Recomendación v2 |
|--------|----|------------------|
| Coordinación | `not_before` solo | `not_before` + `lease` + `ready/<id>` |
| Grace period | 30s, configurable por componente | 5–10s, configurable a nivel de cluster |
| Escritor época | `etcd-server` | `epoch-coordinator` con etcd lease |
| Estado máquina | Autonomy trigger directo | Añade `EPOCH_TRANSITION` con métricas |
| Wire protocol | Trial-decryption dual-key | `1-byte epoch_hint` en header binario |

**Riesgo residual aceptable:** Best-effort con `not_before` + `ready` cubre >99.9% de casos en entornos controlados. El resto se gestiona vía `EPOCH_TRANSITION` → aislamiento automático. No se justifica 2PC ni consenso distribuido para rotación criptográfica interna.

El PI puede proceder a FASE 2 con estas modificaciones. Si necesita especificación C++20 del `epoch_hint` en el framing ZMQ o diseño del `epoch-coordinator` (state machine + etcd lease handling), puedo generar el draft técnico en formato ADR.