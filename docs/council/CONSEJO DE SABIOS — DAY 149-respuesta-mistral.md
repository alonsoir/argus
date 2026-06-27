**Dictamen del Consejo de Sabios — DAY 149 (CI/CD Criptográfica)**
*12 de mayo de 2026 | Respuesta unificada y priorizada*

---

---

## **📜 Resumen Ejecutivo**
**La arquitectura propuesta es sólida y alinea con las mejores prácticas en sistemas distribuidos seguros.**
El diseño **resuelve los problemas P0 críticos** (Jenkins SPoF, estado inconsistente ZeroMQ, Vault inmem) y **mitiga los P1** (disponibilidad vs. TODO O NADA, etcd comprometido).
**Recomendaciones clave:**
1. **Vault RNG es suficiente** para FEDER (Q1), pero **mezclar entropy externa** (RDRAND/TPM) es ideal para producción.
2. **Cache tmpfs es aceptable** (Q2) si se limita a **TTL corto** (ej: 5 min) y **no persiste en disco**.
3. **etcd como barrera pre-arranque** (Q3) **no es un problema de huevo/gallina** si etcd-server arranca **directamente con Vault** (sin depender de sí mismo).
4. **Vault backend `file` es suficiente para dev** (Q4), pero **`raft` es recomendable para prod**.
5. **Rotación atómica** (Q5) es **preferible** para seeds ChaCha20 (blast radius mínimo).
6. **Stage separado en Jenkinsfile** (Q6) para `provision_crypto.sh` (mejor visibilidad).
7. **Seeds por familia (ADR-021)** (Q7) para minimizar blast radius.

---
**Prioridad para DAY 150:**
1. **Implementar `provision_crypto.sh`** (Vault backend `file` + assert `dev≠prod`).
2. **Crear ADR-044** (documentar arquitectura CI/CD criptográfica).
3. **Prototipar `common/vault_client`** (GET seed + cache tmpfs + etcd register).

---

---

---

## **🔍 Respuestas Detalladas a Q1-Q7**

---

### **Q1 — Vault RNG vs Entropy Externa**
**✅ `vault write sys/tools/random` es suficiente para FEDER, pero no óptimo para producción.**

#### **Análisis:**
- **Vault RNG:**
    - Vault usa **`/dev/urandom`** (Linux) o **CSPRNG del sistema** (Windows/macOS) como fuente de entropy por defecto.
    - **NIST SP 800-90A/B/C** (estándar para RNG criptográficos) **no certifica Vault RNG**, pero:
        - `/dev/urandom` en Linux **es seguro** si el sistema tiene suficiente entropy (ej: servidores con TPM/HWRNG).
        - Vault **no usa RDRAND directamente**, pero el kernel Linux sí lo mezcla en `/dev/urandom` si está disponible.
    - **Riesgo:** Si el servidor Vault no tiene suficiente entropy (ej: VM sin HWRNG), `/dev/urandom` podría ser predecible.

- **Entropy externa adicional:**
    - **RDRAND (Intel):** Instrucción de hardware para RNG. **Vulnerable a backdoors** (ej: [CVE-2019-11135](https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-11135)), pero **mejora la entropy**.
    - **TPM (Trusted Platform Module):** Proporciona RNG certificado (NIST FIPS 140-2). **Ideal para producción**.
    - **getrandom() (syscall):** Usa el mismo pool que `/dev/urandom`, pero con bloqueo si no hay suficiente entropy.

#### **Recomendación:**
| Entorno | Fuente de Entropy | Justificación |
|---------|-------------------|---------------|
| **Dev (Vagrant)** | `vault write sys/tools/random` | Suficiente para pruebas. |
| **Prod (FEDER)** | `vault write sys/tools/random` + **mezclar RDRAND/TPM** | Cumple NIST SP 800-90B (entropía suficiente). |
| **Post-FEDER** | **TPM 2.0** (si hardware disponible) | Máximo nivel de seguridad. |

**Implementación para FEDER:**
```bash
# En provision_crypto.sh (prod):
# 1. Obtener entropy de TPM (si disponible)
tpm2_getrandom --hex 32 > /tmp/tpm_entropy.hex 2>/dev/null || true

# 2. Obtener entropy de RDRAND (si disponible)
rdrand_entropy=$(head -c 32 /dev/hwrng 2>/dev/null || echo "")

# 3. Mezclar con Vault RNG
combined_entropy=$(echo "$tpm_entropy$rdrand_entropy" | sha256sum | cut -d' ' -f1)
vault write sys/tools/random bytes=32 format=hex > /tmp/vault_random.hex
final_seed=$(echo "$combined_entropy$(cat /tmp/vault_random.hex)" | sha256sum | cut -d' ' -f1)

# 4. Almacenar en Vault
vault kv put argus/prod/seeds/sniffer value="$final_seed"
```
**Nota:** Si no hay TPM/RDRAND, `vault write sys/tools/random` es suficiente.

