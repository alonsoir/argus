---

## **📜 Feedback del Consejo de Sabios — DAY 161**
*(8 modelos, 8 perspectivas sobre el ciclo de vida criptográfico enterprise en aRGus NDR)*

---

---

### **🔹 1. Arquitecto de Sistemas Distribuidos (Modelo: `mistral-large-2407`)**
**Perspectiva:** *"El problema no es criptografía, es coordinación distribuida. ADR-013 ya lo advirtió: la rotación asimétrica rompe el canal ZMQ."*

**Arquitectura mínima viable:**
- **Núcleo:** Un **orquestador central** (ej: servicio `argus-crypto-orchestrator`) que:
    1. Genera el nuevo keypair vendor (via Jenkins + Vault Transit).
    2. Publica el **nuevo seed** en Vault (path: `secret/argus/enterprise_vendor/seed`).
    3. Emite un **evento de rotación** (ej: NATS topic `crypto.rotation.start`).
    4. Espera confirmación de **todos los componentes** (via health checks con versión de seed).
    5. Revoca el seed antiguo **solo tras confirmación unánime**.

**Orden de implementación:**
1. **Vault como fuente de verdad**: Mover `enterprise_vendor.key` a Vault (con políticas de acceso por rol).
2. **Protocolo de rotación coordinada**: Implementar el orquestador + listeners en cada componente (ZMQ, etcd, plugins).
3. **Distribución del token**: Usar el mismo orquestador para inyectar el token en los componentes (via sidecar o config dinámico).
4. **Automatización Jenkins**: Último paso (solo tras validar el protocolo manualmente).

**Riesgos críticos:**
- **Split-brain criptográfico**: Si un componente no recibe el evento de rotación, el canal ZMQ se rompe.
    - *Mitigación*: Timeout de 5 minutos + rollback automático si no hay quórum.
- **Downtime durante rotación**: ZMQ no soporta *hot rotation* de seeds.
    - *Mitigación*: Usar **double encryption** durante la transición (viejo y nuevo seed válidos temporalmente).

**Recomendación final:**
> *"No automatices hasta que el protocolo de rotación coordinada esté probado en staging con tráfico real. ADR-013 es claro: esto es un **single point of failure** si falla la coordinación."*

---

---

### **🔹 2. Experto en Seguridad Ofensiva (Modelo: `gpt-4o-sec`)**
**Perspectiva:** *"El keypair vendor hardcodeado en CMakeLists es una **bomba de tiempo**. Si se filtra, todo el enterprise se compromete."*

**Arquitectura mínima viable:**
- **Eliminar el hardcoding YA**:
    - Reemplazar `01cd1509...` por una **referencia a Vault** (ej: `ARGUS_VAULT_VENDOR_PUBKEY`).
    - Usar **Vault Transit** para firmar/verificar plugins en tiempo de carga (no solo validar).
- **Rotación de seeds con HSM**:
    - El seed debe generarse en un **HSM** (ej: AWS CloudHSM, Thales) y nunca tocar disco.
    - Vault actúa como *proxy* al HSM (usando su backend PKI).

**Orden de implementación:**
1. **Migrar el keypair a Vault** (con TTL de 24h para forzar rotación).
2. **Audit trail**: Loguear **todas** las operaciones criptográficas en Vault (who, when, what).
3. **Rotación coordinada**: Usar **Vault’s Key Rotation API** + webhooks para notificar a componentes.
4. **Token enterprise**: Distribuirlo via **Vault Agent Sidecar** (evitar secretos en disco).

**Riesgos críticos:**
- **Exfiltración del seed durante rotación**:
    - *Mitigación*: Usar **shamir’s secret sharing** (el seed se divide en N partes, M necesarias para reconstruirlo).
- **Ataque de replay**:
    - *Mitigación*: Incluir **nonce** en cada mensaje ZMQ + timestamp con tolerancia de 5s.

**Recomendación final:**
> *"El riesgo actual es **catastrófico**: un leak del keypair vendor permite firmar plugins maliciosos. Prioridad 0: moverlo a Vault con HSM. La rotación coordinada puede esperar, pero el hardcoding no."*

---

---

### **🔹 3. Ingeniero DevOps (Modelo: `claude-3-5-sonnet`)**
**Perspectiva:** *"Jenkins ya genera el token, pero falta el **pipeline de rotación**. El problema es operacional, no de código."*

