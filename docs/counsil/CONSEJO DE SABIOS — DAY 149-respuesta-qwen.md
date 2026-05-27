**CONSEJO DE SABIOS — DICTAMEN TÉCNICO CI/CD CRIPTOGRÁFICO — DAY 149**
*Respuestas expertas a Q1-Q7, fundamentadas en NIST, libsodium, etcd Raft y operabilidad FEDER.*

---

## 🎯 VEREDICTO GLOBAL

**ARQUITECTURA APROBADA CON REFINAMIENTOS** ✅

El diseño post-análisis es sólido, seguro y operable. Las mitigaciones propuestas para P0.x resuelven los bloqueos críticos. Las respuestas a Q1-Q7 abajo consolidan decisiones para ADR-044.

---

## 🔍 RESPUESTAS A PREGUNTAS DEL CONSEJO

### **Q1 — Vault RNG vs entropy externa: ¿suficiente `sys/tools/random`?**

**Respuesta corta**: ✅ **Sí, es suficiente para producción FEDER**.

**Fundamentación técnica**:
| Estándar | Requisito | Vault cumple |
|----------|-----------|-------------|
| **NIST SP 800-90A** | DRBG con seed de entropy ≥256 bits | ✅ Vault usa `getrandom()` + `/dev/urandom` + CPU RDRAND si disponible |
| **NIST SP 800-90B/C** | Entropy source validation (solo para FIPS) | ⚠️ Vault no es FIPS-certified por defecto, pero FEDER no requiere FIPS |
| **libsodium** | `randombytes_buf()` → `/dev/urandom` o `getrandom()` | ✅ Compatible con output de Vault |

**Recomendación operativa**:
```bash
# En provision_crypto.sh, verificar que Vault tiene acceso a entropy del host:
vault status | grep -q "initialized" || exit 1
# Opcional: mezclar entropy externa si hay paranoia extrema:
external_entropy=$(head -c 32 /dev/urandom | base64)
vault write sys/tools/random bytes=32 | jq -r ".data.value" | \
  openssl sha256 -binary -hmac "$external_entropy" | xxd -p
```
**Conclusión**: No es necesario mezclar entropy externa para FEDER. Documentar en ADR-044 que Vault RNG es la fuente única autorizada.

---

### **Q2 — Cache tmpfs: ¿viola TODO O NADA (ADR-020)?**

**Respuesta corta**: ✅ **No viola; es una extensión razonable del modelo de amenaza**.

**Análisis de modelo de amenaza**:
| Escenario | Cache tmpfs ayuda | Cache tmpfs perjudica |
|-----------|------------------|----------------------|
| Vault caído temporalmente (red, maintenance) | ✅ Componente sigue operativo | — |
| Reboot del nodo | ❌ tmpfs se borra → TODO O NADA se reactiva | ✅ Sin persistencia de secreto |
| Atacante con acceso root al nodo | ❌ Podría leer tmpfs | ❌ Pero ya tenía root: juego perdido |
| OOM killer + restart rápido | ✅ Evita downtime innecesario | — |

**Condición de seguridad para la cache**:
```cpp
// common/vault_client.cpp: cache policy
if (vault_unreachable) {
    if (tmpfs_cache.has_valid_seed(ttl_seconds: 3600)) {
        log_warn("Using cached seed; Vault unreachable");
        metrics.inc("crypto.cache_hit");
    } else {
        log_crit("Vault unreachable + cache empty → exit(1)");
        metrics.inc("crypto.cache_miss_fatal");
        exit(1); // TODO O NADA se mantiene
    }
}
```

**Recomendación**: TTL máximo 1 hora. Documentar en ADR-020 que "TODO O NADA aplica post-reboot o post-cache-expiry".

---

### **Q3 — etcd bootstrap: ¿huevo y gallina?**

**Respuesta corta**: ✅ **etcd-server es el único componente que arranca sin barrera etcd**.

