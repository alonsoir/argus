Aironman DirtDiver, el informe del **DAY 156** es impecable: la integración de la **autonomía criptográfica** en el pipeline de producción es un hito crítico para la resiliencia de aRGus NDR. El cierre de **P0** con todos los tests en verde (50/50 en firewall, 3/3 en etcd-server, etc.) demuestra madurez técnica y rigor en la validación. Aquí tienes el análisis y recomendaciones del Consejo para cada pregunta, estructurado para acción inmediata:

---

---

## **📌 RESPUESTAS DEL CONSEJO**

---

### **Q1 — Persistencia del estado de autonomía: ¿tmpfs, etcd embebido o fichero regular?**
**Recomendación unánime: `c) Fichero regular en `/var/lib/argus/crypto-autonomy-state.json` + fsync + firma Ed25519****
- **Razón principal**: En infraestructura hospitalaria, un **reboot no planificado** durante `AUTONOMOUS` es el escenario crítico que debe cubrirse. `tmpfs` (/run) **no persiste** tras reboot, lo que invalidaría el propósito.
- **Alternativas descartadas**:
  - `a) tmpfs`: Insuficiente para el caso de uso (reboot = pérdida de estado).
  - `b) etcd embebido**: Añade complejidad innecesaria (dependencia adicional) y no resuelve el problema de forma más robusta que un fichero firmado.
- **Detalles de implementación**:
  - Usar **`O_SYNC`** (no solo `fsync`) para garantizar escritura atómica en el fichero.
  - Validar la firma **antes** de cargar el estado al arrancar (evitar ataques de replay).
  - Rotar el fichero con un **timestamp de expiración** (ej: 24h) para evitar estados obsoleto.
  - **Acción**: Registrar como **DEBT-AUTONOMY-STATE-PERSISTENCE-001** con prioridad **P0** (no P1).

---

### **Q2 — `poll_callback` como proxy de Vault: ¿Segunda suscripción ZMQ o mantener el placeholder?**
**Recomendación: Implementar el canal ZMQ SUB en firewall-acl-agent (no es sobreingeniería)**
- **Razón**:
  - El `poll_callback` actual es un **anti-patrón**: asume que la presencia del puntero `etcd_client` ≡ salud de Vault. Esto es frágil (ej: puntero válido pero Vault en estado degradado).
  - **Costo bajo**: El firewall ya tiene un `AutonomySubscriber` (ZMQ SUB) para el estado de autonomía. Añadir un **segundo topic** (`/argus/vault/health`) es trivial (mismo socket, filtro por topic).
  - **Beneficio**: Eliminas una **deuda técnica crítica** (DEBT-CRYPTO-RECONCILIATION-001) y alineas el firewall con el patrón de eventos ya establecido.
- **Alternativa descartada**: Mantener el placeholder **no es sostenible** para el MVP FEDER (riesgo de falsos positivos/negativos en el estado).
- **Acción**: Priorizar en **DAY 157** como parte de **P1 — DEBT-AUTONOMY-STATE-PERSISTENCE-001**.

---

### **Q3 — Integración de Suricata (ADR-046): ¿Eve JSON via file watcher o ZMQ directo?**
**Recomendación: Eve JSON via file watcher (como los CSVs actuales) + conector ZMQ opcional en fase 2**
- **Razón**:
  - **Mínimo riesgo**: El pipeline actual ya usa **file watchers** para CSVs (ej: sniffer, ml-detector). Suricata en modo **Eve JSON** (formato estándar) puede integrarse sin cambios arquitectónicos.
  - **Ventajas**:
    - **Desacoplamiento**: Suricata puede ejecutarse en un contenedor/VM separado sin depender de ZMQ.
    - **Reutilización**: El mismo watcher puede usarse para otros IDS (ej: Zeek).
    - **Debugging**: Los ficheros Eve JSON son **human-readable** y fáciles de auditar.
  - **ZMQ directo**: Solo recomendable si Suricata se ejecuta en el **mismo host** que aRGus y se requiere **latencia ultra-baja** (ej: <100ms). Para el MVP FEDER, el file watcher es suficiente.
- **Acción**:
  - Crear un **nuevo componente** `suricata-watcher` (similar a `sniffer-watcher`).
  - Usar **inotify** para detectar nuevos ficheros Eve JSON en `/var/log/suricata/`.
  - **Fase 2**: Evaluar ZMQ si se demuestra necesidad de tiempo real (ej: correlación con eventos de autonomía).

---