---
---

### **Q2 — Cache tmpfs: ¿Viola TODO O NADA?**
**✅ No viola TODO O NADA si se implementa correctamente.**

#### **Análisis:**
- **TODO O NADA (ADR-020):**
    - **Principio:** *"El pipeline no arranca sin criptografía completa."*
    - **Cache tmpfs no persiste en disco** → **No es un vector de ataque permanente**.
    - **TTL corto** (ej: 5 min) → **Ventana de exposición limitada**.

- **Modelo de amenaza:**
    - **Ataque 1:** Atacante accede a tmpfs (requiere **root** en el nodo).
        - **Mitigación:** tmpfs está en memoria **no swappeable** (`tmpfs size=10M,noatime,noswap`).
    - **Ataque 2:** Atacante fuerza reinicio del nodo para vaciar tmpfs y bloquear el arranque.
        - **Mitigación:** **Aceptable** (el nodo no arranca sin Vault, pero tmpfs acelera recuperación tras fallos temporales de Vault).

- **Alternativas:**
  | Opción | Ventajas | Desventajas |
  |--------|----------|-------------|
  | **Sin cache** | TODO O NADA puro. | **Latencia de arranque** (cada componente espera a Vault). |
  | **Cache tmpfs + TTL** | **Resiliencia** a fallos temporales de Vault. | Complejidad adicional. |
  | **Cache en disco cifrada** | Persiste tras reboot. | **Riesgo de exposición** si el disco es comprometido. |

#### **Recomendación:**
**✅ Usar cache tmpfs con TTL de 5 minutos.**
- **Implementación en `common/vault_client`:**
  ```cpp
  // Pseudocódigo
  std::string get_seed_from_vault_or_cache() {
      // 1. Intentar Vault primero
      auto seed = vault_client.get("argus/" + env + "/seeds/" + component);
      if (seed) {
          tmpfs_cache.store(component, seed, ttl=300); // 5 min
          return seed;
      }

      // 2. Fallback a tmpfs cache
      if (auto cached = tmpfs_cache.get(component)) {
          if (cached.is_valid()) {
              return cached.value();
          }
      }

      // 3. TODO O NADA: exit(1)
      std::cerr << "Vault unreachable and cache empty. Aborting." << std::endl;
      std::exit(1);
  }
  ```
- **Configuración de tmpfs:**
  ```bash
  # En /etc/fstab (o systemd-tmpfiles)
  tmpfs /var/run/argus/tmpfs tmpfs size=10M,noatime,noswap,mode=0700 0 0
  ```
- **Auditoría:**
    - **Loguear** cada uso de cache tmpfs (para detectar abusos).
    - **Alertar** si se usa cache >1 vez en 5 min (posible fallo de Vault).

---
---

### **Q3 — etcd como Barrera Pre-Arranque: ¿Huevo y Gallina?**
**✅ No hay problema de huevo/gallina si etcd-server arranca directamente con Vault.**

#### **Análisis:**
- **Dependencia circular aparente:**
  ```
  etcd-server necesita crypto → etcd-server registra crypto_ready → otros componentes esperan etcd.
  ```
- **Solución:**
    - **etcd-server es el único componente que NO depende de etcd para su crypto.**
    - **Flujo de arranque:**
        1. **etcd-server** arranca **sin etcd** (usa Vault directamente).
        2. etcd-server **registra su propio `crypto_ready` en sí mismo** (bypass temporal).
        3. **Otros componentes** esperan a que etcd-server esté listo (via HTTP health check).
        4. etcd-server **actúa como barrera** para el resto.

#### **Recomendación:**
- **etcd-server:**
    - **No usa `common/vault_client`** (para evitar dependencia circular).
    - **Obtiene su seed directamente de Vault** (via HTTP API).
    - **Expone `/health/crypto_ready`** (endpoint HTTP).
- **Otros componentes:**
    - **Esperan a que `/health/crypto_ready` de etcd-server retorne 200 OK.**
    - **Luego registran su propio `crypto_ready` en etcd.**

