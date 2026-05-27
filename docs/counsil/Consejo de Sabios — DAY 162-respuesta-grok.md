**Respuesta del Consejo de Sabios (Grok) – DAY 161**

### Arquitectura Mínima Viable (MV) para cerrar el ciclo criptográfico enterprise completo

**Objetivo**: Tener un flujo **generación → distribución → rotación coordinada → recarga en caliente** que sea seguro, auditable y que cumpla ADR-013 (rotación atómica o coordinada para evitar romper canales ZMQ).

#### Componentes mínimos de la MV (arquitectura propuesta)

1. **Authority of Record (Vault como fuente de verdad)**
    - `enterprise_vendor/` path en Vault (KV v2 o Transit engine).
    - Secret principal: `enterprise_vendor.key` (privada Ed25519) + `enterprise_vendor.pub` + metadata (version, expiry, fingerprint).
    - Token enterprise (con `features=[vault_crypto]`) también se almacena/renueva allí.

2. **Generación y Rotación Centralizada (Jenkins + Vault)**
    - Job de Jenkins “Enterprise-Key-Rotation” (o GitHub Actions si migráis).
    - Usa Vault Transit o una herramienta offline (mejor) para generar nuevo keypair Ed25519.
    - Escribe la nueva versión en Vault (KV v2 versioning automático).
    - Genera nuevo token enterprise (si aplica) con nuevo expiry.

3. **Distribución Segura (Push + Pull híbrido)**
    - **Config Provider / Secret Sidecar** en cada componente (recomendado):
        - Agente Vault (o custom sidecar ligero) que haga periodic poll + watch en el path `enterprise_vendor/`.
        - Opcional: notificación vía etcd (watch) o NATS cuando cambie la versión.
    - Al arrancar: cada binario lee el keypair/token desde Vault (usando el token enterprise bootstrap) o desde archivo inyectado por sidecar.
    - `enterprise_vendor.key` **nunca más** vive permanentemente en VM; solo temporalmente en memoria o en tmpfs con permisos estrictos.

4. **Rotación Coordinada (el punto más delicado)**
    - **Estrategia recomendada (mínima viable)**: **Blue-Green / Versioned Keys + Grace Period**
        - Vault guarda múltiples versiones (vN y vN+1).
        - Todos los componentes publican su “current_key_version” en etcd (o en un topic de control).
        - Cuando >90% de los nodos reportan que tienen vN+1, se activa la rotación global:
            - Se publica un mensaje de control “ROTATE_NOW vN+1” vía etcd o ZMQ control channel.
            - Cada endpoint recarga el keypair y reinicia/reconfigura el socket ZMQ con graceful shutdown + reconnect.
        - Grace period: 30-60 segundos donde ambos keys son válidos (dual validation).
    - Alternativa más simple (si no podéis permitir dual-key): **Maintenance Window + Coordinated Restart** (todos los pods se reinician en orden controlado vía orchestrator).

5. **Recarga en Caliente (Hot Reload)**
    - `CryptoProvider` debe exponer `reloadKeypair(version)` o `rotateTo(version)`.
    - `plugin-loader` debe soportar reload de plugins ya cargados (o graceful unload + reload).
    - ZMQ sockets: `zmq_ctx_shutdown` + recreate con nuevo key (Curve25519 si usáis zmq CURVE, o firma de mensajes con Ed25519).

### Orden recomendado de implementación (para minimizar riesgo)

1. **Fase 1 (1-2 semanas)**: Vault como fuente de verdad + lectura en arranque
    - Mover `enterprise_vendor.key` a Vault.
    - Todos los componentes leen desde Vault (o sidecar) en startup.
    - Actualizar `CryptoProvider::create()` y token distribution.

2. **Fase 2**: Generación automática por Jenkins + versioning en Vault.

3. **Fase 3**: Distribución + reporting de key version (etcd).

4. **Fase 4**: Rotación coordinada (primero con maintenance window, luego con grace period).

5. **Fase 5**: Hot reload completo + tests E2E de rotación (extender `test-e2e-vault`).

### Riesgos arquitecturales importantes (resolver ANTES de production-ready)

- **Riesgo alto – Desincronización ZMQ**: Si un solo nodo rota antes que otro → canal roto. **Mitigación obligatoria**: versión de key en handshake o dual-key window.
- **Riesgo alto – Secreto en repositorio/VM**: Hardcodear pubkey está bien, pero privada nunca debe tocar disco en producción salvo temporalmente.
- **Riesgo medio – Bootstrap problem**: ¿Cómo obtiene el primer token enterprise el sidecar? (necesitáis un “bootstrap token” muy restringido o approle + Kubernetes auth).
- **Riesgo medio – Performance y latencia**: Polling frecuente a Vault puede ser bottleneck. Preferir watch + cache en memoria.
- **Riesgo de disponibilidad**: Rotación mal hecha → outage total. Necesitáis feature flag + rollback rápido (Vault guarda todas las versiones).
- **Cumplimiento/auditoría**: Todas las rotaciones deben generar audit log inmutable (Vault ya lo hace + etcd watch).

### Recomendaciones adicionales
- Usar **Vault Transit** para firmas/verificación en vez de exportar la clave privada siempre que sea posible (mejor práctica enterprise).
- Considerar **短期** (short-lived) tokens + renewal + revocation list.
- Documentar todo esto en un nuevo **ADR-014: Enterprise Cryptographic Lifecycle**.

¿Quieres que profundicemos en alguna pieza concreta (ej. diagrama de secuencia de rotación, código de sidecar, o cómo extender el plugin-loader)?

El Consejo está listo para la siguiente pregunta.