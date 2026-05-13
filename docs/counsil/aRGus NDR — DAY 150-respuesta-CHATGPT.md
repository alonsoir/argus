## Consejo de Sabios — Respuestas DAY 150

### Q1 — `#ifdef ARGUS_VAULT_ENABLED` vs dos binarios separados

La decisión actual (`ARGUS_VAULT_ENABLED`) es la correcta.

Para un sistema distribuido de alto rendimiento en C++ con fuerte acoplamiento operacional, mantener **un único árbol de código y un único binario lógico** reduce muchísimo:

* divergencia funcional,
* skew de comportamiento,
* deuda de QA,
* matrices CI explosivas,
* bugs “solo enterprise”,
* incompatibilidades ABI,
* y diferencias de timing difíciles de reproducir.

La clave no es evitar `#ifdef`. La clave es **dónde** se coloca.

El antipatrón peligroso es:

```cpp
#ifdef ARGUS_VAULT_ENABLED
   ...
#else
   ...
#endif
```

disperso por toda la codebase.

La solución correcta es:

```cpp
class ICryptoProvider {
public:
    virtual CryptoMaterial fetch() = 0;
};
```

y luego:

```cpp
using CryptoProvider =
#ifdef ARGUS_VAULT_ENABLED
    VaultClient;
#else
    SeedClient;
#endif
```

aislado en una factoría o capa bootstrap.

Es decir:

* `#ifdef` solo en wiring/bootstrap,
* nunca en lógica de negocio,
* nunca en hot paths,
* nunca en protocolos.

Eso evita la “divergencia silenciosa”.

La arquitectura ideal sería:

```text
core/
    crypto/
        interfaces/
        providers/
            seed/
            vault/
```

y el resto del pipeline desconoce qué provider existe.

Consejo importante:
aunque sea open-core, mantened:

* mismo protocolo,
* mismos formatos,
* mismas estructuras,
* mismas rutas de ejecución posteriores.

Solo debe cambiar:
“de dónde viene el seed”.

No debe cambiar:
“cómo funciona aRGus”.

---

### Q2 — Orden de migración

El orden propuesto es muy bueno, pero recomendamos un ajuste:

## Orden recomendado real

### 1. `etcd-server`

Correcto. Es el root-of-trust bootstrap.

---

### 2. `ml-detector`

Antes que `sniffer`.

Razón:
el `ml-detector` normalmente tiene menos dependencia temporal crítica y menor presión de throughput bruto.

Sirve como:

* validación temprana del provider crypto,
* validación de cache,
* validación de lease,
* validación de recovery,
* validación de rotación.

Con menor riesgo operacional.

---

### 3. `sniffer`

El sniffer es el componente más sensible:

* latencia,
* NUMA,
* page faults,
* allocations,
* stalls,
* syscall pressure,
* cache locality.

Cualquier bug de Vault/cache/jitter puede introducir:

* packet drops,
* microbursts,
* head-of-line blocking.

Migrarlo después reduce riesgo.

---

### 4. `firewall-acl-agent`

Correcto después del detector.

Porque:

* ya depende de decisiones ML,
* actúa downstream,
* tolera mejor reinicios breves.

---

### 5. `rag-ingester`

---

### 6. `rag-security`

Correcto al final.
Son componentes menos críticos temporalmente.

---

## Orden final sugerido

```text
1. etcd-server
2. ml-detector
3. sniffer
4. firewall-acl-agent
5. rag-ingester
6. rag-security
```

---

### Q3 — `register_etcd_status()` cuando etcd aún no existe

Sí.
La solución correcta es exactamente esa:
estado local bootstrap-first.

`etcd-server` no puede depender circularmente de sí mismo.

La regla arquitectónica clásica:

> “El bootstrap root no puede requerir el sistema que todavía está creando.”

La solución elegante es:

```text
/run/argus/bootstrap/
    etcd-crypto-status.json
```

o incluso:

```text
/run/argus/bootstrap/etcd/
```

con:

* ownership estricto,
* 0700,
* lifecycle efímero,
* formato minimalista.

Ejemplo:

```json
{
  "status": "READY",
  "fingerprint": "...",
  "lease_active": true,
  "vault_source": "CACHE"
}
```

Luego:

* `etcd-server` publica en local,
* una vez etcd está READY,
* sincroniza ese estado a etcd,
* el resto de componentes usa etcd normalmente.

Eso evita:

* deadlocks bootstrap,
* dependencia circular,
* race conditions tempranas.

Muy importante:
NO intentéis resolver esto con sleeps/retries mágicos.

Eso degenera rápido en “distributed folklore”.

---

### Q4 — tmpfs vs cache persistente

Aquí hay una distinción crítica entre:

* confidentiality,
* availability.

La decisión actual maximiza confidentiality.
Pero un edge node real necesita availability.

La recomendación del Consejo:

## DEV / CI / EMECAS

```text
/run/argus/crypto-cache/
```

tmpfs.

Correcto.

---

## Producción Edge

Persistente cifrado y endurecido.

Pero NO en:

```text
/etc/
```

porque `/etc` implica configuración estática.

Mejor:

```text
/var/lib/argus/crypto-cache/
```

o:

```text
/var/cache/argus/crypto/
```

con:

* 0700,
* owner dedicado,
* fsync controlado,
* SELinux/AppArmor labels,
* rotación TTL,
* invalidación explícita.

Idealmente:

* encrypted filesystem,
* TPM sealing,
* o LUKS-backed storage.

Porque el problema real es:

> “¿Puede un nodo edge sobrevivir a una pérdida temporal de Vault?”

Y la respuesta operativa debe ser:
sí.

Especialmente:

* entornos industriales,
* OT,
* edge remoto,
* nodos embarcados,
* despliegues tácticos.

La disponibilidad local temporal es más importante que pureza criptográfica absoluta.

---

### Q5 — ¿Es suficiente `ARGUS_VAULT_ENABLED`?

Sí… y no.

Para la primera versión:
sí.
Es un separador excelente porque es:

* claro,
* justificable,
* técnicamente coherente,
* no rompe interoperabilidad.

El error típico del open-core es esconder features arbitrarias.
Vosotros habéis separado:
“governance criptográfico”.
Eso es defendible.

---

## Qué NO debería ir enterprise

NO escondería detrás del flag:

* detección ML,
* graph analysis,
* Neo4j,
* honeypots,
* Falco actuation,
* correlación,
* pipelines,
* datasets.

Porque entonces el producto deja de parecer:
“infraestructura seria”
y empieza a parecer:
“crippleware”.

---

## Qué SÍ encaja como enterprise

Sí encajan:

### Governance

* Vault integration
* HSM support
* TPM sealing
* rotation orchestration
* PKI federation
* multi-tenant crypto
* RBAC crypto
* audit trails

### Fleet / Enterprise Ops

* centralized policy management
* remote orchestration
* fleet observability
* HA control plane
* compliance exports
* SOC integrations

### Advanced HA

* geo-federated etcd
* DR orchestration
* quorum analytics

---

## Recomendación estratégica importante

Mantener:

```text
Community = técnicamente útil y respetable
Enterprise = governance, escala y compliance
```

Ese modelo suele sobrevivir mucho mejor a largo plazo en infra/security OSS.
