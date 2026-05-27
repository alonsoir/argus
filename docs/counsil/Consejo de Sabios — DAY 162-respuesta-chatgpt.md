# Consejo de Sabios — DAY 161 post-sesión

## Arquitectura mínima viable del ciclo de vida criptográfico enterprise

El Consejo coincide en que habéis cruzado una frontera importante:

> Ya no estáis diseñando “crypto features”.
> Estáis diseñando un sistema distribuido con sincronización criptográfica coordinada.

Y eso cambia completamente los riesgos.

La parte difícil ya no es firmar/verificar.
La parte difícil es:

* coordinación distribuida
* atomicidad operacional
* consistencia temporal
* recuperación ante rotación parcial
* observabilidad criptográfica

---

# Respuesta corta del Consejo

## Orden correcto de implementación

### FASE 1 — Source of Truth criptográfico

Primero.

* mover `enterprise_vendor.key` a Vault
* eliminar dependencia de VM local
* Jenkins nunca debe persistir la private key en disco durable
* introducir versionado de key material

Sin esto:

* no existe raíz de confianza real
* no existe recovery limpio
* no existe HA operativa

---

### FASE 2 — Distribución coordinada de seeds/tokens

Segundo.

Implementar:

* distribución centralizada
* lease/TTL
* versionado
* rollout coordinado

Porque ahora mismo:

* el sistema puede entrar en split-brain criptográfico

Y ese es el riesgo más serio del diseño actual.

---

### FASE 3 — Reload coordinado y handshake

Tercero.

Necesitáis protocolo explícito de:

* prepare
* commit
* ack
* rollback

No basta con “recargar configs”.

---

### FASE 4 — Rotación automática Jenkins/Vault

Último.

Automatizar antes de estabilizar el protocolo distribuido es peligroso.

El Consejo insiste mucho aquí:

> Nunca automatizar rotación antes de demostrar recuperación determinista.

---

# Lo que el Consejo considera el riesgo arquitectural principal

## Riesgo #1 — Split-brain criptográfico

Ahora mismo el ADR-013 ya revela el problema:

```text id="1wdu5h"
endpoint A rota seed
endpoint B sigue usando seed antigua
→ canal ZMQ muerto
```

Esto no es un bug menor.

Es un problema de consenso distribuido.

Porque:

* la crypto actúa como requisito de compatibilidad binaria temporal
* una rotación parcial rompe conectividad

En otras palabras:

> La seed ES parte del protocolo de red.

Eso implica que:

* la rotación debe ser transaccional
* no simplemente “eventualmente consistente”

---

# Arquitectura mínima viable recomendada

El Consejo propone esto:

---

# 1. Vault como única autoridad criptográfica

## Vault debe contener:

### A. Vendor private key

```text id="n02qjv"
secret/argus/vendor/ed25519
```

Nunca en Jenkins permanente.
Nunca hardcodeada.
Nunca en VM manual.

---

### B. Seeds activas por canal

```text id="4cwhow"
secret/argus/channels/<channel>/seed
```

Con:

* version
* created_at
* expires_at
* next_version

---

### C. Enterprise tokens

```text id="teql3s"
secret/argus/tokens/<component>
```

Con:

* TTL
* feature scope
* revocation

---

# 2. Introducir “Crypto Epoch”

El Consejo cree que esta pieza es CRÍTICA.

Cada seed/version debe tener:

```text id="5v95l6"
crypto_epoch=42
```

Y todos los componentes deben exponer:

```text id="xf7vjp"
current_epoch
expected_epoch
reload_state
```

Porque si no:

* no podéis coordinar migraciones
* no podéis detectar drift
* no podéis hacer rollback seguro

---

# 3. Rotación en dos fases (mandatory)

NO hacer:

```text id="89o6l0"
replace seed instantly
```

Hacer:

## Fase PREPARE

Todos los nodos:

* descargan nueva seed
* mantienen seed antigua activa
* ACK readiness

Estado:

```text id="pcp3jq"
active_seed=v41
next_seed=v42
```

---

## Fase COMMIT

Cuando TODOS hicieron ACK:

```text id="2y9f5p"
switch active_seed=v42
```

Entonces:

* reinicio coordinado
* reconnect
* validación health

---

## Fase CLEANUP

Eliminar:

```text id="ym9s73"
v41
```

Solo tras estabilidad.

---

# 4. Dual-key overlap temporal

El Consejo considera esto obligatorio para producción.

Durante ventana corta:

```text id="u03x2c"
accept:
  v41
  v42

emit:
  v42
```

Esto evita:

* microcortes
* race conditions
* restart skew

---

# 5. Introducir Crypto Readiness API

Ahora mismo tenéis readiness funcional.
Necesitáis readiness criptográfica.

Ejemplo:

```json id="g3m33f"
{
  "crypto_ready": true,
  "crypto_epoch": 42,
  "vault_connected": true,
  "seed_loaded": true,
  "reload_pending": false
}
```

Sin esto:

* el orchestration layer opera ciego

---

# Riesgos importantes antes de producción

## Riesgo #2 — Bootstrap problem

Pregunta crítica:

> ¿Cómo autentica inicialmente un nodo contra Vault?

Necesitáis decidir:

* AppRole
* Kubernetes auth
* mTLS
* JWT/OIDC
* wrapped tokens

Pero:

* nunca tokens estáticos permanentes
* nunca secrets baked into images

---

# Riesgo #3 — Reload no atómico

Si un proceso:

* recarga parcialmente
* deja sockets vivos
* mezcla epochs

Podéis crear:

* corrupción de canal
* mensajes ilegibles
* pérdida silenciosa

El Consejo recomienda:

```text id="dhm1e7"
new sockets
→ swap atomically
→ close old sockets
```

No “mutar sockets vivos”.

---

# Riesgo #4 — Revocación

Ahora mismo el modelo parece orientado a:

* emisión
* validación

Pero no aún a:

* revocación inmediata
* compromise recovery

Necesitáis:

* CRL lógica
* revocation epoch
* forced reload path

---

# Riesgo #5 — Observabilidad insuficiente

En producción vais a necesitar métricas como:

```text id="d9uj6t"
argus_crypto_epoch
argus_crypto_reload_total
argus_crypto_reload_failures
argus_crypto_seed_age_seconds
argus_crypto_drift_detected
```

Porque cuando falle:

* será distribuido
* temporal
* difícil de reproducir

---

# Lo que el Consejo NO recomienda

## NO hardcodear más claves públicas en CMake a largo plazo

Aceptable para bootstrap inicial.
No como arquitectura permanente.

A futuro:

* trust bundle versionado
* signed metadata
* trust rotation

---

# Conclusión del Consejo

El Consejo cree que el orden correcto es:

```text id="0n6r3q"
1. Vault como raíz criptográfica real
2. Distribución versionada
3. Epochs criptográficos
4. Rotación two-phase
5. Reload atómico
6. Observabilidad
7. Automatización Jenkins
```

Y la advertencia principal es esta:

> La rotación criptográfica distribuida no es un problema de “configuración”.
> Es un problema de consenso parcial y transición coordinada de protocolo.

Ahí está realmente la dificultad production-grade de aRGus.