**Diagrama de secuencia:**
```
1. etcd-server → Vault: GET seed
2. etcd-server → etcd: PUT crypto_ready (self-register)
3. etcd-server → HTTP: Expose /health/crypto_ready
4. sniffer → etcd-server: GET /health/crypto_ready (wait)
5. sniffer → Vault: GET seed
6. sniffer → etcd: PUT crypto_ready
7. etcd → sniffer: ACK
8. etcd → ml-detector: "sniffer crypto_ready"
9. ml-detector → Vault: GET seed
10. ml-detector → etcd: PUT crypto_ready
...
11. etcd → ALL: "ALL crypto_ready" → ZeroMQ open
```

---
---

### **Q4 — Vault Backend: `file` vs `raft`**
**✅ `file` es suficiente para dev, pero `raft` es recomendable para prod.**

#### **Análisis:**
| Backend | Ventajas | Desventajas | Recomendación |
|---------|----------|-------------|---------------|
| **`file`** | Simple, sin dependencias. | **Single-point-of-failure** (fichero corrupto = pérdida de seeds). | ✅ **Dev** |
| **`raft`** | HA integrado, replicación automática. | Requiere **3+ nodos Vault** (complejidad). | ✅ **Prod** |
| **`consul`** | Usa Consul existente. | **Dependencia externa**. | ❌ No recomendado |

#### **Recomendación:**
- **Dev (Vagrant):**
    - Usar **`file`** (suficiente para pruebas).
    - **Backup automático** de `/vault/file` a `/backup/vault` cada hora.
    - **`provision_crypto.sh`** debe **restaurar desde backup** si el fichero se corrompe.
- **Prod (FEDER):**
    - Usar **`raft`** con **3 nodos Vault** (mínimo para HA).
    - **Topología:**
      ```
      Vault Node 1 (Leader) — Vault Node 2 (Follower) — Vault Node 3 (Follower)
      ```
    - **Backup:** Snapshots automáticos a **S3 cifrado** (o equivalente).

**Implementación para DAY 150:**
```bash
# En Vagrantfile (dev):
vault server -dev -dev-backend=file -dev-backup-dir=/backup/vault

# En producción (FEDER):
vault server -config=/etc/vault.d/raft.hcl
```
**Configuración `raft.hcl` (prod):**
```hcl
storage "raft" {
  path    = "/vault/data"
  node_id = "vault-node-1"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = false
  tls_cert_file = "/etc/vault/tls/vault.crt"
  tls_key_file  = "/etc/vault/tls/vault.key"
}

service_registration "kubernetes" {}
```

---
---

### **Q5 — Rotación Coordinada: Blast Radius Mínimo**
**✅ Rotación atómica (todos o ninguno) es preferible para seeds ChaCha20.**

#### **Análisis:**
- **Modelo actual (ADR-004):**
    - **Cooldown window** para HMAC keys (evita solapamiento).
    - **Grace period** para permitir drenado de mensajes en vuelo.
- **Seeds ChaCha20:**
    - **No son claves HMAC**, sino **semillas para derivar keypairs Ed25519**.
    - **Riesgo de rotación parcial:**
        - Si `sniffer` usa `seed_v2` y `ml-detector` usa `seed_v1`, **los mensajes entre ellos fallarán** (claves incompatibles).
        - **Ventana de ataque:** Un atacante podría **inyectar tráfico malicioso** durante la rotación.

- **Opciones:**
  | Opción | Blast Radius | Complejidad | Recomendación |
  |--------|--------------|-------------|---------------|
  | **Rotación por componente** | Alto (inconsistencia temporal). | Baja. | ❌ No recomendado |
  | **Rotación atómica (todos a la vez)** | Bajo (ventana mínima). | Media (requiere coordinación). | ✅ **Recomendado** |
  | **Rotación por familia (ADR-021)** | Medio (inconsistencia dentro de familia). | Alta. | ⚠ Compromiso |

#### **Recomendación:**
**✅ Rotación atómica para seeds ChaCha20.**
- **Flujo:**
    1. **Jenkins** genera `seed_v2` y la almacena en Vault (sin activar).
    2. **etcd** notifica a todos los componentes: *"Preparar rotación a `seed_v2`"*.
    3. **Todos los componentes:**
        - Obtienen `seed_v2` de Vault.
        - Derivan el nuevo keypair **en memoria** (sin usar aún).
        - **No cierran ZeroMQ** (siguen usando `seed_v1`).
    4. **etcd** verifica que **todos** han confirmado la preparación.
    5. **etcd** envía señal: *"Activar `seed_v2`"*.
    6. **Todos los componentes:**
        - **Cierran ZeroMQ** (drenan mensajes en vuelo).
        - **Activan `seed_v2`** (nuevo keypair).
        - **Abrir ZeroMQ** con nuevas claves.
    7. **etcd** marca la rotación como completada.

