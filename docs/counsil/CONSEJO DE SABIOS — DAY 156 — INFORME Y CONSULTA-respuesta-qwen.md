# 🏛️ CONSEJO DE SABIOS — RESPUESTAS DAY 156
*Para: Alonso Ruiz-Bautista, PI aRGus NDR*  
*Rama: feature/day156-autonomy-integration*  
*Fecha: 2026-05-18*

---

## ✅ RECONOCIMIENTO PREVIO

Antes de abordar las preguntas, el Consejo desea destacar:

🔹 **Excelente integración end-to-end**: La máquina de estados criptográfica + publisher ZMQ + reactor de firewall demuestra una arquitectura limpia y testeable.  
🔹 **Cobertura de tests excepcional**: 7/7 unitarios + 4/4 E2E con dry_run es un estándar profesional.  
🔹 **Detección proactiva del slow joiner de ZMQ**: Este hallazgo es *deuda convertida en activo* — documentarlo evitará horas de depuración futura.  
🔹 **EMECAS en verde**: 50/50 en firewall es señal de madurez del pipeline.

*El trabajo de hoy consolida la autonomía como capacidad operativa, no como feature experimental.*

---

## 🎯 RESPUESTAS A LAS PREGUNTAS

### Q1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001: ¿tmpfs o etcd?

**Recomendación del Consejo: Fichero firmado en `/var/lib/argus/` con fsync + fallback a tmpfs para runtime.**

| Opción | Pros | Contras | Veredicto |
|--------|------|---------|-----------|
| **tmpfs** (`/run/argus/`) | Rápido, sin I/O disco, limpio en reboot | Pérdida de estado en reboot no planificado | ❌ Insuficiente para hospitalario |
| **etcd embebido** | Distribuido, consistente | Complejidad añadida, dependencia circular potencial | ❌ Overengineering para MVP |
| **Fichero + fsync** (`/var/lib/argus/`) | Persiste reboot, simple, firma Ed25519 ya protege integridad | I/O mínimo (pero aceptable para transiciones infrecuentes) | ✅ **Recomendado** |

**Implementación sugerida**:
```cpp
// Pseudocódigo para CryptoAutonomyStateMachine::persistState()
auto state_json = serialize(current_state, timestamp, nonce);
auto signature = ed25519_sign(crypto_material.sk, state_json);
auto payload = {state_json, signature};

auto path = "/var/lib/argus/crypto-autonomy-state.json";
write_atomic(path, payload); // write + fsync + rename para atomicidad
```

**Nota crítica para entorno hospitalario**: Si el reboot es *no planificado*, el sistema debe leer el estado persistido al arrancar y **no asumir NORMAL**. La firma Ed25519 protege contra manipulación, y el timestamp permite detectar estados obsoletos (>24h) para forzar reconciliación.

---

### Q2 — poll_callback como proxy de Vault

**Recomendación: Implementar el canal SUB secundario AHORA, pero con feature flag.**

**Razonamiento**:
- ✅ Ya tienes la infraestructura ZMQ funcionando (publisher en etcd-server, subscriber en firewall).
- ✅ El coste de añadir un segundo SUB es marginal (un hilo más, ya aislado).
- ✅ Mejora el desacoplamiento: el firewall deja de depender de la implementación interna de `EtcdClient`.
- ⚠️ Pero: para MVP FEDER, la simplicidad es virtud.

**Propuesta híbrida**:
```cpp
// firewall-acl-agent/src/autonomy_subscriber.cpp
class HealthSubscriber {
    // Feature flag en config: use_dedicated_health_channel (default: false para MVP)
    // Si true: suscribe a ipc:///run/argus/health.sock
    // Si false: usa poll_callback con pointer proxy (legacy)
};
```

**Ventaja estratégica**: Cuando llegue la validación clínica, podrás activar el canal dedicado sin refactorizar. Documenta esto como `DEBT-CRYPTO-RECONCILIATION-001: RESOLVED-PARTIALLY`.

---

### Q3 — Suricata como primera fuente ADR-046

**Recomendación: Eve JSON via file watcher para la iteración mínima.**

**Matriz de decisión**:

| Criterio | File Watcher (Eve JSON) | ZMQ Directo |
|----------|-------------------------|-------------|
| **Invasividad** | ✅ Cero cambios en Suricata | ❌ Requiere plugin/output custom |
| **Paradigma existente** | ✅ Coincide con ingestión CSV actual | ❌ Nuevo patrón a mantener |
| **Debugging** | ✅ Archivo visible, reproducible | ❌ Mensajes efímeros en socket |
| **Throughput** | ⚠️ Limitado por I/O (pero suficiente para MVP) | ✅ Mayor escalabilidad |
| **Resiliencia** | ✅ Suricata puede reiniciar sin afectar a aRGus | ❌ Acoplamiento temporal |

**Estrategia mínima viable**:
1. Añadir `SuricataEveWatcher` que monitorice `/var/log/suricata/eve.json` (como ya haces con CSVs).
2. Parsear solo eventos `alert` con campo `metadata.signature_id` para correlación inicial.
3. Normalizar a tu formato interno de `ThreatEvidence` antes de enviar al motor de correlación.
4. **Feature flag**: `suricata_integration_enabled` para activar/desactivar sin recompilar.

