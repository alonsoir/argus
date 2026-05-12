# CONSEJO DE SABIOS — RESPUESTA DAY 149

## Arquitectura CI/CD Criptográfica — Jenkins + Vault + `common/vault_client`

---

# Veredicto general

El Consejo considera que la arquitectura ha cruzado un umbral importante:

> ya no estáis diseñando “crypto para un pipeline”, sino un sistema distribuido con raíz de confianza operacional explícita.

La decisión más importante del DAY 149 es esta:

> ZeroMQ no abre hasta que la criptografía esté validada y coordinada.

Eso convierte la criptografía en:

* prerequisito de topología
* no feature opcional

Arquitectónicamente, es correcto.

---

# Q1 — Vault RNG vs entropy externa

## Veredicto

### Sí: `vault write sys/tools/random bytes=32` es suficiente para FEDER.

Vault ya usa:

* CSPRNG del kernel
* DRBG interno
* entropy pool del SO

Eso ya cae dentro del modelo NIST SP 800-90A razonable para vuestro caso.

---

## Lo importante

El problema NO es:

> “¿es suficientemente aleatorio?”

El problema real es:

> “¿quién controla el proceso de generación?”

Y ahí la arquitectura actual mejora muchísimo:

* Jenkins orquesta
* Vault genera
* Jenkins no conoce la seed completa

---

## Recomendación del consejo

### NO mezclar entropy manualmente en FEDER.

Porque:

* aumentas complejidad
* empeoras auditabilidad
* introduces riesgos de implementación

---

## Recomendación futura (post-FEDER)

Opcional:

* TPM-backed entropy
* HSM
* Vault auto-unseal con KMS/HSM

Pero NO ahora.

---

# Q2 — Cache tmpfs vs TODO O NADA

## Veredicto

### No viola ADR-020.

Porque:

* tmpfs no persiste reboot
* no rompe el modelo de confianza
* solo extiende disponibilidad operacional

El principio real no es:

> “siempre consultar Vault”

El principio es:

> “nunca operar sin material criptográfico válido”.

La cache tmpfs sigue cumpliendo eso.

---

## Modelo de amenaza real

El vector no es tmpfs.

El vector real sería:

* proceso comprometido con lectura memoria
* root local
* dump RAM

Pero en ese escenario:

> el atacante ya ganó.

---

## Recomendación concreta

### Cache:

* tmpfs
* `mlock()`
* TTL corto
* wipe explícito
* nunca swap
* nunca persistencia

---

## Recomendación importante

No cachear:

* seeds raíz

Sí cachear:

* material derivado efímero

Eso reduce blast radius brutalmente.

---

# Q3 — etcd barrera pre-arranque (huevo/gallina)

## Veredicto

Correcto:

> etcd es excepción bootstrap.

---

## Modelo recomendado

### Bootstrap chain:

```text
Vault
  ↓
etcd-server
  ↓
crypto_ready(etcd)
  ↓
resto componentes
```

---

## Principio importante

etcd no participa en la barrera inicial.

Porque:

* la barrera depende de etcd
* etcd es parte del trusted substrate

---

## Recomendación crítica

### etcd debe tener:

* identity fija
* bootstrap credential separada
* NO derivada dinámicamente en runtime

Si etcd depende completamente de Vault runtime:
→ podéis crear deadlocks de recuperación.

---

# Q4 — Vault backend file en dev

## Veredicto

### Sí, suficiente para dev/FEDER.

No intentéis introducir Vault HA ahora.

Porque:

* multiplicáis complejidad operacional
* introducís más moving parts
* desviáis foco del pipeline NDR

---

## Consejo importante

FEDER necesita:

* reproducibilidad
* estabilidad
* demo fiable

NO:

* infraestructura cloud-grade completa

---

## Recomendación

### DEV:

* backend file
* snapshots automáticos
* restore probado

### PRE-PROD/PROD:

* raft integrated storage
* HA

---

# Q5 — Rotación coordinada

## Veredicto

### NO hagáis rotación atómica global.

Eso:

* aumenta blast radius
* aumenta downtime
* aumenta riesgo operacional

---

## Modelo correcto

### Dual-valid window (igual que ADR-004)

Durante ventana temporal:

* old key válida
* new key válida

---

## Importante

La rotación NO debe:

* renegociar todo el pipeline simultáneamente

Debe:

* drenar
* rollover
* confirmar
* avanzar componente a componente

---

## Recomendación operacional

```text
phase 1:
  distribute new material

phase 2:
  enable dual accept

phase 3:
  rotate sender

phase 4:
  rotate receivers

phase 5:
  revoke old
```

Eso es muchísimo más seguro.

---

# Q6 — `provision_crypto.sh`

## Veredicto

### Stage separado en Jenkinsfile.

Y además:

### dependency explícita de bootstrap.

Las dos cosas.

---

## Por qué

### Stage separado:

* auditabilidad
* visibilidad
* troubleshooting
* rollback claro

### Dependency bootstrap:

* garantiza invariantes

---

## Pipeline recomendado

```text
Provision Crypto
    ↓
Validate Crypto
    ↓
Bootstrap
    ↓
Deploy
    ↓
Integration Tests
```

---

# Q7 — Seed families vs componente

## Veredicto fuerte del consejo

### Por familia.

No por componente.

---

## Razón

Las familias representan:

* boundary criptográfico real
* trust domain
* canal operacional

---

## Ventajas enormes

### Blast radius menor

Compromiso:

* sniffer

NO implica:

* firewall-agent
* etcd
* RAG

---

## Arquitectura correcta

```text
argus/dev/families/family_A
argus/dev/families/family_B
argus/dev/families/family_C
```

Y luego:

* derivación HKDF por componente

---

## Recomendación MUY importante

No almacenar:

* 50 seeds distintas

Almacenar:

* pocas raíces de familia
* derivar runtime

Eso:

* simplifica rotación
* simplifica auditoría
* simplifica recovery

---

# Observación arquitectónica más importante del consejo

La arquitectura está evolucionando hacia:

> control-plane criptográfico distribuido

y no simplemente:

> componentes con crypto.

Eso tiene consecuencias importantes:

* bootstrap
* recuperación
* quorum
* rotación
* trust domains

---

# Preguntas adicionales del consejo

## 🔴 AQ1 — ¿Qué ocurre si Vault responde lento pero no caído?

¿Timeouts?
¿Backoff?
¿Circuit breaker?

Porque:

* “slow Vault”
  puede ser peor que:
* “Vault caído”.

---

## 🔴 AQ2 — ¿Cómo evitáis stampede al reiniciar 50 componentes?

Si todos hacen:

```text
GET seed
```

simultáneamente:

* podéis autodosificar Vault.

Necesitáis:

* jitter
* stagger
* exponential backoff

---

## 🔴 AQ3 — ¿Cómo auditáis derivación criptográfica?

Necesitáis:

* fingerprint
* key version
* derivation metadata

NO:

* logs sensibles.

---

## 🔴 AQ4 — ¿Qué ocurre si un componente queda “crypto_ready” pero jamás abre ZeroMQ?

etcd necesita:

* heartbeat posterior
* no solo readiness inicial.

---

# Conclusión final del Consejo

El diseño post-DAY149 ya tiene características de:

* service mesh criptográfico
* trusted bootstrap chain
* distributed trust orchestration

La dirección es correcta.

El mayor riesgo ya no es criptográfico.

Ahora el mayor riesgo es:

> complejidad operacional emergente.

Y eso, sinceramente, es una muy buena señal arquitectónica.