- **Ventana de incompatibilidad:**
    - **Máximo: tiempo de drenado de ZeroMQ** (ej: 1-2 segundos).
    - **Mitigación:** Usar **timeouts cortos** en ZeroMQ (`ZMQ_LINGER=1000`).

**Implementación en etcd:**
```go
// Pseudocódigo (etcd rotation coordinator)
func (s *RotationServer) HandleRotationRequest() {
    // 1. Generar nueva seed (Jenkins → Vault)
    newSeedPath := vault.GenerateSeed("argus/prod/seeds_v2")

    // 2. Notificar a todos los componentes
    for _, component := range topology.Components {
        if !component.PrepareRotation(newSeedPath) {
            s.Rollback(newSeedPath) // Abortar si alguno falla
            return
        }
    }

    // 3. Activar rotación
    for _, component := range topology.Components {
        component.ActivateSeed(newSeedPath)
    }

    // 4. Marcar como completada
    vault.MarkSeedActive(newSeedPath)
    vault.DeleteOldSeed(oldSeedPath) // Opcional: mantener 1 versión anterior
}
```

---
---

### **Q6 — `provision_crypto.sh` en Jenkinsfile: Stage Separado vs Integrado**
**✅ Stage separado en Jenkinsfile ("Provision Crypto").**

#### **Análisis:**
| Opción | Ventajas | Desventajas |
|--------|----------|-------------|
| **Stage separado** | **Visibilidad clara** (fallos de crypto son explícitos). | **Menor atomicidad** (si falla, Jenkinsfile sigue). |
| **Integrado en `bootstrap`** | **Atomicidad** (todo o nada). | **Menor visibilidad** (fallos de crypto se mezclan con otros). |

#### **Recomendación:**
**✅ Stage separado + `failFast: true`.**
- **Jenkinsfile:**
  ```groovy
  pipeline {
      agent any
      stages {
          stage('Provision Crypto') {
              steps {
                  sh './scripts/jenkins/provision_crypto.sh'
              }
              post {
                  failure {
                      error "Provisioning crypto failed. Aborting pipeline."
                  }
              }
          }
          stage('Build') { ... }
          stage('Test') { ... }
          stage('Deploy') { ... }
      }
      options {
          failFast true // Detener el pipeline al primer fallo
      }
  }
  ```
- **Ventajas:**
    - **Visibilidad:** Los fallos de crypto son **inmediatamente visibles**.
    - **Atomicidad:** `failFast: true` asegura que el pipeline se detiene si `provision_crypto.sh` falla.
    - **Debugging:** Más fácil de depurar (logs separados).

---
---

### **Q7 — Seed Families (ADR-021): ¿Paths por Familia o por Componente?**
**✅ Paths por familia (minimiza blast radius).**

#### **Análisis:**
- **ADR-021 define familias de canal:**
    - **Family A:** `sniffer ↔ ml-detector` (comuncación interna).
    - **Family B:** `ml-detector ↔ firewall` (acciones de bloqueo).
    - **Family C:** `sniffer ↔ etcd` (coordinación).
- **Opciones:**
  | Opción | Blast Radius | Complejidad | Recomendación |
  |--------|--------------|-------------|---------------|
  | **Por componente** | Alto (comprometer `sniffer` = acceder a todas sus seeds). | Baja. | ❌ No recomendado |
  | **Por familia** | Medio (comprometer Family A no afecta a Family B). | Media. | ✅ **Recomendado** |
  | **Seed única global** | Mínimo (una seed para todo). | Mínima. | ❌ Riesgo inaceptable |

#### **Recomendación:**
**✅ Paths por familia en Vault.**
- **Estructura:**
  ```
  argus/
  ├── dev/
  │   ├── families/
  │   │   ├── family_A/seed  # sniffer + ml-detector
  │   │   ├── family_B/seed  # ml-detector + firewall
  │   │   └── family_C/seed  # sniffer + etcd
  │   └── components/       # Opcional: seeds por componente (fallback)
  └── prod/
      ├── families/
      │   ├── family_A/seed
      │   ├── family_B/seed
      │   └── family_C/seed
      └── components/
  ```
- **Ventajas:**
    - **Blast radius limitado:** Comprometer una familia no afecta a las demás.
    - **Alinea con ADR-021** (familias de canal).
    - **Flexibilidad:** Si un componente pertenece a múltiples familias (ej: `ml-detector` en A y B), puede usar **múltiples seeds**.