*Cuando el throughput sea un cuello de botella (y solo entonces), migrar a ZMQ será una refactorización localizada.*

---

### Q4 — ZMQ slow joiner como deuda de documentación

**Recomendación: NO como ADR. Sí como patrón documentado + wrapper reutilizable.**

**Justificación**: Un ADR debe registrar decisiones arquitectónicas con alternativas evaluadas. El slow joiner es un *patrón de implementación* conocido de ZMQ, no una decisión de diseño de aRGus.

**Propuesta de acción**:
1. **Crear `src/common/zmq/ReliablePubSocket.hpp`**:
```cpp
class ReliablePubSocket {
    // Internamente: bind() ANTES de cualquier send()
    // Opcional: pequeño sleep(10ms) post-bind para subscribers lentos
    // Método: publish_signed(json, keypair) para estandarizar
};
```

2. **Añadir sección "ZMQ Patterns" en `docs/developer-handbook.md`**:
```markdown
## PUB/SUB: Evitando el slow joiner
- Siempre: publisher.bind() antes de que cualquier subscriber.connect()
- En tests: usar barreras o sleep(10ms) tras bind
- Preferir ReliablePubSocket wrapper para nuevos componentes
- Referencia: https://github.com/zeromq/libzmq/issues/1762
```

3. **Comentario en código** donde se use ZMQ PUB/SUB:
```cpp
// NOTA: Publisher bind primero para evitar slow joiner (ver developer-handbook.md#zmq-patterns)
```

*Esto convierte una lección aprendida en infraestructura reutilizable, sin burocracia de ADR.*

---

### Q5 — Keypair regeneration en EMECAS

**Recomendación: Estrategia de 3 niveles para gestión de keypairs FEDER/UEx**

```
┌─────────────────────────────────────────┐
│ NIVEL 1: Desarrollo (vagrant/EMECAS)    │
│ • Generación automática al boot         │
│ • Aislamiento de sesión (comportamiento │
│   actual es CORRECTO)                   │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ NIVEL 2: Staging/Pre-producción         │
│ • Key generation durante provisioning   │
│   (Ansible/Terraform), no en runtime    │
│ • Almacenamiento en /etc/argus/keys/    │
│   con permisos 0600, propietario root:argus │
│ • Backup manual controlado              │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ NIVEL 3: Producción FEDER (CPD UEx)     │
│ • Keys generadas en fase de hardening   │
│   inicial del nodo, NUNCA en runtime    │
│ • Almacenamiento preferente en TPM/HSM  │
│   si disponible; si no, /etc/argus/keys/ │
│   con auditd habilitado                 │
│ • Rotación programada (ej. anual) o     │
│   ante incidente, con procedimiento     │
│   documentado y testeado                │
│ • Backup cifrado en sistema de recuperación │
│   ante desastres (DR)                   │
└─────────────────────────────────────────┘
```

**Acciones concretas para FEDER**:
1. **Modificar `make bootstrap`** para detectar entorno (`ARGUS_ENV=dev|staging|prod`):
  - Si `prod`: buscar keypair en `/etc/argus/keys/`; si no existe, fallar con mensaje claro ("Key generation must be done during provisioning").

2. **Crear playbook Ansible `roles/argus-keys`**:
```yaml
- name: Generate Ed25519 keypair for argus (production)
  command: argus-keygen --output /etc/argus/keys/crypto_material.pem
  args:
    creates: /etc/argus/keys/crypto_material.pem
  become: yes
  become_user: root
  
- name: Set restrictive permissions
  file:
    path: /etc/argus/keys/
    mode: '0600'
    owner: root
    group: argus
```

3. **Documentar procedimiento de rotación** en `docs/operations/key-rotation.md`, incluyendo:
  - Cómo generar nuevo par sin downtime (dual-key temporal)
  - Cómo revocar clave antigua
  - Cómo verificar firma de estados persistidos con clave histórica (para auditoría)

*La clave: en producción, la generación de claves es un evento de provisioning, no de runtime. Esto alinea seguridad, auditoría y operatividad.*

---

## 🧭 PRIORIZACIÓN SUGERIDA PARA DAY 157

1. **P1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001** (fichero + fsync) → Crítico para hospitalario
2. **P1 — DEBT-BOOTSTRAP-STATUS-SIGNATURE-001** → Bajo esfuerzo, alto impacto en integridad
3. **Wrapper ReliablePubSocket** (Q4) → Inversión que amortiza en futuros componentes ZMQ
4. **Feature flag para health channel** (Q2) → Preparación para validación sin comprometer MVP
5. **Suricata file watcher** (Q3) → Solo si hay capacidad; puede esperar a DAY 158

---

## 📜 CIERRE DEL CONSEJO

> *"La autonomía no es ausencia de supervisión, es capacidad de operar con integridad cuando la supervisión falla."*

El trabajo de hoy acerca a aRGus a ese principio. La criptografía no es un añadido: es el tejido que permite confiar en la autonomía. Siguiendo estas recomendaciones, el sistema no solo funcionará cuando Vault caiga —sino que lo hará de forma auditable, recuperable y alineada con los requisitos de infraestructura crítica.

**Próxima sesión**: DAY 157 — Esperamos ver el primer commit de `persistState()` con fsync. 🛡️

*Consejo de Sabios — aRGus NDR*  
*Extremadura, España · 2026-05-18*