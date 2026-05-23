**Consejo de Sabios — Respuestas para DAY 161**
*(Enfoque práctico: priorizar **entrega FEDER** sin comprometer seguridad o calidad)*

---

---

### 🔧 **Q1 — ¿`.deb` o Vagrant box?**
**✅ Respuesta: `.deb` + Vagrant box (pero priorizar `.deb` para FEDER).**
- **`.deb`:**
  - **Ventaja:** Estándar para hardware físico (RPi5, N100). Permite actualizaciones incrementales (`apt upgrade`), gestión de dependencias, y es **requisito para producción**.
  - **Cómo:** Usar `dpkg-deb` o `cpack` en el pipeline para empaquetar binarios + configuración. Ejemplo:
    ```groovy
    stage('Build .deb') {
      steps {
        sh 'make package-deb'  // Genera libvault_provider_0.9.4_arm64.deb / x86_64.deb
      }
    }
    ```
- **Vagrant box:**
  - **Ventaja:** Validación rápida en entornos de desarrollo. Útil para **testing del pipeline** antes de deploy a hardware.
  - **Cómo:** Usar `vagrant package` para exportar la box tras provisionar. **No es bloqueante para FEDER**, pero sí para validación interna.
- **Acción DAY 161:**
  - **Pipeline:** Generar **ambos** (`.deb` para producción, Vagrant box para testing).
  - **Prioridad:** Si el tiempo apremia, **solo `.deb`** (la box se puede generar después).

---

---

### ⚙️ **Q2 — Valores naive en JSON contrato: ¿hardcoded o generados?**
**✅ Respuesta: Hardcoded para DAY 161, pero con **script de detección en BACKLOG**.**
- **Razón:**
  - El objetivo de DAY 161 es **validar el pipeline**, no optimizar rendimiento.
  - Los valores naive (ej: `HWM=1000`, `IO_threads=2`, `batch_size=64`) funcionan en **RPi5/N100** para el demo.
  - **Riesgo:** Hardcodear valores subóptimos puede causar fallos en hardware con menos recursos, pero es **aceptable para FEDER** (gate mínimo).
- **Implementación:**
  - **DAY 161:** Hardcodear valores en `config/contract.json` (ej: `"zmq": {"hwm": 1000, "io_threads": 2}`).
  - **Post-FEDER:** Crear script en **Python/Bash** que:
    1. Detecte CPUs (`nproc`) y RAM (`free -m`).
    2. Calcule valores mínimos seguros (ej: `io_threads = min(4, cpu_count)`).
    3. Genere el JSON dinámicamente en el pipeline.
  - **Issue:** Vincular a **BACKLOG-ZMQ-TUNING-001** (prioridad P1 post-FEDER).

---

---

### 🔐 **Q3 — Token enterprise en CI/CD: ¿Jenkins Credentials o fichero?**
**✅ Respuesta: **Jenkins Credentials Store** (tipo *Secret Text*) + `withCredentials`.**
- **Razón:**
  - **Seguridad:**
    - Jenkins Credentials Store **cifra** el token en disco (usando `JENKINS_HOME/secrets/`).
    - `withCredentials` inyecta el token **en memoria** (no en logs ni filesystem).
    - Permite **rotación** sin cambiar el pipeline (solo actualizar el credential).
  - **Alternativa (menos segura):** Fichero en la VM (ej: `/tmp/vault_token`) → **Riesgo:** Persiste en disco, visible en logs si se usa `cat`.
- **Implementación en Jenkinsfile:**
  ```groovy
  pipeline {
    agent any
    stages {
      stage('Test Enterprise Plugin') {
        steps {
          withCredentials([string(credentialsId: 'VAULT_ENTERPRISE_TOKEN', variable: 'VAULT_TOKEN')]) {
            sh '''
              export VAULT_TOKEN=$VAULT_TOKEN
              make test-enterprise-plugin
            '''
          }
        }
      }
    }
  }
  ```
- **Recomendación adicional:**
  - **Vault Agent:** Para producción, usar **AppRole** o **Kubernetes Auth** (evitar tokens estáticos).
  - **TTL:** Configurar en Vault un **TTL corto** (ej: 1h) para el token usado en CI/CD.

---

---

### ⚠️ **Q4 — ¿DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001 antes o después del pipeline?**
**✅ Respuesta: **ANTES. El pipeline **debe incluir estos tests como gates obligatorios**.**
- **Razón:**
  - **"Casa sin cimientos"**: Un pipeline que no valida el **wire protocol** (comunicación entre componentes) o el **E2E live delta** (flujo de datos real) **no garantiza calidad**.
  - **FEDER:** El gate requiere **estabilidad**, y estos tests son **críticos** para ello.
- **Acción DAY 161:**
  1. **Priorizar** cerrar **DEBT-WIRE-PROTOCOL-TEST-001** y **DEBT-E2E-LIVE-DELTA-001** **antes** de construir el pipeline.
  2. **Incluirlos en el pipeline** como etapas **bloqueantes**:
     ```groovy
     stage('Wire Protocol Tests') {
       steps { sh 'make test-wire-protocol' }
     }
     stage('E2E Live Delta Tests') {
       steps { sh 'make test-e2e-live-delta' }
     }
     ```
  3. **Si no se cierran a tiempo:** **No proceder con DAY 161**. Replanificar.

---