**Implementación:**
- **`provision_crypto.sh`:**
  ```bash
  # Generar seed para Family A
  vault kv put argus/dev/families/family_A seed="$(vault random -format=hex 32)"

  # Asignar a componentes de Family A
  vault kv put argus/dev/components/sniffer family="family_A"
  vault kv put argus/dev/components/ml-detector family="family_A"
  ```
- **`common/vault_client`:**
  ```cpp
  std::string get_seed() {
      auto family = config.get_family(); // Ej: "family_A"
      auto seed_path = "argus/" + env + "/families/" + family + "/seed";
      return vault_client.get(seed_path);
  }
  ```

---
---

---
## **📌 Resumen de Decisiones para DAY 150**

| Pregunta | Decisión | Acción Concreta |
|----------|----------|-----------------|
| **Q1** | Vault RNG + entropy externa (RDRAND/TPM) | Modificar `provision_crypto.sh` para mezclar fuentes. |
| **Q2** | Cache tmpfs + TTL 5 min | Implementar en `common/vault_client`. |
| **Q3** | etcd-server arranca con Vault (sin dependencia circular) | Modificar flujo de arranque de etcd. |
| **Q4** | Vault backend `file` (dev) + `raft` (prod) | Configurar en Vagrant y prod. |
| **Q5** | Rotación atómica para seeds ChaCha20 | Implementar en etcd rotation coordinator. |
| **Q6** | Stage separado en Jenkinsfile | Crear stage "Provision Crypto". |
| **Q7** | Paths por familia (ADR-021) | Estructura `argus/{env}/families/{family}/seed`. |

---
---
## **🚀 Orden de Implementación para DAY 150**
1. **`provision_crypto.sh` (Q1, Q4, Q7):**
    - Vault backend `file` (dev).
    - Generar seeds por familia (ADR-021).
    - Assert `dev≠prod`.
    - Mezclar entropy (RDRAND/TPM si disponible).
2. **ADR-044 (Documentación):**
    - Documentar arquitectura CI/CD criptográfica.
    - Incluir diagramas de flujo (Vault → etcd → componentes).
3. **`common/vault_client` (Q2, Q3):**
    - GET seed desde Vault (por familia).
    - Cache tmpfs + TTL 5 min.
    - etcd register `crypto_ready`.
4. **etcd rotation coordinator (Q5):**
    - Lógica de rotación atómica.
    - Timeout y rollback.

---
---
## **⚠ Riesgos Residuales y Mitigaciones**

| Riesgo | Mitigación |
|--------|------------|
| **Vault comprometido en prod** | Usar **Vault HA (`raft`)** + **backup cifrado a S3**. |
| **etcd comprometido** | etcd **no tiene acceso a seeds** (solo coordina). |
| **Cache tmpfs abusada** | **TTL corto (5 min)** + **loguear cada acceso**. |
| **Rotación atómica fallida** | **Timeout de 10s** + **rollback automático**. |
| **Jenkins comprometido** | **Jenkins solo dispara procesos** (no genera seeds). |

---
---
## **💡 Recomendaciones Adicionales**
1. **Auditoría de Vault:**
    - **Habilitar logging detallado** en Vault (para detectar accesos no autorizados).
    - **Alertas en Slack/Email** para eventos críticos (ej: `vault kv put` en paths de seeds).
2. **Pruebas de Caos:**
    - **Simular fallo de Vault** durante el arranque (¿los componentes usan cache tmpfs?).
    - **Simular fallo de etcd** (¿los componentes se bloquean correctamente?).
3. **Documentación de Recuperación:**
    - **Procedimiento para restaurar Vault desde backup** (dev y prod).
    - **Procedimiento para rotación manual de seeds** (en caso de emergencia).

---
---
## **📝 Conclusión Final**
**La arquitectura propuesta es robusta y lista para implementación.**
- **Prioridad DAY 150:** `provision_crypto.sh` + ADR-044 + `common/vault_client`.
- **P0 resueltos:** Jenkins SPoF, estado inconsistente ZeroMQ, Vault inmem.
- **P1 mitigados:** Disponibilidad vs. TODO O NADA, etcd comprometido.
- **FEDER ready:** Con esta implementación, el pipeline CI/CD criptográfico **cumple los requisitos de seguridad**.

**Para el Consejo:**
¿Estáis de acuerdo con **priorizar la implementación de `provision_crypto.sh` y `common/vault_client` para DAY 150**? **Sí**, es el camino crítico para desbloquear el resto del pipeline.