### **Q4 — ZMQ slow joiner: ¿ADR o nota técnica en BACKLOG?**
**Recomendación: Registrar como ADR (no solo nota técnica)**
- **Razón**:
  - El **slow joiner** es un **problema sistémico** que afectará a **cualquier componente futuro** que use ZMQ PUB/SUB en aRGus.
  - Un **ADR** (Architecture Decision Record) formaliza:
    1. El problema (pérdida de mensajes si SUB conecta antes que PUB).
    2. La solución adoptada (PUB bind **antes** que SUB connect).
    3. Consecuencias: Tests deben inicializar PUB primero (ya aplicado en DAY 156).
    4. Alternativas descartadas (ej: usar `ZMQ_CONFLATE` o `ZMQ_SYNC`).
  - **Beneficio**: Evita que futuros desarrolladores repitan el error (ej: en la integración de Suricata).
- **Acción**:
  - Crear **ADR-047: ZMQ PUB/SUB Message Loss Prevention**.
  - Incluir **ejemplo de código** (C++) con el patrón correcto.
  - Referenciar en el **BACKLOG** como dependencia para cualquier nueva integración ZMQ.

---

### **Q5 — Gestión de keypairs Ed25519: Estrategia para despliegue FEDER en CPD de UEx**
**Recomendación: Keypair estable por entorno (dev/staging/prod) + rotación controlada**
- **Estrategia**:
  1. **Entornos**:
    - **Desarrollo (EMECAS)**: Keypair generado dinámicamente por `vagrant up` (como ahora). Aislamiento por sesión.
    - **Staging/Producción (FEDER)**: Keypair **estático** almacenado en:
      - **Vault** (para producción): El keypair se inyecta en el despliegue via `argus-secrets` (ya integrado en el pipeline).
      - **Fichero cifrado** (para staging): `/etc/argus/keys/ed25519.pem` (montado como volumen en Kubernetes).
  2. **Rotación**:
    - **Automática**: Cada 90 días (alineado con políticas de seguridad de UEx).
    - **Manual**: Trigger via `argus-key-rotate` (script que genera nuevo keypair, firma los estados existentes y notifica a todos los nodos).
  3. **Backup**:
    - El keypair de producción debe tener **backup offline** (HSM o almacenamiento frío).
- **Acción**:
  - Documentar en **ADR-048: Keypair Management for aRGus NDR**.
  - Implementar **script de rotación** (`argus-key-rotate`) para DAY 158.

---

---
---
## **🎯 PRIORIDADES PARA DAY 157**
| Prioridad | Tarea | Responsable | Dependencias |
|-----------|-------|-------------|--------------|
| **P0** | Implementar persistencia de estado en `/var/lib/argus/` (Q1) | Alonso | - |
| **P0** | Añadir canal ZMQ SUB para salud de Vault en firewall (Q2) | Alonso | P0 de persistencia |
| **P1** | Crear ADR-047 (ZMQ slow joiner) | Consejo | - |
| **P1** | Diseñar `suricata-watcher` (Q3) | Equipo | - |
| **P2** | Esbozar ADR-048 (Keypair Management) | Consejo | - |

---
---
## **🔍 OBSERVACIONES ADICIONALES**
1. **Tests E2E**: El fix del **slow joiner** en ZMQ es un **hallazgo valioso**. Sugerimos:
  - Añadir un **test específico** que simule el escenario (SUB conecta antes que PUB) y verifique que no se pierden mensajes.
  - Documentar el fix en el **README.md** de `argus-zmq-utils`.

2. **Extensión de la SM (Q2 en el plan de mañana)**:
  - El **circuit breaker** para `EXTENDED_AUTONOMY` (30 días) es una buena idea, pero **debe ser configurable por entorno** (ej: 7 días en staging, 30 en producción).
  - Sugerimos usar **YAML** para la configuración (ej: `autonomy_config.yaml`).

3. **Firma de `/run/argus/etcd-bootstrap-status.json` (P1)**:
  - **Crítico**: Si este fichero se modifica, podría llevar a un **estado inconsistente** en el bootstrap. Priorizar su firma junto con la persistencia del estado.

4. **Suricata**:
  - Validar que el formato **Eve JSON** de Suricata incluye los campos necesarios para correlación con aRGus (ej: `timestamp`, `src_ip`, `dest_ip`, `alert.signature`).

---
---
## **❓ PREGUNTA FINAL AL CONSEJO**
El plan para **DAY 157** incluye **2 P1s** (persistencia de estado y firma de bootstrap) y **1 P0** (canal ZMQ en firewall). ¿Deberíamos **reclasificar la persistencia de estado a P0** dado su impacto en la resiliencia tras reboot? **El Consejo vota SÍ: P0.** ¿Confirmas, Aironman?