**Flujo de arranque correcto**:
```
1. Vault → online (backend file, ya provisionado)
2. etcd-server → arranca, obtiene su seed DIRECTAMENTE de Vault (sin barrera)
3. etcd-server → registra "etcd_crypto_ready" en sí mismo (self-check)
4. Componentes (sniffer, ml-detector, etc.) → arrancan, obtienen seed de Vault
5. Componentes → registran "crypto_ready: component_id" en etcd
6. etcd → verifica ALL crypto_ready → broadcast "pipeline_open"
7. Componentes → reciben broadcast → abren ZeroMQ
```

**Implementación clave**:
```yaml
# etcd-server tiene flag especial en su config:
crypto:
  bypass_etcd_barrier: true  # solo para etcd-server
  vault_path: "argus/${ENV}/seeds/etcd"
```

**Justificación**: etcd es el coordinador; no puede coordinar su propio arranque. Su seed está custodiada por Vault; si Vault falla, etcd no arranca (TODO O NADA).

---

### **Q4 — Vault backend file en dev: ¿suficiente o need raft?**

**Respuesta corta**: ✅ **Backend `file` es suficiente para dev FEDER**.

**Trade-off analysis**:
| Backend | Dev | Prod | Razón |
|---------|-----|------|-------|
| `inmem` | ❌ Rompe EMECAS | ❌ Nunca | Sin persistencia |
| `file` | ✅ Simple, persiste, re-provisionable | ❌ Single-node SPOF | Dev prioriza simplicidad |
| `raft` (Vault HA) | ⚠️ Overkill, complejidad | ✅ Requerido | Prod prioriza disponibilidad |

**Recomendación FEDER**:
```yaml
# group_vars/all.yml
vault:
  dev:
    backend: "file"
    path: "/var/lib/vault/data"
    auto_unseal: true  # dev mode, no production
  prod:
    backend: "raft"
    ha_nodes: 3
    auto_unseal: "awskms"  # o transit, según infra
```

**Condición de cierre**: El playbook de dev debe incluir `vault operator init` + `vault operator unseal` automatizados con tokens de desarrollo (nunca en prod).

---

### **Q5 — Rotación coordinada: ¿cooldown vs atómica?**

**Respuesta corta**: 🎯 **Aplicar cooldown = grace_period para ChaCha20 seeds, igual que HMAC keys (ADR-004)**.

**Justificación**:
- ChaCha20-Poly1305 es un cifrado de flujo; no hay "handshake" como en TLS.
- Durante el cooldown, ambos componentes mantienen **dos claves concurrentes** (vieja + nueva).
- etcd coordina el rollout: `rotation_pending` → componente acepta ambas claves → `rotation_done` → componente descarta vieja.

**Flujo de rotación seguro**:
```
T0: etcd marca rotation_pending
T1: Jenkins genera nueva seed → Vault actualiza path
T2: Componentes reciben notificación → cargan nueva seed en memoria (mantienen vieja)
T3: etcd espera ACK de TODOS los componentes (timeout: 5 min)
T4: Si ACK completo → etcd marca rotation_done → componentes descartan vieja clave
T5: Si timeout → etcd marca rotation_rollback → componentes descartan nueva clave
```

**Blast radius mínimo**: Un componente comprometido durante rotación solo afecta a su familia de canal (ADR-021), no al pipeline completo.

---

### **Q6 — `provision_crypto.sh`: ¿stage separado o integrado en bootstrap?**

**Respuesta corta**: 🎯 **Stage separado en Jenkinsfile, pero con dependencia estricta en `make bootstrap`**.

**Ventajas del stage separado**:
- Visibilidad: fallo en crypto = fallo visible en UI de Jenkins, no enterrado en logs de bootstrap.
- Reintentabilidad: se puede re-ejecutar solo el stage crypto sin reprovisionar toda la VM.
- Auditoría: el stage crypto genera un artifact firmado con el hash de las seeds provisionadas.