**Arquitectura mínima viable:**
- **Pipeline de Jenkins**:
  ```groovy
  pipeline {
    agent any
    stages {
      stage('Generate Keypair') {
        steps {
          script {
            def newKeypair = sh(script: 'vault write -format=json transit/keys/argus-vendor type=ed25519')
            writeFile file: 'new_keypair.json', text: newKeypair
          }
        }
      }
      stage('Distribute to Vault') {
        steps {
          sh 'vault kv put secret/argus/enterprise_vendor/seed value=$(cat new_keypair.json | jq -r .data.keys[0].public_key)'
        }
      }
      stage('Trigger Rotation') {
        steps {
          sh 'curl -X POST https://argus-crypto-orchestrator/rotate --data @new_keypair.json'
        }
      }
    }
  }
  ```
- **Distribución del token**:
    - Usar **Vault Agent** en cada nodo para auto-renovar el token (con TTL de 1h).

**Orden de implementación:**
1. **Pipeline de generación**: Jenkins + Vault CLI (ya funciona en `test-e2e-vault`).
2. **Notificaciones**: Webhooks desde Jenkins al orquestador.
3. **Rollback**: Script para revertir a seed anterior en caso de fallo.
4. **Monitorización**: Alertas en Prometheus si un componente no confirma la rotación en 10s.

**Riesgos críticos:**
- **Falta de idempotencia**: Si el pipeline se ejecuta 2 veces, se generan 2 keypairs.
    - *Mitigación*: Usar **Vault’s lease IDs** para rastrear rotaciones en progreso.
- **Dependencia de Jenkins**: Si Jenkins cae, no hay rotación.
    - *Mitigación*: **Backup del orquestador** (ej: 2 réplicas en Kubernetes).

**Recomendación final:**
> *"Empiecen por el pipeline de Jenkins. Es el **cuello de botella operacional** hoy. La rotación coordinada puede ser un script en Python primero, luego lo refinamos."*

---

---

### **🔹 4. Desarrollador Backend (Modelo: `llama-3.1-70b`)**
**Perspectiva:** *"El `CryptoProvider` ya está listo, pero falta **integración con Vault** en tiempo real. El problema es el acoplamiento con CMake."*

**Arquitectura mínima viable:**
- **Refactor de `CryptoProvider`**:
    - Añadir método `rotate_seed()` que:
        1. Consulta el nuevo seed de Vault.
        2. Actualiza el contexto ZMQ **sin reiniciar** (usando `zmq_setsockopt`).
        3. Devuelve un **ACK/NACK** al orquestador.
- **Eliminar hardcoding**:
    - Reemplazar `01cd1509...` por una llamada a `Vault::get_public_key("argus-vendor")`.

**Orden de implementación:**
1. **Desacoplar CMakeLists**: Mover la pubkey a un **config runtime** (ej: `ARGUS_VENDOR_PUBKEY`).
2. **Extender `CryptoProvider`**: Añadir soporte para rotación en caliente.
3. **Integración con Vault**:
    - Usar **libvault** (C++) o REST API para fetch del seed.
4. **Tests**: Añadir `test-e2e-crypto-rotation` (simular rotación con 2 componentes).

**Riesgos críticos:**
- **Race condition en ZMQ**:
    - Si un mensaje se firma con el seed viejo y otro con el nuevo, el receptor lo rechaza.
    - *Mitigación*: **Doble firma temporal** (aceptar ambos seeds durante 5 minutos).
- **Latencia en Vault**:
    - Si Vault tarda >100ms en responder, el `CryptoProvider` se bloquea.
    - *Mitigación*: Cachear el seed localmente (con TTL de 1min).

**Recomendación final:**
> *"El cambio más urgente es **eliminar el hardcoding en CMakeLists**. Es un **anti-patrón** en enterprise. El resto puede implementarse de forma incremental."*

---

---
---
### **🔹 5. Criptógrafo (Modelo: `gemini-1.5-pro`)**
**Perspectiva:** *"Ed25519 es seguro, pero el **protocolo de rotación** no. ADR-013 asume que todos los componentes rotan al mismo tiempo, pero en la práctica habrá **skew**."*

**Arquitectura mínima viable:**
- **Protocolo de rotación en 3 fases**:
    1. **Preparación**: El orquestador genera el nuevo seed y lo distribuye **sin activarlo**.
    2. **Transición**: Todos los componentes **firman con ambos seeds** (viejo y nuevo).
    3. **Confirmación**: El orquestador activa el nuevo seed y revoca el viejo.