---
---
### 🏭 **Q5 — Vault dev mode en CI/CD: ¿aceptable para FEDER?**
**❌ Respuesta: **NO. Vault dev mode **no es aceptable para FEDER**.**
- **Problemas con dev mode:**
  - **In-memory:** Los secretos **desaparecen** al reiniciar Vault.
  - **No HA:** No soporta **unseal automático** (requiere manual `vault operator unseal`).
  - **Seguridad:** Token root **estático** (`root` por defecto), sin auditoría.
- **Solución para FEDER:**
  - **Requisito mínimo:** Vault en modo **producción** con:
    - **Storage backend:** `file` (para demo) o `raft` (para HA).
    - **Unseal keys:** Generar y almacenar en **HSM o ficheros cifrados** (ej: `vault operator seal` + `vault operator unseal`).
    - **Políticas:** Token con **TTL** y permisos mínimos (ej: solo lectura de `secret/argus/crypto`).
  - **Cuándo:** **DEBT-JENKINS-PROD-001 debe resolverse ANTES de BACKLOG-FEDER-001**.
    - **DAY 161:** Usar **dev mode para desarrollo del pipeline** (aceptable temporalmente).
    - **Post-DAY 161:** Crear **DEBT-JENKINS-PROD-002** para migrar a modo producción.
- **Implicación:**
  - **BACKLOG-FEDER-001** depende de **DEBT-JENKINS-PROD-001** → **Bloqueante**.

---

---
---
---
### 📌 **Resumen de Acciones para DAY 161**
| Decisión | Acción Concreta | Prioridad |
|----------|-----------------|-----------|
| **Q1** | Generar `.deb` (obligatorio) + Vagrant box (opcional) | **P0** |
| **Q2** | Hardcodear valores naive en JSON contrato | **P0** |
| **Q3** | Usar **Jenkins Credentials Store** + `withCredentials` | **P0** |
| **Q4** | **Cerrar DEBT-WIRE-PROTOCOL-TEST-001 y DEBT-E2E-LIVE-DELTA-001 ANTES del pipeline** | **P0 (bloqueante)** |
| **Q5** | Usar Vault dev mode en DAY 161, pero **DEBT-JENKINS-PROD-001 es bloqueante para FEDER** | **P0 (post-DAY 161)** |

---
---
### 🛠 **Ejemplo de Jenkinsfile para DAY 161**
```groovy
pipeline {
  agent any
  environment {
    VAULT_ADDR = 'http://127.0.0.1:8200'
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }
    stage('Bootstrap') {
      steps { sh 'make bootstrap' }
    }
    // ⚠️ Gates obligatorios (Q4)
    stage('Critical Tests') {
      parallel {
        stage('Wire Protocol') { steps { sh 'make test-wire-protocol' } }
        stage('E2E Live Delta') { steps { sh 'make test-e2e-live-delta' } }
        stage('All Tests') { steps { sh 'make test-all' } }
      }
    }
    // 🔐 Token seguro (Q3)
    stage('Enterprise Plugin Tests') {
      steps {
        withCredentials([string(credentialsId: 'VAULT_ENTERPRISE_TOKEN', variable: 'VAULT_TOKEN')]) {
          sh 'export VAULT_TOKEN=$VAULT_TOKEN && make test-enterprise-plugin'
        }
      }
    }
    // 📦 Artefactos (Q1)
    stage('Build .deb') {
      steps { sh 'make package-deb' }
    }
    stage('Build Vagrant Box') {
      steps { sh 'make vagrant-box' }
    }
    // 🚀 Deploy a VM de test
    stage('Deploy to Vagrant Test') {
      steps {
        sh 'vagrant up test-vm --provision'
      }
    }
  }
  post {
    always {
      sh 'make vault-dev-stop'  // Limpieza
    }
  }
}
```

---
---
### ⚡ **Recomendaciones Adicionales**
1. **Seguridad en CI/CD:**
  - **Vault Policy:** Crear una política **mínima** para el pipeline (ej: solo `read` en `secret/argus/crypto`).
  - **Jenkins Agents:** Usar **Docker agents** (aislamiento) en lugar de nodos bare-metal.
  - **Audit Logs:** Habilitar logs en Vault (`audit file file_path=/var/log/vault-audit.log`).

2. **Hardware Destino (RPi5/N100):**
  - **`.deb`:** Asegurar que el paquete **no dependa de Java** (el plugin es C++).
  - **Arquitecturas:** Generar **multi-arch** (ARM64 para RPi5, x86_64 para N100) en el pipeline:
    ```groovy
    stage('Build Multi-Arch .deb') {
      steps {
        sh 'make package-deb ARCH=arm64'
        sh 'make package-deb ARCH=x86_64'
      }
    }
    ```

3. **Validación FEDER:**
  - **Prueba de humo:** Desplegar el `.deb` en una **RPi5 real** (no solo Vagrant) antes del gate.
  - **Documentación:** Incluir un `README.deploy` con pasos para instalar el `.deb` y configurar Vault en producción.

4. **Deudas Técnicas:**
  - **BACKLOG-ZMQ-TUNING-001:** Priorizar **inmediatamente después de FEDER**.
  - **DEBT-JENKINS-PROD-001:** **Bloqueante para FEDER** → Asignar recursos **YA**.

---
---
**🎯 Conclusión:**
**DAY 161 puede avanzar con:**
✅ Pipeline que genera `.deb` + Vagrant box.
✅ Valores naive hardcodeados.
✅ Token en Jenkins Credentials.
✅ Tests críticos (wire protocol + E2E) **como pre-requisito**.
⚠️ **Vault dev mode es temporal** → **DEBT-JENKINS-PROD-001 debe resolverse antes de FEDER**.