**Implementación recomendada**:
```groovy
// Jenkinsfile
stage('Provision Crypto') {
    when { expression { env.CRYPTO_PROVISIONED != 'true' } }
    steps {
        sh 'scripts/jenkins/provision_crypto.sh'
        // Si éxito, marcar variable de entorno para saltar en futuros runs
        script { env.CRYPTO_PROVISIONED = 'true' }
        // Generar artifact de auditoría
        archiveArtifacts artifacts: 'crypto_audit.json', fingerprint: true
    }
    post {
        failure {
            // Limpieza: evitar estado inconsistente
            sh 'scripts/jenkins/cleanup_crypto.sh || true'
        }
    }
}

stage('Bootstrap') {
    dependsOn 'Provision Crypto'  // bootstrap no corre si crypto falló
    steps {
        sh 'make bootstrap'
    }
}
```

**Conclusión**: Stage separado con `dependsOn` garantiza atomicidad operacional sin sacrificar visibilidad.

---

### **Q7 — Seed families (ADR-021) en Vault: ¿paths por familia o por componente?**

**Respuesta corta**: 🎯 **Paths por familia (`argus/${ENV}/families/${family_id}`) para FEDER**.

**Justificación de seguridad**:
| Enfoque | Blast radius si componente comprometido | Complejidad operativa |
|---------|----------------------------------------|----------------------|
| Por componente | Compromiso de 1 componente = solo su seed | Baja |
| Por familia | Compromiso de 1 componente = toda su familia de canal | Media |

**Pero**: ADR-021 ya define familias como unidad de aislamiento criptográfico. Respetar ese modelo en Vault:
- Minimiza el blast radius a nivel de canal, no de componente.
- Facilita rotaciones parciales: se puede rotar `family_A` sin tocar `family_B`.
- Alinea la estructura de Vault con la arquitectura lógica del sistema.

**Estructura recomendada**:
```
argus/
├── dev/
│   ├── families/
│   │   ├── family_A/seed          # sniffer ↔ ml-detector
│   │   ├── family_B/seed          # ml-detector ↔ firewall
│   │   └── family_C/seed          # firewall ↔ external
│   └── components/
│       ├── etcd/seed              # solo para etcd-server (bypass barrier)
│       └── vault/audit_key        # clave de auditoría, no de canal
└── prod/ (misma estructura)
```

**Nota operativa**: Los componentes solo leen el path de su familia asignada en su JSON de config. No pueden listar otros paths (política Vault restrictiva).

---

## 📋 RESUMEN DE DECISIONES PARA ADR-044

| Pregunta | Decisión | Justificación clave |
|----------|----------|-------------------|
| Q1 | Vault RNG único | NIST SP 800-90A cumplido; FEDER no requiere FIPS |
| Q2 | Cache tmpfs con TTL 1h | Extiende TODO O NADA sin violarlo; tmpfs no persiste reboot |
| Q3 | etcd-server bypass barrier | Coordinador no puede coordinarse a sí mismo; Vault custodia su seed |
| Q4 | Backend file en dev | Suficiente para EMECAS; prod usará raft (separación dev/prod) |
| Q5 | Cooldown = grace_period | Alinea con ADR-004; permite rollout seguro sin downtime atómico |
| Q6 | Stage separado con dependsOn | Visibilidad + atomicidad operacional |
| Q7 | Paths por familia | Respeta ADR-021; minimiza blast radius a nivel de canal |

---

## 🚀 PRÓXIMOS PASOS (DAY 150)

1. **Actualizar ADR-013 PHASE 3** con arquitectura Vault + vault_client.
2. **Crear ADR-044** con las decisiones de tabla arriba.
3. **Implementar `provision_crypto.sh`** con:
    - Vault backend file
    - `vault write sys/tools/random`
    - Assert `seed_dev != seed_prod`
    - Estructura de paths por familia
4. **Escribir `common/vault_client.{h,cpp}`** con:
    - GET seed + deriva libsodium en memoria
    - Cache tmpfs con TTL 3600s
    - exit(1) si Vault KO + cache vacía
    - etcd register `crypto_ready`
5. **Actualizar Jenkinsfile** con stage separado + dependsOn.

---

> *"La criptografía no es un feature; es el suelo sobre el que camina la confianza. Este pipeline no solo distribuye claves: distribuye responsabilidad. Que cada seed sea un acto de soberanía, y cada rotación, un ritual de renovación."*

**¿Procedemos a crear ADR-044 y comenzar la implementación de `provision_crypto.sh`?** 🛡️🔐🧠