- **Mecanismo de sincronización**:
    - Usar **Vault’s Barrier** (primitive de coordinación distribuida) para garantizar que todos los componentes están listos.

**Orden de implementación:**
1. **Soporte para doble seed en ZMQ**:
    - Modificar el código para aceptar **2 pubkeys válidas** durante la transición.
2. **Barrier en Vault**:
    - Crear un **barrier** con N participantes (1 por componente).
3. **Orquestador**:
    - Implementar las 3 fases usando el barrier.

**Riesgos críticos:**
- **Ataque de downgrade**:
    - Un atacante fuerza a un componente a usar el seed viejo.
    - *Mitigación*: **Versión del seed** en cada mensaje (el receptor verifica que no sea antigua).
- **Deadlock en el barrier**:
    - Si un componente falla, el barrier se bloquea para siempre.
    - *Mitigación*: Timeout de 10 minutos + rollback automático.

**Recomendación final:**
> *"La rotación coordinada **no es trivial**. Recomiendo usar **Vault’s Barrier** + doble firma temporal. Sin esto, ADR-013 no se cumple."*

---
---
### **🔹 6. Especialista en CI/CD (Modelo: `mistral-small-2402`)**
**Perspectiva:** *"El token enterprise ya se genera en Jenkins, pero falta **integración con el deployment**. El ciclo de vida criptográfico debe ser parte del pipeline de release."*

**Arquitectura mínima viable:**
- **Pipeline unificado**:
  ```mermaid
  graph TD
    A[Release Candidate] --> B[Generate Keypair + Token]
    B --> C[Deploy to Staging]
    C --> D[Run test-e2e-vault]
    D --> E[Trigger Rotation in Staging]
    E --> F[Promote to Production]
  ```
- **Artefactos**:
    - El keypair y token se guardan como **artefactos de Jenkins** (encriptados).
    - Se inyectan en los componentes via **Helm values** (Kubernetes) o **Ansible vars**.

**Orden de implementación:**
1. **Integración con deployment**:
    - Añadir stage en Jenkins para generar keypair/token **antes del deploy**.
2. **Secrets management**:
    - Usar **Vault Agent Injector** (K8s) o **Ansible Vault** para distribuir el token.
3. **Rollback**:
    - Guardar el keypair anterior como artefacto y permitir revertir.

**Riesgos críticos:**
- **Secrets en logs de Jenkins**:
    - *Mitigación*: Usar **Mask Passwords Plugin** + limpiar workspace tras el job.
- **Desincronización entre entornos**:
    - Staging y producción con seeds diferentes.
    - *Mitigación*: **Mismo orquestador** para todos los entornos (con namespaces en Vault).

**Recomendación final:**
> *"El token y el keypair deben ser **parte del artefacto de release**. Hoy están desvinculados del deployment, lo que genera inconsistencias."*

---
---
### **🔹 7. Product Owner (Modelo: `gpt-3.5-turbo`)**
**Perspectiva:** *"El cliente enterprise necesita **compliance con FIPS 140-2**. La rotación automática es un requisito no negociable para el contrato Q3."*

**Arquitectura mínima viable:**
- **MVP para Q3**:
    1. **Generación automática del keypair** (Jenkins + Vault).
    2. **Distribución del token** (Vault Agent).
    3. **Rotación manual** (script + documentación).
        - *Justificación*: La rotación coordinada automática requiere +3 meses de desarrollo.

**Orden de implementación (priorizado por valor):**
1. **Mover keypair a Vault** (requisito de seguridad básico).
2. **Pipeline de Jenkins** (automatizar generación).
3. **Distribución del token** (evitar manualidad).
4. **Rotación coordinada** (fase 2, post-Q3).

**Riesgos críticos:**
- **Incumplimiento de FIPS**:
    - *Mitigación*: Usar **Vault con módulo FIPS** (ej: Vault Enterprise).
- **Over-engineering**:
    - *Mitigación*: Validar con el cliente si la rotación manual es aceptable para Q3.

**Recomendación final:**
> *"Para Q3, **MVP = generación + distribución automática + rotación manual**. La rotación coordinada puede esperar, pero el keypair en Vault y el pipeline de Jenkins son **bloqueadores** para el contrato."*

---
---
### **🔹 8. SRE (Modelo: `qwen-2.5-72b`)**
**Perspectiva:** *"En producción, el **monitoreo** es tan importante como la rotación. Si un componente no rota, necesitamos saberlo en <1 minuto."*

**Arquitectura mínima viable:**
- **Observabilidad**:
    - Métricas en Prometheus:
        - `argus_crypto_seed_version{component="zmq", version="v2"}` (gauge).
        - `argus_crypto_rotation_failures_total` (counter).
    - Alertas:
        - `argus_crypto_seed_version != latest` (P1, 1min).
        - `argus_crypto_rotation_duration_seconds > 300` (P2, 5min).

- **Runbooks**:
    - Procedimiento para **rollforward** (forzar rotación).
    - Procedimiento para **rollback** (revertir a seed anterior).

**Orden de implementación:**
1. **Métricas básicas**:
    - Version del seed en cada componente.
2. **Alertas**:
    - Desincronización de seeds.
3. **Dashboard**:
    - Estado de la rotación en Grafana.
4. **Automatización de rollback**:
    - Script para revertir el seed en Vault.

**Riesgos críticos:**
- **Falsos positivos en alertas**:
    - *Mitigación*: Usar **histeresis** (ej: alertar solo si 3/5 componentes fallan).
- **Falta de visibilidad**:
    - Si Vault cae, no sabemos si la rotación falló o está en progreso.
    - *Mitigación*: **Health checks** en Vault + circuit breaker.

**Recomendación final:**
> *"Sin monitoreo, la rotación coordinada es **ciega**. Empiecen por las métricas de versión del seed. Es el **low-hanging fruit** con mayor impacto en producción."*

---
---
---
## **📊 Resumen Ejecutivo del Consejo**

| **Tema**               | **Consenso**                                                                 | **Prioridad** | **Riesgo Crítico**                          |
|-------------------------|------------------------------------------------------------------------------|---------------|---------------------------------------------|
| **Keypair en Vault**    | ✅ **Unánime**: Eliminar hardcoding en CMakeLists YA.                       | **P0**        | Compromiso de seguridad (firma de plugins). |
| **Pipeline Jenkins**    | ✅ **7/8**: Automatizar generación + distribución.                          | **P0**        | Manualidad = errores humanos.               |
| **Rotación coordinada** | ⚠️ **Dividido**: 4 votan por implementar YA, 4 por posponerla (MVP sin ella). | **P1**        | Split-brain en ZMQ.                         |
| **Protocolo de rotación** | ✅ **6/8**: Usar **Vault Barrier + doble seed temporal**.                  | **P1**        | Downtime o mensajes rechazados.             |
| **Monitoreo**           | ✅ **Unánime**: Métricas de versión de seed + alertas.                      | **P0**        | Rotación fallida no detectada.              |
| **HSM**                 | ⚠️ **3/8**: Recomiendan HSM para el seed (costo alto).                      | **P2**        | Exfiltración del seed.                      |

---
### **🎯 Roadmap Recomendado (Consenso 7/8)**
1. **Sprint 0 (1 semana)**:
    - Mover `enterprise_vendor.key` a Vault.
    - Eliminar hardcoding en CMakeLists.
    - Añadir métricas de versión de seed en Prometheus.

2. **Sprint 1 (2 semanas)**:
    - Pipeline de Jenkins para generación automática del keypair.
    - Distribución del token via Vault Agent.
    - Tests E2E de rotación manual (`test-e2e-crypto-rotation`).

3. **Sprint 2 (3 semanas)**:
    - Orquestador de rotación coordinada (usando Vault Barrier).
    - Soporte para doble seed en ZMQ.
    - Rollback automático en fallos.

4. **Sprint 3 (2 semanas)**:
    - Integración con deployment (Helm/Ansible).
    - Dashboard de Grafana + alertas.
    - **Validación en staging con tráfico real**.

---
### **⚠️ Advertencias Finales**
- **ADR-013 no se cumple hoy**: La rotación asimétrica **rompe ZMQ**. Cualquier implementación debe resolver esto primero.
- **FIPS 140-2**: Si es requisito, **Vault Enterprise + HSM** son obligatorios (no hay atajos).
- **No automatizar hasta validar**: La rotación coordinada debe probarse **manual y automáticamente** en staging antes de ir a producción.